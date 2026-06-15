"""
Tests for the instance phone-home registry endpoint.
  POST /api/instance/register

The telemetry sender (app/__init__.py _start_telemetry) posts:
  { uuid, url, version, rules_count, bundles_count }
"""

import uuid
import datetime

import pytest

from app import db
from app.core.db_class.db import RegisteredInstance


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ping(client, payload=None):
    if payload is None:
        payload = {
            "uuid":          str(uuid.uuid4()),
            "url":           "http://example.com",
            "version":       "v1.5.0",
            "rules_count":   10,
            "bundles_count": 2,
        }
    return client.post("/api/instance/register", json=payload,
                       content_type="application/json")


# ── IS_OFFICIAL_INSTANCE guard ────────────────────────────────────────────────

def test_register_returns_404_when_not_official(app, client):
    """Endpoint must be invisible on non-official instances."""
    original = app.config.get("IS_OFFICIAL_INSTANCE")
    app.config["IS_OFFICIAL_INSTANCE"] = False
    try:
        r = _ping(client)
        assert r.status_code == 404
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = original


def test_register_returns_200_when_official(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        r = _ping(client)
        assert r.status_code == 200
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


# ── Payload validation ────────────────────────────────────────────────────────

def test_register_requires_uuid(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        r = client.post("/api/instance/register", json={"url": "http://x.com"},
                        content_type="application/json")
        assert r.status_code in (400, 422)
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


def test_register_without_url_is_ok(app, client):
    """url is optional."""
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        payload = {
            "uuid":          str(uuid.uuid4()),
            "version":       "v1.0.0",
            "rules_count":   0,
            "bundles_count": 0,
        }
        r = client.post("/api/instance/register", json=payload,
                        content_type="application/json")
        assert r.status_code == 200
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


# ── Upsert behavior ───────────────────────────────────────────────────────────

def test_register_creates_new_instance(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        uid = str(uuid.uuid4())
        _ping(client, {"uuid": uid, "url": "http://new.example.com",
                       "version": "v1.0.0", "rules_count": 5, "bundles_count": 1})
        with app.app_context():
            row = RegisteredInstance.query.filter_by(uuid=uid).first()
        assert row is not None
        assert row.public_url == "http://new.example.com"
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


def test_register_updates_existing_instance(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        uid = str(uuid.uuid4())
        _ping(client, {"uuid": uid, "url": "http://update.example.com",
                       "version": "v1.0.0", "rules_count": 1, "bundles_count": 0})
        # Simulate 2h gap to bypass rate-limit
        with app.app_context():
            row = RegisteredInstance.query.filter_by(uuid=uid).first()
            row.last_seen = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
            db.session.commit()
        _ping(client, {"uuid": uid, "url": "http://update.example.com",
                       "version": "v1.1.0", "rules_count": 99, "bundles_count": 3})
        with app.app_context():
            row = RegisteredInstance.query.filter_by(uuid=uid).first()
        assert row.version == "v1.1.0"
        assert row.rules_count == 99
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


def test_register_increments_ping_count(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        uid = str(uuid.uuid4())
        payload = {"uuid": uid, "url": "http://ping.example.com",
                   "version": "v1.0.0", "rules_count": 0, "bundles_count": 0}
        _ping(client, payload)
        # Force past the rate-limit window
        with app.app_context():
            row = RegisteredInstance.query.filter_by(uuid=uid).first()
            row.last_seen = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
            db.session.commit()
        _ping(client, payload)
        with app.app_context():
            row = RegisteredInstance.query.filter_by(uuid=uid).first()
        assert row.ping_count >= 2
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


def test_register_sets_first_seen_only_once(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        uid = str(uuid.uuid4())
        payload = {"uuid": uid, "url": "http://first.example.com",
                   "version": "v1.0.0", "rules_count": 0, "bundles_count": 0}
        _ping(client, payload)
        with app.app_context():
            row = RegisteredInstance.query.filter_by(uuid=uid).first()
            first_seen = row.first_seen
            row.last_seen = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
            db.session.commit()
        _ping(client, payload)
        with app.app_context():
            row = RegisteredInstance.query.filter_by(uuid=uid).first()
        assert row.first_seen == first_seen
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


def test_register_updates_last_seen(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        uid = str(uuid.uuid4())
        payload = {"uuid": uid, "url": "http://lastseen.example.com",
                   "version": "v1.0.0", "rules_count": 0, "bundles_count": 0}
        _ping(client, payload)
        with app.app_context():
            first_last = RegisteredInstance.query.filter_by(uuid=uid).first().last_seen
            RegisteredInstance.query.filter_by(uuid=uid).first().last_seen = (
                datetime.datetime.utcnow() - datetime.timedelta(hours=2)
            )
            db.session.commit()
        _ping(client, payload)
        with app.app_context():
            second_last = RegisteredInstance.query.filter_by(uuid=uid).first().last_seen
        assert second_last >= first_last
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


def test_register_response_contains_status(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        uid = str(uuid.uuid4())
        r = _ping(client, {"uuid": uid, "url": "http://resp.example.com",
                           "version": "v1.0.0", "rules_count": 0, "bundles_count": 0})
        data = r.get_json()
        assert "status" in data or "uuid" in data or "message" in data
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


# ── Rate limiting ─────────────────────────────────────────────────────────────

def test_register_rate_limit_same_uuid_within_hour(app, client):
    """
    Two pings in the same request window: first 200, second may be
    rate-limited (200 with rate_limited status) or still 200.
    """
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        uid = str(uuid.uuid4())
        payload = {"uuid": uid, "url": "http://rate.example.com",
                   "version": "v1.0.0", "rules_count": 0, "bundles_count": 0}
        r1 = _ping(client, payload)
        r2 = _ping(client, payload)
        assert r1.status_code == 200
        # Second ping within an hour → rate_limited or still accepted
        assert r2.status_code in (200, 429)
        if r2.status_code == 200:
            data2 = r2.get_json()
            assert data2.get("status") in ("registered", "rate_limited")
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


# ── Different instances ───────────────────────────────────────────────────────

def test_different_uuids_are_independent_instances(app, client):
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        uid1 = str(uuid.uuid4())
        uid2 = str(uuid.uuid4())
        _ping(client, {"uuid": uid1, "url": "http://a.example.com",
                       "version": "v1.0.0", "rules_count": 1, "bundles_count": 0})
        _ping(client, {"uuid": uid2, "url": "http://b.example.com",
                       "version": "v2.0.0", "rules_count": 2, "bundles_count": 0})
        with app.app_context():
            row1 = RegisteredInstance.query.filter_by(uuid=uid1).first()
            row2 = RegisteredInstance.query.filter_by(uuid=uid2).first()
        assert row1 is not None
        assert row2 is not None
        assert row1.id != row2.id
        assert row1.version == "v1.0.0"
        assert row2.version == "v2.0.0"
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False


def test_same_url_different_uuid(app, client):
    """
    Two instances with the same URL but different UUIDs → two rows.
    """
    app.config["IS_OFFICIAL_INSTANCE"] = True
    try:
        url = "http://shared-url.example.com"
        uid1 = str(uuid.uuid4())
        uid2 = str(uuid.uuid4())
        _ping(client, {"uuid": uid1, "url": url,
                       "version": "v1.0.0", "rules_count": 0, "bundles_count": 0})
        _ping(client, {"uuid": uid2, "url": url,
                       "version": "v1.0.0", "rules_count": 0, "bundles_count": 0})
        with app.app_context():
            rows = RegisteredInstance.query.filter_by(public_url=url).all()
        assert len(rows) >= 2
    finally:
        app.config["IS_OFFICIAL_INSTANCE"] = False
