"""Sigma in the rule editor: validation of each YAML document, the Fields panel's definition, and
the Create pipeline (/editor-api/sigma/plan, /import, /jobs): checked as Rulezet checks a Sigma
rule (schema + pySigma), then created, updated (owner) or proposed (someone else's rule)."""
from app.core.db_class.rule import InvalidRuleModel, Rule
from app.core.db_class.rule_proposal import RuleEditProposal
from tests_new.helpers.rules import make_rule

ID_A = "929a690e-bef0-4204-a928-ef5e620d6fcc"
ID_B = "0f0b2b8a-0f0e-4c63-9a5c-3d6b1c2e4f10"


def sigma(title, uid=ID_A, condition="selection", image="\\evil.exe"):
    return (f"title: {title}\nid: {uid}\nstatus: test\ndescription: Editor test\nauthor: Tester\ndate: 2026-01-02\n"
            f"logsource:\n    category: process_creation\n    product: windows\n"
            f"detection:\n    selection:\n        Image|endswith: '{image}'\n    condition: {condition}\nlevel: medium\n")


def body(*texts):
    import yaml
    return {"rules": [{"name": yaml.safe_load(t)["title"], "text": t} for t in texts]}


def test_validate_checks_each_document_and_places_errors_on_its_rule(clients):
    good = sigma("Ed sigma one")
    ok = clients["user"].post("/editor-api/validate", json={"format": "sigma", "content": good})
    assert ok.status_code == 200 and ok.json["valid"] is True
    two = good + "---\n" + sigma("Ed sigma two", ID_B, condition="nothing")
    bad = clients["user"].post("/editor-api/validate", json={"format": "sigma", "content": two})
    assert bad.json["valid"] is False
    assert {i["line"] for i in bad.json["items"] if i["severity"] == "error"} == {good.count("\n") + 2}


def test_fields_panel_has_sigma_fields(clients):
    res = clients["user"].get("/editor-api/fields?format=sigma")
    assert res.status_code == 200
    by_id = {f["id"]: f for f in res.json["fields"]}
    assert by_id["attack"]["meta"]["key"] == "mitre_attack"
    assert by_id["original_uuid"]["meta"]["key"] == "id"
    assert "meta" not in by_id["tags"]


def test_plan_new_rules_and_errors_create_nothing(clients):
    res = clients["user"].post("/editor-api/sigma/plan",
                               json=body(sigma("Ed sigma one"), sigma("Ed sigma two", ID_B, condition="nothing")))
    by_name = {r["name"]: r for r in res.json["rules"]}
    assert by_name["Ed sigma one"]["status"] == "new"
    assert by_name["Ed sigma one"]["preview"]
    assert by_name["Ed sigma two"]["status"] == "error"
    assert res.json["ok"] is False
    assert Rule.query.filter(Rule.title.like("Ed sigma%")).count() == 0


def test_import_creates_sigma_rules_and_never_a_bad_one(clients):
    bad_before = InvalidRuleModel.query.count()
    refused = clients["user"].post("/editor-api/sigma/import",
                                   json=body(sigma("Ed sigma one"), sigma("Ed sigma two", ID_B, condition="nothing")))
    assert refused.status_code == 409
    assert Rule.query.filter(Rule.title.like("Ed sigma%")).count() == 0
    assert InvalidRuleModel.query.count() == bad_before

    res = clients["user"].post("/editor-api/sigma/import", json=body(sigma("Ed sigma one"), sigma("Ed sigma two", ID_B)))
    assert res.status_code == 200 and res.json["created"] == 2
    rule = Rule.query.filter_by(title="Ed sigma one").one()
    assert rule.format == "sigma" and rule.original_uuid == ID_A and rule.author == "Tester"
    assert "/editor/import-result?" in res.json["result_url"]


def test_same_content_exists_same_title_other_content_is_an_error(clients, users):
    text = sigma("Ed sigma one")
    other = make_rule(users.owner, format="sigma", title="Ed sigma one", to_string=text, original_uuid=ID_A)
    same = clients["user"].post("/editor-api/sigma/plan", json=body(text)).json["rules"][0]
    assert same["status"] == "exists" and same["existing"]["id"] == other.id
    clash = clients["user"].post("/editor-api/sigma/plan", json=body(sigma("Ed sigma one", ID_B, image="\\other.exe"))).json["rules"][0]
    assert clash["status"] == "error"


def _run_job(app, client, payload):
    from app.features.jobs.job_worker import run_next_job
    start = client.post("/editor-api/sigma/jobs", json=payload)
    assert start.status_code == 202
    assert [s["id"] for s in start.json["steps"]] == ["existing", "syntax", "external", "samples", "create"]
    with app.app_context():
        run_next_job(app)
    return client.get(f"/editor-api/sigma/jobs/{start.json['uuid']}").json


