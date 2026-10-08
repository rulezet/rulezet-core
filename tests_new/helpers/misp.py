"""MISP factories — configured MISP servers, a fake remote MISP instance
(no network: PyMISP's client is replaced) and helpers to read the MISP JSON
Rulezet exports.

    remote = fake_remote(monkeypatch)            # every PyMISP client is now `remote`
    remote.version = {"version": "2.5.0"}        # what the instance answers
    remote.add_event_result = {"errors": "..."}  # or garbage, or an exception to raise
"""
import itertools
import uuid

from app import db
from app.core.db_class.db import BackgroundJob, MispServer

API_KEY = "misp-secret-api-key-0123456789abcdef"

_counter = itertools.count(1)


def make_server(added_by, *, api_key=API_KEY, active=True, **overrides):
    """A MISP server connection added by `added_by`, its key encrypted the
    way the "add server" form stores it."""
    from app.features.misp.misp_connector_core import _encrypt
    n = next(_counter)
    fields = dict(uuid=str(uuid.uuid4()), name=f"MISP {n}", url=f"https://misp{n}.example.org",
                  api_key_encrypted=_encrypt(api_key), verify_tls=True, added_by_id=added_by.id,
                  is_active=active)
    fields.update(overrides)
    server = MispServer(**fields)
    db.session.add(server)
    db.session.commit()
    return server


def new_server_payload(**overrides):
    """What the "add a MISP server" form posts (JSON)."""
    payload = dict(name=f"New MISP {next(_counter)}", url="https://misp.example.org/",
                   api_key=API_KEY, verify_tls=True, description="Added in a test")
    payload.update(overrides)
    return payload


ACCEPT = object()   # FakeMisp.add_event_result: the remote accepts the event


class FakeMisp:
    """Stands in for pymisp.ExpandedPyMISP: records how it was built and what
    was pushed to it; answers what the test sets."""

    def __init__(self):
        self.version = {"version": "2.5.0"}
        self.add_event_result = ACCEPT    # or any garbage answer / an exception
        self.connections = []             # (url, key, ssl) per client built
        self.pushed = []                  # events received by add_event()

    def client(self, url, key, ssl=True, timeout=None, **_):
        self.connections.append((url, key, ssl))
        return _FakeClient(self)


class _FakeClient:
    def __init__(self, remote):
        self._remote = remote

    @property
    def misp_instance_version(self):
        if isinstance(self._remote.version, Exception):
            raise self._remote.version
        return self._remote.version

    def add_event(self, event, pythonify=False):
        result = self._remote.add_event_result
        if isinstance(result, Exception):
            raise result
        self._remote.pushed.append(event)
        return event if result is ACCEPT else result


def fake_remote(monkeypatch):
    """Every PyMISP client Rulezet builds now talks to a FakeMisp."""
    import pymisp
    remote = FakeMisp()
    monkeypatch.setattr(pymisp, "ExpandedPyMISP", remote.client)
    return remote


def push_jobs():
    db.session.expire_all()
    return BackgroundJob.query.filter_by(job_type="misp_push").all()


def run_job(job):
    """Run a queued job's registered handler directly (no worker loop)."""
    from flask import current_app
    from app.features.jobs import job_handlers  # noqa: F401 — registers the handlers
    from app.features.jobs.job_worker import _HANDLERS
    _HANDLERS[job.job_type](job, current_app._get_current_object())
    db.session.expire_all()
    return db.session.get(BackgroundJob, job.id)


def objects_named(event, name):
    """The MISP objects called `name` in an exported event (JSON dict)."""
    return [o for o in event.get("Object", []) if o.get("name") == name]


def values(misp_object, relation):
    """Values of the attributes with `relation` in a MISP object (JSON dict)."""
    return [a["value"] for a in misp_object.get("Attribute", []) if a.get("object_relation") == relation]


def add_to_bundle(bundle, *rules):
    """Put `rules` in `bundle` (the bundle ↔ rule link the editor creates)."""
    from app.core.db_class.db import BundleRuleAssociation
    for rule in rules:
        db.session.add(BundleRuleAssociation(bundle_id=bundle.id, rule_id=rule.id))
    db.session.commit()
    return bundle


class FakeStix:
    """Stands in for cti-transmute.org (MISP → STIX): records what was sent,
    answers `answer` (a JSON value, or an exception to raise)."""

    def __init__(self):
        self.answer = {"type": "bundle", "id": "bundle--1", "objects": []}
        self.received = []

    def post(self, url, json=None, **_):
        self.received.append(json)
        if isinstance(self.answer, Exception):
            raise self.answer
        return _FakeResponse(self.answer)


class _FakeResponse:
    def __init__(self, answer):
        self._answer = answer

    def raise_for_status(self):
        pass

    def json(self):
        if isinstance(self._answer, Exception):
            raise self._answer
        return self._answer


def fake_stix(monkeypatch):
    """The MISP → STIX conversion never leaves the machine."""
    from app.features.misp import misp_core
    stix = FakeStix()
    monkeypatch.setattr(misp_core.requests, "post", stix.post)
    return stix
