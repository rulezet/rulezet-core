"""MISP — layer 4: inputs meant to break Rulezet.

Expected every time: a clean answer (< 500), nothing half-written (no server
row, no queued job), and hostile rule content exported as plain data. A
remote (MISP instance, STIX converter) answering garbage never crashes a
route or a job.
"""
import json

import pytest

from app import db
from app.core.db_class.db import MispServer
from tests_new.helpers.attack import trash
from tests_new.helpers.comments import make_bundle
from tests_new.helpers.db import count, reload
from tests_new.helpers.inputs import BAD_IDS, BLANK, EMPTY, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests_new.helpers.misp import (
    API_KEY, add_to_bundle, fake_remote, fake_stix, make_server, new_server_payload, objects_named, push_jobs,
    run_job, values,
)
from tests_new.helpers.rules import make_rule

BROKEN_BODIES = ["not json", "[1, 2]", '"a string"', "42", "null", "{"]
UNKNOWN_UUIDS = ["00000000-0000-0000-0000-000000000000", "abc", "' OR 1=1 --", "A" * 500]


@pytest.fixture
def remote(monkeypatch):
    return fake_remote(monkeypatch)


# ── Adding a server ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", BROKEN_BODIES)
def test_add_server_with_a_broken_body_stores_nothing(body, clients):
    response = clients["admin"].post("/misp/create", data=body, content_type="application/json")

    assert 400 <= response.status_code < 500
    assert count(MispServer) == 0


@pytest.mark.parametrize("field", ["name", "url", "api_key"])
@pytest.mark.parametrize("value", [EMPTY, BLANK, None])
def test_add_server_without_a_required_field_stores_nothing(field, value, clients):
    response = clients["admin"].post("/misp/create", json=new_server_payload(**{field: value}))

    assert response.status_code == 400
    assert count(MispServer) == 0


@pytest.mark.parametrize("field", ["name", "url", "api_key", "description", "verify_tls"])
@pytest.mark.parametrize("value", [12345, ["a", "b"], {"nested": {"x": 1}}], ids=["int", "list", "dict"])
def test_add_server_with_a_wrongly_typed_field_stores_nothing(field, value, clients):
    response = clients["admin"].post("/misp/create", json=new_server_payload(**{field: value}))

    assert response.status_code == 400
    assert count(MispServer) == 0


@pytest.mark.parametrize("field", ["name", "url"])
def test_add_server_with_a_too_long_field_stores_nothing(field, clients):
    response = clients["admin"].post("/misp/create", json=new_server_payload(**{field: TOO_LONG}))

    assert response.status_code == 400
    assert count(MispServer) == 0


@pytest.mark.parametrize("url", ["misp.example.org", "javascript:alert(1)", "file:///etc/passwd",
                                 "ftp://misp.example.org", "../../../../etc/passwd", "https://"])
def test_add_server_with_a_non_http_url_stores_nothing(url, clients):
    response = clients["admin"].post("/misp/create", json=new_server_payload(url=url))

    assert response.status_code == 400
    assert count(MispServer) == 0


@pytest.mark.parametrize("name", INJECTIONS + ODD_CHARACTERS[1:])
def test_add_server_with_a_hostile_name_stores_it_as_text(name, clients):
    response = clients["admin"].post("/misp/create", json=new_server_payload(name=name))

    assert response.status_code == 200
    assert MispServer.query.one().name == name.strip()


def test_add_server_with_a_nul_byte_stores_nothing(clients):
    response = clients["admin"].post("/misp/create", json=new_server_payload(name="null\x00byte"))

    assert response.status_code == 400
    assert count(MispServer) == 0


def test_add_server_cannot_set_its_own_status(clients, users):
    clients["admin"].post("/misp/create", json=new_server_payload(is_verified=True, pushes_count=99,
                                                                  added_by_id=users.user.id, uuid="chosen"))

    server = MispServer.query.one()
    assert server.is_verified is False and server.pushes_count == 0
    assert server.added_by_id == users.admin.id and server.uuid != "chosen"


# ── Editing a server ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", BROKEN_BODIES)
def test_edit_server_with_a_broken_body_changes_nothing(body, clients, users):
    server = make_server(users.admin, name="Before")

    response = clients["admin"].post(f"/misp/update/{server.uuid}", data=body, content_type="application/json")

    assert response.status_code < 500
    assert reload(server).name == "Before"


@pytest.mark.parametrize("field", ["name", "url", "api_key", "description", "verify_tls"])
@pytest.mark.parametrize("value", [12345, ["a", "b"], {"nested": {"x": 1}}], ids=["int", "list", "dict"])
def test_edit_server_with_a_wrongly_typed_field_changes_nothing(field, value, clients, users):
    server = make_server(users.admin, name="Before")

    response = clients["admin"].post(f"/misp/update/{server.uuid}", json={"name": "After", field: value})

    assert response.status_code == 400
    assert reload(server).name == "Before"
    assert reload(server).url.startswith("https://") and reload(server).verify_tls is True


@pytest.mark.parametrize("field, value", [("name", TOO_LONG), ("url", TOO_LONG), ("url", "javascript:alert(1)"),
                                          ("name", "null\x00byte")])
def test_edit_server_with_a_bad_value_changes_nothing(field, value, clients, users):
    server = make_server(users.admin)
    before = getattr(server, field)

    response = clients["admin"].post(f"/misp/update/{server.uuid}", json={field: value})

    assert response.status_code == 400
    assert getattr(reload(server), field) == before


def test_edit_server_cannot_change_its_counters(clients, users):
    server = make_server(users.admin)

    clients["admin"].post(f"/misp/update/{server.uuid}", json={"pushes_count": 99, "is_verified": True,
                                                               "added_by_id": users.user.id})

    assert reload(server).pushes_count == 0 and reload(server).is_verified is False
    assert reload(server).added_by_id == users.admin.id


# ── Unknown servers ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("server_uuid", UNKNOWN_UUIDS)
@pytest.mark.parametrize("method, path", [("get", "history"), ("post", "update"), ("post", "delete"),
                                          ("post", "toggle_active"), ("post", "test")])
def test_unknown_server_is_not_found(method, path, server_uuid, clients, users, remote):
    server = make_server(users.admin)

    response = getattr(clients["admin"], method)(f"/misp/{path}/{server_uuid}", json={"name": "x"})

    assert response.status_code == 404
    assert reload(server).name != "x" and reload(server).is_active is True
    assert remote.connections == []


# ── Push ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", BROKEN_BODIES)
def test_push_with_a_broken_body_queues_nothing(body, clients):
    response = clients["admin"].post("/misp/push", data=body, content_type="application/json")

    assert 400 <= response.status_code < 500
    assert push_jobs() == []


@pytest.mark.parametrize("field", ["rule_id", "bundle_id"])
@pytest.mark.parametrize("bad_id", BAD_IDS + [True, 1.5, [1], {"id": 1}, 999_999])
def test_push_with_a_bad_id_queues_nothing(field, bad_id, clients, users):
    server = make_server(users.admin)
    make_rule(users.owner)
    make_bundle(users.owner)

    response = clients["admin"].post("/misp/push", json={field: bad_id, "server_uuid": server.uuid,
                                                         "push_type": "event"})

    assert 400 <= response.status_code < 500
    assert push_jobs() == []


@pytest.mark.parametrize("server_uuid", WRONG_TYPES + UNKNOWN_UUIDS)
def test_push_to_a_bad_server_queues_nothing(server_uuid, clients, users):
    rule = make_rule(users.owner)

    response = clients["admin"].post("/misp/push", json={"rule_id": rule.id, "server_uuid": server_uuid})

    assert 400 <= response.status_code < 500
    assert push_jobs() == []


@pytest.mark.parametrize("push_type", ["", "both", "<script>", 1, ["event"], {"a": 1}])
def test_push_with_a_bad_push_type_queues_nothing(push_type, clients, users):
    server, rule = make_server(users.admin), make_rule(users.owner)

    response = clients["admin"].post("/misp/push", json={"rule_id": rule.id, "server_uuid": server.uuid,
                                                         "push_type": push_type})

    assert response.status_code == 400
    assert push_jobs() == []


@pytest.mark.parametrize("answer", ["garbage", None, 42, ["a"], {"unexpected": "shape"},
                                    RuntimeError("remote exploded"), TimeoutError("timed out")],
                         ids=["string", "none", "int", "list", "dict", "error", "timeout"])
