"""
oversight_core.py — admins watch how messages are used (page /admin/messages) without reading them.

Shown: the conversations (channel or direct, members, messages, last activity) and, for one conversation, its
messages as who / when / size / image — never their text. An admin may reveal one message on purpose (abuse,
spam, a report): that reveal is itself written to the activity log (who revealed which message, when).

    conversations(q, kind, page)   · messages_meta(channel, before)   · reveal(message, admin)
"""
from __future__ import annotations

from sqlalchemy import func, or_

from app import db
from app.core.db_class.message import Channel, ChannelMember, ChannelMessage
from app.core.db_class.user import User
from app.features.messages.messages_core import user_json

PER_PAGE = 30


def conversations(q=None, kind=None, page=1):
    query = Channel.query
    if kind in ('channel', 'direct'):
        query = query.filter(Channel.kind == kind)
    if q:
        like = f'%{q.strip()[:80]}%'
        member_ids = db.session.query(ChannelMember.channel_id).join(User, User.id == ChannelMember.user_id).filter(
            or_(User.username.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like), User.email.ilike(like)))
        query = query.filter(or_(Channel.name.ilike(like), Channel.id.in_(member_ids)))
    total = query.count()
    rows = query.order_by(Channel.last_message_at.desc().nullslast(), Channel.id.desc()) \
        .offset((max(page, 1) - 1) * PER_PAGE).limit(PER_PAGE).all()
    ids = [c.id for c in rows]
    counts = dict(db.session.query(ChannelMessage.channel_id, func.count(ChannelMessage.id))
                  .filter(ChannelMessage.channel_id.in_(ids), ChannelMessage.kind == 'message')
                  .group_by(ChannelMessage.channel_id).all()) if ids else {}
    out = []
    for c in rows:
        members = c.members.limit(8).all()
        out.append({'uuid': c.uuid, 'kind': c.kind, 'name': c.name, 'is_private': c.is_private,
                    'is_archived': c.is_archived, 'messages': counts.get(c.id, 0), 'member_count': c.members.count(),
                    'members': [{**user_json(m.user), 'role': m.role} for m in members],
                    'last_message_at': c.last_message_at.isoformat() + 'Z' if c.last_message_at else None,
                    'created_at': c.created_at.isoformat() + 'Z' if c.created_at else None})
    return {'conversations': out, 'total': total, 'page': page, 'pages': max(1, -(-total // PER_PAGE))}


def messages_meta(c, before=None, limit=100):
    q = c.messages.filter(ChannelMessage.kind.in_(('message', 'feed')))
    if before:
        q = q.filter(ChannelMessage.id < int(before))
    rows = q.order_by(ChannelMessage.id.desc()).limit(limit + 1).all()
    return {'messages': [{'id': m.id, 'kind': m.kind,
                          'author': user_json(m.author) if m.kind == 'message' else {'name': 'Rulezet', 'id': None},
                          'created_at': m.created_at.isoformat() + 'Z', 'length': len(m.content or ''),
                          'image': '/messages/files/' in (m.content or ''), 'reply': bool(m.reply_to_id),
                          'edited': bool(m.edited_at), 'deleted': bool(m.deleted_at), 'pinned': m.is_pinned,
                          'reactions': len(m.reactions)} for m in rows[:limit]],
            'has_more': len(rows) > limit}


def reveal(m, admin):
    """One message's text, for an admin who asked for it — logged."""
    from app.core.utils.activity_log import log_activity
    c = m.channel
    where = 'a direct conversation' if c.kind == 'direct' else f'#{c.name}'
    log_activity('admin.message_reveal', f'{admin.get_username()} revealed a message of '
                 f'{m.author.get_username() if m.author else "a deleted user"} in {where}',
                 target_type='channel', target_id=c.id, target_uuid=c.uuid, is_public=False, level='warning',
                 icon='fa-solid fa-eye', extra={'message_id': m.id, 'author_id': m.user_id})
    return {'id': m.id, 'content': m.content if not m.deleted_at else m.content, 'deleted': bool(m.deleted_at)}
