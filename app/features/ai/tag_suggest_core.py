"""
tag_suggest_core.py — fast tag candidates for a rule (6th AI integration).

Step 1, no AI, a few milliseconds: a token trie built once in memory from the
tags of the families listed in the setting `ai.tag_suggest` (taxonomy /
galaxy namespaces worth matching on a detection rule) plus the tags already
in real use. Each tag gives its terms — the value of its name
(`misp-galaxy:tool="Mimikatz"` -> "mimikatz"), its galaxy synonyms, the
ATT&CK id in its name — and the rule's text is walked through the trie.
Matches are scored by rarity (a term shared by 200 tags is worth little),
length (multi-word phrases beat single words) and where they were found (the
title counts double).

Step 2 (tag_suggest_agent.py) hands only these candidates to the model,
which picks and explains; anything it names outside the list is dropped.

The trie is rebuilt when the tag table or the setting changes (checked at
most every CHECK_EVERY_S seconds per worker).
"""
import re
import threading
import time
from collections import Counter, defaultdict

from sqlalchemy import func

from app import db
from app.core.db_class.tag import RuleTagAssociation, Tag
from app.core.utils.app_settings import get_setting

CHECK_EVERY_S = 60
MAX_PHRASE_TOKENS = 6
MAX_TEXT_CHARS = 30000
_END = '\0'  # trie node key holding the tag ids ending there

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
_ATTACK_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.I)

_lock = threading.Lock()
_index = {'stamp': None, 'checked': 0.0, 'trie': {}, 'term_tags': {}, 'tags': {}, 'generic': {}}

# Tag.source values per switch of the setting's `sources`. Anything that is
# not a taxonomy, a galaxy or an import (Manual, Connector, NULL, …) is
# "custom": tags people created on this instance or received from another.
SOURCES = ('taxonomy', 'galaxy', 'imported', 'custom')
_SOURCE_OF = {'Taxonomy': 'taxonomy', 'Galaxy': 'galaxy', 'Imported': 'imported'}
GENERIC_SCORE = 1.0          # a tag every rule of the format gets
SIGNAL_SCORE = 1.6           # a tag a signal of the format found in the rule
MAX_AI_GENERIC = 10          # generic tags always handed to the model, besides the top matches


def source_kind(source):
    return _SOURCE_OF.get(source or '', 'custom')


def _settings():
    value = get_setting('ai.tag_suggest') or {}
    value = dict(value) if isinstance(value, dict) else {}
    return {
        'families': set(value.get('families') or []),
        'include_used_min_rules': int(value.get('include_used_min_rules') or 0),
        'exclude_prefixes': tuple(p.lower() for p in (value.get('exclude_prefixes') or [])),
        'min_term_length': int(value.get('min_term_length') or 4),
        'stopwords': {s.lower() for s in (value.get('stopwords') or [])},
        'max_candidates': int(value.get('max_candidates') or 40),
        'max_ai_suggestions': int(value.get('max_ai_suggestions') or 10),
        'simulate_ai': bool(value.get('simulate_ai')),
        'sources': {k: bool((value.get('sources') or {}).get(k, k != 'custom')) for k in SOURCES},
    }


def format_contexts():
    """Setting ai.tag_suggest_formats: {format: {context, tags, signals}},
    regexes compiled once per value (cached on the JSON text)."""
    import json
    value = get_setting('ai.tag_suggest_formats') or {}
    value = json.loads(json.dumps(value, default=dict))
    key = json.dumps(value, sort_keys=True)
    if _formats_cache.get('key') != key:
        compiled = {}
        for fmt, conf in value.items():
            if not isinstance(conf, dict):
                continue
            signals = []
            for s in conf.get('signals') or []:
                try:
                    signals.append({'label': s.get('label') or '', 'tags': list(s.get('tags') or []),
                                    're': re.compile(s.get('pattern') or '(?!)', re.I)})
                except re.error as e:
                    print(f"[tag_suggest] bad signal regex for {fmt} / {s.get('label')}: {e}")
            compiled[fmt.lower()] = {'context': conf.get('context') or '', 'tags': list(conf.get('tags') or []),
                                     'signals': signals}
        _formats_cache.update(key=key, value=compiled)
    return _formats_cache['value']


_formats_cache = {}


