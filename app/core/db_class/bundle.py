"""Bundles: curated rule collections, their tree, history, releases and notes.
"""
from app import db
import datetime
import json


    
#############
#   Bundle  #
#############


class Bundle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(255), nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))
    created_by = db.Column(db.String(255), nullable=False, default="user") # user or bot

    # the creator of the bundle
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    vote_up = db.Column(db.Integer, nullable=False, default=0)
    vote_down = db.Column(db.Integer, nullable=False, default=0)
    view_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=False) # Badge "officiel"

    # visibility
    access = db.Column(db.Boolean, nullable=False, default=True) # if true all user can see the bundle, if false only the creator can see it

    vulnerability_identifiers = db.Column(db.Text, nullable=True) # JSON string of vulnerability identifiers associated with the bundle

    # Connector origin
    connector_id        = db.Column(db.Integer, db.ForeignKey('connector.id', ondelete='SET NULL'), nullable=True, index=True)
    remote_bundle_uuid  = db.Column(db.String(36), nullable=True, index=True)

    # Forks (docs/future/bundle_forks.md, app/features/bundle/bundle_fork_core.py)
    forked_from_id     = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='SET NULL'), nullable=True, index=True)
    forked_from_uuid   = db.Column(db.String(255), nullable=True, index=True)   # kept if the upstream disappears
    fork_base_snapshot = db.Column(db.JSON, nullable=True)      # common ancestor with the upstream (hashes only)
    fork_base_at       = db.Column(db.DateTime, nullable=True)  # last fork / sync / merge with the upstream
    accepts_proposals  = db.Column(db.Boolean, nullable=False, default=True, server_default='1')  # merge requests open to others

    # Set when this bundle was generated via a workspace's "Export as Bundle" action.
    source_workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id', ondelete='SET NULL'), nullable=True, index=True)

    # Private share link: whoever holds /bundle/share/<share_token> (and is
    # logged in) can view the bundle while it's private. NULL = no link.
    # Regenerating replaces it, which cuts off every previous holder.
    # Never serialised in to_json() — only the owner/admin endpoint returns it.
    share_token = db.Column(db.String(64), nullable=True, unique=True, index=True)
    share_token_created_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('user who create bundle', lazy='dynamic', cascade='all, delete-orphan'))

    def get_username_by_id(self):
        user = User.query.get(self.user_id)  
        return user.first_name if user else None
    def get_rule_user_first_name_by_id(self):
        user = User.query.get(self.user_id)  
        return user.first_name + " " + user.last_name if user else None

    def to_json(self):
        submitter = User.query.get(self.user_id)
        active_rules = [a.rule for a in self.rules_assoc if a.rule and not a.rule.is_deleted]
        return {
            "id": self.id,
            "author_avatar": submitter.get_avatar_url() if submitter else None,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M'),
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M'),
            "author": self.get_username_by_id() ,
            "user_id": self.user_id,
            "access": self.access,
            "vote_up": self.vote_up,
            "vote_down": self.vote_down,
            "user_name": self.get_rule_user_first_name_by_id(),
            "list_of_format_of_rules": list(set([r.format for r in active_rules])),
            "number_of_rules": len(active_rules),
            "is_verified": self.is_verified,
            "view_count": self.view_count,
            "download_count": self.download_count,
            "uuid": self.uuid,
            "created_by": self.created_by,
            "forked_from_id": self.forked_from_id,
            "forked_from_uuid": self.forked_from_uuid,
            "is_fork": bool(self.forked_from_uuid),
            "vulnerability_identifiers": json.loads(self.vulnerability_identifiers) if self.vulnerability_identifiers else [],
            "source_workspace_id": self.source_workspace_id,
        }


class BundleNode(db.Model):
    __tablename__ = 'bundle_node'
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete="CASCADE"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('bundle_node.id', ondelete="CASCADE"), nullable=True)
    
    name = db.Column(db.String(255), nullable=False)
    node_type = db.Column(db.String(50), nullable=False) # 'folder' or 'file'
    
    custom_content = db.Column(db.Text, nullable=True)
    
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete="CASCADE"), nullable=True)

    children = db.relationship(
        "BundleNode", 
        backref=db.backref('parent', remote_side=[id]), 
        cascade="all, delete-orphan",
        passive_deletes=True,
        # save_workspace inserts nodes depth-first in display order, so id
        # order == the order the user arranged them in (was unordered)
        order_by="BundleNode.id",
    )
    
    rule = db.relationship("Rule") 

    def to_tree_json(self):
        """Recursively converts nodes to the JSON tree expected by Vue.js"""
        if self.rule_id and self.rule and self.rule.is_deleted:
            # Trashed rule: keep the slot visible but never expose its content
            return {
                "id": f"rule_{self.rule_id}_{self.id}",
                "name": "(deleted rule)",
                "type": "file",
                "content": "",
                "children": [],
                "rule_id": self.rule_id,
                "format": "",
                "deleted": True,
            }
        if self.rule_id and self.rule:
            # Display name includes the extension in the tree explorer.
            # Trailing dots stripped so "Checksum changed." doesn't become "..xml".
            current_name = f"{(self.rule.title or '').rstrip('.')}.{self.rule.get_extension()}"
            current_content = self.rule.to_string
            node_id = f"rule_{self.rule_id}_{self.id}"
        else:
            current_name = self.name
            current_content = self.custom_content or ""
            node_id = f"node_{self.id}"

        node_data = {
            "id": node_id,
            "name": current_name,
            "type": self.node_type,
            "content": current_content,
            "children": [child.to_tree_json() for child in self.children]
        }
        
        if self.rule_id:
            node_data["rule_id"] = self.rule_id
            if self.rule:
                node_data["format"] = self.rule.format or ''

        return node_data


