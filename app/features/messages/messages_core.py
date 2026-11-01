"""
messages_core.py — channels and direct conversations (page /messages/).

Rights — only through the can_* functions:
    direct conversation   its two people only (admins included: a direct conversation stays private)
    public channel        any signed-in user reads and joins it; members write
    private channel       members only (admins can open it to moderate)
    manage (rename, topic, privacy, members, pins, delete any message)
                          the channel's owner and moderators, and admins
    roles, delete the channel   owner and admins
    add people            managers — and every member when the channel allows it (members_can_invite)
    invite link           /messages/join/<code>: whoever has it joins, even a private channel; managers make,
                          renew or turn it off. Making a channel private never removes its members.

    get_channel(uuid) · can_view · can_post · can_manage · can_own
    conversations(user)                    the user's channels and direct conversations, with unread counts
    browse(user, q)                        public channels to join
    create_channel / direct_with / update_channel / delete_channel
    join / leave / add_members / remove_member / set_role / set_member_flags
    messages / post_message / edit_message / delete_message / toggle_reaction / toggle_pin / mark_read / search
Every change of the channel itself leaves a "system" line in the conversation.
"""
from __future__ import annotations

import datetime
import io
import os
import re
import uuid as uuid_mod

from sqlalchemy import and_, func, or_

from app import db
from app.core.db_class.message import Channel, ChannelMember, ChannelMessage, ChannelReaction
from app.core.db_class.user import User
from app.core.utils.app_settings import setting

REACTIONS = setting('messages.reactions')   # app/config/messages.reactions.json
LIMITS = setting('messages.limits')         # app/config/messages.limits.json
ROLES = ('owner', 'moderator', 'member')
MANAGERS = ('owner', 'moderator')
MENTION = re.compile(r'@\[([^\]]{1,80})\]\((\d+)\)')
NAME_MAX, TOPIC_MAX = 80, 300


def _limit(key, default):
    try:
        return int((LIMITS.value or {}).get(key, default))
    except Exception:
        return default


def _now():
    return datetime.datetime.utcnow()


def _is_admin(user):
    return bool(user and getattr(user, 'is_authenticated', False) and user.is_admin())


# ── Rights ─────────────────────────────────────────────────────────────────

def get_channel(uuid) -> Channel | None:
    return Channel.query.filter_by(uuid=str(uuid)).first() if uuid else None


def member(channel, user_id) -> ChannelMember | None:
    if not channel or not user_id:
        return None
    return ChannelMember.query.filter_by(channel_id=channel.id, user_id=user_id).first()


def can_view(channel, user) -> bool:
    if not channel or not user or not user.is_authenticated:
        return False
    if member(channel, user.id):
        return True
    if channel.kind == 'direct':
        return False
    return not channel.is_private or _is_admin(user)


def can_post(channel, user) -> bool:
    """Members write; on a public channel, writing joins it."""
    if not can_view(channel, user) or channel.is_archived:
        return False
    return bool(member(channel, user.id)) or (channel.kind == 'channel' and not channel.is_private)


def can_manage(channel, user) -> bool:
    if not channel or channel.kind != 'channel' or not user or not user.is_authenticated:
        return False
    if _is_admin(user):
        return True
    m = member(channel, user.id)
    return bool(m and m.role in MANAGERS)


def can_own(channel, user) -> bool:
    if not channel or channel.kind != 'channel' or not user or not user.is_authenticated:
        return False
    m = member(channel, user.id)
    return _is_admin(user) or bool(m and m.role == 'owner')


def can_invite(channel, user) -> bool:
    if can_manage(channel, user):
        return True
    return bool(channel and channel.kind == 'channel' and channel.members_can_invite and not channel.is_archived
                and member(channel, user.id))


def visible_channels_query(user):
    """Channels (not direct conversations) the user can see."""
    q = Channel.query.filter(Channel.kind == 'channel')
    if _is_admin(user):
        return q
    mine = db.session.query(ChannelMember.channel_id).filter(ChannelMember.user_id == user.id)
    return q.filter(or_(Channel.is_private.is_(False), Channel.id.in_(mine)))


# ── JSON ───────────────────────────────────────────────────────────────────

def user_json(u):
    if not u:
        return {'id': None, 'name': 'Deleted user', 'avatar': None, 'initial': '?'}
    name = u.get_username()
    return {'id': u.id, 'name': name, 'avatar': u.get_avatar_url(), 'initial': (name or '?')[0].upper(),
            'is_admin': bool(u.admin)}


def _ref_json(c):
    if not c.ref_type:
        return None
    from app.features.messages.refs_core import resolve, url_for_ref, KINDS
    hit = resolve(c.ref_type, c.ref_key)
    if hit:
        return hit
    # gone or not visible to this viewer: the label kept at creation, no link
    return {'kind': c.ref_type, 'key': c.ref_key, 'label': c.ref_label or c.ref_key, 'url': None,
            'icon': KINDS.get(c.ref_type, {}).get('icon', 'fa-solid fa-link'), 'missing': True}


def channel_json(c, user, me=None, unread=None, last=None, full=False):
    me = me if me is not None else member(c, user.id)
    other = None
    if c.kind == 'direct':
        o = (ChannelMember.query.filter(ChannelMember.channel_id == c.id, ChannelMember.user_id != user.id).first())
        other = user_json(o.user) if o else user_json(None)
    data = {
        'avatar': avatar_url(c),
        'uuid': c.uuid, 'kind': c.kind, 'name': (other['name'] if other else c.name), 'topic': c.topic,
        'is_private': c.is_private, 'is_archived': c.is_archived, 'other': other,
        'created_at': c.created_at.isoformat() + 'Z' if c.created_at else None,
        'last_message_at': c.last_message_at.isoformat() + 'Z' if c.last_message_at else None,
        'is_member': bool(me), 'my_role': me.role if me else None,
        'is_muted': bool(me and me.is_muted), 'is_starred': bool(me and me.is_starred),
        'unread': unread or 0, 'ref': _ref_json(c) if full or c.ref_type else None,
        'member_count': c.members.count(),
        'last': last,
    }
    if full:
        data.update({
            'can_post': can_post(c, user), 'can_manage': can_manage(c, user), 'can_own': can_own(c, user),
            'can_invite': can_invite(c, user), 'members_can_invite': c.members_can_invite,
            'invite_code': c.invite_code if can_manage(c, user) else None,
            'created_by': user_json(db.session.get(User, c.created_by)) if c.created_by else None,
            'members': [member_json(m) for m in c.members.order_by(ChannelMember.joined_at).limit(500)],
            'pinned': [message_json(m, user) for m in
                       c.messages.filter_by(is_pinned=True).filter(ChannelMessage.deleted_at.is_(None))
                       .order_by(ChannelMessage.id.desc()).limit(20)],
        })
    return data


def member_json(m):
    return {**user_json(m.user), 'role': m.role, 'joined_at': m.joined_at.isoformat() + 'Z'}


def message_json(m, user):
    deleted = m.deleted_at is not None
    groups = {}
    for r in m.reactions:
        g = groups.setdefault(r.emoji, {'emoji': r.emoji, 'count': 0, 'mine': False, 'user_ids': []})
        g['count'] += 1
        g['user_ids'].append(r.user_id)
        g['mine'] = g['mine'] or r.user_id == user.id
    reply = None
    if m.reply_to is not None:
        p = m.reply_to
        reply = {'id': p.id, 'author': user_json(p.author)['name'],
                 'content': '' if p.deleted_at else (p.content or '')[:200], 'deleted': p.deleted_at is not None}
    return {
        'id': m.id, 'uuid': m.uuid, 'kind': m.kind, 'author': user_json(m.author) if m.kind == 'message' else None,
        'content': '' if deleted else m.content, 'is_deleted': deleted, 'is_pinned': m.is_pinned,
        'created_at': m.created_at.isoformat() + 'Z', 'edited_at': m.edited_at.isoformat() + 'Z' if m.edited_at else None,
        'reply_to': reply, 'reactions': [] if deleted else list(groups.values()),
        'is_mine': m.user_id == user.id,
    }


# ── Lists ──────────────────────────────────────────────────────────────────

def _unread_counts(user_id, channel_ids):
    if not channel_ids:
        return {}
    rows = (db.session.query(ChannelMessage.channel_id, func.count(ChannelMessage.id))
            .join(ChannelMember, and_(ChannelMember.channel_id == ChannelMessage.channel_id,
                                      ChannelMember.user_id == user_id))
            .filter(ChannelMessage.channel_id.in_(channel_ids), ChannelMessage.id > ChannelMember.last_read_id,
                    ChannelMessage.id > ChannelMember.cleared_id,
                    ChannelMessage.kind == 'message', ChannelMessage.deleted_at.is_(None),
                    or_(ChannelMessage.user_id.is_(None), ChannelMessage.user_id != user_id))
            .group_by(ChannelMessage.channel_id).all())
    return dict(rows)


def _last_previews(channel_ids):
    if not channel_ids:
        return {}
    last_ids = (db.session.query(func.max(ChannelMessage.id))
                .filter(ChannelMessage.channel_id.in_(channel_ids), ChannelMessage.kind == 'message',
                        ChannelMessage.deleted_at.is_(None))
                .group_by(ChannelMessage.channel_id))
    out = {}
    for m in ChannelMessage.query.filter(ChannelMessage.id.in_(last_ids)).all():
        text = MENTION.sub(lambda x: '@' + x.group(1), m.content or '')
        text = re.sub(r'#\[([^\]]{1,120})\]\([a-z]+:[^)]+\)', r'#\1', text)
        out[m.channel_id] = {'id': m.id, 'author': user_json(m.author)['name'], 'author_id': m.user_id,
                             'text': re.sub(r'\s+', ' ', text)[:140]}
    return out


