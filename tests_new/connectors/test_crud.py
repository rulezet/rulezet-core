"""Connectors — layer 2: what the connector routes and a pull write in the
database. The remote instance is a FakeRemote (tests/helpers/connectors.py).

A pull matches remote rules to local ones by uuid only: no match → the rule
is created (owned by the connector's shadow user, or by the connector's
owner in "self" mode); a match whose content and metadata are identical →
skipped; a match that differs → updated in place, with a history entry.
"""
import json

import pytest

from app import db
from app.core.db_class.db import (
    ActivityLog, Bundle, BundleRuleAssociation, Connector, Rule, RuleTagAssociation, RuleUpdateHistory, Tag, User,
)
from tests_new.helpers.connectors import (  # noqa: F401
    API, REMOTE_URL, connector_form, make_connector, make_system_connector, no_network, pull_jobs, remote,
    remote_bundle, remote_rule, run_pull,
)
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule


def _tag_names(rule):
    return {Tag.query.get(a.tag_id).name for a in RuleTagAssociation.query.filter_by(rule_id=rule.id)}


def _pulled(remote_item):
    db.session.expire_all()
    return Rule.query.filter_by(uuid=remote_item["uuid"]).one()


def _log_actions(connector):
    db.session.expire_all()
    return [e.action for e in ActivityLog.query.filter_by(target_type="connector", target_id=connector.id)]


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_connector_stores_it_owned_by_the_admin(clients, users):
    form = connector_form(instance_url=f"{REMOTE_URL}/")

    response = clients["admin"].post(f"{API}/create", json=form)

    connector = Connector.query.filter_by(name=form["name"]).one()
    assert response.get_json()["connector"]["uuid"] == connector.uuid
    assert connector.owner_id == users.admin.id
    assert connector.instance_url == REMOTE_URL
    assert connector.api_key_outbound == form["api_key_outbound"]
    assert connector.is_active is True and connector.is_system is False and connector.is_verified is False


def test_create_connector_creates_a_shadow_user_that_cannot_act(clients):
    """Pulled content needs a local owner; that ghost account is no admin and never verified."""
    clients["admin"].post(f"{API}/create", json=connector_form())

    shadow = db.session.get(User, Connector.query.one().shadow_user_id)
    assert shadow is not None
    assert shadow.admin is False and shadow.is_verified is False
    assert shadow.api_key is None or shadow.api_key == ""


def test_create_connector_logs_the_creation_once(clients):
    clients["admin"].post(f"{API}/create", json=connector_form())

    assert _log_actions(Connector.query.one()) == ["connector.create"]


@pytest.mark.parametrize("missing", ["name", "instance_url"])
def test_create_connector_without_a_required_field_is_refused(missing, clients):
    form = connector_form()
    del form[missing]

    response = clients["admin"].post(f"{API}/create", json=form)

    assert response.status_code == 400
    assert count(Connector) == 0


def test_create_connector_never_contacts_the_remote(clients, remote):
    clients["admin"].post(f"{API}/create", json=connector_form())

    assert remote.calls == []


# ── Read ──────────────────────────────────────────────────────────────────────

def test_list_shows_the_admins_connectors_and_the_system_ones(clients, users):
    mine = make_connector(users.admin)
    system = make_system_connector(users.admin)

    data = clients["admin"].get(f"{API}/get").get_json()

    assert {c["uuid"] for c in data} == {mine.uuid, system.uuid}
    assert data[0]["uuid"] == system.uuid


def test_list_hides_the_connectors_of_another_admin(clients, users):
    """Current behaviour (product question in the report): another admin's
    connector is not listed, though any admin can still act on it by uuid."""
    from tests_new.helpers.users import make_user
    other_admin = make_user("other-admin", admin=True)
    theirs = make_connector(other_admin)

    data = clients["admin"].get(f"{API}/get").get_json()

    assert theirs.uuid not in {c["uuid"] for c in data}


def test_list_never_shows_the_remote_api_key(clients, users):
    make_connector(users.admin, api_key_outbound="remote-secret-key")

    response = clients["admin"].get(f"{API}/get")

    assert b"remote-secret-key" not in response.data
    assert "api_key_outbound" not in response.get_json()[0]