def test_job_checks_then_creates(app, clients):
    state = _run_job(app, clients["user"], body(sigma("Ed sigma job")))
    assert state["status"] == "done" and state["ok"] is True
    by_id = {s["id"]: s["status"] for s in state["steps"]}
    assert [by_id[k] for k in ("existing", "syntax", "create")] == ["ok", "ok", "ok"]
    assert by_id["samples"] in ("skipped", "ok", "warning")              # depends on the server
    assert Rule.query.filter_by(title="Ed sigma job", format="sigma").count() == 1


def test_changed_rule_of_mine_is_updated_someone_elses_is_proposed(app, clients, users):
    mine = make_rule(users.user, format="sigma", title="Ed sigma mine", to_string=sigma("Ed sigma mine"), original_uuid=ID_A)
    state = _run_job(app, clients["user"], body(sigma("Ed sigma mine", image="\\changed.exe")))
    assert state["ok"] is True and state["updated"] == 1
    assert "changed.exe" in Rule.query.get(mine.id).to_string

    theirs = make_rule(users.owner, format="sigma", title="Ed sigma theirs", to_string=sigma("Ed sigma theirs", ID_B), original_uuid=ID_B)
    state = _run_job(app, clients["user"], body(sigma("Ed sigma theirs", ID_B, image="\\changed.exe")))
    assert state["ok"] is True and state["proposed"] == 1
    assert "changed.exe" not in Rule.query.get(theirs.id).to_string
    assert RuleEditProposal.query.filter_by(rule_id=theirs.id).count() == 1


def test_anonymous_and_unknown_format_are_refused(clients):
    assert clients["anonymous"].post("/editor-api/sigma/plan", json=body(sigma("x"))).status_code == 401
    assert clients["user"].post("/editor-api/suricata/plan", json={"rules": []}).status_code == 404


def test_external_checks_for_sigma(clients):
    """SIEM conversion and SigmaHQ conventions answer for a Sigma document (advice only)."""
    text = sigma("Ed sigma checks").replace("Image|endswith: '\\evil.exe'", "Image|endswith:\n            - '\\evil.exe'")
    res = clients["user"].post("/editor-api/external-checks", json={"format": "sigma", "text": text, "tools": ["siem", "sigmahq"]})
    assert res.status_code == 200
    siem, hq = res.json["results"]["siem"], res.json["results"]["sigmahq"]
    assert siem["available"] and any(o["label"] == "Splunk SPL" and o["ok"] and "evil.exe" in o["text"] for o in siem["outputs"])
    assert any("one value" in w["message"] for w in hq["warnings"])
    assert any(i["message"].startswith("SigmaHQ file name: proc_creation_win_") for i in hq.get("infos", []))   # a note, not a warning


CORR = ("title: Ed sigma many\nid: 1f0b2b8a-0f0e-4c63-9a5c-3d6b1c2e4f10\nstatus: test\ncorrelation:\n    type: event_count\n"
        "    rules:\n        - ed_base\n    group-by:\n        - User\n    timespan: 5m\n    condition:\n        gte: 10\nlevel: high\n")


def test_correlation_rule_with_the_rule_it_names(clients):
    """A correlation rule is refused alone, accepted with the rule it names (document or Rulezet),
    created after it and linked (sigma_correlation)."""
    from app.core.db_class.rule_relation import RuleRelation
    base = sigma("Ed sigma base").replace("status: test", "name: ed_base\nstatus: test")
    alone = clients["user"].post("/editor-api/validate", json={"format": "sigma", "content": CORR}).json
    assert alone["valid"] is False and "ed_base" in alone["items"][0]["message"]
    both = clients["user"].post("/editor-api/validate", json={"format": "sigma", "content": base + "---\n" + CORR}).json
    assert both["valid"] is True
    res = clients["user"].post("/editor-api/sigma/import", json=body(CORR, base))
    assert res.status_code == 200 and res.json["created"] == 2
    b = Rule.query.filter_by(title="Ed sigma base").one()
    c = Rule.query.filter_by(title="Ed sigma many").one()
    assert RuleRelation.query.filter_by(source_rule_id=c.id, target_rule_id=b.id, relation_type="sigma_correlation").count() == 1
    again = clients["user"].post("/editor-api/validate", json={"format": "sigma", "content": CORR.replace("Ed sigma many", "Ed sigma other").replace("1f0b", "2f0b")}).json
    assert again["valid"] is True                       # the named rule is now in Rulezet
