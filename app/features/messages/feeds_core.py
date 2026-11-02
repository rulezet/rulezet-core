"""
feeds_core.py — channel automations: on an event, Rulezet posts a message in the channels that asked for it.

    rulezet_release   a new Rulezet version is out                      (notification_core.notify_admins_new_version)
    bundle_release    a new release of a chosen bundle                  (bundle_release_core.create_release)
    alert             new rules / bundles matching one of your alerts   (alert_core.run_sweep)
    blog_post         a blog post is published                          (notification_core.notify_blog_published)
    merge_request     a merge request is opened on a chosen bundle      (bundle_fork_core.open_merge_request)

Set up by the channel's owner, moderators and admins (can_manage). Only public content is posted — every member
reads the channel, not only who set it up: a public bundle only, an alert's public matches only, and an alert must
be one of your own. Each message links its page, so the link card shows under it (previews_core.py).

    feeds(c) · add_feed(c, user, kind, target_id) · delete_feed(c, feed_id)
    fire(kind, target_id, text)   — called by the events above; never raises
"""
from __future__ import annotations

import datetime

from app import db
from app.core.db_class.message import Channel, ChannelFeed, ChannelMessage

KINDS = {
    'rulezet_release': {'label': 'Rulezet releases', 'icon': 'fa-solid fa-rocket', 'target': None,
                        'help': 'A new version of Rulezet is out.'},
    'bundle_release':  {'label': 'Releases of a bundle', 'icon': 'fa-solid fa-tag', 'target': 'bundle',
                        'help': 'A new release of the bundle you choose (public bundles only).'},
    'alert':           {'label': 'Matches of one of your alerts', 'icon': 'fa-solid fa-satellite-dish', 'target': 'alert',
                        'help': 'New rules / bundles matching your alert — by format, tag, CVE, ATT&CK technique, author… (public content only).'},
    'blog_post':       {'label': 'New blog posts', 'icon': 'fa-solid fa-newspaper', 'target': None,
                        'help': 'A blog post is published.'},
    'merge_request':   {'label': 'Merge requests on a bundle', 'icon': 'fa-solid fa-code-merge', 'target': 'bundle',
                        'help': 'Someone proposes changes to the bundle you choose (from a fork).'},
}
MAX_FEEDS = 20
ALERT_ITEMS = 10


def _base():
    try:
        from app.features.alert.alert_core import _public_base_url
        return _public_base_url()
    except Exception:
        return ''


def feed_json(f):
    k = KINDS.get(f.kind, {})
    target = None
    if f.kind in ('bundle_release', 'merge_request') and f.target_id:
        from app.core.db_class.bundle import Bundle
        b = db.session.get(Bundle, f.target_id)
        target = {'label': b.name if b else 'Deleted bundle', 'url': f'/bundle/detail/{b.id}' if b else None}
    elif f.kind == 'alert' and f.target_id:
        from app.core.db_class.alert import Alert
        a = db.session.get(Alert, f.target_id)
        target = {'label': a.name if a else 'Deleted alert', 'url': f'/alert/{a.uuid}' if a else None}
    from app.core.db_class.user import User
    who = db.session.get(User, f.created_by) if f.created_by else None
    return {'id': f.id, 'kind': f.kind, 'label': k.get('label', f.kind), 'icon': k.get('icon'), 'target': target,
            'created_by': who.get_username() if who else None, 'posted': f.posted,
            'last_posted_at': f.last_posted_at.isoformat() + 'Z' if f.last_posted_at else None}


def feeds(c):
    return [feed_json(f) for f in c.feeds.order_by(ChannelFeed.created_at)]