def format_context(fmt):
    return format_contexts().get((fmt or '').lower().strip())


def tokenize(text):
    return _TOKEN_RE.findall((text or '').lower())


def _tag_terms(tag, min_len, stopwords):
    """The phrases (token tuples) a tag is found by."""
    name = tag.name or ''
    raw = []
    # misp-galaxy:tool="Mimikatz" / ms-caro-malware:malware-type="Trojan" / tlp:clear / plain
    m = re.search(r'="([^"]+)"', name)
    if m:
        raw.append(m.group(1))
    elif ':' in name:
        raw.append(name.split(':', 1)[1])
    else:
        raw.append(name.replace('_', ' '))
    meta = tag.galaxy_meta if isinstance(tag.galaxy_meta, dict) else {}
    for syn in (meta.get('synonyms') or [])[:30]:
        if isinstance(syn, str):
            raw.append(syn)
    terms = set()
    for value in raw:
        # "Command and Scripting Interpreter - T1059" -> both halves
        for part in re.split(r"\s+-\s+", value):
            toks = tuple(tokenize(part))
            if not toks or len(toks) > MAX_PHRASE_TOKENS:
                continue
            if len(toks) == 1:
                t = toks[0]
                if len(t) < min_len or t in stopwords or t.isdigit():
                    continue
            terms.add(toks)
    for tid in _ATTACK_ID_RE.findall(name):
        terms.add((tid.lower(),))
    return terms


def _stamp(cfg):
    count, last = db.session.query(func.count(Tag.id), func.max(Tag.updated_at)).one()
    generic_names = sorted({n for c in format_contexts().values()
                            for n in c['tags'] + [t for s in c['signals'] for t in s['tags']]})
    return (count, str(last), hash(repr(sorted(cfg['families']))), cfg['include_used_min_rules'],
            cfg['min_term_length'], hash(repr(sorted(cfg['stopwords']))), cfg['exclude_prefixes'],
            tuple(sorted(cfg['sources'].items())), hash(repr(generic_names)))


def _tag_dict(tag):
    return {'id': tag.id, 'name': tag.name, 'description': (tag.description or '')[:300],
            'namespace': tag.namespace, 'color': tag.color, 'icon': tag.icon, 'source': tag.source}


def _source_condition(cfg):
    """SQL filter for the tags the trie is built from, per the `sources`
    switches: taxonomies / galaxies of the listed families; imported / custom
    tags used on at least include_used_min_rules rules (0 = all of them)."""
    on = cfg['sources']
    conds = []
    kinds = [s for s, k in (('Taxonomy', 'taxonomy'), ('Galaxy', 'galaxy')) if on[k]]
    if kinds:
        c = Tag.source.in_(kinds)
        conds.append(c & Tag.namespace.in_(cfg['families']) if cfg['families'] else c)
    used = None
    if cfg['include_used_min_rules'] > 0 and (on['imported'] or on['custom']):
        used = (db.session.query(RuleTagAssociation.tag_id).group_by(RuleTagAssociation.tag_id)
                .having(func.count(RuleTagAssociation.rule_id) >= cfg['include_used_min_rules']))
    for kind, c in (('imported', Tag.source == 'Imported'),
                    ('custom', Tag.source.is_(None) | Tag.source.notin_(('Taxonomy', 'Galaxy', 'Imported')))):
        if on[kind]:
            conds.append(c & Tag.id.in_(used) if used is not None else c)
    if not conds:
        return None
    cond = conds[0]
    for c in conds[1:]:
        cond = cond | c
    return cond


def _excluded(cfg, name):
    return bool(cfg['exclude_prefixes']) and (name or '').lower().startswith(cfg['exclude_prefixes'])


def _build_generic(cfg):
    """The generic tags named by the format contexts, by name — looked up
    whatever their family (an admin chose them on purpose), but still active,
    not excluded and of an enabled source."""
    names = {n for c in format_contexts().values() for n in c['tags'] + [t for s in c['signals'] for t in s['tags']]}
    if not names:
        return {}
    out = {}
    for tag in Tag.query.filter(Tag.name.in_(names), Tag.is_active.is_(True)).with_entities(
            Tag.id, Tag.name, Tag.description, Tag.namespace, Tag.color, Tag.icon, Tag.source):
        if not _excluded(cfg, tag.name) and cfg['sources'][source_kind(tag.source)]:
            out[tag.name] = _tag_dict(tag)
    return out


