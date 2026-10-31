"""
inbox_core.py — notifications handled like an email inbox (page /notifications/).

    FOLDERS                       inbox · unread · starred · archived · all
    query(user_id, …)             the notifications of a folder / label / categories / search / dates
    counts(user_id)               unread in the inbox, starred, archived, per label
    bulk(user_id, ids, action)    read · unread · star · unstar · archive · unarchive · delete · label_add · label_remove
    labels: list_labels, create_label, update_label, delete_label
    auto_archive(user_id)         read notifications older than the user's auto_archive_days go to the archive

Every function only ever touches the given user's own notifications and labels.
"""
from __future__ import annotations

import datetime
import re

from sqlalchemy import func

from app import db
from app.core.db_class.notification import (Notification, NotificationLabel, NotificationPreference,
                                            notification_label_link)

FOLDERS = ('inbox', 'unread', 'starred', 'archived', 'all')
ACTIONS = ('read', 'unread', 'star', 'unstar', 'archive', 'unarchive', 'delete', 'label_add', 'label_remove')
MAX_LABELS = 30
_COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')


def query(user_id, folder='inbox', label_id=None, types=None, search=None, date_from=None, date_to=None):
    q = Notification.query.filter(Notification.user_id == user_id)
    if folder == 'inbox':
        q = q.filter(Notification.is_archived.is_(False))
    elif folder == 'unread':
        q = q.filter(Notification.is_read.is_(False), Notification.is_archived.is_(False))
    elif folder == 'starred':
        q = q.filter(Notification.is_starred.is_(True))
    elif folder == 'archived':
        q = q.filter(Notification.is_archived.is_(True))
    if label_id:
        q = q.filter(Notification.id.in_(db.session.query(notification_label_link.c.notification_id)
                                         .filter(notification_label_link.c.label_id == label_id)))
    if types:
        q = q.filter(Notification.notif_type.in_(list(types)))
    if search and search.strip():
        like = f'%{search.strip()}%'
        q = q.filter(db.or_(Notification.title.ilike(like), Notification.body.ilike(like)))
    for value, op in ((date_from, '>='), (date_to, '<')):
        if not value:
            continue
        try:
            day = datetime.datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            continue
        q = q.filter(Notification.created_at >= day) if op == '>=' else \
            q.filter(Notification.created_at < day + datetime.timedelta(days=1))
    return q


def counts(user_id) -> dict:
    base = Notification.query.filter(Notification.user_id == user_id)
    by_type = dict(db.session.query(Notification.notif_type, func.count(Notification.id))
                   .filter(Notification.user_id == user_id, Notification.is_archived.is_(False),
                           Notification.is_read.is_(False))
                   .group_by(Notification.notif_type).all())
    per_label = dict(db.session.query(notification_label_link.c.label_id, func.count())
                     .join(Notification, Notification.id == notification_label_link.c.notification_id)
                     .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
                     .group_by(notification_label_link.c.label_id).all())
    return {
        'inbox': base.filter(Notification.is_archived.is_(False)).count(),
        'unread': base.filter(Notification.is_read.is_(False), Notification.is_archived.is_(False)).count(),
        'starred': base.filter(Notification.is_starred.is_(True)).count(),
        'archived': base.filter(Notification.is_archived.is_(True)).count(),
        'all': base.count(),
        'unread_by_type': by_type,
        'labels': [l.to_json(per_label.get(l.id, 0)) for l in list_labels(user_id)],
    }