class BundleHistory(db.Model):
    """One entry of a bundle's change history (bundle detail page → History).

    Each row stores a compact before/after snapshot of the bundle (name,
    description, visibility, tags, CVEs, rules, files, folders — see
    bundle_history.snapshot_bundle) plus the precomputed human-readable
    `changes` list rendered by the meta-change-list component. Structure
    autosaves from the editor are coalesced into one row per user per
    window, so the history isn't one row per keystroke.
    """
    __tablename__ = 'bundle_history'

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid         = db.Column(db.String(36), unique=True, nullable=False, index=True)
    bundle_id    = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    # 'created' | 'details' | 'visibility' | 'tags' | 'structure' | 'rules'
    action       = db.Column(db.String(32), nullable=False, index=True)
    summary      = db.Column(db.String(512), nullable=True)
    changes      = db.Column(db.JSON, nullable=True)
    old_snapshot = db.Column(db.JSON, nullable=True)
    new_snapshot = db.Column(db.JSON, nullable=True)
    created_at   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    updated_at   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = db.relationship('User')
    bundle = db.relationship('Bundle', backref=db.backref('history', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self, include_descriptions=False):
        data = {
            "id": self.id,
            "uuid": self.uuid,
            "bundle_id": self.bundle_id,
            "user_id": self.user_id,
            "user_name": self.user.first_name if self.user else None,
            "user_avatar": self.user.get_avatar_url() if self.user else None,
            "action": self.action,
            "summary": self.summary,
            "changes": self.changes or [],
            "created_at": self.created_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
            "updated_at": self.updated_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z' if self.updated_at else None,
            "has_description_diff": bool(self.old_snapshot and self.new_snapshot
                                         and (self.old_snapshot.get('description') or '') != (self.new_snapshot.get('description') or '')),
        }
        if include_descriptions:
            data["old_description"] = (self.old_snapshot or {}).get('description') or ''
            data["new_description"] = (self.new_snapshot or {}).get('description') or ''
        return data


class BundleRelease(db.Model):
    """A published, frozen version of a bundle ("v1.2").

    `snapshot` holds everything needed to reproduce exactly what was
    released, independently of later edits to the bundle or its rules:
    bundle metadata, the structure tree, every custom file's content and
    every rule's content (+ a hash used to detect upstream changes).
    See bundle_release_core.build_snapshot().
    """
    __tablename__ = 'bundle_release'
    __table_args__ = (db.UniqueConstraint('bundle_id', 'version', name='uq_bundle_release_version'),)

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    bundle_id   = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    version     = db.Column(db.String(40), nullable=False)
    title       = db.Column(db.String(255), nullable=True)
    notes       = db.Column(db.Text, nullable=True)          # markdown changelog
    rule_count  = db.Column(db.Integer, nullable=False, default=0)
    file_count  = db.Column(db.Integer, nullable=False, default=0)
    health_score = db.Column(db.Integer, nullable=True)
    snapshot    = db.Column(db.JSON, nullable=False)
    created_at  = db.Column(db.DateTime, nullable=False,
                            default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)

    user = db.relationship('User')
    bundle = db.relationship('Bundle', backref=db.backref('releases', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "bundle_id": self.bundle_id,
            "version": self.version,
            "title": self.title,
            "notes": self.notes or "",
            "rule_count": self.rule_count,
            "file_count": self.file_count,
            "health_score": self.health_score,
            "user_id": self.user_id,
            "user_name": self.user.first_name if self.user else None,
            "user_avatar": self.user.get_avatar_url() if self.user else None,
            "created_at": self.created_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
        }


class BundleNote(db.Model):
    """A community note / known issue on a bundle ("⚠ this bundle doesn't
    work if…"), written in Markdown.

    Can only be created while the bundle is public (or by its owner / an
    admin). Reading — including for its own author — follows the bundle's
    access: while the bundle is private, the author reaches it only through
    the bundle's share link; once it is public again the note is still
    theirs (edit, delete, resolve).
    """
    __tablename__ = 'bundle_note'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    bundle_id   = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    title       = db.Column(db.String(200), nullable=False)
    content     = db.Column(db.Text, nullable=False)                 # markdown
    severity    = db.Column(db.String(16), nullable=False, default='warning')   # info | warning | critical
    status      = db.Column(db.String(16), nullable=False, default='open', index=True)  # open | resolved
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at  = db.Column(db.DateTime, nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    updated_at  = db.Column(db.DateTime, nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id])
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])
    bundle = db.relationship('Bundle', backref=db.backref('notes', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        iso = lambda d: d.strftime('%Y-%m-%dT%H:%M:%S') + 'Z' if d else None
        return {
            "id": self.id,
            "uuid": self.uuid,
            "bundle_id": self.bundle_id,
            "user_id": self.user_id,
            "user_name": self.user.first_name if self.user else None,
            "user_avatar": self.user.get_avatar_url() if self.user else None,
            "title": self.title,
            "content": self.content,
            "severity": self.severity,
            "status": self.status,
            "resolved_by": self.resolved_by.first_name if self.resolved_by else None,
            "resolved_at": iso(self.resolved_at),
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
            "tags": [{"id": t.id, "name": t.name, "color": t.color, "description": t.description}
                     for t in sorted((a.tag for a in self.tag_assocs if a.tag), key=lambda t: t.name)],
        }


class BundleNoteTag(db.Model):
    """A tag on a bundle note — restricted to a curated set of taxonomies
    (false-positive, workflow, detection-engineering…), see
    bundle.NOTE_TAG_PREFIXES."""
    __tablename__ = 'bundle_note_tag'
    __table_args__ = (db.UniqueConstraint('note_id', 'tag_id', name='uq_bundle_note_tag'),)

    id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    note_id = db.Column(db.Integer, db.ForeignKey('bundle_note.id', ondelete='CASCADE'), nullable=False, index=True)
    tag_id  = db.Column(db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), nullable=False, index=True)

    note = db.relationship('BundleNote', backref=db.backref('tag_assocs', cascade='all, delete-orphan'))
    tag  = db.relationship('Tag')


class BundleFavoriteUser(db.Model):
    """A user's favorite bundles (same idea as RuleFavoriteUser)."""
    __tablename__ = 'bundle_favorite_user'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    bundle_id  = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    __table_args__ = (db.UniqueConstraint('user_id', 'bundle_id', name='uq_bundle_favorite_user'),)

    user   = db.relationship('User', backref=db.backref('favorite_bundles_assocs', lazy='dynamic',
                                                        cascade='all, delete-orphan', passive_deletes=True))
    bundle = db.relationship('Bundle', backref=db.backref('favorited_by_users_assocs', lazy='dynamic',
                                                          cascade='all, delete-orphan', passive_deletes=True))


class BundleVote(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    user = db.relationship('User', backref=db.backref('user_votes_bundle', lazy='dynamic', cascade='all, delete-orphan'))
    bundle = db.relationship('Bundle', backref=db.backref('bundle', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "bundle_id": self.bundle_id,
            "vote_type": self.vote_type,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class BundleRuleAssociation(db.Model):
    # Table to associate rule and a bundle 
    # rule can be in many bundles and a bundle can have many rules
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id'), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    description = db.Column(db.Text)

    added_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    bundle = db.relationship('Bundle', backref=db.backref('rules_assoc', lazy='dynamic', cascade='all, delete-orphan'))
    rule = db.relationship('Rule', backref=db.backref('bundles_assoc', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "bundle_id": self.bundle_id,
            "rule_id": self.rule_id,
            "bundle_name": self.bundle.name if self.bundle else None,
            "rule_title": self.rule.title if self.rule else None,
            "description": self.description,
            "added_at": self.added_at.strftime('%Y-%m-%d %H:%M'),
        }


# Imported last: these models are only used inside methods, and importing them
# at the top would be circular.
from app.core.db_class.user import User  # noqa: E402
