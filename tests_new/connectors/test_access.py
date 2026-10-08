"""Connectors — layer 1: who can do what.

Permission model: connectors (federation sync with other Rulezet instances)
are admin-only — every page and JSON route of /connector, whoever owns the
connector. Anonymous visitors are sent to the login page, logged-in
non-admins get 403, even for a connector recorded as theirs. A refused call
never reaches the remote instance and changes nothing. The sync API that
remotes read (/api/sync, layer 3) is public.
"""
import pytest

from app.core.db_class.db import BackgroundJob, Connector, Tag
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from tests_new.helpers.connectors import API, connector_form, make_connector, no_network, remote  # noqa: F401
from tests_new.helpers.db import count, reload

ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}


# ── Pages ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("page", ["list", "how-it-works"])
@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_open_connector_pages(page, role, expected, clients):
    response = clients[role].get(f"{API}/{page}")

    assert_outcome(response, expected)


# ── Reading ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_list_connectors(role, expected, clients, users):
    connector = make_connector(users.admin)

    response = clients[role].get(f"{API}/get")

    assert_outcome(response, expected)
    assert (connector.uuid.encode() in response.data) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_read_connector_history(role, expected, clients, users):
    connector = make_connector(users.owner)

    response = clients[role].get(f"{API}/history/{connector.uuid}")

    assert_outcome(response, expected)


# ── Creating, editing, deleting ───────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_create_connector(role, expected, clients, remote):
    form = connector_form()

    response = clients[role].post(f"{API}/create", json=form)

    assert_outcome(response, expected)
    assert count(Connector, name=form["name"]) == (1 if expected is OK else 0)
    assert remote.calls == []


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_update_connector(role, expected, clients, users):
    """Owning the connector gives a non-admin nothing."""
    connector = make_connector(users.owner)

    response = clients[role].post(f"{API}/update/{connector.uuid}", json={"name": "Renamed"})

    assert_outcome(response, expected)
    assert (reload(connector).name == "Renamed") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_delete_connector(role, expected, clients, users):
    connector = make_connector(users.owner)

    response = clients[role].post(f"{API}/delete/{connector.uuid}")

    assert_outcome(response, expected)
    assert (reload(connector) is None) is (expected is OK)


# ── Talking to the remote ─────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_test_connection(role, expected, clients, users, remote):
    connector = make_connector(users.owner)

    response = clients[role].post(f"{API}/test/{connector.uuid}")

    assert_outcome(response, expected)
    assert bool(remote.calls) is (expected is OK)
    assert reload(connector).is_verified is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_preview_a_pull(role, expected, clients, users, remote):
    connector = make_connector(users.owner)

    response = clients[role].get(f"{API}/preview/{connector.uuid}?cve=CVE-2024-1234")

    assert_outcome(response, expected)
    assert bool(remote.calls) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_trigger_a_pull(role, expected, clients, users, remote):
    connector = make_connector(users.owner)

    response = clients[role].post(f"{API}/pull/{connector.uuid}", json={})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="connector_pull") == (1 if expected is OK else 0)
    assert remote.calls == []


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_import_tag_families(role, expected, clients):
    response = clients[role].post(f"{API}/import_tag_families", json={"families": ["PAP"]})

    assert_outcome(response, expected)
    assert (count(Tag, name="PAP:RED") == 1) is (expected is OK)
