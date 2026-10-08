"""Connectors — layer 4: inputs meant to break Rulezet.

Two sources of bad input: an admin's client posting broken bodies to the
/connector routes, and — far less trusted — a remote instance answering
anything at all (garbage, wrong types, errors, timeouts). Expected every
time: a clean answer (< 500) or a pull that ends instead of crashing, with
nothing half-written — the valid remote rules still arrive, the broken ones
are skipped, and the connector records the error.
"""
import json
import uuid

import pytest
import requests

from app.core.db_class.db import Bundle, Connector, Rule, RuleUpdateHistory, Tag
from tests_new.helpers.connectors import (  # noqa: F401
    API, REMOTE_URL, connector_form, make_connector, no_network, pull_jobs, remote, remote_bundle, remote_rule,
    run_pull,
)
from tests_new.helpers.db import count, reload
from tests_new.helpers.inputs import BLANK, EMPTY, INJECTIONS, ODD_CHARACTERS, TOO_LONG

NOT_AN_OBJECT = ["[]", '"text"', "12", "null", "{broken json"]
NOT_A_TEXT = [12345, ["a", "b"], {"nested": {"x": 1}}]
NOT_A_FLAG = ["false", 1, None]
BAD_URLS = ["file:///etc/passwd", "javascript:alert(1)", "ftp://remote.rulezet.test", "gopher://remote:70",
            "remote.rulezet.test", "//remote.rulezet.test", "http://", "https://:443", "http://[::1"]
HOSTILE_TEXT = [*INJECTIONS, *[c for c in ODD_CHARACTERS if "\x00" not in c]]
BAD_PATH_IDS = ["0", "-1", str(2**63), "1; DROP TABLE rule", "x" * 5000, "%00", "日本語"]
REMOTE_ERRORS = [requests.exceptions.Timeout("timed out"), requests.exceptions.ConnectionError("refused"),
                 requests.exceptions.SSLError("bad certificate"), ValueError("anything else")]


def _post_raw(client, url, body):
    return client.post(url, data=body, content_type="application/json")


# ── Create / update: bodies ───────────────────────────────────────────────────

@pytest.mark.parametrize("body", NOT_AN_OBJECT)
def test_create_connector_with_a_body_that_is_not_an_object_stores_nothing(body, clients):
    response = _post_raw(clients["admin"], f"{API}/create", body)

    assert response.status_code == 400
    assert count(Connector) == 0


@pytest.mark.parametrize("body", NOT_AN_OBJECT)
def test_update_connector_with_a_body_that_is_not_an_object_changes_nothing(body, clients, users):
    connector = make_connector(users.admin)

    response = _post_raw(clients["admin"], f"{API}/update/{connector.uuid}", body)

    assert response.status_code < 500
    assert reload(connector).name == connector.name


@pytest.mark.parametrize("field", ["name", "instance_url", "description", "api_key_outbound", "icon"])
@pytest.mark.parametrize("value", NOT_A_TEXT)
def test_create_connector_with_a_non_text_field_stores_nothing(field, value, clients):
    response = clients["admin"].post(f"{API}/create", json=connector_form(**{field: value}))

    assert response.status_code == 400
    assert count(Connector) == 0


@pytest.mark.parametrize("field", ["name", "instance_url", "description", "api_key_outbound", "icon"])
@pytest.mark.parametrize("value", NOT_A_TEXT)
def test_update_connector_with_a_non_text_field_changes_nothing(field, value, clients, users):
    connector = make_connector(users.admin)
    before = connector.to_json()

    response = clients["admin"].post(f"{API}/update/{connector.uuid}", json={field: value})

    assert response.status_code == 400
    assert reload(connector).to_json() == before


@pytest.mark.parametrize("field", ["sync_rules", "sync_bundles"])
@pytest.mark.parametrize("value", NOT_A_FLAG)
def test_create_connector_with_a_flag_that_is_not_a_boolean_stores_nothing(field, value, clients):
    response = clients["admin"].post(f"{API}/create", json=connector_form(**{field: value}))

    assert response.status_code == 400
    assert count(Connector) == 0


