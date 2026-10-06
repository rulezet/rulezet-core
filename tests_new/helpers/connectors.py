"""Connector factories and a fake remote Rulezet instance.

A connector pulls rules and bundles from another Rulezet over HTTP
(/api/sync/manifest, /stats, /rules, /bundles). Tests never touch the
network: `no_network` (autouse in every connector test module) makes any
outgoing HTTP call fail loudly, and the `remote` fixture replaces
`requests.get` with a `FakeRemote` that answers like a real instance from
the rules / bundles a test gives it — or with whatever broken answer the
test asks for.

    def test_pull_creates_the_remote_rules(app, users, remote):
        remote.rules = [remote_rule(title="From the remote")]
        connector = make_connector(users.admin)

        job = run_pull(app, connector, users.admin)

        assert job.status == "done"
"""
import datetime
import itertools
import socket
import uuid
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from app import db
from app.core.db_class.db import BackgroundJob, Connector
from tests_new.helpers.rules import yara_rule

API = "/connector"
REMOTE_URL = "https://remote.rulezet.test"

_counter = itertools.count(1)


# ── Connectors ────────────────────────────────────────────────────────────────

def make_connector(owner, **overrides):
    """An active Rulezet connector owned by `owner`, pointing at the fake remote."""
    n = next(_counter)
    fields = dict(
        uuid=str(uuid.uuid4()),
        name=f"Test connector {n}",
        connector_type="rulezet",
        instance_url=REMOTE_URL,
        owner_id=owner.id,
        sync_rules=True,
        sync_bundles=False,
        owner_mode="shadow",
    )
    fields.update(overrides)
    connector = Connector(**fields)
    db.session.add(connector)
    db.session.commit()
    return connector


def make_system_connector(owner, **overrides):
    """The read-only kind of connector seeded on every instance ("Rulezet Official")."""
    return make_connector(owner, name="Rulezet Official", is_system=True, sync_bundles=True, **overrides)


def connector_form(**overrides):
    """What the "new connector" dialog posts to /connector/create."""
    n = next(_counter)
    form = dict(name=f"Created connector {n}", instance_url=REMOTE_URL, description="A remote instance",
                api_key_outbound=f"remote-secret-{n}", sync_rules=True, sync_bundles=False, owner_mode="shadow")
    form.update(overrides)
    return form


# ── What a remote serves ──────────────────────────────────────────────────────

def _iso(dt):
    return dt.isoformat() if dt else None


def remote_rule(**overrides):
    """One rule as /api/sync/rules serves it."""
    n = next(_counter)
    now = datetime.datetime(2026, 1, 1, 12, 0, 0)
    item = dict(
        uuid=str(uuid.uuid4()),
        format="yara",
        title=f"Remote rule {n}",
        description=f"Rule {n} of the remote",
        to_string=yara_rule(f"remote_rule_{n}"),
        author="Remote author",
        version="1",
        license="MIT",
        source="remote",
        tags=[],
        cve_ids=[],
        attack_ids=[],
        last_modif=_iso(now),
        created_at=_iso(now),
        update_history=[],
    )
    item.update(overrides)
    return item


def remote_bundle(rules=(), **overrides):
    """One public bundle as /api/sync/bundles serves it, listing `rules` (remote rule dicts)."""
    n = next(_counter)
    item = dict(
        uuid=str(uuid.uuid4()),
        name=f"Remote bundle {n}",
        description=f"Bundle {n} of the remote",
        rules=[r["uuid"] for r in rules],
        tags=[],
        vulnerability_identifiers=[],
        updated_at=_iso(datetime.datetime(2026, 1, 1, 12, 0, 0)),
        created_at=_iso(datetime.datetime(2026, 1, 1, 12, 0, 0)),
        structure=[],
    )
    item.update(overrides)
    return item


MANIFEST = {
    "instance": {"name": "Remote Rulezet", "version": "2.0.0", "url": REMOTE_URL},
    "sync_api_version": 2,
    "capabilities": {"sync_rules": True, "sync_bundles": True, "rule_filters": True, "rule_attacks": True,
                     "rule_uuids": True, "count_only": True, "bundle_structure": True},
}


class FakeResponse:
    def __init__(self, status_code=200, json=None, text=None):
        self.status_code = status_code
        self._json = json
        self.text = text if text is not None else ""

    def json(self):
        if self.text and self._json is None:
            raise requests.exceptions.JSONDecodeError("Expecting value", self.text, 0)
        return self._json


