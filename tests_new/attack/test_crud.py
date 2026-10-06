"""ATT&CK — layer 2: technique mappings, catalogue, coverage and jobs,
checked in the database. Only active rules ever count: a rule in the trash
keeps its mappings (for a restore) but disappears from every number."""
import json
from unittest import mock

import pytest

from app.core.db_class.db import AttackTechnique, BackgroundJob, RuleAttackAssociation, RuleUpdateHistory
from app.features.attack import attack_core
from app.features.jobs.job_handlers import handle_bulk_parse_attack_rules, handle_update_attack_data
from tests_new.helpers.attack import link_technique, make_technique, trash
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule, new_rule_form


@pytest.fixture(autouse=True)
def _no_job_side_effects():
    with mock.patch("app.features.notification.notification_core.create_job_notification"):
        yield


def _ids(items, key="technique_id"):
    return [item[key] for item in items]


def _heatmap_technique(data, technique_id):
    return next((t for tactic in data["tactics"] for t in tactic["techniques"] if t["id"] == technique_id), None)


# ── Mapping a technique on a rule ─────────────────────────────────────────────

def test_add_technique_stores_a_manual_mapping_by_the_user(clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059")

    response = clients["owner"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    assoc = RuleAttackAssociation.query.filter_by(rule_id=rule.id).one()
    assert response.get_json()["status"] == "created"
    assert (assoc.technique_id, assoc.user_id, assoc.source) == ("T1059", users.owner.id, "manual")


def test_add_technique_normalises_the_id(clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059.001")

    clients["owner"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": "  t1059.001 "})

    assert count(RuleAttackAssociation, rule_id=rule.id, technique_id="T1059.001") == 1


def test_add_technique_twice_keeps_one_mapping(clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059")
    clients["owner"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    response = clients["owner"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    assert response.get_json()["status"] == "already_exists"
    assert count(RuleAttackAssociation, rule_id=rule.id) == 1


def test_add_unknown_technique_is_not_found(clients, users):
    rule = make_rule(users.owner)

    response = clients["owner"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    assert response.status_code == 404
    assert count(RuleAttackAssociation) == 0


def test_add_technique_without_an_id_is_refused(clients, users):
    rule = make_rule(users.owner)

    response = clients["owner"].post(f"/attack/rule/{rule.id}/add", json={})

    assert response.status_code == 400


def test_add_technique_to_a_trashed_rule_is_not_found(clients, users):
    rule = trash(make_rule(users.owner), users.admin)
    make_technique("T1059")

    response = clients["admin"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    assert response.status_code == 404
    assert count(RuleAttackAssociation) == 0


def test_add_technique_to_an_unknown_rule_is_not_found(clients):
    make_technique("T1059")

    response = clients["admin"].post("/attack/rule/999999/add", json={"technique_id": "T1059"})

    assert response.status_code == 404
    assert count(RuleAttackAssociation) == 0


def test_add_technique_by_the_owner_leaves_no_contribution_trail(clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059")

    clients["owner"].post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    assert count(RuleUpdateHistory, rule_id=rule.id, change_type="metadata") == 0


def test_add_technique_by_a_tag_manager_is_recorded_in_the_rule_history(client_as, users):
    from tests_new.helpers.users import make_user_with_permission
    tagger = make_user_with_permission("rule.tag_any")
    rule = make_rule(users.owner)
    make_technique("T1059")

    client_as(tagger).post(f"/attack/rule/{rule.id}/add", json={"technique_id": "T1059"})

    assert count(RuleUpdateHistory, rule_id=rule.id, change_type="metadata") == 1


def test_remove_technique_deletes_only_that_mapping(clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))
    link_technique(rule, make_technique("T1105"))

    response = clients["owner"].delete(f"/attack/rule/{rule.id}/remove/t1059")

    assert response.get_json()["success"] is True
    assert [a.technique_id for a in RuleAttackAssociation.query.filter_by(rule_id=rule.id)] == ["T1105"]


def test_remove_a_technique_the_rule_does_not_have_reports_failure(clients, users):
    rule = make_rule(users.owner)
    make_technique("T1059")

    response = clients["owner"].delete(f"/attack/rule/{rule.id}/remove/T1059")

    assert response.status_code == 200 and response.get_json()["success"] is False


def test_remove_technique_from_a_trashed_rule_is_not_found(clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))
    trash(rule, users.admin)

    response = clients["admin"].delete(f"/attack/rule/{rule.id}/remove/T1059")

    assert response.status_code == 404
    assert count(RuleAttackAssociation, rule_id=rule.id) == 1


# ── Reading a rule's techniques ───────────────────────────────────────────────

def test_rule_techniques_are_listed_sorted_by_id(clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1105"))
    link_technique(rule, make_technique("T1059"))

    data = clients["anonymous"].get(f"/attack/rule/{rule.id}").get_json()

    assert _ids(data) == ["T1059", "T1105"]
    assert data[0]["name"] == "Command and Scripting Interpreter"


def test_techniques_of_a_trashed_rule_are_not_found(clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))
    trash(rule, users.admin)

    response = clients["anonymous"].get(f"/attack/rule/{rule.id}")

    assert response.status_code == 404


def test_techniques_of_an_unknown_rule_are_not_found(clients):
    response = clients["anonymous"].get("/attack/rule/999999")

    assert response.status_code == 404


# ── Catalogue ─────────────────────────────────────────────────────────────────

def test_list_techniques_hides_deprecated_ones(clients):
    make_technique("T1059")
    make_technique("T1068", deprecated=True)

    data = clients["anonymous"].get("/attack/techniques").get_json()

    assert _ids(data) == ["T1059"]


def test_list_techniques_filters_by_tactic(clients):
    make_technique("T1059", tactics=["execution"])
    make_technique("T1105", tactics=["command-and-control"])

    data = clients["anonymous"].get("/attack/techniques?tactic=command-and-control").get_json()

    assert _ids(data) == ["T1105"]


def test_list_techniques_by_tactic_finds_techniques_with_several_tactics(clients):
    make_technique("T1068", tactics=["privilege-escalation", "defense-evasion"])

    data = clients["anonymous"].get("/attack/techniques?tactic=defense-evasion").get_json()

    assert _ids(data) == ["T1068"]


def test_search_techniques_matches_id_and_name(clients):
    make_technique("T1059")
    make_technique("T1059.001", name="PowerShell")
    make_technique("T1105")

    by_id = clients["anonymous"].get("/attack/techniques/search?q=t1059").get_json()
    by_name = clients["anonymous"].get("/attack/techniques/search?q=powershell").get_json()

    assert _ids(by_id) == ["T1059", "T1059.001"]
    assert _ids(by_name) == ["T1059.001"]


def test_search_techniques_hides_deprecated_ones(clients):
    make_technique("T1068", deprecated=True)

    data = clients["anonymous"].get("/attack/techniques/search?q=T1068").get_json()

    assert data == []


def test_search_techniques_with_an_empty_query_returns_nothing(clients):
    make_technique("T1059")

    data = clients["anonymous"].get("/attack/techniques/search?q=").get_json()

    assert data == []


def test_search_techniques_caps_the_limit_at_50(clients):
    for n in range(60):
        make_technique(f"T{1000 + n}", name=f"Searchable {n}")

    data = clients["anonymous"].get("/attack/techniques/search?q=Searchable&limit=500").get_json()

    assert len(data) == 50


def test_catalogue_stats_count_only_active_rules(clients, users):
    technique = make_technique("T1059")
    make_technique("T1068", deprecated=True)
    link_technique(make_rule(users.owner), technique)
    link_technique(trash(make_rule(users.owner), users.admin), technique)

    stats = clients["anonymous"].get("/attack/stats").get_json()

    assert stats["total_techniques"] == 2 and stats["deprecated"] == 1
    assert stats["rules_covered"] == 1 and stats["total_assocs"] == 1


def test_technique_page_accepts_a_lowercase_id(clients):
    make_technique("T1059")

    response = clients["anonymous"].get("/attack/technique/t1059")

    assert response.status_code == 200


def test_unknown_technique_page_is_not_found(clients):
    response = clients["anonymous"].get("/attack/technique/T1059")

    assert response.status_code == 404


# ── Coverage — only active rules count ────────────────────────────────────────

def test_technique_usage_counts_only_active_rules(clients, users):
    technique = make_technique("T1059")
    link_technique(make_rule(users.owner), technique)
    link_technique(make_rule(users.owner), technique)
    link_technique(trash(make_rule(users.owner), users.admin), technique)

    data = clients["anonymous"].get("/attack/techniques/usage").get_json()

    assert data["techniques"] == [
        {"id": "T1059", "name": "Command and Scripting Interpreter", "tactic_keys": ["execution"], "count": 2}]


def test_technique_usage_follows_the_rule_filters(clients, users):
    technique = make_technique("T1059")
    link_technique(make_rule(users.owner, format="yara"), technique)
    link_technique(make_rule(users.owner, format="sigma"), technique)

    data = clients["anonymous"].get("/attack/techniques/usage?rule_type=sigma").get_json()

    assert data["techniques"][0]["count"] == 1


def test_heatmap_counts_only_active_rules(clients, users):
    technique = make_technique("T1059")
    active = make_rule(users.owner)
    link_technique(active, technique)
    link_technique(trash(make_rule(users.owner), users.admin), technique)

    data = clients["anonymous"].get("/attack/heatmap_data").get_json()

    entry = _heatmap_technique(data, "T1059")
    assert entry["count"] == 1 and entry["rules"][0]["id"] == active.id
    assert data["stats"]["total_rules"] == 1 and data["stats"]["rules_with_attack"] == 1


def test_heatmap_places_techniques_under_their_tactics(clients, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1105", tactics=["command-and-control", "execution"]))

    data = clients["anonymous"].get("/attack/heatmap_data").get_json()

    covered = {t["key"] for t in data["tactics"] if t["covered"]}
    assert covered == {"command-and-control", "execution"}
    assert data["stats"]["covered_tactics"] == 2 and data["stats"]["unique_techniques"] == 1


def test_heatmap_of_a_trash_only_technique_is_empty(clients, users):
    link_technique(trash(make_rule(users.owner), users.admin), make_technique("T1059"))

    data = clients["anonymous"].get("/attack/heatmap_data").get_json()

    assert _heatmap_technique(data, "T1059") is None
    assert data["stats"]["covered_tactics"] == 0


def test_technique_stats_count_only_active_rules(clients, users):
    technique = make_technique("T1059")
    make_technique("T1059.001")
    link_technique(make_rule(users.owner, format="yara"), technique)
    link_technique(make_rule(users.owner, format="sigma"), technique)
    link_technique(trash(make_rule(users.owner), users.admin), technique)

    data = clients["anonymous"].get("/attack/technique/T1059/stats").get_json()

    assert data["total_rules"] == 2 and data["sub_techniques"] == 1
    assert sorted(data["formats"]["categories"]) == ["sigma", "yara"]
    assert sum(data["over_time"]["series"][0]["values"]) == 2


def test_stats_of_an_unknown_technique_are_not_found(clients):
    response = clients["anonymous"].get("/attack/technique/T1059/stats")

    assert response.status_code == 404


def test_admin_technique_table_counts_only_active_rules(clients, users):
    technique = make_technique("T1059")
    link_technique(make_rule(users.owner), technique)
    link_technique(trash(make_rule(users.owner), users.admin), technique)

    data = clients["admin"].get("/attack/admin/techniques").get_json()

    assert data["techniques"][0]["rule_count"] == 1


def test_admin_technique_table_searches_filters_and_pages(clients):
    make_technique("T1059", tactics=["execution"])
    make_technique("T1105", tactics=["command-and-control"])
    make_technique("T1068", deprecated=True)
    for n in range(12):
        make_technique(f"T{2000 + n}", name=f"Filler {n}")

    by_search = clients["admin"].get("/attack/admin/techniques?search=t1105").get_json()
    by_tactic = clients["admin"].get("/attack/admin/techniques?tactic=command-and-control").get_json()
    with_deprecated = clients["admin"].get("/attack/admin/techniques?show_deprecated=true&per_page=10").get_json()
    page_2 = clients["admin"].get("/attack/admin/techniques?per_page=10&page=2").get_json()

    assert _ids(by_search["techniques"]) == ["T1105"]
    assert _ids(by_tactic["techniques"]) == ["T1105"]
    assert with_deprecated["total"] == 15 and with_deprecated["pages"] == 2
    assert page_2["page"] == 2 and len(page_2["techniques"]) == 4


def test_admin_analytics_count_only_active_rules(clients, users):
    technique = make_technique("T1059")
    link_technique(make_rule(users.owner), technique)
    link_technique(trash(make_rule(users.owner), users.admin), technique)

    data = clients["admin"].get("/attack/admin/analytics").get_json()

    assert data["top_techniques"] == [{"id": "T1059", "name": "Command and Scripting Interpreter", "count": 1}]
    execution = next(t for t in data["tactic_coverage"] if t["key"] == "execution")
    assert (execution["covered"], execution["total"], execution["rule_count"]) == (1, 1, 1)


def test_admin_analytics_ignore_a_trash_only_technique(clients, users):
    link_technique(trash(make_rule(users.owner), users.admin), make_technique("T1059"))

    data = clients["admin"].get("/attack/admin/analytics").get_json()

    assert data["top_techniques"] == []


def test_coverage_gaps_list_techniques_without_an_active_rule(clients, users):
    link_technique(make_rule(users.owner), make_technique("T1059"))
    link_technique(trash(make_rule(users.owner), users.admin), make_technique("T1105", tactics=["command-and-control"]))
    make_technique("T1068", deprecated=True)

    gaps = clients["admin"].get("/attack/admin/gaps").get_json()["gaps"]

    assert [(g["key"], _ids(g["techniques"])) for g in gaps] == [("command-and-control", ["T1105"])]


# ── Auto-parsing techniques from rule content ─────────────────────────────────

def _yara_with_attack(name, technique_ids):
    return (f'rule {name} {{\n    meta:\n        mitre_attack = "{technique_ids}"\n'
            f'    strings:\n        $a = "{name}"\n    condition:\n        $a\n}}')


def test_creating_a_rule_maps_the_techniques_found_in_its_content(clients):
    make_technique("T1059")
    form = new_rule_form(to_string=_yara_with_attack("auto_parsed", "T1059, T9999"))

    clients["owner"].post("/rule/create_rule", data=form)

    assocs = RuleAttackAssociation.query.all()
    assert [(a.technique_id, a.source) for a in assocs] == [("T1059", "auto")]


def _run(handler, job, app):
    handler(job, app)
    return reload(job)


def test_parse_job_maps_techniques_on_active_rules_only(clients, users, app):
    make_technique("T1059")
    make_technique("T1105")
    active = make_rule(users.owner, to_string=_yara_with_attack("active_rule", "T1059"))
    already = make_rule(users.owner, to_string=_yara_with_attack("already_mapped", "T1105"))
    link_technique(already, AttackTechnique.query.filter_by(technique_id="T1105").one(), users.owner)
    trashed = trash(make_rule(users.owner, to_string=_yara_with_attack("trashed_rule", "T1059")), users.admin)
    clients["admin"].post("/attack/admin/trigger_parse", json={})
    job = BackgroundJob.query.filter_by(job_type="bulk_parse_attack_rules").one()

    _run(handle_bulk_parse_attack_rules, job, app)

    assert [(a.technique_id, a.source) for a in RuleAttackAssociation.query.filter_by(rule_id=active.id)] == [
        ("T1059", "auto")]
    assert count(RuleAttackAssociation, rule_id=already.id) == 1
    assert count(RuleAttackAssociation, rule_id=trashed.id) == 0


def test_parse_job_can_be_limited_to_one_format(clients, users, app):
    make_technique("T1059")
    yara = make_rule(users.owner, to_string=_yara_with_attack("yara_rule", "T1059"))
    sigma = make_rule(users.owner, format="sigma", to_string="title: x\ntags:\n  - attack.t1059\n")
    clients["admin"].post("/attack/admin/trigger_parse", json={"format": "sigma"})
    job = BackgroundJob.query.filter_by(job_type="bulk_parse_attack_rules").one()

    _run(handle_bulk_parse_attack_rules, job, app)

    assert job.payload["format"] == "sigma"
    assert count(RuleAttackAssociation, rule_id=sigma.id) == 1
    assert count(RuleAttackAssociation, rule_id=yara.id) == 0


def test_parse_job_without_a_catalogue_maps_nothing(clients, users, app):
    make_rule(users.owner, to_string=_yara_with_attack("no_catalogue", "T1059"))
    clients["admin"].post("/attack/admin/trigger_parse", json={})
    job = BackgroundJob.query.filter_by(job_type="bulk_parse_attack_rules").one()

    _run(handle_bulk_parse_attack_rules, job, app)

    assert count(RuleAttackAssociation) == 0


# ── Refreshing the MITRE catalogue ────────────────────────────────────────────

def _stix(technique_id, name, *, tactics=("execution",), sub=False, revoked=False):
    return {
        "type": "attack-pattern",
        "name": name,
        "description": f"About {name}",
        "external_references": [{"source_name": "mitre-attack", "external_id": technique_id,
                                 "url": f"https://attack.mitre.org/techniques/{technique_id}"}],
        "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": t} for t in tactics],
        "x_mitre_is_subtechnique": sub,
        "revoked": revoked,
    }


@pytest.fixture
def local_cti(tmp_path):
    """The CTI submodule replaced by a tiny STIX bundle — never the network."""
    path = tmp_path / "enterprise-attack.json"

    def write(*objects):
        path.write_text(json.dumps({"type": "bundle", "objects": list(objects)}))

    with mock.patch.object(attack_core, "_LOCAL_CTI_PATH", path), \
            mock.patch("urllib.request.urlopen", side_effect=AssertionError("no network in tests")):
        yield write


def test_update_job_imports_the_catalogue(clients, app, local_cti):
    local_cti(
        _stix("T1059", "Command and Scripting Interpreter"),
        _stix("T1059.001", "PowerShell", sub=True),
        _stix("T1068", "Old technique", revoked=True),
        {"type": "intrusion-set", "name": "not a technique"},
    )
    clients["admin"].post("/attack/admin/trigger_update")
    job = BackgroundJob.query.filter_by(job_type="update_attack_data").one()

    job = _run(handle_update_attack_data, job, app)

    assert job.done == 1
    sub = AttackTechnique.query.filter_by(technique_id="T1059.001").one()
    assert sub.is_subtechnique and sub.parent_technique_id == "T1059"
    assert AttackTechnique.query.filter_by(technique_id="T1068").one().deprecated is True
    assert count(AttackTechnique) == 3


def test_update_job_updates_existing_techniques_in_place(clients, app, local_cti, users):
    technique = make_technique("T1059", name="Old name")
    rule = make_rule(users.owner)
    link_technique(rule, technique)
    local_cti(_stix("T1059", "New name", tactics=("execution", "persistence")))
    clients["admin"].post("/attack/admin/trigger_update")
    job = BackgroundJob.query.filter_by(job_type="update_attack_data").one()

    _run(handle_update_attack_data, job, app)

    refreshed = reload(technique)
    assert refreshed.name == "New name" and refreshed.tactic_keys == ["execution", "persistence"]
    assert count(AttackTechnique) == 1 and count(RuleAttackAssociation, rule_id=rule.id) == 1


def test_trigger_update_records_who_asked(clients, users):
    response = clients["admin"].post("/attack/admin/trigger_update")

    job = BackgroundJob.query.filter_by(job_type="update_attack_data").one()
    assert response.get_json()["job_id"] == job.id
    assert job.created_by == users.admin.id and job.status == "pending"
