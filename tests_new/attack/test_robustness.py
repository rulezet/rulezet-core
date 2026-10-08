"""ATT&CK — layer 4: inputs meant to break Rulezet.

Expected every time: a clean answer (< 500) and no mapping created from a
bad technique id — only techniques of the catalogue are ever linked.
"""
from unittest import mock

import pytest

from app.core.db_class.db import AttackTechnique, BackgroundJob, RuleAttackAssociation
from app.features.attack.attack_core import _extract_technique_ids
from tests_new.helpers.attack import link_technique, make_technique
from tests_new.helpers.db import count
from tests_new.helpers.inputs import BAD_IDS, BLANK, EMPTY, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests_new.helpers.rules import make_rule

BAD_TECHNIQUE_IDS = ["T99999999", "T1059.0001", "1059", "T", "TXXXX", "T1059;DROP", TOO_LONG,
                     BLANK, *INJECTIONS, *ODD_CHARACTERS]
BAD_TEXT = [EMPTY, BLANK, TOO_LONG, *INJECTIONS, *ODD_CHARACTERS]


@pytest.fixture(autouse=True)
def _no_job_side_effects():
    with mock.patch("app.features.notification.notification_core.create_job_notification"):
        yield


# ── Mapping a technique ───────────────────────────────────────────────────────

