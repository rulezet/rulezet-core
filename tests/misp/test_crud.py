"""MISP — layer 2: what each action leaves in the database, and what the
MISP exports contain.

Server connections: the API key is stored encrypted and never sent back.
Exports: valid MISP JSON (an event with a rulezet-metadata object linked to
the rule's content object), the rule's content, CVEs, ATT&CK techniques and
the tags the reader may see — never an e-mail, an API key, a private tag of
someone else or a trashed rule. Push and update jobs are run directly.
"""
import json

import pytest
from pymisp import MISPEvent

from app import db
from app.core.db_class.db import ActivityLog, BackgroundJob, MispServer, Tag
from app.features.misp.misp_connector_core import _decrypt
from tests.helpers.attack import link_technique, make_technique, trash
from tests.helpers.comments import make_bundle
from tests.helpers.db import count, reload
from tests.helpers.misp import (
    API_KEY, add_to_bundle, fake_remote, make_server, new_server_payload, objects_named, push_jobs, run_job, values,
)
from tests.helpers.rules import make_rule
from tests.helpers.tags import TAXONOMY_UUID, fake_misp_data, make_tag, tag_bundle, tag_rule


@pytest.fixture
def remote(monkeypatch):
    return fake_remote(monkeypatch)


def _export(client, rule, fmt="misp_event"):
    body = client.get(f"/rule/download_rule?rule_id={rule.id}&format={fmt}").get_json()
    assert body["success"] is True, body
    return json.loads(body["content"])


def _bundle_export(client, bundle):
    response = client.get(f"/bundle/download_misp?bundle_id={bundle.id}")
    assert response.status_code == 200
    return json.loads(response.data)


# ── Server connections ────────────────────────────────────────────────────────

def test_add_server_stores_the_api_key_encrypted(clients, users):
    clients["admin"].post("/misp/create", json=new_server_payload(name="CIRCL MISP"))

    server = MispServer.query.one()
    assert server.name == "CIRCL MISP" and server.added_by_id == users.admin.id
    assert API_KEY not in server.api_key_encrypted
    assert _decrypt(server.api_key_encrypted) == API_KEY


def test_add_server_never_echoes_the_api_key(clients):
    response = clients["admin"].post("/misp/create", json=new_server_payload())

    assert response.get_json()["success"] is True
    assert API_KEY.encode() not in response.data
    assert b"api_key" not in response.data


def test_add_server_trims_the_url(clients):
    clients["admin"].post("/misp/create", json=new_server_payload(url="  https://misp.example.org/  "))

    assert MispServer.query.one().url == "https://misp.example.org"


def test_add_server_is_logged(clients):
    clients["admin"].post("/misp/create", json=new_server_payload())

    assert count(ActivityLog, action="misp.server_create") == 1


def test_list_servers_never_contains_the_api_key(clients, users):
    server = make_server(users.admin)

    response = clients["admin"].get("/misp/get")

    assert [s["uuid"] for s in response.get_json()] == [server.uuid]
    assert API_KEY.encode() not in response.data
    assert server.api_key_encrypted.encode() not in response.data


def test_edit_server_with_a_blank_key_keeps_the_key(clients, users):
    server = make_server(users.admin)

    clients["admin"].post(f"/misp/update/{server.uuid}", json={"name": "Renamed", "api_key": ""})

    assert reload(server).name == "Renamed"
    assert _decrypt(reload(server).api_key_encrypted) == API_KEY


def test_edit_server_never_echoes_the_api_key(clients, users):
    server = make_server(users.admin)

    response = clients["admin"].post(f"/misp/update/{server.uuid}", json={"api_key": "new-secret-key"})

    assert response.get_json()["success"] is True
    assert b"new-secret-key" not in response.data and API_KEY.encode() not in response.data


def test_edit_server_key_resets_the_verified_flag(clients, users):
    server = make_server(users.admin, is_verified=True)

    clients["admin"].post(f"/misp/update/{server.uuid}", json={"api_key": "new-secret-key"})

    assert _decrypt(reload(server).api_key_encrypted) == "new-secret-key"
    assert reload(server).is_verified is False


def test_edit_server_url_resets_the_verified_flag(clients, users):
    server = make_server(users.admin, is_verified=True)

    clients["admin"].post(f"/misp/update/{server.uuid}", json={"url": "https://other.example.org/"})

    assert reload(server).url == "https://other.example.org"
    assert reload(server).is_verified is False


def test_edit_server_name_only_keeps_the_verified_flag(clients, users):
    server = make_server(users.admin, is_verified=True)

    clients["admin"].post(f"/misp/update/{server.uuid}", json={"name": "Renamed"})

    assert reload(server).is_verified is True


def test_toggle_server_twice_turns_it_back_on(clients, users):
    server = make_server(users.admin, active=True)

    clients["admin"].post(f"/misp/toggle_active/{server.uuid}")
    assert reload(server).is_active is False
    clients["admin"].post(f"/misp/toggle_active/{server.uuid}")

    assert reload(server).is_active is True


def test_delete_server_removes_it(clients, users):
    server, other = make_server(users.admin), make_server(users.admin)

    response = clients["admin"].post(f"/misp/delete/{server.uuid}")

    assert response.get_json()["success"] is True
    assert reload(server) is None and reload(other) is not None


def test_delete_server_is_logged_once(clients, users):
    server = make_server(users.admin)

    clients["admin"].post(f"/misp/delete/{server.uuid}")

    assert count(ActivityLog, action="misp.server_delete") == 1


def test_server_history_lists_its_own_events(clients, users):
    server, other = make_server(users.admin), make_server(users.admin)
    clients["admin"].post(f"/misp/update/{server.uuid}", json={"name": "Renamed"})
    clients["admin"].post(f"/misp/update/{other.uuid}", json={"name": "Other"})

    history = clients["admin"].get(f"/misp/history/{server.uuid}").get_json()

    assert [h["action"] for h in history] == ["misp.server_update"]


# ── Connection test (fake remote) ─────────────────────────────────────────────

def test_connection_test_uses_the_stored_credentials(clients, users, remote):
    server = make_server(users.admin, verify_tls=False)

    clients["admin"].post(f"/misp/test/{server.uuid}")

    assert remote.connections == [(server.url, API_KEY, False)]


def test_connection_test_success_marks_the_server_verified(clients, users, remote):
    server = make_server(users.admin, last_error="old error")

    response = clients["admin"].post(f"/misp/test/{server.uuid}")

    assert response.get_json()["success"] is True
    assert reload(server).is_verified is True
    assert reload(server).last_error is None and reload(server).last_test_at is not None


def test_connection_test_failure_stores_the_error(clients, users, remote):
    remote.version = ConnectionError("connection refused")
    server = make_server(users.admin)

    response = clients["admin"].post(f"/misp/test/{server.uuid}")

    assert response.get_json()["success"] is False
    assert reload(server).is_verified is False
    assert "connection refused" in reload(server).last_error


# ── Push (queued job, run directly against the fake remote) ───────────────────

def test_push_rule_queues_a_job(clients, users):
    server, rule = make_server(users.admin), make_rule(users.owner)

    response = clients["admin"].post("/misp/push", json={"rule_id": rule.id, "server_uuid": server.uuid})

    job = push_jobs()[0]
    assert response.get_json()["job_uuid"] == job.uuid
    assert job.payload == {"server_id": server.id, "push_type": "object", "rule_id": rule.id}
    assert job.created_by == users.admin.id and job.status == "pending"


def test_push_is_logged_on_the_server_history(clients, users):
    server, rule = make_server(users.admin), make_rule(users.owner)

    clients["admin"].post("/misp/push", json={"rule_id": rule.id, "server_uuid": server.uuid})

    entry = ActivityLog.query.filter_by(action="misp.push_triggered").one()
    assert entry.target_id == server.id and entry.extra["rule_uuid"] == rule.uuid


def test_push_to_a_disabled_server_is_refused(clients, users):
    server, rule = make_server(users.admin, active=False), make_rule(users.owner)

    response = clients["admin"].post("/misp/push", json={"rule_id": rule.id, "server_uuid": server.uuid})

    assert response.status_code == 400 and push_jobs() == []


def test_push_bundle_as_object_is_refused(clients, users):
    server, bundle = make_server(users.admin), make_bundle(users.owner)

    response = clients["admin"].post("/misp/push", json={"bundle_id": bundle.id, "server_uuid": server.uuid,
                                                         "push_type": "object"})

    assert response.status_code == 400 and push_jobs() == []


def test_push_rule_and_bundle_together_is_refused(clients, users):
    server, rule, bundle = make_server(users.admin), make_rule(users.owner), make_bundle(users.owner)

    response = clients["admin"].post("/misp/push", json={"rule_id": rule.id, "bundle_id": bundle.id,
                                                         "server_uuid": server.uuid, "push_type": "event"})

    assert response.status_code == 400 and push_jobs() == []


