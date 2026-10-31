"""In-app notifications and notification preferences.
"""
from app import db
import datetime
import json

from sqlalchemy import event
from sqlalchemy.orm import Session


# A notification can carry any of its owner's labels (the inbox's "Labels")
notification_label_link = db.Table(
    'notification_label_link',
    db.Column('notification_id', db.Integer, db.ForeignKey('notification.id', ondelete='CASCADE'), primary_key=True),
    db.Column('label_id', db.Integer, db.ForeignKey('notification_label.id', ondelete='CASCADE'), primary_key=True),
)


########################################
#   Notification                       #
########################################

class Notification(db.Model):
    """
    Persistent notification for a user.

    Types:
      new_rule          — a followed user created a new rule
      rule_update_found — GitHub update scan found pending updates
      job_created       — a background job was queued (linked to job_uuid)
      job_finished      — same job completed (updates the existing row)
    """
    __tablename__ = 'notification'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
                            nullable=False, index=True)

    # Discriminator
    notif_type  = db.Column(db.String(32), nullable=False, index=True)

    # Display
    title       = db.Column(db.String(255), nullable=False)
    body        = db.Column(db.String(500), nullable=True)
    link        = db.Column(db.String(512), nullable=True)
    icon        = db.Column(db.String(64),  nullable=True)   # FA class e.g. 'fa-solid fa-shield-halved'

    # Job tracking — only for job_created / job_finished
    job_uuid    = db.Column(db.String(36),  nullable=True, index=True)
    job_status  = db.Column(db.String(16),  nullable=True)   # mirrors BackgroundJob.status
    job_progress = db.Column(db.Integer,    nullable=True)   # 0-100

    # State
    is_read     = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at  = db.Column(db.DateTime, nullable=False,
                            default=datetime.datetime.utcnow, index=True)
    read_at     = db.Column(db.DateTime, nullable=True)
    # Inbox (like an email box): starred, archived (out of the inbox, still searchable), labels
    is_starred  = db.Column(db.Boolean, nullable=False, default=False, server_default='false', index=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False, server_default='false', index=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic',
                                                      cascade='all, delete-orphan'))
    labels = db.relationship('NotificationLabel', secondary=notification_label_link, lazy='selectin',
                             order_by='NotificationLabel.name')

    def is_job_active(self):
        return self.notif_type in ('job_created', 'job_finished') and \
               self.job_status not in ('done', 'failed', 'cancelled')

    def to_json(self):
        return {
            'id':           self.id,
            'notif_type':   self.notif_type,
            'title':        self.title,
            'body':         self.body,
            'link':         self.link,
            'icon':         self.icon,
            'job_uuid':     self.job_uuid,
            'job_status':   self.job_status,
            'job_progress': self.job_progress,
            'is_read':      self.is_read,
            'is_starred':   bool(self.is_starred),
            'is_archived':  bool(self.is_archived),
            'labels':       [{'id': l.id, 'name': l.name, 'color': l.color} for l in self.labels],
            'is_job_active': self.is_job_active(),
            'created_at':   self.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }


class NotificationPreference(db.Model):
    """Per-user opt-in/out for each notification category."""
    __tablename__ = 'notification_preference'

    id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
                        nullable=False, unique=True, index=True)

    # Follow-based (someone I follow does something)
    pref_follow_new_rule    = db.Column(db.Boolean, nullable=False, default=True)
    pref_follow_new_bundle  = db.Column(db.Boolean, nullable=False, default=True)
    pref_follow_new_comment = db.Column(db.Boolean, nullable=False, default=False)

    # Ownership-based (someone interacts with my content)
    pref_rule_comment   = db.Column(db.Boolean, nullable=False, default=True)
    pref_bundle_comment = db.Column(db.Boolean, nullable=False, default=True)

    # System
    pref_job_done  = db.Column(db.Boolean, nullable=False, default=True)  # GitHub import/update session finished
    pref_proposal  = db.Column(db.Boolean, nullable=False, default=True)
    pref_background_jobs = db.Column(db.Boolean, nullable=False, default=True)  # any BackgroundJob started/finished (bulk actions, connector pulls, sync schedule runs, ...)

    # Proposals & replies
    pref_proposal_comment  = db.Column(db.Boolean, nullable=False, default=True)
    pref_proposal_accepted = db.Column(db.Boolean, nullable=False, default=True)
    pref_comment_reply     = db.Column(db.Boolean, nullable=False, default=True)
    pref_mentioned         = db.Column(db.Boolean, nullable=False, default=True)

    # Platform content
    pref_blog_published = db.Column(db.Boolean, nullable=False, default=True)

    # GitHub sync schedules
    pref_sync_run_finished = db.Column(db.Boolean, nullable=False, default=True)

    # Admin task scheduler workflows — one toggle covers both the launch and
    # the finish notification, same "started & finished together" shape as
    # pref_background_jobs above.
    pref_workflow_runs = db.Column(db.Boolean, nullable=False, default=True)

    # Alerts ("tell me when...") — in-app notifications for every alert at
    # once; each alert still has its own email mode (Alert.email_mode).
    pref_alerts = db.Column(db.Boolean, nullable=False, default=True)

    # A rule I favorited had its content changed (issue #84)
    pref_favorite_rule_update = db.Column(db.Boolean, nullable=False, default=True)

    # Bundle forks: my bundle was forked, merge requests on my bundles / from my forks
    pref_bundle_fork = db.Column(db.Boolean, nullable=False, default=True)

    # Fine-grained: notification types never created for this user (JSON list of notif_type), and the
    # read notifications archived automatically after N days (0 = never)
    muted_types       = db.Column(db.Text, nullable=True)
    auto_archive_days = db.Column(db.Integer, nullable=False, default=0, server_default='0')

    def muted(self) -> set:
        try:
            value = json.loads(self.muted_types or '[]')
            return {str(v) for v in value} if isinstance(value, list) else set()
        except (TypeError, ValueError):
            return set()

    user = db.relationship('User', backref=db.backref(
        'notification_preference', uselist=False, cascade='all, delete-orphan'))

    def to_json(self):
        return {
            'follow_new_rule':    self.pref_follow_new_rule,
            'follow_new_bundle':  self.pref_follow_new_bundle,
            'follow_new_comment': self.pref_follow_new_comment,
            'rule_comment':       self.pref_rule_comment,
            'bundle_comment':     self.pref_bundle_comment,
            'job_done':           self.pref_job_done,
            'proposal':           self.pref_proposal,
            'background_jobs':    self.pref_background_jobs,
            'proposal_comment':   self.pref_proposal_comment,
            'proposal_accepted':  self.pref_proposal_accepted,
            'comment_reply':      self.pref_comment_reply,
            'mentioned':          self.pref_mentioned,
            'blog_published':     self.pref_blog_published,
            'sync_run_finished':  self.pref_sync_run_finished,
            'workflow_runs':      self.pref_workflow_runs,
            'alerts':             self.pref_alerts,
            'favorite_rule_update': self.pref_favorite_rule_update,
            'bundle_fork':        self.pref_bundle_fork,
            'muted_types':        sorted(self.muted()),
            'auto_archive_days':  self.auto_archive_days or 0,
        }



class NotificationLabel(db.Model):
    """A user's own label for their notifications (name + colour), like an email label."""
    __tablename__ = 'notification_label'
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='uq_notification_label_user_name'),)

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    name       = db.Column(db.String(40), nullable=False)
    color      = db.Column(db.String(7), nullable=False, default='#0d6efd')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_json(self, count=None):
        out = {'id': self.id, 'name': self.name, 'color': self.color}
        if count is not None:
            out['count'] = count
        return out


@event.listens_for(Session, 'before_flush')
def _drop_muted_notifications(session, flush_context, instances):
    """A notification of a type its user muted (Notifications › Preferences) is never created — from
    every place that creates one, without changing each of them."""
    new = [o for o in session.new if isinstance(o, Notification)]
    if not new:
        return
    with session.no_autoflush:
        ids = {n.user_id for n in new if n.user_id}
        prefs = {p.user_id: p.muted() for p in session.query(NotificationPreference)
                 .filter(NotificationPreference.user_id.in_(ids)).all()} if ids else {}
    for n in new:
        if n.notif_type in prefs.get(n.user_id, ()):
            session.expunge(n)
