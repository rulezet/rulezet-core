"""
seo_core.py — how search engines see this instance (setting seo): robots.txt, the sitemaps, the default
title / description / keywords and the structured data (JSON-LD) of the pages.

Indexing (seo.indexing): 'auto' = only the official instance (IS_OFFICIAL_INSTANCE, rulezet.org) is indexed,
so self-hosted copies of the same rules never compete with it in search results; 'on' / 'off' to force.
Only what anyone may read is listed: active rules (never the ones tagged with seo.excluded_tags, TLP), public
bundles, published public blog posts, CVE kits that have rules, ATT&CK techniques that have rules.
"""
import datetime

from flask import current_app
from sqlalchemy import func

from app import db
from app.core.utils.app_settings import get_setting

SECTIONS = ('pages', 'rules', 'bundles', 'blog', 'cves', 'attack')


def conf() -> dict:
    try:
        value = get_setting('seo')
    except KeyError:
        value = None
    return value if isinstance(value, dict) else {}


def indexable() -> bool:
    mode = str(conf().get('indexing') or 'auto').lower()
    if mode in ('on', 'off'):
        return mode == 'on'
    return bool(current_app.config.get('IS_OFFICIAL_INSTANCE'))


def page_size() -> int:
    try:
        return max(100, min(50000, int(conf().get('sitemap_page_size') or 20000)))   # 50,000 URLs max per file
    except (TypeError, ValueError):
        return 20000


def _iso(d):
    return d.strftime('%Y-%m-%d') if isinstance(d, (datetime.date, datetime.datetime)) else None


def _rules_query():
    from app.core.db_class.rule import Rule
    from app.core.db_class.tag import Tag, RuleTagAssociation
    from app.features.rule.rule_core import _active
    q = _active()
    excluded = [str(t).lower() for t in (conf().get('excluded_tags') or [])]
    if excluded:
        hidden = db.session.query(RuleTagAssociation.rule_id).join(Tag, Tag.id == RuleTagAssociation.tag_id) \
            .filter(func.lower(Tag.name).in_(excluded))
        q = q.filter(~Rule.id.in_(hidden))
    return q


def count(section) -> int:
    """How many URLs a section has (for the sitemap index)."""
    if section == 'pages':
        return len(conf().get('static_pages') or [])
    if section == 'rules':
        return _rules_query().count()
    if section == 'bundles':
        from app.core.db_class.bundle import Bundle
        return Bundle.query.filter(Bundle.access.is_(True)).count()
    if section == 'blog':
        from app.core.db_class.blog import BlogPost
        return BlogPost.query.filter(BlogPost.is_draft.is_(False), BlogPost.is_public.is_(True)).count()
    if section == 'cves':
        return len(_cve_ids())
    if section == 'attack':
        return len(_attack_ids())
    return 0


def _cve_ids():
    """Vulnerability ids that have at least one rule — their response kits are worth finding."""
    from app.core.db_class.rule import Rule
    ids = set()
    for (value,) in _rules_query().filter(Rule.cve_id.isnot(None), Rule.cve_id != '').with_entities(Rule.cve_id).all():
        for part in str(value).replace(';', ',').replace(' ', ',').split(','):
            part = part.strip().upper()
            if part.startswith(('CVE-', 'GHSA-')):
                ids.add(part)
    return sorted(ids)


def _attack_ids():
    """ATT&CK techniques that have at least one rule."""
    try:
        from app.core.db_class.attack import AttackTechnique, RuleAttackAssociation
        q = db.session.query(AttackTechnique.technique_id).join(
            RuleAttackAssociation, RuleAttackAssociation.technique_id == AttackTechnique.id).distinct()
        return sorted(t for (t,) in q.all())
    except Exception:
        return []