def _push(client, server, **target):
    client.post("/misp/push", json={"server_uuid": server.uuid, **target})
    return push_jobs()[-1]


@pytest.mark.parametrize("push_type", ["object", "event"])
def test_push_job_sends_the_rule_to_the_remote(push_type, clients, users, remote):
    server, rule = make_server(users.admin), make_rule(users.owner)
    job = _push(clients["admin"], server, rule_id=rule.id, push_type=push_type)

    job = run_job(job)

    assert job.status == "done"
    [event] = remote.pushed
    assert isinstance(event, MISPEvent)
    assert {o.name for o in event.objects} == {"rulezet-metadata", "yara"}
    assert reload(server).pushes_count == 1 and reload(server).last_push_at is not None


def test_push_job_event_carries_only_public_tags(clients, users, remote):
    server, rule = make_server(users.admin), make_rule(users.owner)
    tag_rule(rule, make_tag(users.admin, name="public:tag"))
    tag_rule(rule, make_tag(users.owner, name="private:tag", visibility="private"))
    job = _push(clients["admin"], server, rule_id=rule.id, push_type="event")

    run_job(job)

    assert [t.name for t in remote.pushed[0].tags] == ["public:tag"]


def test_push_job_sends_the_bundle_with_its_rules(clients, users, remote):
    server = make_server(users.admin)
    bundle = add_to_bundle(make_bundle(users.owner), make_rule(users.owner), make_rule(users.owner))
    job = _push(clients["admin"], server, bundle_id=bundle.id, push_type="event")

    job = run_job(job)

    assert job.status == "done"
    names = [o.name for o in remote.pushed[0].objects]
    assert names.count("rulezet-bundle") == 1 and names.count("rulezet-metadata") == 2


def test_push_job_bundle_event_carries_its_public_tags(clients, users, remote):
    server, bundle = make_server(users.admin), make_bundle(users.owner)
    add_to_bundle(bundle, make_rule(users.owner))
    tag_bundle(bundle, make_tag(users.admin, name="public:tag"))
    tag_bundle(bundle, make_tag(users.owner, name="private:tag", visibility="private"))
    job = _push(clients["admin"], server, bundle_id=bundle.id, push_type="event")

    run_job(job)

    assert [t.name for t in remote.pushed[0].tags] == ["public:tag"]


def test_push_job_for_a_rule_trashed_meanwhile_sends_nothing(clients, users, remote):
    server, rule = make_server(users.admin), make_rule(users.owner)
    job = _push(clients["admin"], server, rule_id=rule.id)
    trash(rule, users.admin)

    job = run_job(job)

    assert job.status == "failed" and remote.pushed == []
    assert reload(server).pushes_count == 0


def test_push_job_to_a_server_disabled_meanwhile_sends_nothing(clients, users, remote):
    server, rule = make_server(users.admin), make_rule(users.owner)
    job = _push(clients["admin"], server, rule_id=rule.id)
    server.is_active = False
    db.session.commit()

    job = run_job(job)

    assert job.status == "failed" and remote.pushed == []


def test_push_job_rejected_by_the_remote_fails_and_keeps_the_error(clients, users, remote):
    remote.add_event_result = {"errors": "Event already exists"}
    server, rule = make_server(users.admin), make_rule(users.owner)
    job = _push(clients["admin"], server, rule_id=rule.id)

    job = run_job(job)

    assert job.status == "failed" and "already exists" in job.error
    assert reload(server).pushes_count == 0 and "already exists" in reload(server).last_error


def test_push_job_is_logged_on_the_server_history(clients, users, remote):
    server, rule = make_server(users.admin), make_rule(users.owner)
    job = _push(clients["admin"], server, rule_id=rule.id)

    run_job(job)

    entry = ActivityLog.query.filter_by(action="misp.push_done").one()
    assert entry.target_id == server.id and entry.extra["success"] is True


# ── Rule export ───────────────────────────────────────────────────────────────

def test_rule_event_links_metadata_to_the_content(clients, users):
    rule = make_rule(users.owner)

    event = _export(clients["anonymous"], rule)

    [metadata] = objects_named(event, "rulezet-metadata")
    [content] = objects_named(event, "yara")
    assert event["info"].endswith(rule.title)
    assert [r["referenced_uuid"] for r in metadata["ObjectReference"]] == [content["uuid"]]