@pytest.mark.parametrize("field", ["sync_rules", "sync_bundles", "is_active"])
@pytest.mark.parametrize("value", NOT_A_FLAG)
def test_update_connector_with_a_flag_that_is_not_a_boolean_changes_nothing(field, value, clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/update/{connector.uuid}", json={field: value})

    assert response.status_code == 400
    assert getattr(reload(connector), field) is getattr(connector, field)


@pytest.mark.parametrize("field, value", [("owner_mode", "root"), ("owner_mode", ""), ("owner_mode", 1),
                                          ("connector_type", "misp"), ("connector_type", "x" * 100)])
def test_create_connector_with_an_unknown_mode_or_type_stores_nothing(field, value, clients):
    response = clients["admin"].post(f"{API}/create", json=connector_form(**{field: value}))

    assert response.status_code == 400
    assert count(Connector) == 0


@pytest.mark.parametrize("value", ["root", "", None, 1])
def test_update_connector_with_an_unknown_owner_mode_changes_nothing(value, clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/update/{connector.uuid}", json={"owner_mode": value})

    assert response.status_code == 400
    assert reload(connector).owner_mode == "shadow"


# ── Create / update: text values ──────────────────────────────────────────────

@pytest.mark.parametrize("name", [EMPTY, BLANK])
def test_create_connector_with_an_empty_name_stores_nothing(name, clients):
    response = clients["admin"].post(f"{API}/create", json=connector_form(name=name))

    assert response.status_code == 400
    assert count(Connector) == 0


@pytest.mark.parametrize("field", ["name", "instance_url"])
@pytest.mark.parametrize("value", [EMPTY, BLANK, None])
def test_update_connector_can_never_empty_its_name_or_url(field, value, clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/update/{connector.uuid}", json={field: value})

    assert response.status_code == 400
    assert getattr(reload(connector), field) == getattr(connector, field)


@pytest.mark.parametrize("field, limit", [("name", 255), ("instance_url", 512), ("api_key_outbound", 512),
                                          ("icon", 64)])
def test_create_connector_with_a_too_long_value_stores_nothing(field, limit, clients):
    value = f"{REMOTE_URL}/{'a' * limit}" if field == "instance_url" else "a" * (limit + 1)

    response = clients["admin"].post(f"{API}/create", json=connector_form(**{field: value}))

    assert response.status_code == 400
    assert count(Connector) == 0


def test_update_connector_with_a_too_long_name_changes_nothing(clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/update/{connector.uuid}", json={"name": TOO_LONG})

    assert response.status_code == 400
    assert reload(connector).name == connector.name


def test_create_connector_with_a_huge_description_never_errors(clients):
    response = clients["admin"].post(f"{API}/create", json=connector_form(description=TOO_LONG))

    assert response.status_code < 500


@pytest.mark.parametrize("text", HOSTILE_TEXT)
def test_create_connector_stores_hostile_text_verbatim(text, clients):
    response = clients["admin"].post(f"{API}/create", json=connector_form(name=text, description=text))

    connector = Connector.query.one()
    assert response.status_code == 200
    assert connector.name == text.strip() and connector.description == text.strip()
    assert response.get_json()["connector"]["name"] == text.strip()


def test_create_connector_never_stores_a_null_byte(clients):
    """PostgreSQL refuses NUL characters in text — storing one would be a 500 in production."""
    response = clients["admin"].post(f"{API}/create", json=connector_form(name="null\x00byte",
                                                                           description="a\x00b"))

    connector = Connector.query.one()
    assert response.status_code == 200
    assert "\x00" not in connector.name and "\x00" not in connector.description


# ── Create / update: remote URL ───────────────────────────────────────────────

@pytest.mark.parametrize("url", BAD_URLS)
def test_create_connector_with_a_url_that_is_not_http_stores_nothing(url, clients, remote):
    response = clients["admin"].post(f"{API}/create", json=connector_form(instance_url=url))

    assert response.status_code == 400
    assert count(Connector) == 0 and remote.calls == []


@pytest.mark.parametrize("url", BAD_URLS)
def test_update_connector_with_a_url_that_is_not_http_changes_nothing(url, clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/update/{connector.uuid}", json={"instance_url": url})

    assert response.status_code == 400
    assert reload(connector).instance_url == REMOTE_URL


@pytest.mark.parametrize("url", ["http://localhost:7009", "http://127.0.0.1", "http://10.0.0.5",
                                 "http://192.168.1.10:8080", "http://[::1]:7009", "http://169.254.169.254"])
def test_create_connector_to_a_private_network_address_is_accepted(url, clients):
    """Current behaviour (product question in the report): connectors are
    admin-only and an instance on the local network is a legitimate remote,
    so loopback / private / link-local addresses are not refused."""
    response = clients["admin"].post(f"{API}/create", json=connector_form(instance_url=url))

    assert response.status_code == 200


# ── Unknown or odd connector ids in the path ──────────────────────────────────

@pytest.mark.parametrize("bad_uuid", BAD_PATH_IDS)
@pytest.mark.parametrize("method, action", [("post", "update"), ("post", "delete"), ("post", "test"),
                                            ("get", "history"), ("get", "preview"), ("post", "pull")])
def test_actions_on_an_unknown_connector_are_not_found(bad_uuid, method, action, clients, users, remote):
    make_connector(users.admin)

    response = getattr(clients["admin"], method)(f"{API}/{action}/{bad_uuid}?cve=CVE-2024-1",
                                                 json={"name": "x"})

    assert response.status_code == 404
    assert count(Connector) == 1 and remote.calls == [] and pull_jobs() == []


# ── Pull trigger ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", NOT_AN_OBJECT)
def test_pull_with_a_body_that_is_not_an_object_never_errors(body, clients, users):
    connector = make_connector(users.admin)

    response = _post_raw(clients["admin"], f"{API}/pull/{connector.uuid}", body)

    assert response.status_code < 500


@pytest.mark.parametrize("field", ["sync_rules", "sync_bundles"])
@pytest.mark.parametrize("value", NOT_A_FLAG[:2] + [{"a": 1}])
def test_pull_with_a_flag_that_is_not_a_boolean_queues_nothing(field, value, clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/pull/{connector.uuid}", json={field: value})

    assert response.status_code == 400
    assert pull_jobs() == []


@pytest.mark.parametrize("filters", [
    "yara", ["yara"], 12,
    {"formats": "yara"}, {"formats": [1, 2]}, {"authors": {"a": 1}}, {"attacks": "T1059"},
    {"cves": "CVE-2024-1"}, {"cves": ["CVE-2024-1"]}, {"cves": [{"names": "CVE-2024-1"}]},
    {"tags": [{"names": [1]}]}, {"licenses": [None]},
    {"date_from": 20250101}, {"date_to": ["2025"]},
])
def test_pull_with_malformed_filters_queues_nothing(filters, clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/pull/{connector.uuid}", json={"filters": filters})

    assert response.status_code == 400
    assert pull_jobs() == []


def test_pull_filter_values_reach_the_remote_intact(app, users, remote):
    """A value holding "&" or "#" must not turn into another remote parameter."""
    connector = make_connector(users.admin)

    run_pull(app, connector, users.admin, filters={"formats": ["yara&uuids=x"], "authors": ["a#b"]})

    url = remote.urls("rules?since")[0]
    assert "&uuids=" not in url and "#" not in url


# ── Tag families ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("families", [[1, 2], [None], [["tlp"]], [{"a": 1}], "tlp", {"tlp": True}, None, []])
def test_import_tag_families_with_malformed_families_is_refused(families, clients):
    response = clients["admin"].post(f"{API}/import_tag_families", json={"families": families})

    assert response.status_code == 400


@pytest.mark.parametrize("family", ["../../../etc/passwd", "misp-galaxy:../../x", "x" * 5000, BLANK,
                                    *INJECTIONS])
def test_import_tag_families_with_an_odd_name_imports_nothing(family, clients):
    tags_before = count(Tag)

    response = clients["admin"].post(f"{API}/import_tag_families", json={"families": [family]})

    assert response.status_code < 500
    assert count(Tag) == tags_before


@pytest.mark.parametrize("body", NOT_AN_OBJECT)
def test_import_tag_families_with_a_body_that_is_not_an_object_is_refused(body, clients):
    response = _post_raw(clients["admin"], f"{API}/import_tag_families", body)

    assert response.status_code == 400


# ── Connection test and preview: a broken remote ──────────────────────────────

@pytest.mark.parametrize("answer", [
    dict(text="<html>not json</html>"), dict(json=[]), dict(json="text"), dict(json=None),
    dict(json={"instance": "not an object"}), dict(json={"instance": None}),
])
def test_connection_test_against_a_remote_answering_garbage_never_errors(answer, clients, users, remote):
    remote.answer("manifest", **answer)
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/test/{connector.uuid}")

    assert response.status_code < 500


@pytest.mark.parametrize("error", REMOTE_ERRORS)
def test_connection_test_against_an_unreachable_remote_records_the_error(error, clients, users, remote):
    remote.answer("manifest", raises=error)
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/test/{connector.uuid}")

    assert response.status_code == 200 and response.get_json()["success"] is False
    connector = reload(connector)
    assert connector.is_verified is False and connector.last_error


@pytest.mark.parametrize("stats", [{"rules": "many", "bundles": "few"}, {"rules": [], "bundles": {}},
                                   {"rules": -1, "bundles": 2**70}, {"rules": True, "bundles": 1.5}, ["x"]])
def test_connection_test_never_stores_wrong_typed_remote_counts(stats, clients, users, remote):
    remote.answer("stats", json=stats)
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/test/{connector.uuid}")

    connector = reload(connector)
    assert response.status_code == 200
    assert connector.remote_rules_count is None and connector.remote_bundles_count is None


@pytest.mark.parametrize("answer", [dict(text="garbage"), dict(json=[]), dict(json="text"), dict(json=None)])
def test_preview_against_a_remote_answering_garbage_is_a_bad_gateway(answer, clients, users, remote):
    remote.answer("count", **answer)
    connector = make_connector(users.admin)

    response = clients["admin"].get(f"{API}/preview/{connector.uuid}?cve=CVE-2024-1234")

    assert response.status_code == 502


@pytest.mark.parametrize("error", REMOTE_ERRORS)
def test_preview_against_an_unreachable_remote_is_a_bad_gateway(error, clients, users, remote):
    remote.answer("count", raises=error)
    connector = make_connector(users.admin)

    response = clients["admin"].get(f"{API}/preview/{connector.uuid}?cve=CVE-2024-1234")

    assert response.status_code == 502


def test_preview_sends_the_cve_to_the_remote_intact(clients, users, remote):
    connector = make_connector(users.admin)

    clients["admin"].get(f"{API}/preview/{connector.uuid}", query_string={"cve": "CVE-1&uuids=x#y"})

    url = remote.urls("rules")[0]
    assert "&uuids=" not in url and "#" not in url


# ── Pull: a remote answering garbage ──────────────────────────────────────────

def _pull_against_broken_rules_page(app, users, remote, **answer):
    remote.rules = [remote_rule()]
    remote.answer("rules", **answer)
    connector = make_connector(users.admin)
    job = run_pull(app, connector, users.admin)
    return job, reload(connector)


@pytest.mark.parametrize("answer", [
    dict(text="<html>502 Bad Gateway</html>"), dict(json=[]), dict(json="rules"), dict(json=12), dict(json=None),
    dict(json={"rules": "not a list"}), dict(json={"rules": {"uuid": "x"}}), dict(json={"rules": 12}),
])
def test_pull_from_a_remote_answering_garbage_records_the_error(answer, app, users, remote):
    job, connector = _pull_against_broken_rules_page(app, users, remote, **answer)

    assert job.status in ("done", "failed")
    assert connector.last_error
    assert count(Rule) == 0 and count(Tag) == 2


@pytest.mark.parametrize("status", [401, 403, 404, 500, 503])
def test_pull_from_a_remote_answering_an_error_records_it(status, app, users, remote):
    job, connector = _pull_against_broken_rules_page(app, users, remote, status=status, json={})

    assert str(status) in connector.last_error
    assert connector.last_sync_at is None and count(Rule) == 0


@pytest.mark.parametrize("error", REMOTE_ERRORS)
def test_pull_from_an_unreachable_remote_records_the_error(error, app, users, remote):
    job, connector = _pull_against_broken_rules_page(app, users, remote, raises=error)

    assert job.status in ("done", "failed")
    assert connector.last_error and connector.last_sync_at is None and count(Rule) == 0


@pytest.mark.parametrize("error", REMOTE_ERRORS)
def test_pull_with_an_unreachable_manifest_still_ends(error, app, users, remote):
    remote.rules = [remote_rule()]
    remote.answer("manifest", raises=error)
    connector = make_connector(users.admin)

    job = run_pull(app, connector, users.admin)

    assert job.status in ("done", "failed")


@pytest.mark.parametrize("manifest", [[], "text", {"instance": "x", "capabilities": "y"},
                                      {"sync_api_version": "two", "capabilities": ["sync_rules"]}])
def test_pull_with_a_garbage_manifest_still_ends(manifest, app, users, remote):
    remote.rules = [remote_rule()]
    remote.manifest = manifest
    connector = make_connector(users.admin)

    job = run_pull(app, connector, users.admin)

    assert job.status in ("done", "failed")


@pytest.mark.parametrize("total", ["lots", [], {"n": 1}, -5, None, 1.5])
def test_pull_with_a_wrong_typed_remote_count_still_imports(total, app, users, remote):
    remote.rules = [remote_rule()]
    remote.answer("count", json={"count": total})
    connector = make_connector(users.admin)

    job = run_pull(app, connector, users.admin)

    assert job.status == "done" and count(Rule) == 1


def test_pull_from_a_remote_repeating_the_same_page_stops(app, users, remote):
    """A remote ignoring `page` would otherwise be read 10 000 times."""
    item = remote_rule()
    remote.answer("rules", json={"page": 1, "total": 10**9, "has_more": True, "rules": [item]})
    connector = make_connector(users.admin)

    job = run_pull(app, connector, users.admin)

    assert job.status == "done" and count(Rule) == 1
    assert len(remote.urls("rules?since")) < 20


# ── Pull: broken rules among valid ones ───────────────────────────────────────

BROKEN_RULES = [
    None, "a rule", 12, [], ["uuid"],
    {"title": "no uuid"},
    {"uuid": None}, {"uuid": 12}, {"uuid": ["x"]}, {"uuid": ""}, {"uuid": "not-a-uuid"},
    {"uuid": "x" * 37}, {"uuid": "../../../etc/passwd"}, {"uuid": str(uuid.uuid4()) + "\x00"},
]
BROKEN_FIELDS = [
    ("title", 12), ("title", ["a"]), ("title", {"a": 1}),
    ("to_string", None), ("to_string", ["rule"]), ("to_string", {"x": 1}),
    ("format", ["yara"]), ("format", {"f": 1}), ("author", ["me"]), ("license", {"l": 1}),
    ("description", ["d"]), ("source", 1.5),
]


def _pull_items(app, users, remote, items):
    remote.rules = items
    connector = make_connector(users.admin)
    job = run_pull(app, connector, users.admin)
    return job


@pytest.mark.parametrize("broken", BROKEN_RULES)
def test_pull_skips_a_broken_remote_rule_and_keeps_the_valid_ones(broken, app, users, remote):
    valid = remote_rule()

    job = _pull_items(app, users, remote, [broken, valid])

    assert job.status == "done"
    assert [r.uuid for r in Rule.query.all()] == [valid["uuid"]]


@pytest.mark.parametrize("field, value", BROKEN_FIELDS)
def test_pull_skips_a_remote_rule_with_a_wrong_typed_field(field, value, app, users, remote):
    valid, broken = remote_rule(), remote_rule(**{field: value})

    job = _pull_items(app, users, remote, [broken, valid])

    assert job.status == "done"
    assert [r.uuid for r in Rule.query.all()] == [valid["uuid"]]


@pytest.mark.parametrize("field, value", BROKEN_FIELDS)
def test_pull_never_half_updates_a_local_rule_from_a_broken_remote_copy(field, value, app, users, remote):
    item = remote_rule()
    remote.rules = [item]
    connector = make_connector(users.admin)
    run_pull(app, connector, users.admin)
    local = Rule.query.one()
    before = (local.title, local.to_string, local.format, local.author, local.license, local.description)
    changed = dict(item, to_string=item["to_string"] + "\n// v2")
    changed[field] = value
    remote.rules = [changed]

    job = run_pull(app, connector, users.admin)

    local = reload(local)
    assert job.status == "done"
    assert (local.title, local.to_string, local.format, local.author, local.license, local.description) == before


@pytest.mark.parametrize("field, value", [
    ("tags", "tlp:clear"), ("tags", {"tlp:clear": 1}), ("tags", [1, None, ["x"], {"a": 1}]),
    ("cve_ids", "CVE-2024-1234"), ("cve_ids", [1, {"a": 1}]), ("attack_ids", "T1059"), ("attack_ids", [1, None]),
    ("update_history", "history"), ("update_history", [1, "x", None]),
    ("update_history", [{"analyzed_at": 12, "message": ["m"], "old_content": {"x": 1}, "success": "yes"}]),
    ("version", ["1"]), ("version", 2),
])
def test_pull_ignores_wrong_typed_extras_of_a_remote_rule(field, value, app, users, remote):
    """Tags, CVEs, techniques and history that aren't lists of the right
    thing are dropped — never spelled out letter by letter as tags."""
    item = remote_rule(**{field: value})

    job = _pull_items(app, users, remote, [item])

    rule = Rule.query.one()
    assert job.status == "done" and rule.uuid == item["uuid"]
    assert count(Tag) == 2
    assert all(len(t) > 1 for t in json.loads(rule.cve_id or "[]"))
    assert all(isinstance(h.message, (str, type(None))) for h in RuleUpdateHistory.query.all())


@pytest.mark.parametrize("text", [TOO_LONG, *HOSTILE_TEXT])
def test_pull_stores_hostile_remote_text_verbatim(text, app, users, remote):
    item = remote_rule(title=text, description=text, author=text)

    _pull_items(app, users, remote, [item])

    rule = Rule.query.one()
    assert (rule.title, rule.description, rule.author) == (text, text, text)


def test_pull_never_stores_a_null_byte_from_the_remote(app, users, remote):
    """PostgreSQL refuses NUL characters — one would fail the whole page in production."""
    item = remote_rule(title="null\x00byte", description="a\x00b", tags=["evil\x00tag"])

    _pull_items(app, users, remote, [item])

    rule = Rule.query.one()
    assert "\x00" not in rule.title and "\x00" not in rule.description
    assert all("\x00" not in t.name for t in Tag.query.all())


def test_pull_with_a_duplicated_uuid_in_one_page_creates_one_rule(app, users, remote):
    item = remote_rule()

    job = _pull_items(app, users, remote, [item, dict(item, title="Same uuid, other title")])

    assert job.status == "done" and count(Rule) == 1


# ── Pull: broken bundles ──────────────────────────────────────────────────────

@pytest.mark.parametrize("broken", [
    None, "bundle", 12, [], {"name": "no uuid"}, {"uuid": 12, "name": "x"}, {"uuid": "x" * 300, "name": "x"},
    {"uuid": str(uuid.uuid4()), "name": None}, {"uuid": str(uuid.uuid4()), "name": ["x"]},
    {"uuid": str(uuid.uuid4()), "name": "x" * 300}, {"uuid": str(uuid.uuid4()), "name": "x", "rules": "abc"},
    {"uuid": str(uuid.uuid4()), "name": "x", "tags": "tlp:clear"},
    {"uuid": str(uuid.uuid4()), "name": "x", "structure": "tree"},
    {"uuid": str(uuid.uuid4()), "name": "x", "updated_at": ["2026"]},
])
def test_pull_skips_a_broken_remote_bundle_and_keeps_the_valid_ones(broken, app, users, remote):
    valid = remote_bundle()
    remote.bundles = [broken, valid]
    connector = make_connector(users.admin, sync_rules=False, sync_bundles=True)

    job = run_pull(app, connector, users.admin)

    assert job.status == "done"
    assert valid["uuid"] in {b.remote_bundle_uuid for b in Bundle.query.all()}
    assert count(Tag) == 2


@pytest.mark.parametrize("answer", [dict(text="garbage"), dict(json=[]), dict(json={"bundles": "x"}),
                                    dict(status=500, json={})])
def test_pull_from_a_remote_answering_garbage_bundles_still_ends(answer, app, users, remote):
    remote.answer("bundles", **answer)
    connector = make_connector(users.admin, sync_rules=False, sync_bundles=True)

    job = run_pull(app, connector, users.admin)

    assert job.status in ("done", "failed") and count(Bundle) == 0


# ── Sync API: odd parameters ──────────────────────────────────────────────────

ODD_SYNC_PARAMS = [
    "page=abc", "page=-1", "page=0", f"page={2**63}", f"page={10**30}", "per_page=abc", f"per_page={10**30}",
    "since=garbage", "since=", "since=9999-99-99", "since=2025-01-01T00:00:00%2B05:00",
    "date_from=garbage", "date_to=garbage", "date_from=2025-13-45", "date_from=2025-01-01T00:00:00Z",
    "tags=tlp:clear&tag_mode=XOR", "tags=tlp:clear&tag_exclude=maybe", "formats=,,,", "author=%25", "cve=%25%25",
    "attacks=,", "uuids=,,,", "uuids=" + ",".join(str(uuid.uuid4()) for _ in range(500)), "count_only=maybe",
    *[f"author={i}" for i in INJECTIONS], "formats=" + "a" * 5_000,
]


@pytest.mark.parametrize("query", ODD_SYNC_PARAMS)
def test_sync_rules_with_odd_parameters_never_errors(query, app, users):
    from tests_new.helpers.rules import make_rule
    make_rule(users.owner)

    response = app.test_client().get(f"/api/sync/rules?{query}")

    assert response.status_code < 500


@pytest.mark.parametrize("query", ["page=abc", f"page={2**63}", f"page={10**30}", f"per_page={10**30}",
                                   "since=garbage", "per_page=-3"])
def test_sync_bundles_with_odd_parameters_never_errors(query, app, users):
    from tests_new.helpers.comments import make_bundle
    make_bundle(users.owner)

    response = app.test_client().get(f"/api/sync/bundles?{query}")

    assert response.status_code < 500


@pytest.mark.parametrize("header, value", [("X-Rulezet-Instance-UUID", "x" * 10_000),
                                           ("X-Rulezet-Instance-URL", "y" * 10_000),
                                           ("X-Forwarded-For", "z" * 10_000)])
def test_sync_rules_with_odd_puller_headers_never_errors(header, value, app, users):
    response = app.test_client().get("/api/sync/rules", headers={header: value})

    assert response.status_code == 200