def test_list_counts_only_the_active_rules_pulled_by_a_connector(clients, users):
    connector = make_connector(users.admin)
    make_rule(users.owner, connector_id=connector.id)
    make_rule(users.owner, connector_id=connector.id, is_deleted=True)

    data = clients["admin"].get(f"{API}/get").get_json()

    assert data[0]["local_rules_count"] == 1


def test_list_flags_a_connector_pointing_at_this_instance(clients, users, app):
    make_connector(users.admin, instance_url=f"http://{app.config['SERVER_NAME']}")

    data = clients["admin"].get(f"{API}/get").get_json()

    assert data[0]["is_self"] is True


def test_history_lists_the_connector_events_newest_first(clients, users):
    clients["admin"].post(f"{API}/create", json=connector_form())
    connector = Connector.query.one()
    clients["admin"].post(f"{API}/update/{connector.uuid}", json={"name": "Renamed"})

    data = clients["admin"].get(f"{API}/history/{connector.uuid}").get_json()

    assert [e["action"] for e in data] == ["connector.update", "connector.create"]


def test_history_of_an_unknown_connector_is_not_found(clients):
    response = clients["admin"].get(f"{API}/history/no-such-uuid")

    assert response.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_connector_changes_the_editable_fields(clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/update/{connector.uuid}", json={
        "name": "Renamed", "description": "New text", "instance_url": "https://other.rulezet.test/",
        "api_key_outbound": "new-secret", "sync_bundles": True, "is_active": False, "owner_mode": "self"})

    connector = reload(connector)
    assert response.get_json()["success"] is True
    assert (connector.name, connector.description) == ("Renamed", "New text")
    assert connector.instance_url == "https://other.rulezet.test"
    assert connector.api_key_outbound == "new-secret"
    assert connector.sync_bundles is True and connector.is_active is False and connector.owner_mode == "self"


def test_update_connector_ignores_protected_fields(clients, users):
    connector = make_connector(users.admin)
    original_uuid = connector.uuid

    clients["admin"].post(f"{API}/update/{connector.uuid}", json={
        "uuid": "forged", "owner_id": users.user.id, "is_system": True, "shadow_user_id": users.user.id,
        "rules_synced": 999})

    connector = reload(connector)
    assert connector.uuid == original_uuid and connector.owner_id == users.admin.id
    assert connector.is_system is False and connector.shadow_user_id != users.user.id
    assert connector.rules_synced == 0


def test_update_connector_logs_the_change_once(clients, users):
    connector = make_connector(users.admin)

    clients["admin"].post(f"{API}/update/{connector.uuid}", json={"name": "Renamed"})

    assert _log_actions(connector) == ["connector.update"]


def test_update_system_connector_is_refused(clients, users):
    connector = make_system_connector(users.admin)

    response = clients["admin"].post(f"{API}/update/{connector.uuid}", json={"name": "Hijacked"})

    assert response.status_code == 403
    assert reload(connector).name == "Rulezet Official"


def test_update_unknown_connector_is_not_found(clients):
    response = clients["admin"].post(f"{API}/update/no-such-uuid", json={"name": "x"})

    assert response.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_connector_keeps_the_rules_it_pulled(clients, users):
    connector = make_connector(users.admin)
    rule = make_rule(users.owner, connector_id=connector.id)

    response = clients["admin"].post(f"{API}/delete/{connector.uuid}")

    assert response.get_json()["success"] is True
    assert reload(connector) is None
    rule = reload(rule)
    assert rule is not None and rule.connector_id is None and rule.is_deleted is False


def test_delete_connector_logs_the_deletion_once(clients, users):
    connector = make_connector(users.admin)
    connector_uuid = connector.uuid

    clients["admin"].post(f"{API}/delete/{connector.uuid}")

    db.session.expire_all()
    assert ActivityLog.query.filter_by(action="connector.delete").count() == 1
    assert ActivityLog.query.filter_by(action="connector.delete").one().target_uuid == connector_uuid