def bulk(user_id, ids, action, label_id=None) -> tuple[int, str]:
    """(how many changed, error). ids: the user's notification ids (others are ignored)."""
    if action not in ACTIONS:
        return 0, 'Unknown action.'
    ids = [i for i in (ids or []) if isinstance(i, int)][:5000]
    if not ids:
        return 0, 'Nothing selected.'
    q = Notification.query.filter(Notification.user_id == user_id, Notification.id.in_(ids))
    now = datetime.datetime.utcnow()
    if action == 'delete':
        n = 0
        for notif in q.all():
            db.session.delete(notif)
            n += 1
        db.session.commit()
        return n, ''
    if action in ('label_add', 'label_remove'):
        label = NotificationLabel.query.filter_by(id=label_id, user_id=user_id).first()
        if not label:
            return 0, 'Label not found.'
        n = 0
        for notif in q.all():
            if action == 'label_add' and label not in notif.labels:
                notif.labels.append(label)
                n += 1
            elif action == 'label_remove' and label in notif.labels:
                notif.labels.remove(label)
                n += 1
        db.session.commit()
        return n, ''
    values = {'read': {Notification.is_read: True, Notification.read_at: now},
              'unread': {Notification.is_read: False, Notification.read_at: None},
              'star': {Notification.is_starred: True}, 'unstar': {Notification.is_starred: False},
              'archive': {Notification.is_archived: True, Notification.is_read: True},
              'unarchive': {Notification.is_archived: False}}[action]
    n = q.update(values, synchronize_session=False)
    db.session.commit()
    return n, ''


# ── Labels ────────────────────────────────────────────────────────────────

def list_labels(user_id):
    return NotificationLabel.query.filter_by(user_id=user_id).order_by(NotificationLabel.name).all()


def _clean(name, color):
    name = (name or '').strip()[:40]
    if not name:
        return None, None, 'A label needs a name.'
    color = (color or '#0d6efd').strip()
    if not _COLOR.match(color):
        return None, None, 'The colour must look like #0d6efd.'
    return name, color.lower(), ''


def create_label(user_id, name, color=None) -> tuple[NotificationLabel | None, str]:
    name, color, err = _clean(name, color)
    if err:
        return None, err
    if NotificationLabel.query.filter_by(user_id=user_id).count() >= MAX_LABELS:
        return None, f'{MAX_LABELS} labels at most.'
    if NotificationLabel.query.filter(NotificationLabel.user_id == user_id,
                                      func.lower(NotificationLabel.name) == name.lower()).first():
        return None, 'You already have a label with this name.'
    label = NotificationLabel(user_id=user_id, name=name, color=color)
    db.session.add(label)
    db.session.commit()
    return label, ''


def update_label(user_id, label_id, name=None, color=None) -> tuple[NotificationLabel | None, str]:
    label = NotificationLabel.query.filter_by(id=label_id, user_id=user_id).first()
    if not label:
        return None, 'Label not found.'
    name, color, err = _clean(name if name is not None else label.name, color if color is not None else label.color)
    if err:
        return None, err
    clash = NotificationLabel.query.filter(NotificationLabel.user_id == user_id, NotificationLabel.id != label.id,
                                           func.lower(NotificationLabel.name) == name.lower()).first()
    if clash:
        return None, 'You already have a label with this name.'
    label.name, label.color = name, color
    db.session.commit()
    return label, ''


def delete_label(user_id, label_id) -> bool:
    label = NotificationLabel.query.filter_by(id=label_id, user_id=user_id).first()
    if not label:
        return False
    db.session.execute(notification_label_link.delete().where(notification_label_link.c.label_id == label.id))
    db.session.delete(label)
    db.session.commit()
    return True


# ── Auto-archive ──────────────────────────────────────────────────────────

def auto_archive(user_id) -> int:
    pref = NotificationPreference.query.filter_by(user_id=user_id).first()
    days = (pref.auto_archive_days or 0) if pref else 0
    if days <= 0:
        return 0
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    n = (Notification.query.filter(Notification.user_id == user_id, Notification.is_read.is_(True),
                                   Notification.is_archived.is_(False), Notification.is_starred.is_(False),
                                   Notification.created_at < cutoff)
         .update({Notification.is_archived: True}, synchronize_session=False))
    if n:
        db.session.commit()
    return n
