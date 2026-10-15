"""Activity log entries and per-action display settings.
"""
from app import db
import datetime


########################################
#   Activity Log                       #
########################################

class ActivityLog(db.Model):
    """Records every significant user action across the platform."""
    __tablename__ = 'activity_log'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)

    # e.g. "rule.create", "rule.delete", "user.login", "bundle.edit", "admin.promote_user"
    action      = db.Column(db.String(64), nullable=False, index=True)
    title       = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    category    = db.Column(db.String(32), nullable=True, index=True)
    level       = db.Column(db.String(16), nullable=True, index=True)

    ip_address  = db.Column(db.String(45), nullable=True)   # IPv4 or IPv6
    url         = db.Column(db.String(512), nullable=True)
    method      = db.Column(db.String(8), nullable=True)
    user_agent  = db.Column(db.String(256), nullable=True)

    # What entity was acted on
    target_type = db.Column(db.String(32), nullable=True, index=True)  # "rule" | "bundle" | "user" | "tag" | "job"
    target_id   = db.Column(db.Integer, nullable=True)
    target_uuid = db.Column(db.String(36), nullable=True)

    extra       = db.Column(db.JSON, nullable=True)

    # Visibility & display
    is_public   = db.Column(db.Boolean, nullable=False, default=False, index=True)
    icon        = db.Column(db.String(64), nullable=True)   # FontAwesome class e.g. "fa-solid fa-file-shield"
    created_at  = db.Column(db.DateTime, nullable=False,
                            default=lambda: datetime.datetime.now(datetime.timezone.utc),
                            index=True)

    user = db.relationship('User', backref=db.backref('activity_logs', lazy='dynamic'))

    def to_json(self):
        # No user + a request IP = an anonymous visitor (view, download…);
        # no user and no request at all = a genuine system action (cron, job).
        username = "Anonymous" if self.ip_address else "System"
        try:
            if self.user:
                username = self.user.get_username()
        except Exception:
            pass
        return {
            "id":          self.id,
            "uuid":        self.uuid,
            "user_id":     self.user_id,
            "username":    username,
            "actor_name":  username,
            "action":      self.action,
            "title":       self.title or '',
            "category":    self.category or 'system',
            "level":       self.level or 'info',
            "description": self.description,
            "ip_address":  self.ip_address,
            "user_agent":  self.user_agent,
            "url":         self.url,
            "method":      self.method,
            "target_type": self.target_type,
            "target_id":   self.target_id,
            "target_uuid": self.target_uuid,
            "extra":       self.extra,
            "is_public":   self.is_public,
            "icon":        self.icon,
            "created_at":  self.created_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
        }
    
    def to_json_public(self):
        username = "System"
        try:
            if self.user:
                username = self.user.get_username()
        except Exception:
            pass
        return {
            "id":          self.id,
            "uuid":        self.uuid,
            "user_id":     self.user_id,
            "username":    username,
            "action":      self.action,
            "description": self.description,
            "url":         self.url,
            "method":      self.method,
            "target_type": self.target_type,
            "target_id":   self.target_id,
            "target_uuid": self.target_uuid,
            "extra":       self.extra,
            "is_public":   self.is_public,
            "icon":        self.icon,
            "created_at":  self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }


class LogActionDefinition(db.Model):
    """Admin-editable display overrides for activity-log action keys.

    Presence of a row for an action_key means "admin has customized this action's
    display"; any column left NULL falls back to the hardcoded default in
    app/features/admin/log_action_defaults.py (see log_definitions_core.py).
    """
    __tablename__ = 'log_action_definition'

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    action_key    = db.Column(db.String(64), unique=True, nullable=False, index=True)
    icon          = db.Column(db.String(64), nullable=True)
    title         = db.Column(db.String(255), nullable=True)
    is_public     = db.Column(db.Boolean, nullable=True)  # NULL = inherit default
    category      = db.Column(db.String(32), nullable=True)
    updated_at    = db.Column(db.DateTime, nullable=False,
                              default=lambda: datetime.datetime.now(datetime.timezone.utc),
                              onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    def to_json(self):
        return {
            "id":         self.id,
            "action_key": self.action_key,
            "icon":       self.icon,
            "title":      self.title,
            "is_public":  self.is_public,
            "category":   self.category,
            "updated_at": self.updated_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z' if self.updated_at else None,
        }