def test_push_job_with_a_remote_answering_garbage_fails_cleanly(answer, clients, users, remote):
    remote.add_event_result = answer
    server, rule = make_server(users.admin), make_rule(users.owner)
    clients["admin"].post("/misp/push", json={"rule_id": rule.id, "server_uuid": server.uuid})

    job = run_job(push_jobs()[0])

    assert job.status == "failed" and job.error
    assert reload(server).pushes_count == 0 and reload(server).last_push_at is None


def test_push_job_with_a_payload_naming_nothing_fails_cleanly(users, remote):
    from app.features.jobs.jobs_core import create_job
    server = make_server(users.admin)
    job = create_job("misp_push", {"server_id": server.id, "rule_id": "abc"}, "push", users.admin.id)

    job = run_job(job)

    assert job.status == "failed" and remote.pushed == []


# ── Connection test with a remote answering garbage ───────────────────────────

@pytest.mark.parametrize("version", ["garbage", None, 42, [], {}, {"version": None},
                                     ValueError("not json"), OSError("no route to host")],
                         ids=["string", "none", "int", "list", "empty", "null-version", "bad-json", "network"])
def test_connection_test_with_a_remote_answering_garbage_is_not_verified(version, clients, users, remote):
    remote.version = version
    server = make_server(users.admin)

    response = clients["admin"].post(f"/misp/test/{server.uuid}")

    assert response.status_code == 200 and response.get_json()["success"] is False
    assert reload(server).is_verified is False and reload(server).last_error


def test_connection_test_with_an_undecryptable_key_fails_cleanly(clients, users, remote):
    server = make_server(users.admin)
    server.api_key_encrypted = "not-a-fernet-token"
    db.session.commit()

    response = clients["admin"].post(f"/misp/test/{server.uuid}")

    assert response.status_code == 200 and response.get_json()["success"] is False
    assert remote.connections == []


# ── Exports with hostile rule data ────────────────────────────────────────────

def _event(client, rule):
    response = client.get(f"/rule/download_rule?rule_id={rule.id}&format=misp_event")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True, body
    return json.loads(body["content"])


@pytest.mark.parametrize("text", INJECTIONS + ODD_CHARACTERS + [TOO_LONG])
def test_hostile_title_is_exported_as_plain_text(text, clients, users):
    rule = make_rule(users.owner, title=text)

    event = _event(clients["anonymous"], rule)

    assert values(objects_named(event, "rulezet-metadata")[0], "title") == [text]


@pytest.mark.parametrize("text", INJECTIONS + ODD_CHARACTERS + [TOO_LONG])
def test_hostile_content_is_exported_as_plain_text(text, clients, users):
    rule = make_rule(users.owner, to_string=text)

    event = _event(clients["anonymous"], rule)

    assert values(objects_named(event, "yara")[0], "yara") == [text]


@pytest.mark.parametrize("fmt", ["not-a-format", "", "<script>", "../../etc", "zeek", "sagan", None])
def test_rule_of_an_unmapped_format_exports_without_error(fmt, clients, users):
    rule = make_rule(users.owner, format=fmt)

    for export in ("misp", "misp_event"):
        response = clients["anonymous"].get(f"/rule/download_rule?rule_id={rule.id}&format={export}")
        assert response.status_code == 200


@pytest.mark.parametrize("cve_id", ["CVE-2021-44228", '"CVE-2021-44228"', "[1, 2]", "{}", "[", '[null]',
                                    '{"a": "b"}', "  "])
def test_rule_with_malformed_cves_exports_without_error(cve_id, clients, users):
    rule = make_rule(users.owner, cve_id=cve_id)

    event = _event(clients["anonymous"], rule)
    page = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}")

    assert objects_named(event, "rulezet-metadata")
    assert page.status_code == 200


@pytest.mark.parametrize("cve_id", ['"CVE-2021-44228"', "[1, 2]", "{}", "[", "[null]"])
def test_bundle_with_malformed_cves_exports_without_error(cve_id, clients, users):
    bundle = add_to_bundle(make_bundle(users.owner, vulnerability_identifiers=cve_id), make_rule(users.owner))

    response = clients["anonymous"].get(f"/bundle/download_misp?bundle_id={bundle.id}")

    assert response.status_code == 200
    assert objects_named(json.loads(response.data), "rulezet-bundle")


