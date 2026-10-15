"""Tags and their links to rules and bundles.
"""
from app import db
import datetime


class RuleTagAssociation(db.Model):
    __tablename__ = 'rule_tag_association'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # the user who added the tag to the bundle

    added_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    rule = db.relationship('Rule', backref=db.backref('rule_tags_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    tag = db.relationship('Tag', backref=db.backref('rules_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('user_rule_tags_assocs', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "rule_id": self.rule_id,
            "tag_id": self.tag_id,
            "user_id": self.user_id,
            "tag_name": self.tag.name if self.tag else None,
            "added_at": self.added_at.strftime('%Y-%m-%d %H:%M'),
        }


    

class Tag(db.Model):
    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))
    is_active = db.Column(db.Boolean, default=False)
    visibility = db.Column(db.String(255), nullable=True)
    external_id = db.Column(db.String, nullable=True)

    color = db.Column(db.String(50), nullable=True) # Hex color code, e.g., #FF5733
    icon = db.Column(db.String(50), nullable=True) # fontawesome icon name
    source = db.Column(db.String(255), nullable=True) # Taxonomy or Manuel or Other
    # Browse folder of the tag pickers/filters ("tlp" for "tlp:clear", the
    # galaxy type for 'misp-galaxy:tool="X"', '' for a plain name). Kept in
    # sync with `name` by the listeners below, so the pickers can list and
    # count folders in SQL instead of loading every tag to group them.
    namespace = db.Column(db.String(255), nullable=True, index=True)

    # Metadata for galxie (galaxie -> tag with galaxie_meta not null)
    galaxy_meta = db.Column(db.JSON, nullable=True)

    # Relationships

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    is_approved_by_admin = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref=db.backref('tags', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M'),
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M'),
            "is_active": self.is_active,
            "visibility": self.visibility,
            "color": self.color,
            "icon": self.icon,
            "created_by_user_id": self.created_by,
            "created_by_user_name": self.user.first_name if self.user else None,
            "is_approved_by_admin": self.is_approved_by_admin,
            "external_id": self.external_id,
            "source": self.source,
            "galaxy_meta": self.galaxy_meta if self.galaxy_meta else None,
            # Injected by _inject_usage_counts() in tags_core.py — falls back to 0
            # when called outside a listing context (e.g. direct Tag.to_json()).
            "rule_count":   getattr(self, '_rule_count',   0),
            "bundle_count": getattr(self, '_bundle_count', 0),
        }


 


def tag_namespace(name) -> str:
    """Browse folder of a tag name — same rule as the JS pickers' namespaceOf():
    'misp-galaxy:tool="X"' -> 'tool', 'tlp:clear' -> 'tlp', 'malware' -> ''."""
    name = name or ''
    if ':' not in name:
        return ''
    if name.startswith('misp-galaxy:') and '=' in name:
        return name.split(':', 1)[1].split('=', 1)[0][:255]
    return name.split(':', 1)[0][:255]


@db.event.listens_for(Tag, 'before_insert')
@db.event.listens_for(Tag, 'before_update')
def _tag_sync_namespace(mapper, connection, target):
    target.namespace = tag_namespace(target.name)


class BundleTagAssociation(db.Model):
    __tablename__ = 'bundle_tag_association'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # the user who added the tag to the bundle

    added_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    bundle = db.relationship('Bundle', backref=db.backref('tags_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    tag = db.relationship('Tag', backref=db.backref('bundles_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('user_tags_assocs', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "bundle_id": self.bundle_id,
            "tag_id": self.tag_id,
            "user_id": self.user_id,
            "tag_name": self.tag.name if self.tag else None,
            "added_at": self.added_at.strftime('%Y-%m-%d %H:%M'),
        }