class FakeRemote:
    """A remote Rulezet instance behind `requests.get`.

    rules / bundles   what the remote serves (dicts from remote_rule() /
                      remote_bundle()), paginated like the real sync API
    manifest          the /api/sync/manifest answer
    answer(endpoint, ...)  replace one endpoint's answer — endpoint is
                      "manifest", "stats", "rules", "count" (rules?count_only)
                      or "bundles"; give `json=`, `text=` (not JSON),
                      `status=`, or `raises=` an exception
    calls             every URL requested, with its headers
    """

    def __init__(self):
        self.rules = []
        self.bundles = []
        self.manifest = MANIFEST
        self.overrides = {}
        self.calls = []

    def answer(self, endpoint, *, status=200, json=None, text=None, raises=None):
        self.overrides[endpoint] = (status, json, text, raises)

    def urls(self, endpoint=None):
        return [url for url, _ in self.calls if endpoint is None or f"/api/sync/{endpoint}" in url]

    def __call__(self, url, headers=None, timeout=None, params=None, **kwargs):
        self.calls.append((url, dict(headers or {})))
        parsed = urlparse(url)
        query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
        query.update(params or {})
        endpoint = parsed.path.rsplit("/", 1)[-1]
        if endpoint == "rules" and query.get("count_only") == "true":
            endpoint = "count"

        if endpoint in self.overrides:
            status, json, text, raises = self.overrides[endpoint]
            if raises is not None:
                raise raises
            return FakeResponse(status, json, text)
        return self._serve(endpoint, query)

    def _serve(self, endpoint, query):
        if endpoint == "manifest":
            return FakeResponse(200, self.manifest)
        if endpoint == "stats":
            return FakeResponse(200, {"rules": len(self.rules), "bundles": len(self.bundles)})
        if endpoint == "count":
            return FakeResponse(200, {"count": len(self.rules), "cve": query.get("cve", "")})
        if endpoint == "rules" and query.get("uuids"):
            wanted = set(query["uuids"].split(","))
            found = [r for r in self.rules if r.get("uuid") in wanted]
            return FakeResponse(200, {"page": 1, "per_page": len(found), "total": len(found),
                                      "has_more": False, "rules": found})
        if endpoint in ("rules", "bundles"):
            items = self.rules if endpoint == "rules" else self.bundles
            page, per_page = int(query.get("page", 1)), int(query.get("per_page", 50))
            chunk = items[(page - 1) * per_page: page * per_page]
            return FakeResponse(200, {"page": page, "per_page": per_page, "total": len(items),
                                      "has_more": page * per_page < len(items), endpoint: chunk})
        return FakeResponse(404, {"error": "Not found."})


def _refuse_network(*args, **kwargs):
    raise AssertionError(f"A test tried to reach the network: {args[:2]}")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """No HTTP call leaves the test process, and job notifications stay quiet."""
    monkeypatch.setattr(requests.Session, "request", _refuse_network)
    monkeypatch.setattr(socket.socket, "connect", _refuse_network)
    with mock.patch("app.features.notification.notification_core.create_job_notification"):
        yield


@pytest.fixture
def remote(monkeypatch):
    """A FakeRemote answering every `requests.get` the connector code makes."""
    fake = FakeRemote()
    monkeypatch.setattr(requests, "get", fake)
    return fake


# ── Running a pull ────────────────────────────────────────────────────────────

def run_pull(app, connector, by, **options):
    """Queue a pull of `connector` as `by` (like the "Pull" button) and run
    the connector_pull job handler on it directly, not through the worker.
    `options`: sync_rules, sync_bundles, filters. Returns the job, reloaded."""
    from app.features.connector.connector_core import trigger_pull

    job = trigger_pull(connector, triggered_by=by.id, **options)
    return run_job(app, job)


def run_job(app, job):
    """Run a queued connector_pull job's handler — an exception it raises
    reaches the test (the worker would only mark the job failed)."""
    from app.features.jobs.job_handlers import handle_connector_pull

    handle_connector_pull(job, app)
    db.session.expire_all()
    return db.session.get(BackgroundJob, job.id)


def pull_jobs():
    db.session.expire_all()
    return BackgroundJob.query.filter_by(job_type="connector_pull").all()
