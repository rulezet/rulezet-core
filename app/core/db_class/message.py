"""Messages: channels (public or private, with members and roles) and direct conversations between users
(page /messages/, logic in app/features/messages/). A channel can be about something in Rulezet — a rule,
a bundle, a CVE… (ref_type / ref_key), started from that object's page."""
import datetime
import uuid as _uuid

from app import db


def _now():
    return datetime.datetime.utcnow()


def _uuid4():
    return str(_uuid.uuid4())


class Channel(db.Model):
    __tablename__ = 'channel'

    id              = db.Column(db.Integer, primary_key=True)
    uuid            = db.Column(db.String(36), unique=True, nullable=False, index=True, default=_uuid4)
    kind            = db.Column(db.String(16), nullable=False, default='channel', index=True)   # channel | direct
    name            = db.Column(db.String(80), nullable=True)
    topic           = db.Column(db.String(300), nullable=True)
    is_private      = db.Column(db.Boolean, nullable=False, default=False, server_default='false', index=True)
    is_archived     = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    # What the conversation is about (rule:12, bundle:4, cve:CVE-2024-1234, attack:T1059, blog:<uuid>, repo:<uuid>)
    ref_type        = db.Column(db.String(20), nullable=True, index=True)
    ref_key         = db.Column(db.String(120), nullable=True, index=True)
    ref_label       = db.Column(db.String(255), nullable=True)
    avatar          = db.Column(db.String(80), nullable=True)
    # Private channels: whoever has the link /messages/join/<invite_code> joins (None = no link)
    invite_code     = db.Column(db.String(40), nullable=True, unique=True, index=True)
    members_can_invite = db.Column(db.Boolean, nullable=False, default=False, server_default='false')    # file under static/uploads/channels/ (messages_core.set_avatar)
    created_by      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at      = db.Column(db.DateTime, nullable=False, default=_now)
    last_message_at = db.Column(db.DateTime, nullable=True, index=True)

    members = db.relationship('ChannelMember', backref='channel', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('ChannelMessage', backref='channel', lazy='dynamic', cascade='all, delete-orphan')


class ChannelMember(db.Model):
    __tablename__ = 'channel_member'
    __table_args__ = (db.UniqueConstraint('channel_id', 'user_id', name='uq_channel_member'),)

    id           = db.Column(db.Integer, primary_key=True)
    channel_id   = db.Column(db.Integer, db.ForeignKey('channel.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    role         = db.Column(db.String(16), nullable=False, default='member')   # owner | moderator | member
    joined_at    = db.Column(db.DateTime, nullable=False, default=_now)
    last_read_id = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    is_muted     = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    is_starred   = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    # "Delete for me": messages up to this id are hidden for this member; the conversation leaves the list until a newer one
    cleared_id   = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    # Messages by email: messages up to this id were already in an email to this member
    emailed_id   = db.Column(db.Integer, nullable=False, default=0, server_default='0')

    user = db.relationship('User', lazy='joined')


class ChannelMessage(db.Model):
    __tablename__ = 'channel_message'

    id         = db.Column(db.Integer, primary_key=True)
    uuid       = db.Column(db.String(36), unique=True, nullable=False, index=True, default=_uuid4)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    kind       = db.Column(db.String(16), nullable=False, default='message')   # message | system
    content    = db.Column(db.Text, nullable=False)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('channel_message.id', ondelete='SET NULL'), nullable=True)
    is_pinned  = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    created_at = db.Column(db.DateTime, nullable=False, default=_now, index=True)
    edited_at  = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    author = db.relationship('User', lazy='joined')
    reply_to = db.relationship('ChannelMessage', remote_side=[id], lazy='joined', join_depth=1)
    reactions = db.relationship('ChannelReaction', backref='message', lazy='selectin', cascade='all, delete-orphan')


class ChannelReaction(db.Model):
    __tablename__ = 'channel_reaction'
    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_channel_reaction'),)

    id         = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('channel_message.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    emoji      = db.Column(db.String(16), nullable=False)
