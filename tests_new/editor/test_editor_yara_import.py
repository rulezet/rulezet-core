"""Several YARA rules from the editor: each one checked, then created and linked
(/editor-api/yara/plan and /editor-api/yara/import)."""
from app.core.db_class.rule import InvalidRuleModel, Rule
from app.core.db_class.rule_relation import RuleRelation
from tests_new.helpers.rules import make_rule, yara_rule

BASE = 'rule ed_base\n{\n    strings:\n        $a = "base_marker"\n    condition:\n        $a\n}'
USES_BASE = 'rule ed_uses_base\n{\n    strings:\n        $b = "other_marker"\n    condition:\n        ed_base and $b\n}'
BROKEN = 'rule ed_broken\n{\n    condition:\n        $missing\n}'
NEEDS_BROKEN = 'rule ed_needs_broken\n{\n    condition:\n        ed_broken\n}'
PE = 'rule ed_pe\n{\n    condition:\n        pe.is_dll()\n}'


def body(*rules, imports=()):
    import re
    return {"imports": list(imports),
            "rules": [{"name": re.search(r"rule (\w+)", r).group(1), "text": r} for r in rules]}


def links(rule_id):
    return {(r.target_rule_id, r.relation_type) for r in RuleRelation.query.filter_by(source_rule_id=rule_id)}


def test_plan_checks_each_rule_and_creates_nothing(clients):
    res = clients["user"].post("/editor-api/yara/plan", json=body(BASE, USES_BASE))
    assert res.json["ok"] is True
    status = {r["name"]: r["status"] for r in res.json["rules"]}
    assert status == {"ed_base": "new", "ed_uses_base": "new"}
    uses = next(r for r in res.json["rules"] if r["name"] == "ed_uses_base")
    assert uses["depends_on"] == [{"name": "ed_base", "where": "document"}]
    assert Rule.query.filter(Rule.title.in_(["ed_base", "ed_uses_base"])).count() == 0


def test_import_creates_every_rule_linked_to_what_it_needs(clients):
    res = clients["user"].post("/editor-api/yara/import", json=body(USES_BASE, BASE))
    assert res.status_code == 200 and res.json["created"] == 2
    base = Rule.query.filter_by(title="ed_base").one()
    uses = Rule.query.filter_by(title="ed_uses_base").one()
    assert (base.id, "yara_condition_ref") in links(uses.id)


def test_existing_rule_is_reused_and_linked(clients, users):
    other = make_rule(users.owner, title="ed_base", to_string=BASE)
    res = clients["user"].post("/editor-api/yara/import", json=body(BASE, USES_BASE))
    assert res.status_code == 200
    by_name = {r["name"]: r for r in res.json["rules"]}
    assert by_name["ed_base"]["status"] == "exists"
    assert by_name["ed_base"]["existing"]["id"] == other.id
    uses = Rule.query.filter_by(title="ed_uses_base").one()
    assert (other.id, "yara_condition_ref") in links(uses.id)
    assert Rule.query.filter_by(title="ed_base").count() == 1


def test_dependency_found_in_rulezet_only(clients, users):
    other = make_rule(users.owner, title="ed_base", to_string=BASE)
    res = clients["user"].post("/editor-api/yara/plan", json=body(USES_BASE))
    entry = res.json["rules"][0]
    assert entry["status"] == "new"
    assert entry["depends_on"] == [{"name": "ed_base", "where": "rulezet", "id": other.id,
                                    "title": "ed_base", "url": f"/rule/detail_rule/{other.id}"}]


def test_one_error_creates_nothing_and_no_bad_rule(clients):
    bad_before = InvalidRuleModel.query.count()
    res = clients["user"].post("/editor-api/yara/import", json=body(BASE, BROKEN, NEEDS_BROKEN))
    assert res.status_code == 409
    by_name = {r["name"]: r for r in res.json["rules"]}
    assert by_name["ed_broken"]["status"] == "error"
    assert by_name["ed_broken"]["errors"][0]["line"] in (4, 5)   # YARA reports the end of the condition
    assert by_name["ed_needs_broken"]["status"] == "blocked"
    assert by_name["ed_base"]["status"] == "new"
    assert Rule.query.filter(Rule.title.like("ed_%")).count() == 0
    assert InvalidRuleModel.query.count() == bad_before


def test_unknown_dependency_is_an_error(clients):
    res = clients["user"].post("/editor-api/yara/plan", json=body(USES_BASE))
    entry = res.json["rules"][0]
    assert entry["status"] == "error"
    assert "ed_base" in entry["errors"][0]["message"]


