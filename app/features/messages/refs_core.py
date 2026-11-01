"""
refs_core.py — things of Rulezet a message (or a channel) can point to.

In a message a reference is the token  #[label](kind:key)  inserted by the composer's "#" picker;
a channel can be about one of them (Channel.ref_type / ref_key).

    KINDS                  kind → label, icon
    resolve(kind, key)     {kind, key, label, url, icon} if it exists and the current user may see it, else None
    search(q, kinds)       what the "#" picker offers — only what the current user may see
    url_for_ref(kind, key)
"""
from __future__ import annotations

from urllib.parse import quote

from flask_login import current_user
import re

from sqlalchemy import and_, false, func, or_

from app import db

KINDS = {
    'rule':    {'label': 'Rule',        'icon': 'fa-solid fa-shield-halved'},
    'bundle':  {'label': 'Bundle',      'icon': 'fa-solid fa-box-archive'},
    'blog':    {'label': 'Blog post',   'icon': 'fa-solid fa-newspaper'},
    'cve':     {'label': 'Vulnerability', 'icon': 'fa-solid fa-bug'},
    'attack':  {'label': 'ATT&CK',      'icon': 'fa-solid fa-crosshairs'},
    'repo':    {'label': 'Git source',  'icon': 'fa-brands fa-git-alt'},
    'channel': {'label': 'Channel',     'icon': 'fa-solid fa-hashtag'},
}
LIMIT = 6


def url_for_ref(kind, key, extra=None):
    key = str(key)
    return {
        'rule': f'/rule/detail_rule/{quote(key)}',
        'bundle': f'/bundle/detail/{quote(key)}',
        'blog': f'/blog/post/{quote(key)}',
        'cve': f'/vulnerability/{quote(key)}',
        'attack': f'/attack/technique/{quote(key)}',
        'repo': f'/rule/github_detail?url={quote(extra or "", safe="")}',
        'channel': f'/messages/c/{quote(key)}',
    }.get(kind)


def _item(kind, key, label, extra=None, sub=None):
    return {'kind': kind, 'key': str(key), 'label': (label or str(key))[:120], 'sub': sub,
            'url': url_for_ref(kind, key, extra), 'icon': KINDS[kind]['icon'], 'kind_label': KINDS[kind]['label']}


def _is_admin():
    return current_user.is_authenticated and current_user.is_admin()


def _bundle_ok(b):
    from app.features.bundle.bundle_core import can_view_bundle
    return can_view_bundle(b)


def resolve(kind, key):
    """The referenced object, or None when it doesn't exist or the current user can't see it."""
    if kind not in KINDS or key in (None, ''):
        return None
    key = str(key).strip()
    try:
        if kind == 'rule':
            from app.features.rule.rule_core import _active
            from app.core.db_class.rule import Rule
            r = _active().filter(Rule.id == int(key)).first() if key.isdigit() else None
            return _item('rule', r.id, r.title, sub=r.format) if r else None
        if kind == 'bundle':
            from app.core.db_class.bundle import Bundle
            b = db.session.get(Bundle, int(key)) if key.isdigit() else None
            return _item('bundle', b.id, b.name) if b and _bundle_ok(b) else None
        if kind == 'blog':
            from app.core.db_class.blog import BlogPost
            p = BlogPost.query.filter_by(uuid=key).first()
            return _item('blog', p.uuid, p.title) if p and (p.is_public or _is_admin()) else None
        if kind == 'cve':
            from app.features.vulnerability.vulnerability_core import normalize_id
            vid = normalize_id(key)
            return _item('cve', vid, vid) if vid else None
        if kind == 'attack':
            from app.core.db_class.attack import AttackTechnique
            t = AttackTechnique.query.filter_by(technique_id=key.upper()).first()
            return _item('attack', t.technique_id, f'{t.technique_id} {t.name}') if t else None
        if kind == 'repo':
            from app.core.db_class.git import GithubRepo
            g = GithubRepo.query.filter_by(uuid=key).first()
            return _item('repo', g.uuid, _short_repo(g.url), extra=g.url) if g else None
        if kind == 'channel':
            from app.features.messages.messages_core import can_view, get_channel
            c = get_channel(key)
            return _item('channel', c.uuid, c.name) if c and c.kind == 'channel' and can_view(c, current_user) else None
    except Exception:
        db.session.rollback()
    return None