def test_delete_system_connector_is_refused(clients, users):
    connector = make_system_connector(users.admin)

    response = clients["admin"].post(f"{API}/delete/{connector.uuid}")

    assert response.status_code == 403
    assert reload(connector) is not None


def test_delete_unknown_connector_is_not_found(clients):
    response = clients["admin"].post(f"{API}/delete/no-such-uuid")

    assert response.status_code == 404


# ── Connection test ───────────────────────────────────────────────────────────

def test_connection_test_records_the_remote_counts(clients, users, remote):
    remote.rules = [remote_rule(), remote_rule()]
    connector = make_connector(users.admin, last_error="old error")

    response = clients["admin"].post(f"{API}/test/{connector.uuid}")

    data = response.get_json()
    connector = reload(connector)
    assert data["success"] is True and data["stats"] == {"rules": 2, "bundles": 0}
    assert connector.is_verified is True and connector.last_error is None
    assert (connector.remote_rules_count, connector.remote_bundles_count) == (2, 0)


def test_connection_test_sends_the_remote_api_key_to_the_remote_only(clients, users, remote):
    connector = make_connector(users.admin, api_key_outbound="remote-secret-key")

    response = clients["admin"].post(f"{API}/test/{connector.uuid}")

    assert all(url.startswith(REMOTE_URL) for url in remote.urls())
    assert all(headers.get("X-API-KEY") == "remote-secret-key" for _, headers in remote.calls)
    assert b"remote-secret-key" not in response.data


def test_connection_test_logs_success_once(clients, users, remote):
    connector = make_connector(users.admin)

    clients["admin"].post(f"{API}/test/{connector.uuid}")

    assert _log_actions(connector) == ["connector.test_ok"]


@pytest.mark.parametrize("status", [404, 500, 503])
def test_connection_test_against_a_failing_remote_records_the_error(status, clients, users, remote):
    remote.answer("manifest", status=status, json={})
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/test/{connector.uuid}")

    connector = reload(connector)
    assert response.status_code == 200 and response.get_json()["success"] is False
    assert connector.is_verified is False and str(status) in connector.last_error


def test_connection_test_of_an_unknown_connector_is_not_found(clients, remote):
    response = clients["admin"].post(f"{API}/test/no-such-uuid")

    assert response.status_code == 404
    assert remote.calls == []


# ── Pull preview ──────────────────────────────────────────────────────────────

def test_preview_returns_the_remote_count_for_a_cve(clients, users, remote):
    remote.rules = [remote_rule(), remote_rule(), remote_rule()]
    connector = make_connector(users.admin)

    response = clients["admin"].get(f"{API}/preview/{connector.uuid}?cve=CVE-2024-1234")

    assert response.get_json() == {"success": True, "count": 3, "cve": "CVE-2024-1234"}
    assert "cve=CVE-2024-1234" in remote.urls("rules")[0]
    assert count(Rule) == 0


def test_preview_without_a_cve_is_refused(clients, users, remote):
    connector = make_connector(users.admin)

    response = clients["admin"].get(f"{API}/preview/{connector.uuid}")

    assert response.status_code == 400
    assert remote.calls == []


def test_preview_against_a_failing_remote_is_a_bad_gateway(clients, users, remote):
    remote.answer("count", status=500, json={})
    connector = make_connector(users.admin)

    response = clients["admin"].get(f"{API}/preview/{connector.uuid}?cve=CVE-2024-1234")

    assert response.status_code == 502


# ── Pull trigger ──────────────────────────────────────────────────────────────

def test_pull_queues_a_job_with_the_connector_and_options(clients, users, remote):
    connector = make_connector(users.admin)
    filters = {"formats": ["yara"]}

    response = clients["admin"].post(f"{API}/pull/{connector.uuid}",
                                     json={"sync_rules": True, "sync_bundles": True, "filters": filters})

    job = pull_jobs()[0]
    assert response.get_json()["job_uuid"] == job.uuid
    assert job.status == "pending" and job.created_by == users.admin.id
    assert job.payload == {"connector_id": connector.id, "sync_rules": True, "sync_bundles": True,
                           "filters": filters}
    assert remote.calls == []