def test_rule_keeps_only_the_imports_it_uses(clients):
    res = clients["user"].post("/editor-api/yara/import", json=body(PE, BASE, imports=["pe", "math"]))
    assert res.status_code == 200
    pe_rule = Rule.query.filter_by(title="ed_pe").one()
    assert pe_rule.to_string.startswith('import "pe"')
    assert "math" not in pe_rule.to_string
    assert "import" not in Rule.query.filter_by(title="ed_base").one().to_string


def test_duplicate_name_in_document(clients):
    res = clients["user"].post("/editor-api/yara/plan", json=body(BASE, BASE.replace("base_marker", "x2")))
    assert res.json["ok"] is False
    assert res.json["rules"][1]["status"] == "error"


def test_anonymous_cannot_plan_or_import(clients):
    assert clients["anonymous"].post("/editor-api/yara/plan", json=body(BASE)).status_code == 401
    assert clients["anonymous"].post("/editor-api/yara/import", json=body(BASE)).status_code == 401


def test_result_page_lists_created_and_reused_rules(clients, users):
    other = make_rule(users.owner, title="ed_base", to_string=BASE)
    res = clients["user"].post("/editor-api/yara/import", json=body(BASE, USES_BASE))
    url = res.json["result_url"]
    assert "created=" in url and f"reused={other.id}" in url
    page = clients["user"].get(url)
    assert page.status_code == 200
    html = page.data.decode()
    assert "ed_uses_base" in html and "ed_base" in html
    assert "1 created" in html and "1 already in Rulezet" in html and "1 dependency link" in html
    assert clients["anonymous"].get(url).status_code in (302, 401)


def _run_job(app, client, payload):
    from app.features.jobs.job_worker import run_next_job
    start = client.post("/editor-api/yara/jobs", json=payload)
    assert start.status_code == 202
    with app.app_context():
        run_next_job(app)
    return client.get(f"/editor-api/yara/jobs/{start.json['uuid']}").json


def test_job_checks_then_creates(app, clients):
    state = _run_job(app, clients["user"], body(BASE, USES_BASE))
    assert state["status"] == "done" and state["ok"] is True
    assert [s["status"] for s in state["steps"]] == ["ok", "ok", "skipped", "ok"]
    assert {r["name"] for r in state["rules"] if r["status"] == "created"} == {"ed_base", "ed_uses_base"}
    assert state["result_url"].startswith("/editor/import-result?")
    assert "text" not in state["rules"][0]


def test_job_with_an_error_creates_nothing(app, clients):
    bad_before = InvalidRuleModel.query.count()
    state = _run_job(app, clients["user"], body(BASE, BROKEN))
    assert state["status"] == "done" and state["ok"] is False
    assert [s["status"] for s in state["steps"]] == ["ok", "error", "skipped", "skipped"]
    assert Rule.query.filter(Rule.title.like("ed_%")).count() == 0
    assert InvalidRuleModel.query.count() == bad_before


def test_job_state_is_private(app, clients):
    start = clients["user"].post("/editor-api/yara/jobs", json=body(BASE))
    assert clients["owner"].get(f"/editor-api/yara/jobs/{start.json['uuid']}").status_code == 404


def test_changed_rule_of_mine_is_updated(app, clients, users):
    mine = make_rule(users.user, title="ed_base", to_string=BASE, version="1.0")
    changed = BASE.replace("base_marker", "base_marker_v2")
    plan = clients["user"].post("/editor-api/yara/plan", json=body(changed)).json
    assert plan["rules"][0]["status"] == "update"
    state = _run_job(app, clients["user"], body(changed))
    assert state["ok"] is True and state["rules"][0]["status"] == "updated"
    db_rule = Rule.query.get(mine.id)
    assert "base_marker_v2" in db_rule.to_string and db_rule.version != "1.0"
    assert Rule.query.filter_by(title="ed_base").count() == 1


def test_changed_rule_of_someone_else_becomes_a_proposal(app, clients, users):
    from app.core.db_class.rule_proposal import RuleEditProposal
    other = make_rule(users.owner, title="ed_base", to_string=BASE)
    changed = BASE.replace("base_marker", "base_marker_v2")
    plan = clients["user"].post("/editor-api/yara/plan", json=body(changed)).json
    assert plan["rules"][0]["status"] == "proposal"
    state = _run_job(app, clients["user"], body(changed))
    assert state["ok"] is True and state["rules"][0]["status"] == "proposed"
    assert "base_marker_v2" not in Rule.query.get(other.id).to_string
    proposal = RuleEditProposal.query.filter_by(rule_id=other.id).one()
    assert "base_marker_v2" in proposal.proposed_content
    page = clients["user"].get(state["result_url"]).data.decode()
    assert "Edit proposals" in page