@pytest.mark.parametrize("name", INJECTIONS + ODD_CHARACTERS)
def test_bundle_with_a_hostile_name_exports_it_as_plain_text(name, clients, users):
    bundle = add_to_bundle(make_bundle(users.owner, name=name), make_rule(users.owner))

    response = clients["anonymous"].get(f"/bundle/download_misp?bundle_id={bundle.id}")

    assert response.status_code == 200
    assert values(objects_named(json.loads(response.data), "rulezet-bundle")[0], "name") == [name]


def test_empty_bundle_exports_its_own_object(clients, users):
    bundle = make_bundle(users.owner)

    response = clients["anonymous"].get(f"/bundle/download_misp?bundle_id={bundle.id}")

    assert response.status_code == 200
    assert values(objects_named(json.loads(response.data), "rulezet-bundle")[0], "number-of-rules") == ["0"]


# ── Bad ids on the exports ────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_id", BAD_IDS + ["", "1.5", "999999"])
@pytest.mark.parametrize("fmt", ["misp", "misp_event", "stix"])
def test_export_unknown_rule_gives_nothing(fmt, bad_id, clients, users, monkeypatch):
    stix = fake_stix(monkeypatch)
    make_rule(users.owner)

    response = clients["anonymous"].get(f"/rule/download_rule?rule_id={bad_id}&format={fmt}")

    assert response.status_code < 500
    assert response.get_json()["success"] is False
    assert stix.received == []


@pytest.mark.parametrize("bad_id", BAD_IDS + ["", "1.5", "999999"])
def test_export_unknown_bundle_is_refused(bad_id, clients, users):
    make_bundle(users.owner)

    response = clients["anonymous"].get(f"/bundle/download_misp?bundle_id={bad_id}")

    assert 400 <= response.status_code < 500


@pytest.mark.parametrize("bad_id", ["0", "999999", "-1", str(2**63)])
def test_stix_of_an_unknown_rule_is_empty(bad_id, clients, monkeypatch):
    stix = fake_stix(monkeypatch)

    response = clients["anonymous"].get(f"/rule/get_stix/{bad_id}")

    assert response.status_code in (200, 404)
    assert stix.received == []


# ── STIX converter answering garbage ──────────────────────────────────────────

@pytest.mark.parametrize("answer", [ValueError("not json"), "garbage", None, []],
                         ids=["not-json", "string", "none", "empty-list"])
def test_stix_with_a_converter_answering_garbage_never_errors(answer, clients, users, monkeypatch):
    import requests
    stix = fake_stix(monkeypatch)
    stix.answer = requests.exceptions.JSONDecodeError("bad", "doc", 0) if isinstance(answer, ValueError) else answer
    rule = make_rule(users.owner)

    page = clients["anonymous"].get(f"/rule/get_stix/{rule.id}")
    download = clients["anonymous"].get(f"/rule/download_rule?rule_id={rule.id}&format=stix")

    assert page.status_code == 200 and download.status_code == 200


def test_stix_with_the_converter_unreachable_gives_nothing(clients, users, monkeypatch):
    import requests
    stix = fake_stix(monkeypatch)
    stix.answer = requests.exceptions.ConnectionError("unreachable")
    rule = make_rule(users.owner)

    response = clients["anonymous"].get(f"/rule/get_stix/{rule.id}")

    assert response.status_code == 200 and response.get_json()["stix"] is None


# ── Convert_MISP API parameters ───────────────────────────────────────────────

@pytest.mark.parametrize("query", ["search=" + "A" * 300, "author=" + "A" * 200, "sort_by=nope",
                                   "rule_type=not-a-format", "sort_by=' OR 1=1 --"])
def test_convert_misp_with_bad_parameters_is_refused(query, app, users):
    make_rule(users.owner)

    response = app.test_client().get(f"/api/rule/public/Convert_MISP?{query}")

    assert response.status_code == 400


@pytest.mark.parametrize("search", INJECTIONS + ODD_CHARACTERS[1:])
def test_convert_misp_with_a_hostile_search_never_errors(search, app, users):
    make_rule(users.owner)

    response = app.test_client().get("/api/rule/public/Convert_MISP", query_string={"search": search})

    assert response.status_code == 200
    assert response.get_json()["total_rules_found"] == 0


def test_convert_misp_with_a_trashed_rule_of_a_hostile_title_leaks_nothing(app, users):
    trash(make_rule(users.owner, title="<script>alert(1)</script>"), users.admin)

    response = app.test_client().get("/api/rule/public/Convert_MISP?search=script")

    assert response.get_json()["total_rules_found"] == 0
