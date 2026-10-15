"""Saved alerts (watch criteria) and their matches.
"""
from app import db
from sqlalchemy import event
import datetime


########################################
#   Alerts ("tell me when...")         #
########################################

class Alert(db.Model):
    """A user's saved watch: "tell me when a rule/bundle matching these
    criteria is published". Evaluated in bulk by the alert sweeper
    (app/features/alert/alert_core.py::run_sweep), never inline on rule
    creation — rules are created from ~20 code paths and their tags/CVEs/
    ATT&CK links are often attached later.

    criteria (JSON): {
        "cves":         ["CVE-2026-19490", ...],
        "tags":         ["ransomware", ...],          # tag names
        "attacks":      ["T1190", ...],               # technique ids
        "keywords":     ["netscaler", ...],           # title / description / content
        "formats":      ["yara", "sigma", ...],
        "users":        [12, 34],                     # rule/bundle owner user ids
        "github_repos": ["elastic/detection-rules"],  # rule source contains this
        "cve_any":      false,   # any vulnerability id at all
        "tag_any":      false,   # any tag except the tlp:/pap: markings
        "attack_any":   false,   # any ATT&CK technique
        "github_any":   false    # any rule imported from a git repository
    }
    Each "*_any" switch supersedes its specific list.
    Within one criterion any value matches (OR). match_mode says how the
    non-empty criteria combine: 'any' (OR) or 'all' (AND)."""
    __tablename__ = 'alert'

    EMAIL_MODES = ('off', 'instant', 'daily', 'weekly')
    TARGETS     = ('rule', 'bundle')
    EVENTS      = ('created', 'updated')

    id                = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid              = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
                                  nullable=False, index=True)
    name              = db.Column(db.String(120), nullable=False)
    is_active         = db.Column(db.Boolean, nullable=False, default=True, index=True)
    targets           = db.Column(db.JSON, nullable=False, default=lambda: ['rule'])
    events            = db.Column(db.JSON, nullable=False, default=lambda: ['created'])
    criteria          = db.Column(db.JSON, nullable=False, default=dict)
    match_mode        = db.Column(db.String(8), nullable=False, default='any')
    notify_in_app     = db.Column(db.Boolean, nullable=False, default=True)
    email_mode        = db.Column(db.String(16), nullable=False, default='off')
    match_count       = db.Column(db.Integer, nullable=False, default=0)
    last_triggered_at = db.Column(db.DateTime, nullable=True)
    last_emailed_at   = db.Column(db.DateTime, nullable=True)
    created_at        = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at        = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow,
                                  onupdate=datetime.datetime.utcnow)

    user    = db.relationship('User', backref=db.backref('alerts', lazy='dynamic',
                                                        cascade='all, delete-orphan'))
    matches = db.relationship('AlertMatch', backref='alert', lazy='dynamic',
                              cascade='all, delete-orphan')

    def to_json(self, unseen_count=None):
        return {
            'id':                self.id,
            'uuid':              self.uuid,
            'name':              self.name,
            'is_active':         self.is_active,
            'targets':           self.targets or [],
            'events':            self.events or [],
            'criteria':          self.criteria or {},
            'match_mode':        self.match_mode,
            'notify_in_app':     self.notify_in_app,
            'email_mode':        self.email_mode,
            'match_count':       self.match_count,
            'unseen_count':      unseen_count,
            'last_triggered_at': self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            'created_at':        self.created_at.isoformat() if self.created_at else None,
        }


class AlertMatch(db.Model):
    """One rule/bundle event that matched one alert. The unique constraint
    makes the sweeper idempotent — re-scanning a window never duplicates.
    object_version distinguishes successive updates of the same object."""
    __tablename__ = 'alert_match'
    __table_args__ = (
        db.UniqueConstraint('alert_id', 'object_type', 'object_id', 'event', 'object_version',
                            name='uq_alert_match'),
    )

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alert_id       = db.Column(db.Integer, db.ForeignKey('alert.id', ondelete='CASCADE'),
                               nullable=False, index=True)
    object_type    = db.Column(db.String(16), nullable=False)
    object_id      = db.Column(db.Integer, nullable=False, index=True)
    object_version = db.Column(db.String(64), nullable=False, default='')
    event          = db.Column(db.String(16), nullable=False)
    matched_on     = db.Column(db.JSON, nullable=True)   # ["cve:CVE-2026-1", "tag:ransomware"]
    created_at     = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)
    seen_at        = db.Column(db.DateTime, nullable=True)
    emailed_at     = db.Column(db.DateTime, nullable=True, index=True)


class AlertSweepState(db.Model):
    """Single row: how far the alert sweeper got, so each pass only looks
    at what changed since the previous one."""
    __tablename__ = 'alert_sweep_state'

    id                 = db.Column(db.Integer, primary_key=True)
    last_rule_id       = db.Column(db.Integer, nullable=False, default=0)
    last_bundle_id     = db.Column(db.Integer, nullable=False, default=0)
    rules_modified_at  = db.Column(db.DateTime, nullable=True)
    bundles_updated_at = db.Column(db.DateTime, nullable=True)
    last_run_at        = db.Column(db.DateTime, nullable=True)
    last_pruned_at     = db.Column(db.DateTime, nullable=True)   # AlertMatch retention purge


class AlertEmailLog(db.Model):
    """One row per alert email actually sent. It is what the anti-spam
    quotas count (per user per day, per instance per hour / day — see
    alert_core.send_due_emails) and an audit trail of what went out."""
    __tablename__ = 'alert_email_log'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
                            nullable=False, index=True)
    sent_at     = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)
    alert_count = db.Column(db.Integer, nullable=False, default=0)
    match_count = db.Column(db.Integer, nullable=False, default=0)