def test_rule_event_holds_the_rule_metadata_and_content(clients, users):
    rule = make_rule(users.owner, version="3", license="GPL", author="Jane Analyst")

    event = _export(clients["anonymous"], rule)

    [metadata] = objects_named(event, "rulezet-metadata")
    [content] = objects_named(event, "yara")
    assert values(metadata, "uuid") == [rule.uuid] and values(metadata, "title") == [rule.title]
    assert values(metadata, "version") == ["3"] and values(metadata, "license") == ["GPL"]
    assert values(metadata, "author") == ["Jane Analyst"]
    assert values(content, "yara") == [rule.to_string]


def test_rule_object_export_holds_only_objects(clients, users):
    rule = make_rule(users.owner)

    exported = _export(clients["anonymous"], rule, fmt="misp")

    assert list(exported) == ["Object"]
    assert {o["name"] for o in exported["Object"]} == {"rulezet-metadata", "yara"}


def test_rule_event_lists_its_cves(clients, users):
    rule = make_rule(users.owner, cve_id=json.dumps(["CVE-2021-44228", "CVE-2023-1234"]))

    event = _export(clients["anonymous"], rule)

    [metadata] = objects_named(event, "rulezet-metadata")
    assert values(metadata, "cve-id") == ["CVE-2021-44228", "CVE-2023-1234"]
    assert [a["value"] for a in event["Attribute"] if a["type"] == "vulnerability"] == ["CVE-2021-44228",
                                                                                       "CVE-2023-1234"]


def test_rule_event_lists_its_attack_techniques(clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))
    link_technique(rule, make_technique("T1105"))

    event = _export(clients["anonymous"], rule)

    [metadata] = objects_named(event, "rulezet-metadata")
    assert values(metadata, "attack-id") == ["T1059", "T1105"]


def test_rule_event_carries_its_public_tags(clients, users):
    rule = make_rule(users.owner)
    tag_rule(rule, make_tag(users.admin, name="tlp:green", color="#33FF00"))

    event = _export(clients["anonymous"], rule)

    assert [(t["name"], t["colour"]) for t in event["Tag"]] == [("tlp:green", "#33FF00")]


@pytest.mark.parametrize("role", ["anonymous", "user"])
def test_rule_event_hides_someone_elses_private_tag(role, clients, users):
    rule = make_rule(users.owner)
    tag_rule(rule, make_tag(users.owner, name="owner:secret", visibility="private"))

    event = _export(clients[role], rule)

    assert "owner:secret" not in json.dumps(event)


def test_rule_event_shows_the_owner_their_private_tag(clients, users):
    rule = make_rule(users.owner)
    tag_rule(rule, make_tag(users.owner, name="owner:secret", visibility="private"))

    event = _export(clients["owner"], rule)

    assert [t["name"] for t in event["Tag"]] == ["owner:secret"]


@pytest.mark.parametrize("fmt", ["misp", "misp_event"])
def test_rule_export_never_contains_account_secrets(fmt, clients, users):
    rule = make_rule(users.owner)

    body = clients["admin"].get(f"/rule/download_rule?rule_id={rule.id}&format={fmt}").get_data(as_text=True)

    for secret in (users.owner.email, users.owner.api_key, users.admin.email, users.admin.api_key):
        assert secret not in body


@pytest.mark.parametrize("fmt, content_object", [
    ("sigma", "sigma"), ("suricata", "suricata"), ("splunk", "splunk-rule"),
    ("elastic", "elastic-detection-rule"), ("kql", "kql-analytics-rule"), ("kunai", "kunai-rule"),
])
def test_rule_export_maps_each_format_to_its_misp_object(fmt, content_object, clients, users):
    rule = make_rule(users.owner, format=fmt, to_string=f"content of a {fmt} rule")

    event = _export(clients["anonymous"], rule)

    [content] = objects_named(event, content_object)
    assert f"content of a {fmt} rule" in [a["value"] for a in content["Attribute"]]


def test_rule_export_is_logged_as_a_download(clients, users):
    rule = make_rule(users.owner)

    _export(clients["user"], rule)

    assert ActivityLog.query.filter_by(action="rule.download").one().extra["format"] == "misp_event"


# ── Bundle export ─────────────────────────────────────────────────────────────

def test_bundle_event_holds_the_bundle_and_each_rule(clients, users):
    first, second = make_rule(users.owner), make_rule(users.owner)
    bundle = add_to_bundle(make_bundle(users.owner), first, second)

    event = _bundle_export(clients["anonymous"], bundle)

    [bundle_object] = objects_named(event, "rulezet-bundle")
    metadata = objects_named(event, "rulezet-metadata")
    assert values(bundle_object, "uuid") == [bundle.uuid]
    assert values(bundle_object, "number-of-rules") == ["2"]
    assert sorted(v for m in metadata for v in values(m, "uuid")) == sorted([first.uuid, second.uuid])
    assert {r["referenced_uuid"] for r in bundle_object["ObjectReference"]} == {m["uuid"] for m in metadata}


