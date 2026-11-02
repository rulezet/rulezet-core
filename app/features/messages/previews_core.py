"""
previews_core.py — the card shown under a message for a link to a Rulezet page (rule, bundle, edit proposal,
merge request, blog post, CVE, ATT&CK technique, profile, channel, git source).

Only this instance's own pages: the address is read, never fetched (no request to another site, no SSRF), and the
card is built from the database — only for what the reader may see, else nothing.

    preview(url, user)   {url, kind, kind_label, icon, color, title, description, image, meta} or None
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from flask import current_app, request

from app import db
from app.core.utils.share_card import plain_text

MAX_PER_REQUEST = 20

KINDS = {
    'rule':     ('Rule', 'fa-solid fa-shield-halved', '#0d6efd'),
    'bundle':   ('Bundle', 'fa-solid fa-box-archive', '#6f42c1'),
    'proposal': ('Edit proposal', 'fa-solid fa-code-pull-request', '#f97316'),
    'mr':       ('Merge request', 'fa-solid fa-code-merge', '#6f42c1'),
    'blog':     ('Blog post', 'fa-solid fa-newspaper', '#198754'),
    'cve':      ('Vulnerability', 'fa-solid fa-bug', '#dc3545'),
    'attack':   ('ATT&CK technique', 'fa-solid fa-crosshairs', '#e8590c'),
    'user':     ('Profile', 'fa-solid fa-user', '#0dcaf0'),
    'channel':  ('Channel', 'fa-solid fa-hashtag', '#0a58ca'),
    'repo':     ('Git source', 'fa-brands fa-git-alt', '#495057'),
}


def _date(d):
    return d.strftime('%d %b %Y') if hasattr(d, 'strftime') else None


def _own_hosts():
    hosts = {request.host.lower()}
    for value in (current_app.config.get('INSTANCE_PUBLIC_URL'),):
        if value:
            hosts.add(urlparse(value).netloc.lower())
    return hosts


def _card(kind, url, title, description='', image=None, meta=None):
    label, icon, color = KINDS[kind]
    return {'url': url, 'kind': kind, 'kind_label': label, 'icon': icon, 'color': color,
            'title': (title or '')[:160], 'description': plain_text(description or '', 180),
            'image': image, 'meta': [m for m in (meta or []) if m][:4]}


def preview(url, user):
    """The card of a link to one of this instance's pages, or None (another site, not found, not visible)."""
    try:
        p = urlparse((url or '').strip())
    except ValueError:
        return None
    if p.scheme not in ('', 'http', 'https') or (p.netloc and p.netloc.lower() not in _own_hosts()):
        return None
    path, q = p.path.rstrip('/') or '/', parse_qs(p.query)
    href = p.path + (('?' + p.query) if p.query else '')
    try:
        return _by_path(path, q, href, user)
    except Exception:
        db.session.rollback()
        return None


def _by_path(path, q, href, user):
    from app.features.messages.refs_core import resolve
    m = re.fullmatch(r'/rule/detail_rule/([\w-]+)', path)
    if m:
        from app.core.db_class.rule import Rule
        from app.features.rule.rule_core import _active
        key = m.group(1)
        rule = _active().filter(Rule.id == int(key)).first() if key.isdigit() else _active().filter(Rule.uuid == key).first()
        if not rule:
            return None
        return _card('rule', href, rule.title, rule.description,
                     meta=[(rule.format or '').upper(), rule.author and f'by {rule.author}',
                           _date(getattr(rule, 'creation_date', None) or getattr(rule, 'created_at', None))])
    m = re.fullmatch(r'/bundle/detail/([\w-]+)', path)
    if m:
        from app.core.db_class.bundle import Bundle
        from app.features.bundle.bundle_core import can_view_bundle
        key = m.group(1)
        b = db.session.get(Bundle, int(key)) if key.isdigit() else Bundle.query.filter_by(uuid=key).first()
        if not b or not can_view_bundle(b):
            return None
        owner = b.user.get_username() if getattr(b, 'user', None) else None
        return _card('bundle', href, b.name, b.description,
                     meta=['Fork' if getattr(b, 'forked_from_id', None) else None, owner and f'by {owner}',
                           None if b.access else 'Private'])
    if path == '/rule/proposal_content_discuss' and q.get('id', [''])[0].isdigit():
        from app.core.db_class.rule_proposal import RuleEditProposal
        prop = db.session.get(RuleEditProposal, int(q['id'][0]))
        if not prop or not resolve('rule', prop.rule_id):
            return None
        rule = prop.rule if hasattr(prop, 'rule') else None
        author = prop.user.get_username() if getattr(prop, 'user', None) else None
        return _card('proposal', href, f'Edit proposal #{prop.id}' + (f' on {rule.title}' if rule else ''),
                     prop.message, meta=[(prop.status or '').capitalize(), author and f'by {author}'])
    m = re.fullmatch(r'/bundle/merge_request/([\w-]+)', path)
    if m:
        from app.core.db_class.bundle_fork import BundleMergeRequest
        from app.features.bundle.bundle_fork_core import can_view_mr
        mr = BundleMergeRequest.query.filter_by(uuid=m.group(1)).first()
        if not mr or not can_view_mr(mr, user):
            return None
        return _card('mr', href, mr.title, mr.message,
                     meta=[(mr.status or '').capitalize(), mr.target and f'into {mr.target.name}'])
    m = re.fullmatch(r'/blog/post/([\w-]+)', path)
    if m:
        from app.core.db_class.blog import BlogPost
        post = BlogPost.query.filter_by(uuid=m.group(1)).first()
        if not post or not resolve('blog', post.uuid):
            return None
        return _card('blog', href, post.title, post.excerpt or post.content, image=post.cover_image_url,
                     meta=[post.published_at and post.published_at.strftime('%d %b %Y')])
    m = re.fullmatch(r'/vulnerability/([\w.-]+)', path)
    if m:
        hit = resolve('cve', m.group(1))
        return _card('cve', href, hit['label'], 'Every rule for this vulnerability: coverage per format, gaps, download.') if hit else None
    m = re.fullmatch(r'/attack/technique/([\w.]+)', path)
    if m:
        from app.core.db_class.attack import AttackTechnique
        t = AttackTechnique.query.filter_by(technique_id=m.group(1).upper()).first()
        return _card('attack', href, f'{t.technique_id} {t.name}', t.description) if t else None
    m = re.fullmatch(r'/account/detail_user/(\d+)', path)
    if m:
        from app.core.db_class.user import User
        u = db.session.get(User, int(m.group(1)))
        if not u:
            return None
        return _card('user', href, u.get_username(), getattr(u, 'bio', None), image=u.get_avatar_url(),
                     meta=[o.label or o.name for o in getattr(u, 'organisations', [])[:2]])
    m = re.fullmatch(r'/messages/c/([\w-]+)', path)
    if m:
        from app.features.messages import messages_core as M
        c = M.get_channel(m.group(1))
        if not c or c.kind != 'channel' or not M.can_view(c, user):
            return None
        return _card('channel', href, c.name, c.topic, image=M.avatar_url(c),
                     meta=['Private' if c.is_private else 'Public', f'{c.members.count()} members'])
    if path == '/rule/github_detail' and q.get('url'):
        from app.core.db_class.git import GithubRepo
        g = GithubRepo.query.filter_by(url=q['url'][0].rstrip('/')).first()
        return _card('repo', href, q['url'][0].split('://', 1)[-1], meta=[g and f'{g.rule_count} rules']) if g else None
    return None