def _build(cfg):
    cond = _source_condition(cfg)
    if cond is None:
        return {}, {}, {}
    trie, term_tags, tags = {}, defaultdict(set), {}
    q = Tag.query.filter(Tag.is_active.is_(True))
    for tag in q.filter(cond).with_entities(Tag.id, Tag.name, Tag.description, Tag.namespace,
                                            Tag.galaxy_meta, Tag.color, Tag.icon, Tag.source).yield_per(2000):
        if _excluded(cfg, tag.name):
            continue
        terms = _tag_terms(tag, cfg['min_term_length'], cfg['stopwords'])
        if not terms:
            continue
        tags[tag.id] = _tag_dict(tag)
        for toks in terms:
            node = trie
            for t in toks:
                node = node.setdefault(t, {})
            node.setdefault(_END, set()).add(tag.id)
            term_tags[toks].add(tag.id)
    return trie, {k: len(v) for k, v in term_tags.items()}, tags


def get_index():
    """The live trie, rebuilt when tags or the setting changed."""
    now = time.monotonic()
    if _index['stamp'] is not None and now - _index['checked'] < CHECK_EVERY_S:
        return _index
    with _lock:
        if _index['stamp'] is not None and now - _index['checked'] < CHECK_EVERY_S:
            return _index
        cfg = _settings()
        stamp = _stamp(cfg)
        if stamp != _index['stamp']:
            trie, term_df, tags = _build(cfg)
            _index.update(trie=trie, term_tags=term_df, tags=tags, generic=_build_generic(cfg), stamp=stamp)
        _index['checked'] = now
    return _index


def _walk(trie, tokens):
    """Every (phrase, tag ids) of the trie found in the token stream."""
    found = []
    n = len(tokens)
    for i in range(n):
        node = trie
        for j in range(i, min(n, i + MAX_PHRASE_TOKENS)):
            node = node.get(tokens[j])
            if node is None:
                break
            if _END in node:
                found.append((tuple(tokens[i:j + 1]), node[_END]))
    return found


def candidates(*, title='', description='', content='', format='', exclude_ids=(), limit=None, **_ignored):
    """Ranked tag candidates for this rule text: [{...tag, score, matched,
    generic}]. Names found in the text come from the trie; generic tags come
    from the format's context (setting ai.tag_suggest_formats): the ones every
    rule of the format gets, and the ones a signal found in the rule."""
    cfg = _settings()
    idx = get_index()
    trie, term_df, tags = idx['trie'], idx['term_tags'], dict(idx['tags'])
    exclude = set(exclude_ids or ())
    scores, matched = defaultdict(float), defaultdict(set)
    generic_ids = set()
    ctx = format_context(format)
    if ctx:
        text = '\n'.join((title or '', description or '', (content or '')[:MAX_TEXT_CHARS]))
        found = [(GENERIC_SCORE, f'{format.lower()} rule', n) for n in ctx['tags']]
        for sig in ctx['signals']:
            if sig['re'].search(text):
                found += [(SIGNAL_SCORE, sig['label'], n) for n in sig['tags']]
        for value, why, name in found:
            tag = idx['generic'].get(name)
            if not tag or tag['id'] in exclude:
                continue
            tags.setdefault(tag['id'], tag)
            scores[tag['id']] += value
            matched[tag['id']].add(why)
            generic_ids.add(tag['id'])
    for weight, text in ((2.0, title), (1.0, description), (1.0, (content or '')[:MAX_TEXT_CHARS])):
        seen = set()
        for phrase, tag_ids in _walk(trie, tokenize(text)):
            if phrase in seen:          # a word repeated 50 times in the content counts once per field
                continue
            seen.add(phrase)
            value = weight * len(phrase) / max(1, term_df.get(phrase, 1)) ** 0.5
            for tid in tag_ids:
                if tid in exclude:
                    continue
                scores[tid] += value
                matched[tid].add(' '.join(phrase))
    limit = limit or cfg['max_candidates']
    order = sorted(scores, key=lambda t: (-scores[t], tags[t]['name']))
    # names found in the text first get their places, generic tags always get theirs
    ranked = [t for t in order if t not in generic_ids][:limit] + [t for t in order if t in generic_ids][:MAX_AI_GENERIC]
    ranked.sort(key=lambda t: (-scores[t], tags[t]['name']))
    return [{**tags[t], 'score': round(scores[t], 3), 'matched': sorted(matched[t]), 'generic': t in generic_ids}
            for t in ranked]


