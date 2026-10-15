"""Permissions and roles (RBAC).
"""
from app import db
import datetime


###########################
#  Roles & Permissions    #
###########################
# Purely additive middle tier between "any logged-in user" and admin
# (User.admin / is_admin()) — that flag is untouched and still bypasses
# everything (see User.has_permission above). This layer only ever grants
# a non-admin extra capability beyond their own resources; nothing here can
# take a capability away from anyone.

class Permission(db.Model):
    """A single grantable capability, identified by a stable dotted key
    (e.g. "rule.tag_any"). The catalog is seeded from code
    (app/features/roles/roles_core.py) — it's a fixed vocabulary tied to
    what the app actually checks, not something admins can invent freely
    from the UI.
    """
    __tablename__ = "permission"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    key = db.Column(db.String(128), unique=True, nullable=False, index=True)
    label = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "key": self.key,
            "label": self.label,
            "description": self.description,
        }


class Role(db.Model):
    """A named, admin-managed group of permissions, assignable to users."""
    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    # System roles (seeded at startup, e.g. "Tag manager") can't be deleted from
    # the admin UI — only their permission set can be edited — so a
    # has_permission() call site never silently starts failing because
    # someone deleted the role it depended on.
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    def to_json(self, include_permissions=True):
        data = {
            "id": self.id,
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description,
            "is_system": self.is_system,
            "user_count": UserRole.query.filter_by(role_id=self.id).count(),
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }
        if include_permissions:
            perms = (
                db.session.query(Permission)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .filter(RolePermission.role_id == self.id)
                .order_by(Permission.key)
                .all()
            )
            data["permissions"] = [p.to_json() for p in perms]
        return data


class RolePermission(db.Model):
    """Grants a Permission to a Role."""
    __tablename__ = "role_permission"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    role = db.relationship('Role', backref=db.backref('role_permission_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    permission = db.relationship('Permission', backref=db.backref('permission_role_assocs', lazy='dynamic', cascade='all, delete-orphan'))

    __table_args__ = (db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),)


class UserRole(db.Model):
    """Grants a Role to a User."""
    __tablename__ = "user_role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('user_role_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    role = db.relationship('Role', backref=db.backref('user_role_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    granter = db.relationship('User', foreign_keys=[granted_by])

    __table_args__ = (db.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),)

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "granted_by": self.granted_by,
            "granted_at": self.granted_at.strftime('%Y-%m-%d %H:%M') if self.granted_at else None,
        }