def _short_repo(url):
    return (url or '').split('://', 1)[-1]


def _squash(col):
    """lower(col) without spaces, _ - . — "my rule" finds my_rule, my-rule, MyRule."""
    out = func.lower(col)
    for ch in (' ', '_', '-', '.'):
        out = func.replace(out, ch, '')
    return out


def text_match(q, *cols, id_col=None, uuid_col=None):
    """Every word somewhere in one of the columns, or the whole search with no separators, or the exact id /
    uuid."""
    words = [w for w in re.split(r'[\s_\-.]+', q.lower()) if w][:8]
    squashed = re.sub(r'[\s_\-.]+', '', q.lower())
    conds = []
    for col in cols:
        if words:
            conds.append(and_(*[col.ilike(f'%{w}%') for w in words]))
        if squashed:
            conds.append(_squash(col).like(f'%{squashed}%'))
    if id_col is not None and q.strip().lstrip('#').isdigit():
        conds.append(id_col == int(q.strip().lstrip('#')))
    if uuid_col is not None and re.fullmatch(r'[0-9a-fA-F-]{8,36}', q.strip()):
        conds.append(uuid_col.ilike(f'{q.strip()}%'))
    return or_(*conds) if conds else false()


def search(q, kinds=None):
    """[{kind, key, label, url, icon}] for the "#" picker."""
    q = (q or '').strip()[:80]
    kinds = [k for k in (kinds or KINDS) if k in KINDS]
    out = []
    if not q and len(kinds) != 1:
        return out              # an empty search lists the latest items of one kind only (the "Attach" menu)
    if 'cve' in kinds and q:
        hit = resolve('cve', q)
        if hit:
            out.append(hit)
    if 'rule' in kinds:
        from app.features.rule.rule_core import _active
        from app.core.db_class.rule import Rule
        qq = _active().filter(text_match(q, Rule.title, id_col=Rule.id, uuid_col=Rule.uuid)) if q else _active()
        out += [_item('rule', r.id, r.title, sub=r.format) for r in qq.order_by(Rule.id.desc()).limit(LIMIT)]
    if 'bundle' in kinds:
        from app.core.db_class.bundle import Bundle
        qq = Bundle.query.filter(text_match(q, Bundle.name, id_col=Bundle.id, uuid_col=Bundle.uuid)) if q else Bundle.query
        if not _is_admin():
            qq = qq.filter(or_(Bundle.access.is_(True), Bundle.user_id == current_user.id))
        out += [_item('bundle', b.id, b.name) for b in qq.order_by(Bundle.id.desc()).limit(LIMIT)]
    if 'blog' in kinds:
        from app.core.db_class.blog import BlogPost
        qq = BlogPost.query.filter(text_match(q, BlogPost.title, BlogPost.slug, id_col=BlogPost.id, uuid_col=BlogPost.uuid)) if q else BlogPost.query
        if not _is_admin():
            qq = qq.filter(BlogPost.is_public.is_(True))
        out += [_item('blog', p.uuid, p.title) for p in qq.order_by(BlogPost.id.desc()).limit(LIMIT)]
    if 'attack' in kinds:
        from app.core.db_class.attack import AttackTechnique
        qq = AttackTechnique.query.filter(text_match(q, AttackTechnique.technique_id, AttackTechnique.name)) if q else AttackTechnique.query.order_by(AttackTechnique.technique_id)
        out += [_item('attack', t.technique_id, f'{t.technique_id} {t.name}') for t in qq.limit(LIMIT)]
    if 'repo' in kinds:
        from app.core.db_class.git import GithubRepo
        out += [_item('repo', g.uuid, _short_repo(g.url), extra=g.url)
                for g in (GithubRepo.query.filter(text_match(q, GithubRepo.url, uuid_col=GithubRepo.uuid)) if q
                          else GithubRepo.query.order_by(GithubRepo.id.desc())).limit(LIMIT)]
    if 'channel' in kinds:
        from app.features.messages.messages_core import visible_channels_query
        from app.core.db_class.message import Channel
        out += [_item('channel', c.uuid, c.name)
                for c in (visible_channels_query(current_user).filter(text_match(q, Channel.name, Channel.topic, uuid_col=Channel.uuid))
                          if q else visible_channels_query(current_user).order_by(Channel.last_message_at.desc().nullslast())).limit(LIMIT)]
    return out