def simulate_ai_picks(found, max_suggestions, fmt=''):
    """What the model is asked to do, done from the trie scores — setting
    simulate_ai (dev machine with a slow local Ollama). Keeps the clearly
    leading NAME candidates, one tag per set of matched words (a galaxy /
    taxonomy tag rather than its plain twin), with a reason naming the words;
    then the GENERIC tags a signal of the format found (not the ones every
    rule of the format gets — a model would judge those, the simulation can't)."""
    if not found:
        return []
    names = [c for c in found if not c.get('generic')]
    picks = _simulate_names(names, max_suggestions)
    for c in sorted((c for c in found if c.get('generic')), key=lambda c: -c['score']):
        signals = [m for m in c['matched'] if not m.endswith(' rule')]
        if len(picks) >= max_suggestions or not signals:
            continue
        picks.append({'id': c['id'], 'confidence': 'medium' if c['score'] >= 2 * SIGNAL_SCORE else 'low',
                      'reason': f'[simulated] Generic tag: the {fmt or "rule"} rule looks like ' + ', '.join(signals) + '.'})
    return picks


def _simulate_names(found, max_suggestions):
    if not found:
        return []
    top = found[0]['score'] or 1
    picks, seen_terms = [], set()
    for c in sorted(found, key=lambda c: (-c['score'], c['namespace'] == '')):
        if c['score'] < top * 0.35 or len(picks) >= max_suggestions:
            break
        terms = tuple(c['matched'])
        if terms in seen_terms:
            continue
        seen_terms.add(terms)
        ratio = c['score'] / top
        picks.append({'id': c['id'], 'confidence': 'high' if ratio >= .7 else 'medium' if ratio >= .45 else 'low',
                      'reason': '[simulated] The rule mentions ' + ', '.join(f'"{t}"' for t in terms[:3]) + '.'})
    return picks


def can_use(user) -> bool:
    """Who sees and uses Tag Suggestions — trie AND AI step: admins, AI
    Operators (ai.use) and AI Managers (ai.manage), while the agent is enabled
    (AI admin → Tag Suggestions / Overview). Plain users never see it. Every
    route and template goes through this one check. On the rule edit page this
    includes a Tag manager (rule.tag_any) who is also an AI Operator, in the
    tags-only restricted edit of someone else's rule."""
    from app.core.db_class.ai import AIAgentConfig
    if not user or not user.is_authenticated:
        return False
    if not (user.is_admin() or user.has_permission('ai.use') or user.has_permission('ai.manage')):
        return False
    cfg = AIAgentConfig.query.filter_by(agent_key='tag_suggest').first()
    return cfg.enabled if cfg else True


ai_available = can_use   # the AI step has the same audience as the trie


def bundle_text(bundle, max_rules=300):
    """What a bundle is about, as text for the trie: its name and description,
    plus the titles and tag names of its (non-deleted) rules — a tag already
    used by several of its rules is a strong hint for the bundle itself."""
    from app.core.db_class.bundle import BundleRuleAssociation
    from app.core.db_class.rule import Rule
    rows = (db.session.query(Rule.id, Rule.title, Rule.format)
            .join(BundleRuleAssociation, BundleRuleAssociation.rule_id == Rule.id)
            .filter(BundleRuleAssociation.bundle_id == bundle.id, Rule.is_deleted.is_(False))
            .limit(max_rules).all())
    rule_ids = [r.id for r in rows]
    tag_names = []
    if rule_ids:
        tag_names = [n for (n,) in db.session.query(Tag.name)
                     .join(RuleTagAssociation, RuleTagAssociation.tag_id == Tag.id)
                     .filter(RuleTagAssociation.rule_id.in_(rule_ids))]
    content = '\n'.join([r.title or '' for r in rows] + [n.replace('_', ' ') for n in tag_names])
    formats = Counter((r.format or '').lower() for r in rows if r.format)
    return {'title': bundle.name or '', 'description': bundle.description or '',
            'content': content, 'format': formats.most_common(1)[0][0] if formats else ''}