def conversations(user) -> list:
    mems = ChannelMember.query.filter_by(user_id=user.id).all()
    ids = [m.channel_id for m in mems]
    by_id = {c.id: c for c in Channel.query.filter(Channel.id.in_(ids)).all()} if ids else {}
    unread, last = _unread_counts(user.id, ids), _last_previews(ids)
    newest = dict(db.session.query(ChannelMessage.channel_id, func.max(ChannelMessage.id))
                  .filter(ChannelMessage.channel_id.in_(ids)).group_by(ChannelMessage.channel_id).all()) if ids else {}
    out = [channel_json(by_id[m.channel_id], user, me=m, unread=unread.get(m.channel_id, 0),
                        last=last.get(m.channel_id) if (last.get(m.channel_id) and last[m.channel_id]['id'] > m.cleared_id) else None)
           for m in mems if m.channel_id in by_id
           and not (m.cleared_id and newest.get(m.channel_id, 0) <= m.cleared_id)]
    out.sort(key=lambda c: (c['last_message_at'] or c['created_at'] or ''), reverse=True)
    return out


def unread_total(user) -> int:
    ids = [cid for (cid,) in db.session.query(ChannelMember.channel_id)
           .filter(ChannelMember.user_id == user.id, ChannelMember.is_muted.is_(False))]
    return sum(_unread_counts(user.id, ids).values())


def browse(user, q=None, limit=50) -> list:
    query = Channel.query.filter(Channel.kind == 'channel', Channel.is_private.is_(False),
                                 Channel.is_archived.is_(False))
    if q:
        like = f'%{q.strip()[:80]}%'
        query = query.filter(or_(Channel.name.ilike(like), Channel.topic.ilike(like)))
    chans = query.order_by(Channel.last_message_at.desc().nullslast(), Channel.id.desc()).limit(limit).all()
    return [channel_json(c, user) for c in chans]


def for_ref(user, ref_type, ref_key) -> list:
    """Channels about this object that the user can see."""
    chans = (visible_channels_query(user).filter(Channel.ref_type == ref_type, Channel.ref_key == str(ref_key))
             .order_by(Channel.last_message_at.desc().nullslast()).limit(20).all())
    return [channel_json(c, user) for c in chans]


# ── Channels ───────────────────────────────────────────────────────────────

def _system(channel, text, actor=None):
    db.session.add(ChannelMessage(channel_id=channel.id, user_id=actor.id if actor else None, kind='system',
                                  content=text[:500]))


def _clean_name(name):
    name = re.sub(r'\s+', ' ', (name or '').strip())[:NAME_MAX]
    return name


def _users(ids, exclude=None):
    ids = {int(i) for i in (ids or []) if str(i).isdigit() and int(i) != exclude}
    return User.query.filter(User.id.in_(ids)).all() if ids else []


def create_channel(user, name, topic=None, is_private=False, member_ids=None, ref_type=None, ref_key=None):
    from app.features.messages.refs_core import resolve
    name = _clean_name(name)
    if not name:
        return None, 'A channel needs a name.'
    since = _now() - datetime.timedelta(days=1)
    if not _is_admin(user) and Channel.query.filter(Channel.created_by == user.id, Channel.kind == 'channel',
                                                    Channel.created_at > since).count() >= _limit('channels_per_day', 20):
        return None, 'Too many channels created today — try again tomorrow.'
    ref = resolve(ref_type, ref_key) if ref_type else None
    if ref_type and not ref:
        return None, 'What this channel is about was not found.'
    c = Channel(kind='channel', name=name, topic=(topic or '').strip()[:TOPIC_MAX] or None,
                is_private=bool(is_private), created_by=user.id, last_message_at=_now(),
                ref_type=ref['kind'] if ref else None, ref_key=ref['key'] if ref else None,
                ref_label=ref['label'] if ref else None)
    db.session.add(c)
    db.session.flush()
    db.session.add(ChannelMember(channel_id=c.id, user_id=user.id, role='owner'))
    _system(c, f'{user.get_username()} created the channel', user)
    others = _users(member_ids, exclude=user.id)[:_limit('members_max', 500)]
    for u in others:
        db.session.add(ChannelMember(channel_id=c.id, user_id=u.id, role='member'))
    if others:
        _system(c, f'{user.get_username()} added {", ".join(u.get_username() for u in others)}', user)
    db.session.commit()
    for u in others:
        _notify_invite(c, u, user)
    from app.core.utils.activity_log import log_activity
    log_activity('channel.create', f'Channel "{c.name}" created', target_type='channel', target_id=c.id,
                 target_uuid=c.uuid, is_public=not c.is_private, actor_id=user.id)
    return c, ''