def test_pull_logs_the_trigger_once(clients, users):
    connector = make_connector(users.admin)

    clients["admin"].post(f"{API}/pull/{connector.uuid}", json={})

    assert _log_actions(connector) == ["connector.pull_triggered"]


def test_pull_of_a_disabled_connector_is_refused(clients, users):
    connector = make_connector(users.admin, is_active=False)

    response = clients["admin"].post(f"{API}/pull/{connector.uuid}", json={})

    assert response.status_code == 400
    assert pull_jobs() == []


def test_pull_from_this_very_instance_is_refused(clients, users, app):
    connector = make_connector(users.admin, instance_url=f"http://{app.config['SERVER_NAME']}")

    response = clients["admin"].post(f"{API}/pull/{connector.uuid}", json={})

    assert response.status_code == 400
    assert pull_jobs() == []


def test_pull_with_nothing_selected_is_refused(clients, users):
    connector = make_connector(users.admin)

    response = clients["admin"].post(f"{API}/pull/{connector.uuid}", json={"sync_rules": False, "sync_bundles": False})

    assert response.status_code == 400
    assert pull_jobs() == []


def test_pull_of_an_unknown_connector_is_not_found(clients):
    response = clients["admin"].post(f"{API}/pull/no-such-uuid", json={})

    assert response.status_code == 404
    assert pull_jobs() == []


# ── Tag families ──────────────────────────────────────────────────────────────

def test_import_tag_families_installs_a_known_taxonomy(clients):
    response = clients["admin"].post(f"{API}/import_tag_families", json={"families": ["PAP", "no-such-family"]})

    data = response.get_json()
    assert [(r["family"], r["ok"]) for r in data["results"]] == [("PAP", True), ("no-such-family", False)]
    assert data["all_ok"] is False
    assert count(Tag, name="PAP:RED") == 1


# ── Pull: new rules ───────────────────────────────────────────────────────────

def test_pull_creates_the_remote_rules_owned_by_the_shadow_user(app, users, remote):
    item = remote_rule(title="From the remote")
    remote.rules = [item]
    connector = make_connector(users.admin)

    job = run_pull(app, connector, users.admin)

    rule = _pulled(item)
    connector = reload(connector)
    assert job.status == "done"
    assert rule.title == "From the remote" and rule.to_string == item["to_string"]
    assert rule.remote_rule_uuid == item["uuid"] and rule.connector_id == connector.id
    assert rule.sync_instance_url == REMOTE_URL
    assert rule.user_id == connector.shadow_user_id and rule.user_id != users.admin.id
    assert rule.is_deleted is False


def test_pull_in_self_mode_gives_the_rules_to_the_connector_owner(app, users, remote):
    item = remote_rule()
    remote.rules = [item]
    connector = make_connector(users.admin, owner_mode="self")

    run_pull(app, connector, users.admin)

    assert _pulled(item).user_id == users.admin.id


def test_pull_attaches_tags_cves_and_history(app, users, remote):
    item = remote_rule(tags=["tlp:clear", "remote-only-tag"], cve_ids=["CVE-2024-1234"], update_history=[
        {"old_content": "a", "new_content": "b", "message": "remote edit", "success": True,
         "analyzed_at": "2025-06-01T10:00:00", "manuel_submit": True}])
    remote.rules = [item]
    connector = make_connector(users.admin)

    run_pull(app, connector, users.admin)

    rule = _pulled(item)
    assert _tag_names(rule) == {"tlp:clear", "remote-only-tag"}
    assert json.loads(rule.cve_id) == ["CVE-2024-1234"]
    assert [h.message for h in RuleUpdateHistory.query.filter_by(rule_id=rule.id)] == ["remote edit"]


def test_pull_reads_every_page(app, users, remote):
    remote.rules = [remote_rule() for _ in range(1203)]
    connector = make_connector(users.admin)

    job = run_pull(app, connector, users.admin)

    assert job.status == "done"
    assert count(Rule) == 1203


def test_pull_records_the_sync_on_the_connector(app, users, remote):
    remote.rules = [remote_rule(), remote_rule()]
    connector = make_connector(users.admin)

    run_pull(app, connector, users.admin)

    connector = reload(connector)
    assert connector.last_sync_at is not None and connector.is_verified is True
    assert connector.rules_synced == 2
    done = ActivityLog.query.filter_by(action="connector.pull_done", target_id=connector.id).one()
    assert done.extra["rules_added"] == 2


