"""MISP — layer 1: who can do what.

"owner" is the owner of the exported rule / bundle; MISP server connections
have no owner (they are instance settings).

Permission model: the MISP connector — listing, adding, editing, enabling,
deleting, testing a remote MISP server, reading its history and pushing a
rule or a bundle to it — is admin-only. Exporting an active rule as a MISP
object / event (or STIX, converted from it) is public, like reading the rule;
a trashed rule is exported to nobody. A public bundle's MISP event is public;
a private one only for its owner and admins.
"""
import pytest

from app import db
from app.core.db_class.db import MispServer
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from tests_new.helpers.attack import trash
from tests_new.helpers.comments import make_bundle
from tests_new.helpers.db import count, reload
from tests_new.helpers.misp import add_to_bundle, fake_remote, fake_stix, make_server, new_server_payload, push_jobs
from tests_new.helpers.rules import make_rule

EVERYONE = {"anonymous": OK, "user": OK, "owner": OK, "admin": OK}
OWNER_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}


@pytest.fixture
def remote(monkeypatch):
    return fake_remote(monkeypatch)


# ── MISP server connections (admin settings) ──────────────────────────────────

@pytest.mark.parametrize("url", ["/misp/list", "/misp/how-it-works"])
@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_open_misp_pages(role, expected, url, clients):
    response = clients[role].get(url)

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_list_servers(role, expected, clients, users):
    server = make_server(users.admin)

    response = clients[role].get("/misp/get")

    assert_outcome(response, expected)
    assert (server.url.encode() in response.data) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_add_server(role, expected, clients):
    response = clients[role].post("/misp/create", json=new_server_payload())

    assert_outcome(response, expected)
    assert count(MispServer) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_read_server_history(role, expected, clients, users):
    server = make_server(users.admin)

    response = clients[role].get(f"/misp/history/{server.uuid}")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_edit_server(role, expected, clients, users):
    server = make_server(users.admin, name="Before")

    response = clients[role].post(f"/misp/update/{server.uuid}", json={"name": "After"})

    assert_outcome(response, expected)
    assert reload(server).name == ("After" if expected is OK else "Before")


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_delete_server(role, expected, clients, users):
    server = make_server(users.admin)

    response = clients[role].post(f"/misp/delete/{server.uuid}")

    assert_outcome(response, expected)
    assert (reload(server) is None) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_enable_or_disable_server(role, expected, clients, users):
    server = make_server(users.admin, active=True)

    response = clients[role].post(f"/misp/toggle_active/{server.uuid}")

    assert_outcome(response, expected)
    assert reload(server).is_active is (expected is not OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_test_server_connection(role, expected, clients, users, remote):
    server = make_server(users.admin)

    response = clients[role].post(f"/misp/test/{server.uuid}")

    assert_outcome(response, expected)
    assert len(remote.connections) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_push_rule_to_misp(role, expected, clients, users):
    server = make_server(users.admin)
    rule = make_rule(users.owner)

    response = clients[role].post("/misp/push", json={"rule_id": rule.id, "server_uuid": server.uuid})

    assert_outcome(response, expected)
    assert len(push_jobs()) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_push_bundle_to_misp(role, expected, clients, users):
    server = make_server(users.admin)
    bundle = make_bundle(users.owner)

    response = clients[role].post("/misp/push", json={"bundle_id": bundle.id, "server_uuid": server.uuid,
                                                      "push_type": "event"})

    assert_outcome(response, expected)
    assert len(push_jobs()) == (1 if expected is OK else 0)


def test_push_a_trashed_rule_is_refused(clients, users):
    server = make_server(users.admin)
    rule = trash(make_rule(users.owner), users.admin)

    response = clients["admin"].post("/misp/push", json={"rule_id": rule.id, "server_uuid": server.uuid})

    assert response.status_code == 404
    assert push_jobs() == []


# ── Rule export (MISP object / event, STIX) ───────────────────────────────────

@pytest.mark.parametrize("fmt", ["misp", "misp_event"])
@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_export_rule_as_misp(role, expected, fmt, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].get(f"/rule/download_rule?rule_id={rule.id}&format={fmt}")

    assert_outcome(response, expected)
    assert response.get_json()["success"] is True
    assert rule.uuid in response.get_json()["content"]


@pytest.mark.parametrize("fmt", ["misp", "misp_event", "stix"])
@pytest.mark.parametrize("role", ["anonymous", "user", "owner", "admin"])
def test_export_trashed_rule_gives_nothing(role, fmt, clients, users, monkeypatch):
    fake_stix(monkeypatch)
    rule = trash(make_rule(users.owner), users.admin)

    response = clients[role].get(f"/rule/download_rule?rule_id={rule.id}&format={fmt}")

    assert response.status_code < 500
    assert response.get_json()["success"] is False
    assert rule.uuid.encode() not in response.data


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_rule_as_stix(role, expected, clients, users, monkeypatch):
    stix = fake_stix(monkeypatch)
    rule = make_rule(users.owner)

    response = clients[role].get(f"/rule/get_stix/{rule.id}")

    assert_outcome(response, expected)
    assert response.get_json()["stix"] is not None
    assert len(stix.received) == 1


@pytest.mark.parametrize("role", ["anonymous", "user", "owner", "admin"])
def test_trashed_rule_is_never_sent_for_stix_conversion(role, clients, users, monkeypatch):
    stix = fake_stix(monkeypatch)
    rule = trash(make_rule(users.owner), users.admin)

    response = clients[role].get(f"/rule/get_stix/{rule.id}")

    assert response.get_json()["stix"] is None
    assert stix.received == []


# ── Bundle export (MISP event) ────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_export_public_bundle_as_misp(role, expected, clients, users):
    bundle = add_to_bundle(make_bundle(users.owner, public=True), make_rule(users.owner))

    response = clients[role].get(f"/bundle/download_misp?bundle_id={bundle.id}")

    assert_outcome(response, expected)
    assert bundle.uuid.encode() in response.data


# Same answer as every other read of a private bundle: 403, anonymous included
PRIVATE_BUNDLE_READ = {"anonymous": FORBIDDEN, "user": FORBIDDEN, "owner": OK, "admin": OK}


@pytest.mark.parametrize("role, expected", matrix(PRIVATE_BUNDLE_READ))
def test_export_private_bundle_as_misp(role, expected, clients, users):
    bundle = add_to_bundle(make_bundle(users.owner, public=False), make_rule(users.owner))

    response = clients[role].get(f"/bundle/download_misp?bundle_id={bundle.id}")

    assert_outcome(response, expected)
    assert (bundle.uuid.encode() in response.data) is (expected is OK)