@pytest.mark.parametrize("technique_id", BAD_TECHNIQUE_IDS)
def test_add_a_malformed_technique_maps_nothing(technique_id, clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059")

    response = clients["owner"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": technique_id})

    assert 400 <= response.status_code < 500
    assert count(RuleAttackAssociation) == 0


@pytest.mark.parametrize("technique_id", [value for value in WRONG_TYPES if value])
def test_add_a_technique_id_of_the_wrong_type_is_refused(technique_id, clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059")

    response = clients["owner"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": technique_id})

    assert response.status_code == 400
    assert count(RuleAttackAssociation) == 0


@pytest.mark.parametrize("body", ["not json", "[1, 2]", '"T1059"', "42", "null"])
def test_add_technique_with_a_broken_body_is_refused(body, clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059")

    response = clients["owner"].post(f"/attack/rule/{rule.id}/add", data=body, content_type="application/json")

    assert response.status_code == 400
    assert count(RuleAttackAssociation) == 0


def test_add_technique_without_a_body_is_refused(clients, users):
    rule = make_rule(users.owner)

    response = clients["owner"].post(f"/attack/rule/{rule.id}/add")

    assert response.status_code == 400


@pytest.mark.parametrize("rule_id", [0, 2**31, 2**63])
def test_add_technique_to_a_bad_rule_id_is_not_found(rule_id, clients):
    make_technique("T1059")

    response = clients["admin"].post(f"/attack/rule/{rule_id}/add", json={"technique_id": "T1059"})

    assert response.status_code == 404
    assert count(RuleAttackAssociation) == 0


@pytest.mark.parametrize("rule_id", ["-1", "abc", "1;DROP"])
def test_add_technique_to_a_non_numeric_rule_id_is_not_found(rule_id, clients):
    response = clients["admin"].post(f"/attack/rule/{rule_id}/add", json={"technique_id": "T1059"})

    assert response.status_code == 404


@pytest.mark.parametrize("technique_id", ["T99999999", "%", "T1059%", "<script>", "' OR 1=1 --", "A" * 5000])
def test_remove_a_malformed_technique_removes_nothing(technique_id, clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))

    response = clients["owner"].delete(f"/attack/rule/{rule.id}/remove/{technique_id}")

    assert response.status_code < 500
    assert count(RuleAttackAssociation, rule_id=rule.id) == 1


@pytest.mark.parametrize("rule_id", [0, 2**31, 2**63])
def test_read_techniques_of_a_bad_rule_id_is_not_found(rule_id, clients):
    response = clients["anonymous"].get(f"/attack/rule/{rule_id}")

    assert response.status_code == 404


# ── Catalogue: search, listing, technique pages ───────────────────────────────

@pytest.mark.parametrize("query", BAD_TEXT + ["%", "_", "\\"])
def test_search_with_hostile_text_never_errors(query, clients):
    make_technique("T1059")

    response = clients["anonymous"].get("/attack/techniques/search", query_string={"q": query})

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


@pytest.mark.parametrize("limit", ["abc", "", "1.5", "-5", "0", str(2**63), "<script>"])
def test_search_with_a_bad_limit_never_errors(limit, clients):
    make_technique("T1059")

    response = clients["anonymous"].get("/attack/techniques/search", query_string={"q": "T1059", "limit": limit})

    assert response.status_code < 500


@pytest.mark.parametrize("tactic", BAD_TEXT)
def test_list_techniques_with_a_hostile_tactic_never_errors(tactic, clients):
    make_technique("T1059")

    response = clients["anonymous"].get("/attack/techniques", query_string={"tactic": tactic})

    assert response.status_code == 200


@pytest.mark.parametrize("technique_id", ["T99999999", "%", "<script>alert(1)</script>", "' OR 1=1 --",
                                          "{{7*7}}", "A" * 5000, "日本語"])
def test_unknown_technique_page_and_stats_are_not_found(technique_id, clients):
    make_technique("T1059")

    page = clients["anonymous"].get(f"/attack/technique/{technique_id}")
    stats = clients["anonymous"].get(f"/attack/technique/{technique_id}/stats")

    assert page.status_code == 404 and stats.status_code == 404


def test_technique_name_is_escaped_on_its_page(clients):
    make_technique("T1059", name="<script>alert('pwned')</script>")

    page = clients["anonymous"].get("/attack/technique/T1059").get_data(as_text=True)

    assert "<script>alert('pwned')</script>" not in page


@pytest.mark.parametrize("params", [
    {"rule_type": "<script>"}, {"tags": "' OR 1=1 --"}, {"author": TOO_LONG},
    {"attacks": "T99999999"}, {"search": "{{7*7}}"}, {"page": "abc"},
])
def test_technique_usage_with_hostile_filters_never_errors(params, clients, users):
    link_technique(make_rule(users.owner), make_technique("T1059"))

    response = clients["anonymous"].get("/attack/techniques/usage", query_string=params)

    assert response.status_code == 200


# ── Admin: technique table and jobs ───────────────────────────────────────────

@pytest.mark.parametrize("params", [
    {"page": "abc"}, {"per_page": "-1"}, {"page": str(2**63)}, {"per_page": "1e9"},
    {"sort_by": "password_hash"}, {"sort_dir": "'; DROP TABLE rule; --"},
    {"search": "%"}, {"search": "' OR 1=1 --"}, {"search": TOO_LONG}, {"tactic": '"'}, {"tactic": TOO_LONG},
    {"show_deprecated": "<script>"},
])
def test_admin_technique_table_with_bad_parameters_never_errors(params, clients):
    make_technique("T1059")

    response = clients["admin"].get("/attack/admin/techniques", query_string=params)

    assert response.status_code == 200
    assert isinstance(response.get_json()["techniques"], list)


def test_admin_technique_table_search_is_not_an_injection(clients):
    make_technique("T1059")

    data = clients["admin"].get("/attack/admin/techniques", query_string={"search": "' OR 1=1 --"}).get_json()

    assert data["total"] == 0


@pytest.mark.parametrize("body", ["not json", "[1, 2]", "42", "null"])
def test_trigger_parse_with_a_broken_body_never_errors(body, clients):
    response = clients["admin"].post("/attack/admin/trigger_parse", data=body, content_type="application/json")

    assert response.status_code < 500


@pytest.mark.parametrize("fmt", [12345, ["sigma"], {"a": 1}, True])
def test_trigger_parse_with_a_format_of_the_wrong_type_queues_nothing(fmt, clients):
    response = clients["admin"].post("/attack/admin/trigger_parse", json={"format": fmt})

    assert response.status_code == 400
    assert count(BackgroundJob) == 0


# ── Auto-parsing hostile rule content ─────────────────────────────────────────

@pytest.mark.parametrize("fmt", ["yara", "sigma", "suricata", "wazuh", "elastic", "splunk", "zeek", None])
@pytest.mark.parametrize("content", [EMPTY, TOO_LONG, "T" * 50_000, "attack." * 20_000, *INJECTIONS,
                                     *ODD_CHARACTERS, "mitre_attack = T99999999, T1059.0001"])
def test_extracting_techniques_from_hostile_content_never_errors(fmt, content):
    ids = _extract_technique_ids(fmt, content)

    assert isinstance(ids, list)
    assert "T99999999" not in ids


def test_auto_parse_never_maps_a_technique_outside_the_catalogue(clients):
    make_technique("T1059")
    content = ('rule hostile {\n    meta:\n        mitre_attack = "T1059, T9999, T1059.999, T99999999"\n'
               '    strings:\n        $a = "x"\n    condition:\n        $a\n}')

    clients["owner"].post("/rule/create_rule", data={
        "format": "yara", "title": "Hostile ATT&CK meta", "license": "MIT", "version": "1",
        "description": "", "source": "tests", "to_string": content})

    assert [a.technique_id for a in RuleAttackAssociation.query.all()] == ["T1059"]
    assert count(AttackTechnique) == 1
