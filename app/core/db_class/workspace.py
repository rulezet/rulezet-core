"""Workspaces: a user's working set of rules, bundles, documents, files and links.
"""
from app import db
import datetime


########################################
#   Workspace                          #
########################################

class WorkspaceTagAssociation(db.Model):
    __tablename__ = 'workspace_tag_association'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False)
    tag_id       = db.Column(db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    tag          = db.relationship('Tag', foreign_keys=[tag_id], lazy='joined')
    __table_args__ = (db.UniqueConstraint('workspace_id', 'tag_id'),)


class WorkspaceAttackAssociation(db.Model):
    __tablename__ = 'workspace_attack_association'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False)
    technique_id = db.Column(db.String(20), db.ForeignKey('attack_technique.technique_id', ondelete='CASCADE'), nullable=False)
    technique    = db.relationship('AttackTechnique', foreign_keys=[technique_id], lazy='joined')
    __table_args__ = (db.UniqueConstraint('workspace_id', 'technique_id'),)


class Workspace(db.Model):
    """Personal rule workspace — grouping owned rules by context."""
    __tablename__ = 'workspace'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon        = db.Column(db.String(50), nullable=False, default='fa-folder')
    color       = db.Column(db.String(20), nullable=False, default='#0d6efd')
    url         = db.Column(db.Text, nullable=True)
    cve_id      = db.Column(db.Text, nullable=True)
    other       = db.Column(db.Text, nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    updated_at  = db.Column(db.DateTime,
                             default=lambda: datetime.datetime.now(tz=datetime.timezone.utc),
                             onupdate=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    owner       = db.relationship('User', backref=db.backref('workspaces', lazy='dynamic'))
    rules_assoc = db.relationship('WorkspaceRule', backref='workspace', lazy='dynamic',
                                   cascade='all, delete-orphan')
    tag_assocs  = db.relationship('WorkspaceTagAssociation', backref='workspace',
                                   cascade='all, delete-orphan', foreign_keys='WorkspaceTagAssociation.workspace_id')
    attack_assocs = db.relationship('WorkspaceAttackAssociation', backref='workspace',
                                     cascade='all, delete-orphan', foreign_keys='WorkspaceAttackAssociation.workspace_id')
    bundles_assoc = db.relationship('WorkspaceBundle', backref='workspace', lazy='dynamic',
                                     cascade='all, delete-orphan', foreign_keys='WorkspaceBundle.workspace_id')

    def rule_count(self):
        return self.rules_assoc.count()

    @property
    def cves_list(self):
        import json as _json
        return _json.loads(self.cve_id) if self.cve_id else []

    def to_json(self):
        return {
            'id':          self.id,
            'uuid':        self.uuid,
            'name':        self.name,
            'description': self.description,
            'icon':        self.icon,
            'color':       self.color,
            'url':         self.url,
            'cves':        self.cves_list,
            'user_id':     self.user_id,
            'owner_name':  self.owner.get_username() if self.owner else None,
            'rule_count':  self.rule_count(),
            'bundle_count': self.bundles_assoc.count(),
            'created_at':  self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'updated_at':  self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
        }


class WorkspaceRule(db.Model):
    """Association table between Workspace and Rule."""
    __tablename__ = 'workspace_rule'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False)
    rule_id      = db.Column(db.Integer, db.ForeignKey('rule.id',      ondelete='CASCADE'), nullable=False)
    added_at     = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    note         = db.Column(db.Text, nullable=True)
    __table_args__ = (db.UniqueConstraint('workspace_id', 'rule_id'),)

    def to_json(self):
        return {
            'id':           self.id,
            'workspace_id': self.workspace_id,
            'rule_id':      self.rule_id,
            'note':         self.note,
            'added_at':     self.added_at.strftime('%Y-%m-%d %H:%M') if self.added_at else None,
        }


class WorkspaceBundle(db.Model):
    """Association table between Workspace and Bundle — a workspace can
    collect any bundle its owner can see (own, public, or someone else's),
    independently of the workspace's rules. Bundles exported from the
    workspace also get a row here (and keep Bundle.source_workspace_id as
    provenance)."""
    __tablename__ = 'workspace_bundle'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False, index=True)
    bundle_id    = db.Column(db.Integer, db.ForeignKey('bundle.id',    ondelete='CASCADE'), nullable=False, index=True)
    added_at     = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    note         = db.Column(db.Text, nullable=True)
    __table_args__ = (db.UniqueConstraint('workspace_id', 'bundle_id', name='uq_workspace_bundle'),)

    bundle = db.relationship('Bundle', foreign_keys=[bundle_id],
                             backref=db.backref('workspace_links', cascade='all, delete-orphan', passive_deletes=True))


class WorkspaceDocument(db.Model):
    __tablename__ = 'workspace_document'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False)
    title        = db.Column(db.String(200), nullable=False, default='Untitled')
    content      = db.Column(db.Text, nullable=False, default='')
    created_at   = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    updated_at   = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc),
                              onupdate=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    def to_json(self):
        return {
            'id':         self.id,
            'title':      self.title,
            'content':    self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
        }


class WorkspaceFile(db.Model):
    """A binary file (image, PDF, office document) attached to a workspace.

    Stored on disk under app/uploads/workspace/ (never under static/: only
    the workspace owner or an admin may read it, through the workspace
    blueprint). Allowed types and checks: workspace_core.validate_upload().
    """
    __tablename__ = 'workspace_file'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid          = db.Column(db.String(36), unique=True, nullable=False, index=True)
    workspace_id  = db.Column(db.Integer, db.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name   = db.Column(db.String(255), nullable=False)
    mime_type     = db.Column(db.String(128), nullable=False)
    size_bytes    = db.Column(db.Integer, nullable=False)
    uploaded_by   = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at    = db.Column(db.DateTime, nullable=False, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    def to_json(self, ws_uuid: str):
        return {
            'id':            self.id,
            'uuid':          self.uuid,
            'original_name': self.original_name,
            'mime_type':     self.mime_type,
            'size_bytes':    self.size_bytes,
            'is_image':      self.mime_type.startswith('image/'),
            'created_at':    self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'url':           f'/workspace/{ws_uuid}/files/{self.uuid}',
        }


class WorkspaceLink(db.Model):
    __tablename__ = 'workspace_link'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False)
    title        = db.Column(db.String(200), nullable=False)
    url          = db.Column(db.String(1000), nullable=False)
    description  = db.Column(db.String(500), nullable=True)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    def to_json(self):
        return {
            'id':          self.id,
            'title':       self.title,
            'url':         self.url,
            'description': self.description,
            'created_at':  self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }
