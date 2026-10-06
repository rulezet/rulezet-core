"""
Tests for the connector blueprint routes (CRUD + actions).
All routes require an admin session.
"""

import uuid
import pytest

from app import db
from app.core.db_class.db import Connector, User


# ── Auth helper ───────────────────────────────────────────────────────────────

def login_admin(client):
    """Log in as the test admin and return the client (session is kept)."""
    client.post("/account/login", data={
        "email": "admin@admin.admin",
        "password": "admin",
        "remember_me": False,
    }, follow_redirects=True)
    return client


def login_user(client):
    """Log in as a regular (non-admin) user."""
    client.post("/account/login", data={
        "email": "t@t.t",
        "password": "password1@A",
        "remember_me": False,
    }, follow_redirects=True)
    return client


def create_connector_via_api(client, name="TestConn", url="http://remote.example.com"):
    return client.post("/connector/create", json={
        "name": name,
        "instance_url": url,
        "sync_rules": True,
        "sync_bundles": False,
        "owner_mode": "shadow",
    }, content_type="application/json")


# ── Auth enforcement ──────────────────────────────────────────────────────────

def test_connector_list_requires_login(client):
    r = client.get("/connector/list", follow_redirects=False)
    # Should redirect to login
    assert r.status_code in (302, 403)


def test_connector_create_requires_admin(client):
    login_user(client)
    r = client.post("/connector/create", json={"name": "x", "instance_url": "http://x.com"})
    assert r.status_code == 403


def test_connector_get_requires_login(client):
    r = client.get("/connector/get")
    assert r.status_code in (302, 403)


# ── Create connector ──────────────────────────────────────────────────────────

def test_create_connector_valid(client):
    login_admin(client)
    r = create_connector_via_api(client)
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert "connector" in data
    assert data["connector"]["name"] == "TestConn"


def test_create_connector_stores_url_without_trailing_slash(client):
    login_admin(client)
    r = create_connector_via_api(client, url="http://remote.example.com/")
    data = r.get_json()
    assert data["connector"]["instance_url"] == "http://remote.example.com"


