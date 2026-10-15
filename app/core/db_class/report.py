"""User reports / flags on rules and other content.
"""
from app import db
import datetime


class RepportRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # the user who made the repport
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True) # the rule which has repport
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))
    reason = db.Column(db.Text) # list (....differents reasons)

    user = db.relationship('User', backref=db.backref('user who repport', lazy='dynamic', cascade='all, delete-orphan'))
    rule = db.relationship('Rule', backref=db.backref('the rule repport', lazy='dynamic',  cascade='all, delete-orphan'))

    def to_json(self):
            return {
                "id": self.id,
                "user_id": self.user_id,
                "user_name": self.user.first_name if self.user else None,
                "rule_id": self.rule_id,
                "rule_name": self.rule.title if self.rule else None,
                "rule_user_owner": self.rule.get_rule_user_first_name_by_id() if self.rule else None,
                "rule_owner_id": self.rule.user_id if self.rule else None,
                "rule_owner_avatar": User.query.get(self.rule.user_id).get_avatar_url() if self.rule and self.rule.user_id else None,
                "rule_format": self.rule.format if self.rule else None,
                "message": self.message,
                'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
                "reason": self.reason,
                "content": self.rule.to_string if self.rule else None
            }


    

class Report(db.Model):
    """Unified report model for rules, bundles, and comments."""
    __tablename__ = 'report'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    object_type = db.Column(db.String(20), nullable=False, index=True)   # 'rule' | 'bundle' | 'comment'
    object_id   = db.Column(db.Integer, nullable=False, index=True)
    reason      = db.Column(db.String(100), nullable=False)
    message     = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime,
                            default=lambda: datetime.datetime.now(datetime.timezone.utc),
                            index=True)
    status        = db.Column(db.String(20), default='pending', nullable=False, index=True)
    checked_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    checked_at    = db.Column(db.DateTime, nullable=True)

    user       = db.relationship('User', foreign_keys=[user_id], backref=db.backref('reports_submitted', lazy='dynamic'))
    checked_by = db.relationship('User', foreign_keys=[checked_by_id], backref=db.backref('reports_checked', lazy='dynamic'))

    def get_object_label(self):
        """Human-readable name of the reported object."""
        try:
            if self.object_type == 'rule':
                obj = Rule.query.get(self.object_id)
                return obj.title if obj else f'Rule #{self.object_id}'
            if self.object_type == 'bundle':
                obj = Bundle.query.get(self.object_id)
                return obj.name if obj else f'Bundle #{self.object_id}'
            if self.object_type == 'comment':
                obj = UnifiedComment.query.get(self.object_id)
                if obj and obj.object_type == 'proposal':
                    return f'Comment on proposal #{obj.object_id}'
                return f'Comment #{self.object_id}'
        except Exception:
            pass
        return f'{self.object_type} #{self.object_id}'

    def get_object_url(self):
        if self.object_type == 'rule':
            return f'/rule/detail_rule/{self.object_id}'
        if self.object_type == 'bundle':
            return f'/bundle/detail/{self.object_id}'
        if self.object_type == 'comment':
            c = UnifiedComment.query.get(self.object_id)
            if c:
                if c.object_type == 'rule':
                    return f'/rule/detail_rule/{c.object_id}?comment={c.id}'
                if c.object_type == 'bundle':
                    return f'/bundle/detail/{c.object_id}?comment={c.id}'
                if c.object_type == 'proposal':
                    return f'/rule/proposal_content_discuss?id={c.object_id}&comment={c.id}'
        return '#'

    def to_json(self):
        reporter = self.user
        checker  = self.checked_by
        return {
            'id':               self.id,
            'user_id':          self.user_id,
            'reporter_name':    reporter.get_username() if reporter else '?',
            'user_avatar':      reporter.get_avatar_url() if reporter else None,
            'object_type':      self.object_type,
            'object_id':        self.object_id,
            'object_label':     self.get_object_label(),
            'object_url':       self.get_object_url(),
            'reason':           self.reason,
            'message':          self.message,
            'created_at':       self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'status':           self.status,
            'checked_by_id':    self.checked_by_id,
            'checked_by_name':  checker.get_username() if checker else None,
            'checked_by_avatar': checker.get_avatar_url() if checker else None,
            'checked_at':       self.checked_at.strftime('%Y-%m-%d %H:%M') if self.checked_at else None,
        }


# Imported last: these models are only used inside methods, and importing them
# at the top would be circular.
from app.core.db_class.bundle import Bundle  # noqa: E402
from app.core.db_class.comment import UnifiedComment  # noqa: E402
from app.core.db_class.rule import Rule  # noqa: E402
from app.core.db_class.user import User  # noqa: E402