def urls(section, page, base):
    """[(loc, lastmod, changefreq, priority)] of one sitemap file (page 1-based)."""
    size = page_size()
    offset = (page - 1) * size
    if section == 'pages':
        out = []
        for p in (conf().get('static_pages') or [])[offset:offset + size]:
            if isinstance(p, dict) and p.get('path'):
                out.append((base + p['path'], None, p.get('changefreq'), p.get('priority')))
        return out
    if section == 'rules':
        from app.core.db_class.rule import Rule
        rows = _rules_query().with_entities(Rule.id, Rule.last_modif, Rule.creation_date) \
            .order_by(Rule.id).offset(offset).limit(size).all()
        return [(f'{base}/rule/detail_rule/{i}', _iso(m or c), 'monthly', 0.6) for i, m, c in rows]
    if section == 'bundles':
        from app.core.db_class.bundle import Bundle
        rows = Bundle.query.filter(Bundle.access.is_(True)).order_by(Bundle.id).offset(offset).limit(size).all()
        return [(f'{base}/bundle/detail/{b.id}', _iso(getattr(b, 'updated_at', None) or getattr(b, 'created_at', None)),
                 'weekly', 0.6) for b in rows]
    if section == 'blog':
        from app.core.db_class.blog import BlogPost
        rows = BlogPost.query.filter(BlogPost.is_draft.is_(False), BlogPost.is_public.is_(True)) \
            .order_by(BlogPost.id).offset(offset).limit(size).all()
        return [(f'{base}/blog/post/{p.uuid}', _iso(getattr(p, 'updated_at', None) or p.published_at), 'monthly', 0.5)
                for p in rows]
    if section == 'cves':
        return [(f'{base}/vulnerability/{v}', None, 'weekly', 0.6) for v in _cve_ids()[offset:offset + size]]
    if section == 'attack':
        return [(f'{base}/attack/technique/{t}', None, 'weekly', 0.6) for t in _attack_ids()[offset:offset + size]]
    return []


def rule_jsonld(rule, base):
    """Structured data of a rule page: a piece of source code in the rule's language."""
    data = {
        '@context': 'https://schema.org', '@type': 'SoftwareSourceCode',
        'name': rule.title, 'url': f'{base}/rule/detail_rule/{rule.id}',
        'description': (rule.description or f'{(rule.format or "").upper()} detection rule.')[:500],
        'programmingLanguage': (rule.format or '').upper() or None,
        'codeSampleType': 'full (compile ready) solution',
        'text': (rule.to_string or '')[:5000],
        'identifier': rule.uuid,
        'keywords': ', '.join(k for k in [f'{(rule.format or "").upper()} rule', 'detection rule', rule.cve_id] if k),
        'isPartOf': {'@type': 'WebSite', 'name': 'Rulezet', 'url': base + '/'},
    }
    if rule.author:
        data['author'] = {'@type': 'Person', 'name': rule.author[:200]}
    if rule.license:
        data['license'] = rule.license
    if rule.creation_date:
        data['dateCreated'] = _iso(rule.creation_date)
    if rule.last_modif:
        data['dateModified'] = _iso(rule.last_modif)
    if rule.source and str(rule.source).startswith(('http://', 'https://')):
        data['codeRepository'] = rule.source
    return {k: v for k, v in data.items() if v not in (None, '')}


def site_jsonld(base):
    """The site and who makes it — lets search engines show the search box and the name."""
    return [
        {'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Rulezet', 'url': base + '/',
         'description': conf().get('description') or '',
         'potentialAction': {'@type': 'SearchAction',
                             'target': {'@type': 'EntryPoint', 'urlTemplate': base + '/rule/rules_list?search={search_term_string}'},
                             'query-input': 'required name=search_term_string'}},
        {'@context': 'https://schema.org', '@type': 'Organization', 'name': 'Rulezet', 'url': base + '/',
         'logo': base + '/static/image/rulezet_official_logo.png',
         'sameAs': ['https://github.com/rulezet', 'https://www.circl.lu/']},
    ]