def test_bundle_event_lists_each_rules_attack_techniques(clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))
    bundle = add_to_bundle(make_bundle(users.owner), rule)

    event = _bundle_export(clients["anonymous"], bundle)

    [metadata] = objects_named(event, "rulezet-metadata")
    assert values(metadata, "attack-id") == ["T1059"]


def test_bundle_event_leaves_out_trashed_rules(clients, users):
    kept, trashed = make_rule(users.owner), make_rule(users.owner)
    bundle = add_to_bundle(make_bundle(users.owner), kept, trashed)
    trash(trashed, users.admin)

    event = _bundle_export(clients["anonymous"], bundle)

    [bundle_object] = objects_named(event, "rulezet-bundle")
    assert trashed.uuid not in json.dumps(event) and trashed.to_string not in json.dumps(event)
    assert values(bundle_object, "number-of-rules") == ["1"]


def test_bundle_event_carries_its_public_tags_only(clients, users):
    bundle = add_to_bundle(make_bundle(users.owner), make_rule(users.owner))
    tag_bundle(bundle, make_tag(users.admin, name="public:tag"))
    tag_bundle(bundle, make_tag(users.owner, name="owner:secret", visibility="private"))

    event = _bundle_export(clients["user"], bundle)

    assert [t["name"] for t in event["Tag"]] == ["public:tag"]


def test_bundle_event_never_contains_account_secrets(clients, users):
    bundle = add_to_bundle(make_bundle(users.owner), make_rule(users.owner))

    body = clients["admin"].get(f"/bundle/download_misp?bundle_id={bundle.id}").get_data(as_text=True)

    for secret in (users.owner.email, users.owner.api_key, users.admin.email, users.admin.api_key):
        assert secret not in body


# ── MISP data update job (update_misp_data) ───────────────────────────────────

@pytest.fixture
def misp_data(tmp_path, monkeypatch):
    """Fake taxonomies / galaxies on disk, and a git that never reaches GitHub."""
    from app.features.jobs import job_handlers
    fake_misp_data(tmp_path, monkeypatch)
    pulls = []
    monkeypatch.setattr(job_handlers, "_git_submodule_update",
                        lambda path: pulls.append(path.name) or (True, "Already up to date."))
    return tmp_path, pulls


def _update_job(user):
    job = BackgroundJob(uuid=f"update-misp-{user.id}", job_type="update_misp_data", status="running",
                        created_by=user.id, payload={})
    db.session.add(job)
    db.session.commit()
    return job


def _add_predicate(base, value):
    path = base / "misp-taxonomies" / "testtax" / "machinetag.json"
    data = json.loads(path.read_text())
    data["predicates"].append({"value": value, "expanded": value.title()})
    data["version"] += 1
    path.write_text(json.dumps(data))


def test_update_job_pulls_both_misp_repositories(users, misp_data):
    _, pulls = misp_data

    run_job(_update_job(users.admin))

    assert pulls == ["misp-taxonomies", "misp-galaxy"]


def test_update_job_adds_new_values_of_an_imported_taxonomy(users, misp_data):
    from app.features.tags import tags_core
    base, _ = misp_data
    tags_core.add_tags_from_misp_taxonomy(TAXONOMY_UUID, users.admin)
    _add_predicate(base, "third")

    job = run_job(_update_job(users.admin))

    assert {t.name for t in Tag.query.filter_by(source="Taxonomy")} == {"testtax:first", "testtax:second",
                                                                       "testtax:third"}
    assert job.done == job.total == 3


def test_update_job_never_imports_a_taxonomy_or_galaxy_not_imported_yet(users, misp_data):
    run_job(_update_job(users.admin))

    assert count(Tag, source="Taxonomy") == 0 and count(Tag, source="Galaxy") == 0


def test_update_job_keeps_existing_tags_untouched(users, misp_data):
    from app.features.tags import tags_core
    tags_core.add_tags_from_misp_taxonomy(TAXONOMY_UUID, users.admin)
    before = {t.id: t.name for t in Tag.query.filter_by(source="Taxonomy")}

    run_job(_update_job(users.admin))

    assert {t.id: t.name for t in Tag.query.filter_by(source="Taxonomy")} == before