def test_pull_sends_the_filters_to_the_remote(app, users, remote):
    connector = make_connector(users.admin)
    filters = {"formats": ["yara", "sigma"], "authors": ["alice"], "cves": [{"names": ["CVE-2024-1234"]}],
               "tags": [{"names": ["tlp:clear"], "mode": "AND", "exclude": True}],
               "date_from": "2025-01-01", "attacks": ["T1059"]}

    run_pull(app, connector, users.admin, filters=filters)

    url = remote.urls("rules?since")[0]
    for part in ("formats=yara,sigma", "author=alice", "cve=CVE-2024-1234", "tags=tlp:clear",
                 "tag_mode=AND", "tag_exclude=true", "date_from=2025-01-01", "attacks=T1059"):
        assert part in url


def test_pull_sends_the_remote_api_key(app, users, remote):
    connector = make_connector(users.admin, api_key_outbound="remote-secret-key")

    run_pull(app, connector, users.admin)

    assert remote.calls and all(h.get("X-API-KEY") == "remote-secret-key" for _, h in remote.calls)


# ── Pull: matching by uuid ────────────────────────────────────────────────────

def test_pull_twice_skips_the_unchanged_rules(app, users, remote):
    item = remote_rule()
    remote.rules = [item]
    connector = make_connector(users.admin)
    run_pull(app, connector, users.admin)
    history_before = count(RuleUpdateHistory)

    run_pull(app, connector, users.admin)

    assert count(Rule) == 1
    assert count(RuleUpdateHistory) == history_before
    done = ActivityLog.query.filter_by(action="connector.pull_done").order_by(ActivityLog.id.desc()).first()
    assert (done.extra["rules_added"], done.extra["rules_skipped"]) == (0, 1)


def test_pull_updates_a_changed_rule_in_place_with_history(app, users, remote):
    item = remote_rule()
    remote.rules = [item]
    connector = make_connector(users.admin)
    run_pull(app, connector, users.admin)
    rule_id = _pulled(item).id
    old_content = item["to_string"]
    item["to_string"] = old_content.replace("condition", "condition /* v2 */")

    run_pull(app, connector, users.admin)

    rule = _pulled(item)
    assert rule.id == rule_id and rule.to_string == item["to_string"]
    entry = RuleUpdateHistory.query.filter_by(rule_id=rule_id, change_type="content").one()
    assert (entry.old_content, entry.new_content) == (old_content, item["to_string"])


def test_pull_records_a_metadata_only_change(app, users, remote):
    item = remote_rule()
    remote.rules = [item]
    connector = make_connector(users.admin)
    run_pull(app, connector, users.admin)
    item["title"] = "Renamed on the remote"

    run_pull(app, connector, users.admin)

    rule = _pulled(item)
    assert rule.title == "Renamed on the remote"
    assert count(RuleUpdateHistory, rule_id=rule.id, change_type="metadata") == 1


def test_pull_updates_a_local_rule_with_the_same_uuid(app, users, remote):
    """Matching is by uuid only — a local rule with the remote's uuid is the same rule."""
    local = make_rule(users.owner)
    item = remote_rule(uuid=local.uuid, title="Remote version")
    remote.rules = [item]
    connector = make_connector(users.admin)

    run_pull(app, connector, users.admin)

    local = reload(local)
    assert count(Rule) == 1
    assert local.title == "Remote version" and local.user_id == users.owner.id
    assert local.connector_id == connector.id


def test_pull_never_matches_by_title_or_content(app, users, remote):
    local = make_rule(users.owner)
    remote.rules = [remote_rule(title=local.title, to_string=local.to_string)]
    connector = make_connector(users.admin)

    run_pull(app, connector, users.admin)

    assert count(Rule) == 2
    assert reload(local).connector_id is None