def add_feed(c, user, kind, target_id=None):
    if c.kind != 'channel':
        return None, 'Automations are for channels.'
    if kind not in KINDS:
        return None, 'Unknown automation.'
    if c.feeds.count() >= MAX_FEEDS:
        return None, f'{MAX_FEEDS} automations at most per channel.'
    need = KINDS[kind]['target']
    target_id = int(target_id) if str(target_id or '').isdigit() else None
    if need == 'bundle':
        from app.core.db_class.bundle import Bundle
        from app.features.bundle.bundle_core import can_view_bundle
        b = db.session.get(Bundle, target_id) if target_id else None
        if not b or not can_view_bundle(b):
            return None, 'Choose a bundle.'
        if not b.access:
            return None, 'Only a public bundle — every member of the channel reads what is posted.'
    elif need == 'alert':
        from app.core.db_class.alert import Alert
        a = db.session.get(Alert, target_id) if target_id else None
        if not a or a.user_id != user.id:
            return None, 'Choose one of your alerts.'
    else:
        target_id = None
    if c.feeds.filter_by(kind=kind, target_id=target_id).first():
        return None, 'This channel already has it.'
    f = ChannelFeed(channel_id=c.id, kind=kind, target_id=target_id, created_by=user.id)
    db.session.add(f)
    from app.features.messages.messages_core import _system
    _system(c, f'{user.get_username()} added an automation: {KINDS[kind]["label"].lower()}', user)
    db.session.commit()
    if kind == 'rulezet_release':          # the latest release right away (the check runs only once a day)
        latest = _latest_release()
        if latest:
            on_rulezet_release(latest['version'], latest['url'])
    return f, ''


def _latest_release():
    """The latest Rulezet release the update check saw (app/__init__.py), or None."""
    from flask import current_app
    info = current_app.config.get('LATEST_RELEASE')
    if not info:
        try:                                # the check runs in the worker process: shared through the cache
            from app import UPDATE_CACHE_KEY, cache
            info = cache.get(UPDATE_CACHE_KEY) or None
        except Exception:
            info = None
    if not info:                            # no check yet (or no shared cache): ask GitHub once
        try:
            import os
            import requests
            r = requests.get(os.environ.get('UPDATE_CHECK_URL', 'https://api.github.com/repos/rulezet/rulezet-core/releases/latest'),
                             timeout=6, headers={'Accept': 'application/vnd.github+json'})
            if r.ok:
                d = r.json()
                info = {'version': (d.get('tag_name') or '').lstrip('v'), 'url': d.get('html_url')}
        except Exception:
            info = None
    return info if info and info.get('version') else None


def delete_feed(c, user, feed_id):
    f = c.feeds.filter_by(id=feed_id).first()
    if not f:
        return False
    from app.features.messages.messages_core import _system
    _system(c, f'{user.get_username()} removed an automation: {KINDS.get(f.kind, {}).get("label", f.kind).lower()}', user)
    db.session.delete(f)
    db.session.commit()
    return True


def _post(c, text):
    """A message from Rulezet in the channel; its members are told like for any message."""
    m = ChannelMessage(channel_id=c.id, user_id=None, kind='feed', content=text[:8000])
    db.session.add(m)
    c.last_message_at = datetime.datetime.utcnow()
    db.session.flush()
    _notify(c, m, text)
    return m


def _notify(c, m, text):
    from app.core.db_class.notification import Notification
    from app.features.messages.messages_core import _link, _plain
    from app.features.notification.notification_core import create_notification
    members = list(c.members)
    pending = {n.user_id for n in Notification.query.filter(
        Notification.notif_type == 'message_channel', Notification.is_read.is_(False), Notification.link == _link(c),
        Notification.user_id.in_([x.user_id for x in members])).all()}
    for mm in members:
        if mm.is_muted or mm.user_id in pending:
            continue
        create_notification(mm.user_id, 'message_channel', f'Rulezet posted in #{c.name}', body=_plain(text)[:200],
                            link=_link(c))


def fire(kind, target_id, text, once_key=None):
    """Post `text` in every channel with an active automation for this event. once_key: post it only once per
    channel (e.g. the version of a Rulezet release, the sweep may see it again). Never raises."""
    try:
        q = (ChannelFeed.query.join(Channel, Channel.id == ChannelFeed.channel_id)
             .filter(ChannelFeed.kind == kind, ChannelFeed.is_active.is_(True), Channel.is_archived.is_(False)))
        q = q.filter(ChannelFeed.target_id == target_id) if target_id is not None else q.filter(ChannelFeed.target_id.is_(None))
        n = 0
        for f in q.all():
            # once per channel — a message someone deleted doesn't count: removing and adding the automation posts it again
            if once_key and ChannelMessage.query.filter(ChannelMessage.channel_id == f.channel_id,
                                                         ChannelMessage.kind == 'feed',
                                                         ChannelMessage.deleted_at.is_(None),
                                                         ChannelMessage.content.contains(once_key)).first():
                continue
            _post(f.channel, text)
            f.posted += 1
            f.last_posted_at = datetime.datetime.utcnow()
            n += 1
        if n:
            db.session.commit()
        return n
    except Exception as e:
        db.session.rollback()
        print(f'[messages] automation {kind} failed: {e}', flush=True)
        return 0


