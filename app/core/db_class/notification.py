"""In-app notifications and notification preferences.
"""
from app import db
import datetime


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

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic',
                                                      cascade='all, delete-orphan'))

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
        }
