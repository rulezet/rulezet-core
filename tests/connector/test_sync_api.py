"""
Tests for the public sync API endpoints exposed to remote connectors.
  GET /api/sync/manifest
  GET /api/sync/stats
  GET /api/sync/rules
  GET /api/sync/bundles
No authentication required on these routes.
"""

import datetime
import uuid

import pytest

from app import db
from app.core.db_class.db import Rule, Bundle, User


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_rule(user_id, title="Test Rule", fmt="yara", to_string="rule x { condition: true }",
               last_modif=None):
    now = last_modif or datetime.datetime.utcnow()
    r = Rule(
        uuid=str(uuid.uuid4()),
        user_id=user_id,
        format=fmt,
        title=title,
        to_string=to_string,
        author="tester",
        source="test",
        version=1,
        vote_up=0,
        vote_down=0,
        creation_date=now,
        last_modif=now,
        is_deleted=False,
    )
    db.session.add(r)
    db.session.commit()
    return r


def _make_bundle(user_id, name="Test Bundle", access=True, updated_at=None):
    now = updated_at or datetime.datetime.utcnow()
    b = Bundle(
        uuid=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        description="test",
        created_by="test",
        access=access,
        vote_up=0,
        vote_down=0,
        created_at=now,
        updated_at=now,
    )
    db.session.add(b)
    db.session.commit()
    return b


def _editor_id(app):
    with app.app_context():
        return User.query.filter_by(email="t@t.t").first().id


# ── /api/sync/manifest ────────────────────────────────────────────────────────

def test_manifest_returns_200(client):
    r = client.get("/api/sync/manifest")
    assert r.status_code == 200


def test_manifest_has_instance_block(client):
    data = client.get("/api/sync/manifest").get_json()
    assert "instance" in data
    assert "version" in data["instance"]


def test_manifest_has_capabilities(client):
    data = client.get("/api/sync/manifest").get_json()
    assert "capabilities" in data
    caps = data["capabilities"]
    assert caps.get("sync_rules") is True
    assert caps.get("sync_bundles") is True


# ── /api/sync/stats ───────────────────────────────────────────────────────────

def test_stats_returns_200(client):
    r = client.get("/api/sync/stats")
    assert r.status_code == 200


def test_stats_has_rules_and_bundles(client):
    data = client.get("/api/sync/stats").get_json()
    assert "rules" in data
    assert "bundles" in data
    assert isinstance(data["rules"], int)
    assert isinstance(data["bundles"], int)


def test_stats_reflects_created_rule(app, client):
    with app.app_context():
        before = client.get("/api/sync/stats").get_json()["rules"]
        _make_rule(_editor_id(app), title="Stats Test Rule")
        after = client.get("/api/sync/stats").get_json()["rules"]
    assert after == before + 1


def test_stats_excludes_deleted_rules(app, client):
    with app.app_context():
        rule = _make_rule(_editor_id(app), title="Deleted Rule")
        rule.is_deleted = True
        db.session.commit()
        data = client.get("/api/sync/stats").get_json()
        # The deleted rule must not appear in the count
        non_deleted = Rule.query.filter_by(is_deleted=False).count()
    assert data["rules"] == non_deleted


def test_stats_excludes_private_bundles(app, client):
    with app.app_context():
        _make_bundle(_editor_id(app), name="Private", access=False)
        data = client.get("/api/sync/stats").get_json()
        public_count = Bundle.query.filter_by(access=True).count()
    assert data["bundles"] == public_count


# ── /api/sync/rules ───────────────────────────────────────────────────────────

def test_rules_returns_200(client):
    r = client.get("/api/sync/rules")
    assert r.status_code == 200


def test_rules_response_shape(client):
    data = client.get("/api/sync/rules").get_json()
    for key in ("since", "page", "per_page", "total", "has_more", "rules"):
        assert key in data


def test_rules_default_page_is_1(client):
    data = client.get("/api/sync/rules").get_json()
    assert data["page"] == 1


def test_rules_pagination(app, client):
    with app.app_context():
        uid = _editor_id(app)
        for i in range(5):
            _make_rule(uid, title=f"Pag Rule {i}")
    r1 = client.get("/api/sync/rules?per_page=2&page=1").get_json()
    r2 = client.get("/api/sync/rules?per_page=2&page=2").get_json()
    assert len(r1["rules"]) == 2
    assert r1["has_more"] is True
    # UUIDs on page 2 must be different from page 1
    uuids1 = {r["uuid"] for r in r1["rules"]}
    uuids2 = {r["uuid"] for r in r2["rules"]}
    assert uuids1.isdisjoint(uuids2)


def test_rules_per_page_capped_at_500(client):
    data = client.get("/api/sync/rules?per_page=99999").get_json()
    assert data["per_page"] == 500