def ai_pick(user, text, exclude, target_type, target_id):
    """Runs the AI step for a rule or a bundle: trie candidates -> agent ->
    history row. Returns (json body, http status)."""
    from app.features.ai.ai_core import get_agent
    found = candidates(exclude_ids=exclude, **text)
    if not found:
        return {"ok": True, "suggestions": []}, 200
    cfg = _settings()
    result = get_agent('tag_suggest').run(
        user=user, rule_id=target_id if target_type == 'rule' else None,
        input_summary=text['title'] or text['content'][:200],
        candidates=found, max_suggestions=cfg['max_ai_suggestions'], simulate=cfg['simulate_ai'], **text,
    )
    if not result.ok:
        return {"ok": False, "error": result.error or "The AI call failed."}, 502
    by_id = {c['id']: c for c in found}
    picks = [{**by_id[s['id']], 'confidence': s['confidence'], 'reason': s['reason']}
             for s in result.meta.get('suggestions', [])]
    _save_history(user, text, target_type, target_id, found, picks, result.model_used)
    return {"ok": True, "model": result.model_used, "simulated": cfg['simulate_ai'], "suggestions": picks}, 200


def _save_history(user, text, target_type, target_id, found, picks, model, extra_meta=None):
    """One AIGeneration row per AI call — the admin page's history table
    (/ai/admin/tag-suggest), like the other agents."""
    import uuid as uuid_mod
    from app.core.db_class.ai import AIGeneration
    noun = 'Bundle' if target_type == 'bundle' else 'Rule'
    lines = [f"**{noun}:** {text['title'] or '(untitled)'}" + (f" ({text['format']})" if target_type == 'rule' else ''), "",
             f"**AI picks** ({len(picks)} of {len(found)} candidates):", ""]
    lines += [f"- `{p['name']}` — {p['confidence']}: {p['reason']}" for p in picks] or ["- none"]
    lines += ["", "**Candidates from the trie:** " + ', '.join(f"`{c['name']}`" for c in found)]
    try:
        db.session.add(AIGeneration(
            uuid=str(uuid_mod.uuid4()), agent_key='tag_suggest',
            rule_id=target_id if target_type == 'rule' else None,
            bundle_id=target_id if target_type == 'bundle' else None,
            user_id=getattr(user, 'id', None), content='\n'.join(lines), model=model,
            job_uuid=(extra_meta or {}).get('job_uuid'),
            meta={'target': target_type,
                  'suggestions': [{'id': p['id'], 'name': p['name'], 'confidence': p['confidence'],
                                   'reason': p['reason']} for p in picks],
                  'candidates': [c['name'] for c in found], **(extra_meta or {})},
            is_public=False,
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[tag_suggest] history not saved: {e}")


def index_stats():
    idx = get_index()
    by_source = Counter(source_kind(t['source']) for t in idx['tags'].values())
    formats = []
    for fmt, c in sorted(format_contexts().items()):
        names = set(c['tags']) | {t for s in c['signals'] for t in s['tags']}
        formats.append({'format': fmt, 'context': c['context'], 'tags': len(c['tags']),
                        'signals': len(c['signals']),
                        'missing': sorted(n for n in names if n not in idx['generic'])})
    return {'tags': len(idx['tags']), 'terms': len(idx['term_tags']), 'by_source': dict(by_source),
            'generic': len(idx['generic']), 'formats': formats}


def set_sources(sources, user_id):
    """Save the `sources` switches into setting ai.tag_suggest (with its
    history, like any change from Admin → Configuration). Returns an error
    message or None."""
    import json
    from app.core.utils import app_settings
    value = json.loads(json.dumps(app_settings.current_json_value('ai.tag_suggest')))
    value['sources'] = {k: bool(sources.get(k, value.get('sources', {}).get(k, k != 'custom'))) for k in SOURCES}
    if not any(value['sources'].values()):
        return 'Keep at least one tag source.'
    error = app_settings.validate('ai.tag_suggest', value)
    if error:
        return error
    app_settings.set_setting('ai.tag_suggest', value, user_id=user_id)
    _index['checked'] = 0.0      # rebuild on the next request of this worker
    return None
