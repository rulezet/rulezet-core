"""ATT&CK — layer 1: who can do what.

Permission model: the technique catalogue, the heatmap, technique pages and
the techniques mapped on an active rule are public to read. Mapping a
technique on a rule, or removing one, is for the rule's owner or an admin —
and for a `rule.tag_any` holder on anyone's rule. The admin views (technique
list, analytics, coverage gaps) and the jobs (refresh the MITRE catalogue,
auto-parse rules) are admin-only.
"""
from unittest import mock

import pytest

from app.core.db_class.db import BackgroundJob, RuleAttackAssociation, RuleEditContribution
from tests.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from tests.helpers.attack import link_technique, make_technique
from tests.helpers.db import count
from tests.helpers.rules import make_rule
from tests.helpers.users import make_user_with_permission

EVERYONE = {"anonymous": OK, "user": OK, "owner": OK, "admin": OK}
OWNER_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}


@pytest.fixture(autouse=True)
def _no_job_side_effects():
    """Creating a job notifies its owner — irrelevant here, keep it quiet."""
    with mock.patch("app.features.notification.notification_core.create_job_notification"):
        yield


# ── Reading (public) ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_list_techniques(role, expected, clients):
    make_technique("T1059")

    response = clients[role].get("/attack/techniques")

    assert_outcome(response, expected)
    assert [t["technique_id"] for t in response.get_json()] == ["T1059"]


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_search_techniques(role, expected, clients):
    make_technique("T1059")

    response = clients[role].get("/attack/techniques/search?q=T1059")

    assert_outcome(response, expected)
    assert [t["technique_id"] for t in response.get_json()] == ["T1059"]


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_view_catalogue_stats(role, expected, clients):
    make_technique("T1059")

    response = clients[role].get("/attack/stats")

    assert_outcome(response, expected)
    assert response.get_json()["total_techniques"] == 1


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_view_technique_usage(role, expected, clients, users):
    link_technique(make_rule(users.owner), make_technique("T1059"))

    response = clients[role].get("/attack/techniques/usage")

    assert_outcome(response, expected)
    assert [t["id"] for t in response.get_json()["techniques"]] == ["T1059"]


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_view_rule_techniques(role, expected, clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))

    response = clients[role].get(f"/attack/rule/{rule.id}")

    assert_outcome(response, expected)
    assert [t["technique_id"] for t in response.get_json()] == ["T1059"]


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_open_heatmap(role, expected, clients):
    response = clients[role].get("/attack/heatmap")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_view_heatmap_data(role, expected, clients, users):
    link_technique(make_rule(users.owner), make_technique("T1059"))

    response = clients[role].get("/attack/heatmap_data")

    assert_outcome(response, expected)
    assert response.get_json()["stats"]["unique_techniques"] == 1


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_open_technique_page(role, expected, clients):
    make_technique("T1059")

    response = clients[role].get("/attack/technique/T1059")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_view_technique_stats(role, expected, clients, users):
    link_technique(make_rule(users.owner), make_technique("T1059"))

    response = clients[role].get("/attack/technique/T1059/stats")

    assert_outcome(response, expected)
    assert response.get_json()["total_rules"] == 1


# ── Mapping a technique on a rule ─────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_add_technique_to_rule(role, expected, clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059")

    response = clients[role].post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    assert_outcome(response, expected)
    assert count(RuleAttackAssociation, rule_id=rule.id, technique_id="T1059") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_remove_technique_from_rule(role, expected, clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))

    response = clients[role].delete(f"/attack/rule/{rule.id}/remove/T1059")

    assert_outcome(response, expected)
    assert count(RuleAttackAssociation, rule_id=rule.id, technique_id="T1059") == (0 if expected is OK else 1)


def test_tag_manager_can_add_a_technique_to_someone_elses_rule(client_as, users):
    tagger = make_user_with_permission("rule.tag_any")
    rule = make_rule(users.owner)
    make_technique("T1059")

    response = client_as(tagger).post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    assert_outcome(response, OK)
    assert count(RuleAttackAssociation, rule_id=rule.id, technique_id="T1059") == 1
    assert count(RuleEditContribution, rule_id=rule.id, user_id=tagger.id) == 1


def test_tag_manager_can_remove_a_technique_from_someone_elses_rule(client_as, users):
    tagger = make_user_with_permission("rule.tag_any")
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))

    response = client_as(tagger).delete(f"/attack/rule/{rule.id}/remove/T1059")

    assert_outcome(response, OK)
    assert count(RuleAttackAssociation, rule_id=rule.id) == 0


# ── Admin views ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_open_admin_technique_list(role, expected, clients):
    response = clients[role].get("/attack/admin/list")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_list_techniques_as_admin_table(role, expected, clients):
    make_technique("T1059")

    response = clients[role].get("/attack/admin/techniques")

    assert_outcome(response, expected)
    if expected is OK:
        assert response.get_json()["total"] == 1


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_view_admin_analytics(role, expected, clients):
    response = clients[role].get("/attack/admin/analytics")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_view_coverage_gaps(role, expected, clients):
    make_technique("T1059")

    response = clients[role].get("/attack/admin/gaps")

    assert_outcome(response, expected)
    if expected is OK:
        assert response.get_json()["gaps"][0]["techniques"][0]["technique_id"] == "T1059"


# ── Admin jobs ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_trigger_catalogue_update(role, expected, clients):
    response = clients[role].post("/attack/admin/trigger_update")

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="update_attack_data") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_trigger_auto_parse(role, expected, clients):
    response = clients[role].post("/attack/admin/trigger_parse", json={})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="bulk_parse_attack_rules") == (1 if expected is OK else 0)