def test_rules_per_page_minimum_is_1(client):
    data = client.get("/api/sync/rules?per_page=0").get_json()
    assert data["per_page"] == 1


def test_rules_since_filter(app, client):
    with app.app_context():
        uid = _editor_id(app)
        old_ts = datetime.datetime(2000, 1, 1)
        new_ts = datetime.datetime.utcnow()
        _make_rule(uid, title="Old Rule", last_modif=old_ts)
        new_rule = _make_rule(uid, title="New Rule", last_modif=new_ts)
        since = "2020-01-01T00:00:00"
        data = client.get(f"/api/sync/rules?since={since}").get_json()
        titles = [r["title"] for r in data["rules"]]
    assert "New Rule" in titles
    assert "Old Rule" not in titles


def test_rules_invalid_since_falls_back_to_epoch(client):
    # Should not crash, just treat as epoch
    r = client.get("/api/sync/rules?since=not-a-date")
    assert r.status_code == 200


def test_rules_excludes_deleted(app, client):
    with app.app_context():
        uid = _editor_id(app)
        rule = _make_rule(uid, title="Will Be Deleted")
        rule.is_deleted = True
        db.session.commit()
        deleted_uuid = rule.uuid
    data = client.get("/api/sync/rules").get_json()
    uuids = [r["uuid"] for r in data["rules"]]
    assert deleted_uuid not in uuids


def test_rules_item_has_required_fields(app, client):
    with app.app_context():
        _make_rule(_editor_id(app), title="Field Check Rule")
    data = client.get("/api/sync/rules").get_json()
    assert len(data["rules"]) > 0
    rule = data["rules"][0]
    for field in ("uuid", "format", "title", "to_string", "tags", "update_history"):
        assert field in rule


def test_rules_has_more_false_on_last_page(app, client):
    with app.app_context():
        uid = _editor_id(app)
        total = Rule.query.filter_by(is_deleted=False).count()
        # Request more than total
        data = client.get(f"/api/sync/rules?per_page={total + 100}").get_json()
    assert data["has_more"] is False


def test_rules_page_beyond_last_returns_empty(app, client):
    with app.app_context():
        total = Rule.query.filter_by(is_deleted=False).count()
    data = client.get(f"/api/sync/rules?page=99999&per_page=500").get_json()
    assert data["rules"] == []
    assert data["has_more"] is False


# ── /api/sync/bundles ─────────────────────────────────────────────────────────

def test_bundles_returns_200(client):
    r = client.get("/api/sync/bundles")
    assert r.status_code == 200


def test_bundles_response_shape(client):
    data = client.get("/api/sync/bundles").get_json()
    for key in ("since", "page", "per_page", "total", "has_more", "bundles"):
        assert key in data


def test_bundles_excludes_private(app, client):
    with app.app_context():
        uid = _editor_id(app)
        _make_bundle(uid, name="Secret Bundle", access=False)
        data = client.get("/api/sync/bundles").get_json()
        names = [b["name"] for b in data["bundles"]]
    assert "Secret Bundle" not in names


def test_bundles_includes_public(app, client):
    with app.app_context():
        uid = _editor_id(app)
        _make_bundle(uid, name="Public Bundle", access=True)
        data = client.get("/api/sync/bundles").get_json()
        names = [b["name"] for b in data["bundles"]]
    assert "Public Bundle" in names


def test_bundles_pagination(app, client):
    with app.app_context():
        uid = _editor_id(app)
        for i in range(6):
            _make_bundle(uid, name=f"Bundle Pag {i}")
    data = client.get("/api/sync/bundles?per_page=3&page=1").get_json()
    assert len(data["rules"] if "rules" in data else data["bundles"]) <= 3


def test_bundles_since_filter(app, client):
    with app.app_context():
        uid = _editor_id(app)
        old_ts = datetime.datetime(2000, 6, 1)
        new_ts = datetime.datetime.utcnow()
        _make_bundle(uid, name="Old Bundle", updated_at=old_ts)
        _make_bundle(uid, name="New Bundle", updated_at=new_ts)
        data = client.get("/api/sync/bundles?since=2020-01-01T00:00:00").get_json()
        names = [b["name"] for b in data["bundles"]]
    assert "New Bundle" in names
    assert "Old Bundle" not in names


def test_bundles_item_has_required_fields(app, client):
    with app.app_context():
        _make_bundle(_editor_id(app), name="Field Check Bundle")
    data = client.get("/api/sync/bundles").get_json()
    assert len(data["bundles"]) > 0
    b = data["bundles"][0]
    for field in ("uuid", "name", "description", "updated_at", "created_at"):
        assert field in b


def test_bundles_per_page_capped(client):
    data = client.get("/api/sync/bundles?per_page=99999").get_json()
    assert data["per_page"] == 500