def direct_with(user, other_id):
    """The direct conversation between the two users, made the first time."""
    other = db.session.get(User, other_id) if str(other_id).isdigit() else None
    if not other or other.id == user.id:
        return None, 'User not found.'
    mine = db.session.query(ChannelMember.channel_id).filter(ChannelMember.user_id == user.id)
    theirs = db.session.query(ChannelMember.channel_id).filter(ChannelMember.user_id == other.id)
    c = Channel.query.filter(Channel.kind == 'direct', Channel.id.in_(mine), Channel.id.in_(theirs)).first()
    if c:
        return c, ''
    c = Channel(kind='direct', is_private=True, created_by=user.id, last_message_at=_now())
    db.session.add(c)
    db.session.flush()
    db.session.add_all([ChannelMember(channel_id=c.id, user_id=user.id, role='member'),
                        ChannelMember(channel_id=c.id, user_id=other.id, role='member')])
    db.session.commit()
    return c, ''


def update_channel(c, user, name=None, topic=None, is_private=None, is_archived=None, members_can_invite=None):
    changes = []
    if name is not None:
        name = _clean_name(name)
        if not name:
            return 'A channel needs a name.'
        if name != c.name:
            changes.append(f'renamed the channel to "{name}"')
            c.name = name
    if topic is not None:
        topic = topic.strip()[:TOPIC_MAX] or None
        if topic != c.topic:
            changes.append('changed the topic' if topic else 'removed the topic')
            c.topic = topic
    if is_private is not None and bool(is_private) != c.is_private:
        c.is_private = bool(is_private)
        changes.append('made the channel private' if c.is_private else 'made the channel public')
    if is_archived is not None and bool(is_archived) != c.is_archived:
        c.is_archived = bool(is_archived)
        changes.append('archived the channel' if c.is_archived else 'reopened the channel')
    if members_can_invite is not None and bool(members_can_invite) != c.members_can_invite:
        c.members_can_invite = bool(members_can_invite)
        changes.append('let every member add people' if c.members_can_invite else 'let only moderators add people')
    for text in changes:
        _system(c, f'{user.get_username()} {text}', user)
    db.session.commit()
    return ''


AVATAR_DIR = os.path.join('app', 'static', 'uploads', 'channels')
AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_SIZE = 256


def avatar_url(c):
    return f'/static/uploads/channels/{c.avatar}' if c.avatar else None


def _remove_avatar_file(name):
    if name and re.fullmatch(r'[0-9a-f]{32}\.png', name):
        try:
            os.remove(os.path.join(AVATAR_DIR, name))
        except OSError:
            pass


def set_avatar(c, user, file_storage):
    """The channel's picture: any image (PNG, JPEG, GIF, WebP) up to 2 MB, cropped square, re-encoded as a
    256 px PNG (nothing of the uploaded file is kept as is)."""
    from PIL import Image, ImageOps
    data = file_storage.read(AVATAR_MAX_BYTES + 1) if file_storage else b''
    if not data:
        return 'Choose an image.'
    if len(data) > AVATAR_MAX_BYTES:
        return 'The image is larger than 2 MB.'
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in ('PNG', 'JPEG', 'GIF', 'WEBP'):
            return 'PNG, JPEG, GIF or WebP only.'
        img.seek(0)
        img = ImageOps.fit(ImageOps.exif_transpose(img).convert('RGBA'), (AVATAR_SIZE, AVATAR_SIZE))
    except Exception:
        return 'This file is not an image.'
    os.makedirs(AVATAR_DIR, exist_ok=True)
    name = f'{uuid_mod.uuid4().hex}.png'
    img.save(os.path.join(AVATAR_DIR, name), 'PNG', optimize=True)
    old, c.avatar = c.avatar, name
    _system(c, f'{user.get_username()} changed the channel picture', user)
    db.session.commit()
    _remove_avatar_file(old)
    return ''


FILES_DIR = ('uploads', 'messages')       # under the app root, not static: served by messages.file (rights checked)
IMAGE_MAX_BYTES = 5 * 1024 * 1024
IMAGE_MAX_SIDE = 2400


def files_dir(c=None):
    from flask import current_app
    base = os.path.join(current_app.root_path, *FILES_DIR)
    return os.path.join(base, c.uuid) if c else base