def test_pull_restores_a_trashed_local_copy(app, users, remote):
    """Current behaviour (product question in the report): a rule trashed
    locally comes back from the trash when the remote still serves it."""
    item = remote_rule()
    remote.rules = [item]
    connector = make_connector(users.admin)
    run_pull(app, connector, users.admin)
    rule = _pulled(item)
    rule.is_deleted = True
    db.session.commit()

    run_pull(app, connector, users.admin)

    assert reload(rule).is_deleted is False
    assert count(Rule) == 1


def test_pull_never_deletes_local_rules_the_remote_no_longer_serves(app, users, remote):
    gone, kept = remote_rule(), remote_rule()
    remote.rules = [gone, kept]
    connector = make_connector(users.admin)
    run_pull(app, connector, users.admin)
    remote.rules = [kept]

    run_pull(app, connector, users.admin)

    assert _pulled(gone).is_deleted is False


# ── Pull: bundles ─────────────────────────────────────────────────────────────

def test_pull_creates_the_remote_bundles_with_their_rules(app, users, remote):
    rule_item = remote_rule()
    bundle_item = remote_bundle(rules=[rule_item])
    remote.rules, remote.bundles = [rule_item], [bundle_item]
    connector = make_connector(users.admin, sync_bundles=True)

    run_pull(app, connector, users.admin)

    bundle = Bundle.query.filter_by(remote_bundle_uuid=bundle_item["uuid"]).one()
    assert bundle.connector_id == connector.id and bundle.access is True
    assert [a.rule_id for a in BundleRuleAssociation.query.filter_by(bundle_id=bundle.id)] == [_pulled(rule_item).id]


def test_pull_bundles_only_fetches_just_the_rules_they_reference(app, users, remote):
    referenced, unrelated = remote_rule(), remote_rule()
    remote.rules, remote.bundles = [referenced, unrelated], [remote_bundle(rules=[referenced])]
    connector = make_connector(users.admin, sync_rules=False, sync_bundles=True)

    run_pull(app, connector, users.admin)

    assert count(Rule, uuid=referenced["uuid"]) == 1
    assert count(Rule, uuid=unrelated["uuid"]) == 0


def test_pull_twice_skips_an_unchanged_bundle(app, users, remote):
    remote.bundles = [remote_bundle()]
    connector = make_connector(users.admin, sync_bundles=True)
    run_pull(app, connector, users.admin)

    run_pull(app, connector, users.admin)

    assert count(Bundle) == 1


# ── Pull: refused before anything is written ──────────────────────────────────

def test_pull_of_a_connector_disabled_after_queueing_fails_without_contacting_the_remote(app, users, remote):
    from app.features.connector.connector_core import trigger_pull
    from tests_new.helpers.connectors import run_job
    remote.rules = [remote_rule()]
    connector = make_connector(users.admin)
    job = trigger_pull(connector, triggered_by=users.admin.id)
    connector.is_active = False
    db.session.commit()

    job = run_job(app, job)

    assert job.status == "failed"
    assert remote.calls == [] and count(Rule) == 0


def test_pull_from_a_remote_without_the_sync_api_fails(app, users, remote):
    remote.rules = [remote_rule()]
    remote.answer("manifest", status=404, json={})
    connector = make_connector(users.admin)

    job = run_pull(app, connector, users.admin)

    assert job.status == "failed"
    assert reload(connector).last_error and count(Rule) == 0


def test_pull_with_a_filter_the_remote_does_not_support_is_refused(app, users, remote):
    """An ignored filter would pull the whole remote corpus instead."""
    remote.rules = [remote_rule()]
    remote.manifest = {"sync_api_version": 2, "capabilities": {"sync_rules": True, "rule_filters": False}}
    connector = make_connector(users.admin)

    job = run_pull(app, connector, users.admin, filters={"formats": ["yara"]})

    assert job.status == "failed" and count(Rule) == 0


def test_pull_never_contacts_anything_but_the_connector_url(app, users, remote):
    remote.rules, remote.bundles = [remote_rule()], [remote_bundle()]
    connector = make_connector(users.admin, sync_bundles=True)

    run_pull(app, connector, users.admin)

    assert remote.calls and all(url.startswith(f"{REMOTE_URL}/api/sync/") for url in remote.urls())
