"""Shared fixtures — see docs/design/test_restructure.md.

Every test gets a fresh SQLite database (FLASKENV=testing) and runs inside the
app context, so the objects it creates stay usable after requests (reload
them with `reload(obj)` to see what a request changed).

Fixtures:
    app        the Flask app, DB created and seeded (roles/permissions)
    users      SimpleNamespace(admin, owner, user) — see helpers/users.py
    clients    {"anonymous", "user", "owner", "admin"} → logged-in test clients
    client_as  client_as(user) → a test client logged in as any user
"""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.append(os.getcwd())
os.environ.setdefault("FLASKENV", "testing")

from app import create_app, db  # noqa: E402
from app.core.utils.init_db import create_default_user  # noqa: E402
from tests.helpers.users import make_user  # noqa: E402

# The copy-me examples for a new feature live here, they are not tests.
collect_ignore_glob = ["_template/*"]


@pytest.fixture
def app():
    app = create_app(start_worker=False)
    app.config.update({
        "TESTING": True,
        "SERVER_NAME": f"{app.config.get('FLASK_URL')}:{app.config.get('FLASK_PORT')}",
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
        from app.features.roles.roles_core import seed_default_permissions_and_roles
        seed_default_permissions_and_roles()
        create_default_user()   # author of rules imported without an owner

        # The login brute-force guard is per process and keyed by IP — every
        # test client is 127.0.0.1, so each test starts with a clean slate.
        from app.features.account import account as _account
        _account._login_failures.clear()

        yield app

        db.session.remove()


@pytest.fixture
def users(app):
    return SimpleNamespace(
        admin=make_user("admin", admin=True),
        owner=make_user("owner"),
        user=make_user("user"),
    )


def _logged_in_client(app, user):
    client = app.test_client()
    if user is not None:
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True
    return client


@pytest.fixture
def client_as(app):
    return lambda user: _logged_in_client(app, user)


@pytest.fixture
def clients(app, users):
    return {
        "anonymous": _logged_in_client(app, None),
        "user": _logged_in_client(app, users.user),
        "owner": _logged_in_client(app, users.owner),
        "admin": _logged_in_client(app, users.admin),
    }