def test_create_connector_missing_name(client):
    login_admin(client)
    r = client.post("/connector/create", json={"instance_url": "http://x.com"},
                    content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["success"] is False


def test_create_connector_missing_url(client):
    login_admin(client)
    r = client.post("/connector/create", json={"name": "MyConn"},
                    content_type="application/json")
    assert r.status_code == 400


def test_create_connector_shadow_mode(client):
    login_admin(client)
    r = create_connector_via_api(client, name="ShadowConn")
    data = r.get_json()
    assert data["connector"]["owner_mode"] == "shadow"


def test_create_connector_sync_bundles_flag(client):
    login_admin(client)
    r = client.post("/connector/create", json={
        "name": "BundleConn",
        "instance_url": "http://b.example.com",
        "sync_rules": True,
        "sync_bundles": True,
    }, content_type="application/json")
    data = r.get_json()
    assert data["connector"]["sync_bundles"] is True


# ── Get connectors ────────────────────────────────────────────────────────────

def test_get_connectors_returns_list(client):
    login_admin(client)
    r = client.get("/connector/get")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_get_connectors_includes_created(client):
    login_admin(client)
    create_connector_via_api(client, name="ListMe")
    data = client.get("/connector/get").get_json()
    names = [c["name"] for c in data]
    assert "ListMe" in names


def test_get_connectors_has_is_self_field(client):
    login_admin(client)
    data = client.get("/connector/get").get_json()
    for c in data:
        assert "is_self" in c


# ── Update connector ──────────────────────────────────────────────────────────

def test_update_connector_name(app, client):
    login_admin(client)
    r = create_connector_via_api(client, name="OldName")
    conn_uuid = r.get_json()["connector"]["uuid"]

    r2 = client.post(f"/connector/update/{conn_uuid}", json={"name": "NewName"},
                     content_type="application/json")
    assert r2.status_code == 200
    assert r2.get_json()["success"] is True

    with app.app_context():
        conn = Connector.query.filter_by(uuid=conn_uuid).first()
        assert conn.name == "NewName"


def test_update_connector_not_found(client):
    login_admin(client)
    r = client.post(f"/connector/update/{uuid.uuid4()}", json={"name": "x"},
                    content_type="application/json")
    assert r.status_code == 404


def test_update_system_connector_is_forbidden(app, client):
    login_admin(client)
    with app.app_context():
        sys_conn = Connector.query.filter_by(is_system=True).first()
        if sys_conn is None:
            pytest.skip("No system connector seeded")
        conn_uuid = sys_conn.uuid
    r = client.post(f"/connector/update/{conn_uuid}", json={"name": "Hacked"},
                    content_type="application/json")
    assert r.status_code == 403


# ── Delete connector ──────────────────────────────────────────────────────────

def test_delete_connector(app, client):
    login_admin(client)
    r = create_connector_via_api(client, name="DeleteMe")
    conn_uuid = r.get_json()["connector"]["uuid"]

    r2 = client.post(f"/connector/delete/{conn_uuid}")
    assert r2.status_code == 200
    assert r2.get_json()["success"] is True

    with app.app_context():
        assert Connector.query.filter_by(uuid=conn_uuid).first() is None


def test_delete_connector_not_found(client):
    login_admin(client)
    r = client.post(f"/connector/delete/{uuid.uuid4()}")
    assert r.status_code == 404


def test_delete_system_connector_is_forbidden(app, client):
    login_admin(client)
    with app.app_context():
        sys_conn = Connector.query.filter_by(is_system=True).first()
        if sys_conn is None:
            pytest.skip("No system connector seeded")
        conn_uuid = sys_conn.uuid
    r = client.post(f"/connector/delete/{conn_uuid}")
    assert r.status_code == 403


# ── Pull trigger ──────────────────────────────────────────────────────────────

def test_pull_self_is_blocked(app, client):
    """Pulling from the current instance URL must be rejected."""
    login_admin(client)
    # The test server runs on the same host:port that _is_self() checks
    self_url = f"http://{app.config.get('FLASK_URL', '127.0.0.1')}:{app.config.get('FLASK_PORT', 7009)}"
    r = create_connector_via_api(client, name="SelfConn", url=self_url)
    conn_uuid = r.get_json()["connector"]["uuid"]

    r2 = client.post(f"/connector/pull/{conn_uuid}", json={"mode": "soft"},
                     content_type="application/json")
    assert r2.status_code == 400
    assert "yourself" in r2.get_json()["error"].lower()


def test_pull_invalid_connector(client):
    login_admin(client)
    r = client.post(f"/connector/pull/{uuid.uuid4()}", json={"mode": "soft"},
                    content_type="application/json")
    assert r.status_code == 404


def test_pull_disabled_connector(app, client):
    login_admin(client)
    r = create_connector_via_api(client, name="DisabledConn", url="http://disabled.example.com")
    conn_uuid = r.get_json()["connector"]["uuid"]
    with app.app_context():
        conn = Connector.query.filter_by(uuid=conn_uuid).first()
        conn.is_active = False
        db.session.commit()

    r2 = client.post(f"/connector/pull/{conn_uuid}", json={"mode": "soft"},
                     content_type="application/json")
    assert r2.status_code == 400
    assert "disabled" in r2.get_json()["error"].lower()


def test_pull_valid_connector_queues_job(app, client):
    login_admin(client)
    r = create_connector_via_api(client, name="PullConn", url="http://remote.pull.example.com")
    conn_uuid = r.get_json()["connector"]["uuid"]

    r2 = client.post(f"/connector/pull/{conn_uuid}", json={"mode": "soft"},
                     content_type="application/json")
    assert r2.status_code == 200
    data = r2.get_json()
    assert data["success"] is True
    assert "job_uuid" in data or "job_id" in data or "job" in data


# ── Connector history ─────────────────────────────────────────────────────────

def test_connector_history_returns_list(client):
    login_admin(client)
    r = create_connector_via_api(client, name="HistoryConn")
    conn_uuid = r.get_json()["connector"]["uuid"]

    r2 = client.get(f"/connector/history/{conn_uuid}")
    assert r2.status_code == 200
    assert isinstance(r2.get_json(), list)


def test_connector_history_not_found(client):
    login_admin(client)
    r = client.get(f"/connector/history/{uuid.uuid4()}")
    assert r.status_code == 404
