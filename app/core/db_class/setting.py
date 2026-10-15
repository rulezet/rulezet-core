"""Admin-editable settings: one row per setting changed from the admin page
(see app/core/utils/app_settings.py).

`value` is the admin's value; `base_value` is the file value it was made
from — when an update changes the file, the two are merged three-way so the
admin's changes survive and the update's new entries still show up.
"""
import datetime

from app import db


class AppSetting(db.Model):
    __tablename__ = 'app_setting'

    key           = db.Column(db.String(128), primary_key=True)
    value         = db.Column(db.JSON, nullable=False)
    base_value    = db.Column(db.JSON, nullable=True)
    updated_at    = db.Column(db.DateTime, nullable=False,
                              default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    def to_json(self):
        return {
            'key': self.key,
            'value': self.value,
            'base_value': self.base_value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by_id': self.updated_by_id,
        }


class AppSettingHistory(db.Model):
    """One entry per change of a setting from the admin page (save, reset,
    accepted merge, restore) — the value it had afterwards, to compare or
    restore any earlier version."""
    __tablename__ = 'app_setting_history'

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key        = db.Column(db.String(128), nullable=False, index=True)
    action     = db.Column(db.String(16), nullable=False)   # saved | reset | merged | restored
    value      = db.Column(db.JSON, nullable=True)          # value after the change (file value after a reset)
    base_value = db.Column(db.JSON, nullable=True)          # file value at that moment
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, index=True,
                           default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    def to_json(self):
        from app.core.db_class.user import User
        user = db.session.get(User, self.user_id) if self.user_id else None
        return {
            'id': self.id,
            'key': self.key,
            'action': self.action,
            'value': self.value,
            'base_value': self.base_value,
            'user': (user.username or f'{user.first_name} {user.last_name}'.strip()) if user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
