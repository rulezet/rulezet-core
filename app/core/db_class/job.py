"""Background jobs and their logs.
"""
from app import db
from sqlalchemy import event
import datetime


########################################
#   Background Job Queue               #
########################################
 
class BackgroundJob(db.Model):
    """Persistent background job — any long-running task goes through this."""
    __tablename__ = 'background_job'
 
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    created_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 
    # job type e.g. 'bulk_add_tag_to_rules', 'bulk_remove_tag_from_rules'
    job_type    = db.Column(db.String(64), nullable=False, index=True)
 
    # status: pending | running | done | failed | cancelled | paused
    status      = db.Column(db.String(16), nullable=False, default='pending', index=True)
 
    total       = db.Column(db.Integer, default=0)
    done        = db.Column(db.Integer, default=0)
 
    # arbitrary JSON payload — filters, tag ids, resume offset, etc.
    payload     = db.Column(db.JSON, nullable=True)
 
    # human-readable label shown in the UI
    label       = db.Column(db.String(255), nullable=True)
 
    error       = db.Column(db.Text, nullable=True)
 
    created_at  = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    started_at  = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
 
    user = db.relationship('User', backref=db.backref('background_jobs', lazy='dynamic',
                                                       cascade='all, delete-orphan'))
    logs = db.relationship('BackgroundJobLog', backref='job',
                           lazy='dynamic', cascade='all, delete-orphan',
                           order_by='BackgroundJobLog.created_at')
 
    @property
    def progress_pct(self):
        if not self.total:
            # a finished job with no countable items is still 100% complete
            return 100 if self.status == 'done' else 0
        return round((self.done / self.total) * 100)
 
    def to_json(self):
        return {
            "id":           self.id,
            "uuid":         self.uuid,
            "job_type":     self.job_type,
            "status":       self.status,
            "total":        self.total,
            "done":         self.done,
            "progress_pct": self.progress_pct,
            "label":        self.label,
            "error":        self.error,
            "created_by":   self.created_by,
            "created_at":   self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "started_at":   self.started_at.strftime('%Y-%m-%d %H:%M:%S') if self.started_at else None,
            "finished_at":  self.finished_at.strftime('%Y-%m-%d %H:%M:%S') if self.finished_at else None,
        }


 
 
class BackgroundJobLog(db.Model):
    """
    Structured log lines for a background job.
    Each significant event (start, pause, resume, batch progress, done, error)
    writes one row here so the UI can display a real-time activity feed.
    """
    __tablename__ = 'background_job_log'
 
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id     = db.Column(db.Integer, db.ForeignKey('background_job.id', ondelete='CASCADE'),
                           nullable=False, index=True)
 
    # level: info | success | warning | error
    level      = db.Column(db.String(16), nullable=False, default='info')
 
    # short machine-readable event key e.g. 'started', 'paused', 'batch', 'done', 'cancelled'
    event      = db.Column(db.String(64), nullable=True)
 
    message    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.datetime.now(datetime.timezone.utc))
 
    def to_json(self):
        return {
            "id":         self.id,
            "level":      self.level,
            "event":      self.event,
            "message":    self.message,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