def save_image(c, user, file_storage):
    """An image for a message: PNG, JPEG, GIF or WebP up to 5 MB, re-encoded (JPEG stays JPEG, the rest becomes
    PNG, at most 2400 px a side) — nothing of the uploaded file is kept as is. Returns (url, name, error)."""
    from PIL import Image, ImageOps
    data = file_storage.read(IMAGE_MAX_BYTES + 1) if file_storage else b''
    if not data:
        return None, None, 'Choose an image.'
    if len(data) > IMAGE_MAX_BYTES:
        return None, None, 'The image is larger than 5 MB.'
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        if fmt not in ('PNG', 'JPEG', 'GIF', 'WEBP'):
            return None, None, 'PNG, JPEG, GIF or WebP only.'
        img.seek(0)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
    except Exception:
        return None, None, 'This file is not an image.'
    os.makedirs(files_dir(c), exist_ok=True)
    ext = 'jpg' if fmt == 'JPEG' else 'png'
    name = f'{uuid_mod.uuid4().hex}.{ext}'
    if ext == 'jpg':
        img.convert('RGB').save(os.path.join(files_dir(c), name), 'JPEG', quality=88, optimize=True)
    else:
        img.convert('RGBA').save(os.path.join(files_dir(c), name), 'PNG', optimize=True)
    original = re.sub(r'[^\w .-]', '', (file_storage.filename or 'image'))[:60] or 'image'
    return f'/messages/files/{c.uuid}/{name}', original, ''


def file_path(c, name):
    if not re.fullmatch(r'[0-9a-f]{32}\.(png|jpg)', name or ''):
        return None
    path = os.path.join(files_dir(c), name)
    return path if os.path.isfile(path) else None


def remove_avatar(c, user):
    old, c.avatar = c.avatar, None
    if old:
        _system(c, f'{user.get_username()} removed the channel picture', user)
    db.session.commit()
    _remove_avatar_file(old)


def delete_channel(c):
    import shutil
    _remove_avatar_file(c.avatar)
    shutil.rmtree(files_dir(c), ignore_errors=True)       # its message images
    db.session.delete(c)
    db.session.commit()


def set_invite(c, user, enabled=True):
    """Make (or renew) the invite link, or turn it off."""
    import secrets
    c.invite_code = secrets.token_urlsafe(18) if enabled else None
    _system(c, f'{user.get_username()} ' + ('made a new invite link' if enabled else 'turned the invite link off'), user)
    db.session.commit()


def join_by_code(user, code):
    c = Channel.query.filter_by(invite_code=code).first() if code else None
    if not c or c.kind != 'channel' or c.is_archived:
        return None, 'This invite link is not valid anymore.'
    if not member(c, user.id):
        if c.members.count() >= _limit('members_max', 500):
            return None, 'This channel is full.'
        db.session.add(ChannelMember(channel_id=c.id, user_id=user.id, role='member'))
        _system(c, f'{user.get_username()} joined with the invite link', user)
        db.session.commit()
    return c, ''


