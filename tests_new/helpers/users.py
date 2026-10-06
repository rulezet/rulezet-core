"""Users for each role of the access matrix.

Roles used across the suite (see docs/design/test_restructure.md):

    anonymous   not logged in
    user        logged in, NOT the owner of the resource under test
    owner       logged in, owner of the resource under test
    admin       user.admin = True

plus users holding one special permission (e.g. "rule.tag_any"), created on
demand with make_user_with_permission().
"""
import functools
import uuid

from werkzeug.security import generate_password_hash

from app import db
from app.core.db_class.db import Permission, Role, RolePermission, User, UserRole

ROLES = ("anonymous", "user", "owner", "admin")

PASSWORD = "Passw0rd-tests"


@functools.lru_cache(maxsize=1)
def _password_hash():
    # Hashing is deliberately slow (scrypt): do it once per run, not per user.
    return generate_password_hash(PASSWORD)


def make_user(name, *, admin=False):
    """A verified local account with a known password and API key."""
    user = User(
        first_name=name.capitalize(),
        last_name="Tester",
        email=f"{name}@tests.rulezet",
        password_hash=_password_hash(),
        admin=admin,
        api_key=f"api-key-{name}",
        is_verified=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def make_user_with_permission(permission_key, name=None):
    """A non-admin user whose only extra right is `permission_key`
    (through a dedicated role, the way an admin would grant it)."""
    permission = Permission.query.filter_by(key=permission_key).one()
    user = make_user(name or permission_key.replace(".", "-"))
    role = Role(uuid=str(uuid.uuid4()), name=f"tests {permission_key}")
    db.session.add(role)
    db.session.flush()
    db.session.add(RolePermission(uuid=str(uuid.uuid4()), role_id=role.id, permission_id=permission.id))
    db.session.add(UserRole(uuid=str(uuid.uuid4()), user_id=user.id, role_id=role.id))
    db.session.commit()
    return user


def api_headers(user):
    """Headers for the REST API as `user` (None = no key at all)."""
    return {"X-API-KEY": user.api_key} if user is not None else {}
