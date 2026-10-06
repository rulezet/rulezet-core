"""Shared fixtures — see docs/design/test_restructure.md.

The app and its tables are built once per run; every test then starts from an
empty, freshly seeded database (FLASKENV=testing, SQLite) and runs inside the
app context, so the objects it creates stay usable after requests (reload
them with `reload(obj)` to see what a request changed).

Fixtures:
    app        the Flask app, DB created and seeded like a real instance:
               roles/permissions, default tags (tlp:clear, PAP:CLEAR)
    users      SimpleNamespace(admin, owner, user) — see helpers/users.py;
               also seeds the rule formats (they need an admin to exist)
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
from app.core.utils.init_db import insert_default_formats  # noqa: E402
from tests.helpers.users import _password_hash, make_user  # noqa: E402

# The copy-me examples for a new feature live here, they are not tests.
collect_ignore_glob = ["_template/*"]


@pytest.fixture(scope="session")
def _app():
    """The Flask app and its tables, built once per run."""
    app = create_app(start_worker=False)
    app.config.update({
        "TESTING": True,
        "SERVER_NAME": f"{app.config.get('FLASK_URL')}:{app.config.get('FLASK_PORT')}",
    })
    # Tests run inside one app context (so their objects stay usable), and a
    # request reuses the app context already pushed — so Flask's `g`, where
    # Flask-Login caches the logged-in user, would leak from one request to
    # the next (every client seen as the first user loaded). Start each
    # request with an empty `g`, as on a real server.
    def _fresh_request_globals():
        from flask import g
        for name in list(vars(g)):
            delattr(g, name)
    app.before_request_funcs.setdefault(None, []).insert(0, _fresh_request_globals)

    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def _empty_all_tables():
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


@pytest.fixture
def app(_app):
    """The app with an empty database, seeded like a real instance."""
    with _app.app_context():
        _empty_all_tables()
        from app.features.roles.roles_core import seed_default_permissions_and_roles
        seed_default_permissions_and_roles()
        default_user = _seed_default_user()   # author of rules imported without an owner
        _seed_default_tags(created_by=default_user)

        # The login brute-force guard is per process and keyed by IP — every
        # test client is 127.0.0.1, so each test starts with a clean slate.
        from app.features.account import account as _account
        _account._login_failures.clear()

        yield _app

        db.session.remove()


def _seed_default_user():
    """The account init_db.create_default_user() makes — built here with the
    cached password hash: hashing its random password (scrypt) on every test
    was most of the per-test setup time."""
    from app.core.db_class.db import User
    from app.core.utils.utils import generate_api_key
    user = User(first_name="no editor", last_name="no editor", email="default@default.default",
                password_hash=_password_hash(), admin=False, api_key=generate_api_key(), is_verified=True)
    db.session.add(user)
    db.session.commit()
    return user


def _seed_default_tags(created_by):
    """The tags auto-attached to every new rule (config/default_tags.json)."""
    import uuid
    from app.core.db_class.db import Tag
    for name in ("tlp:clear", "PAP:CLEAR"):
        db.session.add(Tag(uuid=str(uuid.uuid4()), name=name, is_active=True, created_by=created_by.id))
    db.session.commit()


@pytest.fixture
def users(app):
    admin = make_user("admin", admin=True)
    insert_default_formats()
    return SimpleNamespace(
        admin=admin,
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