# ── The events ─────────────────────────────────────────────────────────────

def release_post(version):
    """The Rulezet blog's post of this release (public, published, tagged "release" and "v<version>"), or None."""
    from app.core.db_class.blog import BlogPost
    want = {'release', f'v{version}'.lower()}
    for p in (BlogPost.query.filter(BlogPost.is_public.is_(True), BlogPost.is_draft.is_(False))
              .order_by(BlogPost.published_at.desc().nullslast()).limit(50)):
        if want <= {a.tag.name.lower() for a in p.tags if a.tag}:
            return p
    return None


def on_rulezet_release(version, url):
    """A new Rulezet release: read on the Rulezet blog when its release post exists, else on GitHub."""
    post = release_post(version)
    where = (f'[read the release notes on the blog]({_base()}/blog/post/{post.uuid})' if post
             else f'[read the release notes]({url})')
    return fire('rulezet_release', None, f'🚀 **Rulezet v{version} is out** — {where}', once_key=f'Rulezet v{version} ')


def on_release_post(post):
    """The release post of a version published after the release was announced: point to it (once)."""
    import re as _re
    tags = [a.tag.name for a in post.tags if a.tag]
    if 'release' not in {t.lower() for t in tags}:
        return 0
    version = next((t.lstrip('vV') for t in tags if _re.fullmatch(r'[vV]\d+(\.\d+)*', t)), None)
    if not version:
        return 0
    return fire('rulezet_release', None,
                f'📰 **Release notes of Rulezet v{version}** on the blog: [{post.title}]({_base()}/blog/post/{post.uuid})',
                once_key=f'Release notes of Rulezet v{version}')


def on_bundle_release(bundle, release):
    if not bundle or not bundle.access:
        return 0
    title = f' — {release.title}' if getattr(release, 'title', None) else ''
    return fire('bundle_release', bundle.id,
                f'🏷️ **New release {release.version}** of [{bundle.name}]({_base()}/bundle/detail/{bundle.id}){title}')


def on_blog_post(post):
    if not post or not post.is_public or post.is_draft:
        return 0
    on_release_post(post)                  # a release post also goes to the "Rulezet releases" channels
    return fire('blog_post', None, f'📰 **New blog post:** [{post.title}]({_base()}/blog/post/{post.uuid})')


def on_merge_request(mr):
    target = getattr(mr, 'target', None)
    if not target or not target.access:
        return 0
    who = mr.user.get_username() if getattr(mr, 'user', None) else 'Someone'
    return fire('merge_request', target.id,
                f'🔀 **{who}** opened a merge request on [{target.name}]({_base()}/bundle/detail/{target.id}): '
                f'[{mr.title}]({_base()}/bundle/merge_request/{mr.uuid})')


def on_alert_matches(alert, matches):
    """The public items among an alert's new matches."""
    from app.core.db_class.bundle import Bundle
    from app.core.db_class.rule import Rule
    lines = []
    for m in matches:
        if m.object_type == 'rule':
            r = db.session.get(Rule, m.object_id)
            if r and not r.is_deleted:
                lines.append(f'- {"Updated" if m.event == "updated" else "New"} rule: [{r.title}]({_base()}/rule/detail_rule/{r.id})')
        elif m.object_type == 'bundle':
            b = db.session.get(Bundle, m.object_id)
            if b and b.access:
                lines.append(f'- {"Updated" if m.event == "updated" else "New"} bundle: [{b.name}]({_base()}/bundle/detail/{b.id})')
    if not lines:
        return 0
    more = f'\n- …and {len(lines) - ALERT_ITEMS} more' if len(lines) > ALERT_ITEMS else ''
    return fire('alert', alert.id, f'🛰️ **{alert.name}** — {len(lines)} new match{"es" if len(lines) > 1 else ""}:\n'
                + '\n'.join(lines[:ALERT_ITEMS]) + more)
