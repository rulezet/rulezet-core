"""feed_core.py — the rule feeds Rulezet serves to tools (setting feeds.outbound): every active
rule of a format, written the way the tool loads it (a .yar file, a .rules file, multi-document
Sigma YAML, else JSON lines), filtered (since, tag, source), without the rules whose tags say they
must not be shared (TLP:RED / AMBER). Read through GET /api/feed/<format> with a free account's
API key (app/api/feed/feed_api.py); the page /feeds explains it."""
import datetime
import hashlib
import json

from sqlalchemy import func

from app import db
from app.core.db_class.rule import Rule
from app.core.db_class.tag import RuleTagAssociation, Tag
from app.core.utils.app_settings import get_setting
from app.features.rule.rule_core import _active


def _conf():
    return get_setting('feeds.outbound') or {}


def feed_formats():
    """[{format, label, style, ext, icon}] offered by the setting."""
    return [f for f in (_conf().get('formats') or []) if isinstance(f, dict) and f.get('format')]


def _query(fmt, since=None, tag=None, source=None):
    q = _active().filter(func.lower(Rule.format) == fmt.lower())
    excluded = [t.lower() for t in (_conf().get('excluded_tags') or [])]
    if excluded:
        hidden = db.session.query(RuleTagAssociation.rule_id).join(Tag, Tag.id == RuleTagAssociation.tag_id) \
            .filter(func.lower(Tag.name).in_(excluded))
        q = q.filter(~Rule.id.in_(hidden))
    if since:
        q = q.filter(func.coalesce(Rule.last_modif, Rule.creation_date) >= since)
    if tag:
        tagged = db.session.query(RuleTagAssociation.rule_id).join(Tag, Tag.id == RuleTagAssociation.tag_id) \
            .filter(func.lower(Tag.name) == tag.lower())
        q = q.filter(Rule.id.in_(tagged))
    if source:
        q = q.filter(Rule.source.ilike(f'%{source}%'))
    return q


_SUMMARY = {'at': 0.0, 'key': None, 'value': None}
SUMMARY_TTL = 600            # counting every rule (and the TLP exclusion) is slow on a big instance


def summary():
    """Each offered format with its number of rules (shown on /feeds), cached SUMMARY_TTL seconds."""
    import time
    formats = feed_formats()
    key = json.dumps([formats, _conf().get('excluded_tags')], sort_keys=True)
    if _SUMMARY['value'] is not None and _SUMMARY['key'] == key and time.monotonic() - _SUMMARY['at'] < SUMMARY_TTL:
        return _SUMMARY['value']
    value = [{**f, 'count': _query(f['format']).count()} for f in formats]
    _SUMMARY.update(at=time.monotonic(), key=key, value=value)
    return value


def _parse_since(value):
    if not value:
        return None
    for pattern in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.datetime.strptime(value, pattern)
        except ValueError:
            continue
    raise ValueError('since must be a date: YYYY-MM-DD (or YYYY-MM-DDTHH:MM:SS)')


def _header_lines(rule, base_url):
    return [f'Rulezet: {base_url}/rule/detail_rule/{rule.id}',
            f'Title: {rule.title}', f'Author: {rule.author or "unknown"} | License: {rule.license or "unknown"}',
            *([f'Source: {rule.source}'] if rule.source else [])]


def build(fmt, base_url, since=None, tag=None, source=None, as_json=False):
    """(body, mimetype, filename, etag, count) of one feed. Raises ValueError on a bad filter."""
    conf = _conf()
    spec = next((f for f in feed_formats() if f['format'].lower() == fmt.lower()), None)
    if not spec:
        raise LookupError(fmt)
    q = _query(fmt, _parse_since(since), tag, source).order_by(func.coalesce(Rule.last_modif, Rule.creation_date).desc())
    rules = q.limit(int(conf.get('max_rules') or 100000)).all()
    if conf.get('dedupe', True):
        seen, kept = set(), []
        for r in rules:                       # newest first: the first of an identifier wins
            ident = (r.corpus_identifier or '').strip()
            if ident and ident in seen:
                continue
            seen.add(ident)
            kept.append(r)
        rules = kept
    style = 'json' if as_json else spec.get('style', 'json')
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    banner = [f'Rulezet {spec.get("label", fmt)} feed — {len(rules)} rules — {now}', f'{base_url}/feeds',
              'Each rule keeps its own licence (see above it).']
    if style == 'yara':
        parts = ['\n'.join(f'// {l}' for l in banner)]
        for r in rules:
            parts.append('\n'.join(f'// {l}' for l in _header_lines(r, base_url)) + '\n' + (r.to_string or '').strip())
        body, mime = '\n\n'.join(parts) + '\n', 'text/plain'
    elif style == 'lines':
        lines = [f'# {l}' for l in banner]
        for r in rules:
            lines.append(f'# {r.title} | {r.license or "unknown"} | {base_url}/rule/detail_rule/{r.id}')
            lines.extend(l for l in (r.to_string or '').strip().splitlines() if l.strip())
        body, mime = '\n'.join(lines) + '\n', 'text/plain'
    elif style == 'yaml':
        docs = ['\n'.join(f'# {l}' for l in banner)]
        for r in rules:
            docs.append('\n'.join(f'# {l}' for l in _header_lines(r, base_url)) + '\n' + (r.to_string or '').strip())
        body, mime = '\n---\n'.join(docs) + '\n', 'application/yaml'
    else:
        rows = [json.dumps({'id': r.id, 'uuid': r.uuid, 'title': r.title, 'format': r.format, 'author': r.author,
                            'license': r.license, 'source': r.source, 'url': f'{base_url}/rule/detail_rule/{r.id}',
                            'updated': (r.last_modif or r.creation_date).isoformat() if (r.last_modif or r.creation_date) else None,
                            'content': r.to_string}, ensure_ascii=False) for r in rules]
        body, mime = '\n'.join(rows) + ('\n' if rows else ''), 'application/x-ndjson'
    ext = 'jsonl' if style == 'json' else spec.get('ext', 'txt')
    etag = hashlib.sha1(f'{fmt}|{since}|{tag}|{source}|{style}|{len(rules)}|'
                        f'{max(((r.last_modif or r.creation_date) for r in rules), default="")}'.encode()).hexdigest()
    return body, mime, f'rulezet_{fmt}.{ext}', etag, len(rules)
