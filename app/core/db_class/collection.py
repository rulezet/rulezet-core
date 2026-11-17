"""Personal collections: a user's own folders of rules and bundles, with a
note, a status and an optional reminder per item. Always private.

Logic: app/features/collection/collection_core.py — design: docs/design/collections.md
"""
import datetime

from app import db


def _now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


class UserCollection(db.Model):
    """One folder. parent_id makes sub-folders (any depth)."""
    __tablename__ = 'user_collection'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user_collection.id', ondelete='CASCADE'), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(60), nullable=True)
    color = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    items = db.relationship('UserCollectionItem', backref='collection', lazy='dynamic',
                            cascade='all, delete-orphan', passive_deletes=True)
    children = db.relationship('UserCollection', backref=db.backref('parent', remote_side=[id]),
                               cascade='all, delete-orphan', passive_deletes=True)

    def to_json(self):
        return {
            "id": self.id, "parent_id": self.parent_id, "name": self.name,
            "icon": self.icon, "color": self.color, "description": self.description,
            "position": self.position,
        }


class UserCollectionItem(db.Model):
    """A rule or a bundle in a folder (exactly one of rule_id / bundle_id)."""
    __tablename__ = 'user_collection_item'
    __table_args__ = (
        db.UniqueConstraint('collection_id', 'rule_id', name='uq_collection_rule'),
        db.UniqueConstraint('collection_id', 'bundle_id', name='uq_collection_bundle'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('user_collection.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=True, index=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=True, index=True)
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='todo')   # todo | doing | done
    remind_at = db.Column(db.DateTime, nullable=True, index=True)       # naive UTC
    reminded_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    rule = db.relationship('Rule')
    bundle = db.relationship('Bundle')