def people(user, q=None, org=None, channel=None, page=1, per_page=30, ids_only=False):
    """The people you can add: verified accounts, with their organisations; filter by name and organisation
    ('mine' = any of yours). channel: members are flagged (already in it)."""
    from app.core.db_class.user import Organisation, user_organisation
    query = User.query.filter(User.is_verified.is_(True), User.id != user.id)
    if q:
        q = q.strip()[:80]
        like = f'%{q}%'
        query = query.filter(or_(User.username.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like),
                                 (User.first_name + ' ' + User.last_name).ilike(like)))
    my_orgs = [o.id for o in getattr(user, 'organisations', [])]
    org_ids = my_orgs if org == 'mine' else ([int(org)] if str(org or '').isdigit() else None)
    if org_ids is not None:
        query = query.filter(User.id.in_(db.session.query(user_organisation.c.user_id)
                                         .filter(user_organisation.c.organisation_id.in_(org_ids or [-1]))))
    query = query.order_by(func.lower(func.coalesce(User.username, User.first_name)), User.id)
    if ids_only:
        return [u.id for u in query.limit(500)]
    total = query.count()
    rows = query.offset((max(page, 1) - 1) * per_page).limit(per_page).all()
    in_channel = {m.user_id for m in channel.members} if channel else set()
    return {
        'users': [{**user_json(u), 'username': u.get_username(),
                   'orgs': [{'id': o.id, 'name': o.name, 'text': o.label or o.name, 'color': o.color or '#6f42c1',
                             'icon': o.icon or 'fa-building'} for o in u.organisations],
                   'in_channel': u.id in in_channel} for u in rows],
        'total': total, 'page': page, 'pages': max(1, -(-total // per_page)),
        'orgs': [{'id': o.id, 'name': o.name, 'mine': o.id in my_orgs}
                 for o in Organisation.query.order_by(Organisation.name).all()],
        'my_orgs': my_orgs,
    }


def join(c, user):
    if member(c, user.id):
        return True
    if c.kind != 'channel' or c.is_private or c.is_archived:
        return False
    db.session.add(ChannelMember(channel_id=c.id, user_id=user.id, role='member'))
    _system(c, f'{user.get_username()} joined', user)
    db.session.commit()
    return True


def leave(c, user):
    m = member(c, user.id)
    if not m or c.kind != 'channel':
        return 'You are not in this channel.'
    if m.role == 'owner':
        heir = (ChannelMember.query.filter(ChannelMember.channel_id == c.id, ChannelMember.user_id != user.id)
                .order_by(db.case((ChannelMember.role == 'moderator', 0), else_=1), ChannelMember.joined_at).first())
        if heir:
            heir.role = 'owner'
            _system(c, f'{heir.user.get_username()} is now the owner', user)
    db.session.delete(m)
    _system(c, f'{user.get_username()} left', user)
    db.session.commit()
    return ''


def add_members(c, actor, user_ids):
    if c.kind != 'channel':
        return [], 'People are added to channels only.'
    have = {m.user_id for m in c.members}
    room = _limit('members_max', 500) - len(have)
    new = [u for u in _users(user_ids) if u.id not in have][:max(room, 0)]
    for u in new:
        db.session.add(ChannelMember(channel_id=c.id, user_id=u.id, role='member'))
    if new:
        _system(c, f'{actor.get_username()} added {", ".join(u.get_username() for u in new)}', actor)
    db.session.commit()
    for u in new:
        _notify_invite(c, u, actor)
    return new, ''


def remove_member(c, actor, user_id):
    m = member(c, user_id)
    if not m:
        return 'Not a member.'
    if m.role == 'owner':
        return 'The owner can\'t be removed — give the channel to someone else first.'
    if m.role == 'moderator' and not can_own(c, actor):
        return 'Only the owner removes a moderator.'
    name = m.user.get_username()
    db.session.delete(m)
    _system(c, f'{actor.get_username()} removed {name}', actor)
    db.session.commit()
    return ''


def set_role(c, actor, user_id, role):
    if role not in ROLES:
        return 'Unknown role.'
    m = member(c, user_id)
    if not m:
        return 'Not a member.'
    if m.role == role:
        return ''
    if role == 'owner':     # ownership moves: the current owner becomes a moderator
        for o in c.members.filter_by(role='owner'):
            o.role = 'moderator'
    elif m.role == 'owner':
        return 'Give the channel to someone else first.'
    m.role = role
    _system(c, f'{actor.get_username()} made {m.user.get_username()} {"the owner" if role == "owner" else "a " + role}', actor)
    db.session.commit()
    return ''


def clear_for_me(c, user):
    """Delete a conversation for me: its messages so far are hidden for me only (the others keep them) and it
    leaves my list until someone writes again. A channel you leave instead."""
    m = member(c, user.id)
    if not m:
        return 'You are not in this conversation.'
    m.cleared_id = db.session.query(func.max(ChannelMessage.id)).filter(ChannelMessage.channel_id == c.id).scalar() or 0
    m.last_read_id = max(m.last_read_id, m.cleared_id)
    db.session.commit()
    return ''


def set_member_flags(c, user, muted=None, starred=None):
    m = member(c, user.id)
    if not m:
        return False
    if muted is not None:
        m.is_muted = bool(muted)
    if starred is not None:
        m.is_starred = bool(starred)
    db.session.commit()
    return True


# ── Messages ───────────────────────────────────────────────────────────────

def messages(c, user, before=None, after=None, limit=None, around=None):
    limit = min(int(limit or _limit('page_size', 50)), 200)
    q = c.messages
    me = member(c, user.id)
    if me and me.cleared_id:
        q = q.filter(ChannelMessage.id > me.cleared_id)
    if after:
        rows = q.filter(ChannelMessage.id > int(after)).order_by(ChannelMessage.id).limit(limit).all()
        return [message_json(m, user) for m in rows], False
    if before:
        q = q.filter(ChannelMessage.id < int(before))
    rows = q.order_by(ChannelMessage.id.desc()).limit(limit + 1).all()
    more = len(rows) > limit
    return [message_json(m, user) for m in reversed(rows[:limit])], more


def post_message(c, user, content, reply_to_id=None):
    content = (content or '').strip()
    if not content:
        return None, 'The message is empty.'
    if len(content) > _limit('message_max_chars', 8000):
        return None, f'{_limit("message_max_chars", 8000)} characters at most.'
    if not member(c, user.id):
        if not join(c, user):
            return None, 'You can\'t write here.'
    reply = None
    if reply_to_id:
        reply = ChannelMessage.query.filter_by(id=int(reply_to_id), channel_id=c.id).first()
    m = ChannelMessage(channel_id=c.id, user_id=user.id, content=content, reply_to_id=reply.id if reply else None)
    db.session.add(m)
    c.last_message_at = _now()
    db.session.flush()
    me = member(c, user.id)
    me.last_read_id = m.id
    db.session.commit()
    _notify_message(c, m, user)
    return m, ''


def edit_message(m, user, content):
    if m.user_id != user.id or m.kind != 'message' or m.deleted_at:
        return 'Only the author edits a message.'
    content = (content or '').strip()
    if not content or len(content) > _limit('message_max_chars', 8000):
        return 'The message is empty or too long.'
    m.content, m.edited_at = content, _now()
    db.session.commit()
    return ''


def delete_message(m, user):
    if m.user_id != user.id and not can_manage(m.channel, user):
        return 'Only the author or a moderator deletes a message.'
    m.deleted_at, m.is_pinned = _now(), False
    ChannelReaction.query.filter_by(message_id=m.id).delete()
    db.session.commit()
    return ''


def toggle_reaction(m, user, emoji):
    allowed = list(REACTIONS.value or [])
    if emoji not in allowed:
        return 'This reaction is not offered.'
    if m.deleted_at or m.kind != 'message':
        return 'This message can\'t get reactions.'
    r = ChannelReaction.query.filter_by(message_id=m.id, user_id=user.id, emoji=emoji).first()
    if r:
        db.session.delete(r)
    else:
        db.session.add(ChannelReaction(message_id=m.id, user_id=user.id, emoji=emoji))
    db.session.commit()
    return ''


def toggle_pin(m, user):
    if not can_manage(m.channel, user) and m.channel.kind != 'direct':
        return 'Only moderators pin messages.'
    if m.deleted_at or m.kind != 'message':
        return 'This message can\'t be pinned.'
    m.is_pinned = not m.is_pinned
    if m.is_pinned:
        _system(m.channel, f'{user.get_username()} pinned a message', user)
    db.session.commit()
    return ''


def mark_read(c, user, upto=None):
    me = member(c, user.id)
    if not me:
        return
    last = upto or db.session.query(func.max(ChannelMessage.id)).filter(ChannelMessage.channel_id == c.id).scalar() or 0
    if int(last) > me.last_read_id:
        me.last_read_id = int(last)
        db.session.commit()


def search(user, q, channel=None, limit=40):
    q = (q or '').strip()[:100]
    if len(q) < 2:
        return []
    mine = db.session.query(ChannelMember.channel_id).filter(ChannelMember.user_id == user.id)
    query = ChannelMessage.query.filter(ChannelMessage.kind == 'message', ChannelMessage.deleted_at.is_(None),
                                        ChannelMessage.content.ilike(f'%{q}%'))
    query = query.filter(ChannelMessage.channel_id == channel.id) if channel else \
        query.filter(ChannelMessage.channel_id.in_(mine))
    out = []
    cleared = dict(db.session.query(ChannelMember.channel_id, ChannelMember.cleared_id)
                   .filter(ChannelMember.user_id == user.id).all())
    for m in query.order_by(ChannelMessage.id.desc()).limit(limit * 2):
        if m.id <= cleared.get(m.channel_id, 0):
            continue
        if len(out) >= limit:
            break
        out.append({**message_json(m, user), 'channel': {'uuid': m.channel.uuid,
                                                         'name': channel_json(m.channel, user)['name'],
                                                         'kind': m.channel.kind}})
    return out


# ── Notifications ──────────────────────────────────────────────────────────

def _link(c, m=None):
    return f'/messages/c/{c.uuid}' + (f'?m={m.id}' if m else '')


def _notify_invite(c, u, actor):
    from app.features.notification.notification_core import create_notification
    create_notification(u.id, 'message_invite', f'{actor.get_username()} added you to #{c.name}',
                        body=c.topic, link=_link(c))


def _notify_message(c, m, author):
    from app.core.db_class.notification import Notification
    from app.features.notification.notification_core import create_notification
    text = MENTION.sub(lambda x: '@' + x.group(1), m.content)
    text = re.sub(r'#\[([^\]]{1,120})\]\([a-z]+:[^)]+\)', r'#\1', text)[:200]
    members = {x.user_id: x for x in c.members}
    mentioned = {int(i) for _, i in MENTION.findall(m.content)} - {author.id}
    done = set()
    for uid in mentioned:
        mm = members.get(uid)
        if mm is None or (c.kind == 'channel' and c.is_private and mm is None):
            continue                      # only people who can read the conversation are told
        create_notification(uid, 'message_mention',
                            f'{author.get_username()} mentioned you in ' + ('a message' if c.kind == 'direct' else f'#{c.name}'),
                            body=text, link=_link(c, m))
        done.add(uid)
    if c.kind == 'direct':
        for uid, mm in members.items():
            if uid == author.id or uid in done or mm.is_muted:
                continue
            # one unread notification per conversation is enough
            if Notification.query.filter_by(user_id=uid, notif_type='message_direct', is_read=False,
                                            link=_link(c)).first():
                continue
            create_notification(uid, 'message_direct', f'New message from {author.get_username()}', body=text,
                                link=_link(c))


# ── Messages by email ──────────────────────────────────────────────────────
# NotificationPreference.email_messages: off (default) | direct (direct messages and mentions) | all (also every
# channel you're in). A message is emailed once it has been unread for messages.email.delay_minutes — read it in
# time and no email goes; several messages go in one email. Muted conversations never; ChannelMember.emailed_id
# remembers what was already sent.

EMAIL = setting('messages.email')           # app/config/messages.email.json


def _email_conf(key, default):
    try:
        return int((EMAIL.value or {}).get(key, default))
    except Exception:
        return default


def _mentions(content, user_id):
    return any(int(i) == user_id for _, i in MENTION.findall(content or ''))


def email_digest(user, now=None):
    """[{channel, link, messages: [{author, text, at}], more}] still unread and due for this user's email."""
    from app.core.db_class.notification import NotificationPreference
    pref = NotificationPreference.query.filter_by(user_id=user.id).first()
    mode = pref.email_messages if pref else 'off'
    if mode not in ('direct', 'all'):
        return []
    now = now or _now()
    due = now - datetime.timedelta(minutes=_email_conf('delay_minutes', 10))
    out = []
    for m in ChannelMember.query.filter_by(user_id=user.id, is_muted=False).all():
        floor = max(m.last_read_id, m.emailed_id, m.cleared_id)
        rows = (ChannelMessage.query.filter(ChannelMessage.channel_id == m.channel_id, ChannelMessage.id > floor,
                                            ChannelMessage.kind == 'message', ChannelMessage.deleted_at.is_(None),
                                            ChannelMessage.user_id != user.id, ChannelMessage.created_at <= due)
                .order_by(ChannelMessage.id).all())
        c = m.channel
        if c.kind == 'channel' and mode != 'all':
            rows = [r for r in rows if _mentions(r.content, user.id)]
        if not rows:
            continue
        keep = _email_conf('max_messages_per_conversation', 3)
        out.append({'member': m, 'channel': c, 'upto': rows[-1].id,
                    'name': channel_json(c, user)['name'], 'kind': c.kind,
                    'messages': [{'author': user_json(r.author)['name'], 'at': r.created_at,
                                  'text': _plain(r.content)[:400]} for r in rows[-keep:]],
                    'more': max(0, len(rows) - keep)})
    out.sort(key=lambda d: d['upto'], reverse=True)
    return out


def _plain(text):
    text = MENTION.sub(lambda x: '@' + x.group(1), text or '')
    text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'[image \1]', text)
    text = re.sub(r'#\[([^\]]{1,120})\]\([a-z]+:[^)]+\)', r'#\1', text)
    return re.sub(r'[ \t]+', ' ', text).strip()


def send_due_emails(now=None) -> int:
    """One pass: every user who chose emails and has due unread messages gets one email. Returns emails sent."""
    from flask import current_app
    from flask_mail import Message
    from app import mail
    from app.core.db_class.notification import NotificationPreference
    from app.core.utils.mail_status import is_email_available
    if not is_email_available():
        return 0
    now = now or _now()
    users = (User.query.join(NotificationPreference, NotificationPreference.user_id == User.id)
             .filter(NotificationPreference.email_messages.in_(('direct', 'all')), User.is_verified.is_(True),
                     User.email.isnot(None)).limit(_email_conf('max_emails_per_pass', 200) * 5).all())
    try:
        from app.features.alert.alert_core import _public_base_url
        base = _public_base_url()
    except Exception:
        base = ''
    sent = 0
    env = current_app.jinja_env
    for user in users:
        if sent >= _email_conf('max_emails_per_pass', 200):
            break
        convs = email_digest(user, now)
        if not convs:
            continue
        shown = convs[:_email_conf('max_conversations', 10)]
        for d in shown:
            d['url'] = f"{base}/messages/c/{d['channel'].uuid}"
        total = sum(len(d['messages']) + d['more'] for d in convs)
        first = convs[0]
        who = first['messages'][-1]['author']
        subject = (f"Rulezet — {who} wrote to you" if len(convs) == 1 and first['kind'] == 'direct'
                   else f"Rulezet — {who} in #{first['name']}" if len(convs) == 1
                   else f"Rulezet — {total} unread messages in {len(convs)} conversations")
        ctx = dict(user=user, conversations=shown, hidden=len(convs) - len(shown), total=total, base_url=base,
                   messages_url=f'{base}/messages/', prefs_url=f'{base}/notifications/?tab=prefs', year=now.year)
        try:
            msg = Message(subject=subject, recipients=[user.email])
            msg.body = env.get_template('messages/email/messages_email.txt').render(**ctx)
            msg.html = env.get_template('messages/email/messages_email.html').render(**ctx)
            mail.send(msg)
        except Exception as e:
            print(f'[messages] email to user {user.id} failed: {e}', flush=True)
            db.session.rollback()
            break
        for d in convs:                      # everything due counts as sent, shown in full or not
            d['member'].emailed_id = d['upto']
        db.session.commit()
        sent += 1
    return sent
