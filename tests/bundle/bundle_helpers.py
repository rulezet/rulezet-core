"""Shared helpers for the bundle feature tests (structure, history, health,
releases, share links). Tests talk to the web blueprint as a logged-in user
through the Flask-Login session; CSRF is disabled in the testing config."""

import datetime
import uuid

from app import db
from app.core.db_class.db import Rule, Tag, User


def user(email):
    return User.query.filter_by(email=email).first()


def owner():
    return user("t@t.t")          # create_user_test() — the "editor" user


def admin():
    return user("admin@admin.admin")


def other():
    return user("neo@admin.admin")  # a second normal user


def login(client, u):
    """Log `client` in as `u`. Tests run many requests inside one
    app_context, where Flask-Login caches the current user on `g` — drop it
    so the next request re-reads the session."""
    from flask import g
    with client.session_transaction() as s:
        s["_user_id"] = str(u.id)
        s["_fresh"] = True
    g.pop("_login_user", None)


def as_anonymous():
    """Next request runs as nobody (see login() about the cached user)."""
    from flask import g
    g.pop("_login_user", None)


def logout(client):
    from flask import g
    with client.session_transaction() as s:
        s.pop("_user_id", None)
    g.pop("_login_user", None)


def make_rule(title, fmt, content, license="MIT", author_id=None):
    r = Rule(
        format=fmt, title=title, license=license, description="test", uuid=str(uuid.uuid4()),
        source="test", author="test", version=1, user_id=author_id or owner().id,
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
        vote_up=0, vote_down=0, to_string=content,
    )
    db.session.add(r)
    db.session.commit()
    return r


def make_bundle(name="Test bundle", public=True, u=None):
    from app.features.bundle import bundle_core as BM
    return BM.create_bundle({"name": name, "description": "desc", "public": public}, u or owner())


def tag(name):
    t = Tag.query.filter_by(name=name).first()
    if not t:
        t = Tag(name=name, uuid=str(uuid.uuid4()), is_active=True, visibility="public",
                created_by=admin().id)
        db.session.add(t)
        db.session.commit()
    return t


def F(name, content=""):
    return {"name": name, "type": "file", "content": content, "children": []}


def D(name, children):
    return {"name": name, "type": "folder", "children": children}


def R(rule_id, name="x"):
    return {"name": name, "type": "file", "rule_id": rule_id, "children": []}


def save_structure(client, bundle_id, structure):
    return client.post(f"/bundle/save_workspace/{bundle_id}", json={"structure": structure})


def fresh(model, pk):
    db.session.expire_all()
    return db.session.get(model, pk)


SURICATA = 'alert http any any -> any any (msg:"{msg}"; content:"x"; sid:{sid}; rev:1;)'
