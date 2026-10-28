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
    assert [s["status"] for s in state["steps"][:2] + state["steps"][3:]] == ["ok", "ok", "ok"]
    assert state["steps"][2]["status"] in ("skipped", "ok", "warning")    # samples: depends on the server
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


def with_id(payload, rule_id):
    payload["rules"][0]["id"] = rule_id
    return payload


def test_changed_rule_of_mine_is_updated(app, clients, users):
    mine = make_rule(users.user, title="ed_base", to_string=BASE, version="1.0")
    changed = BASE.replace("base_marker", "base_marker_v2")
    plan = clients["user"].post("/editor-api/yara/plan", json=with_id(body(changed), mine.id)).json
    assert plan["rules"][0]["status"] == "update"
    state = _run_job(app, clients["user"], with_id(body(changed), mine.id))
    assert state["ok"] is True and state["rules"][0]["status"] == "updated"
    db_rule = Rule.query.get(mine.id)
    assert "base_marker_v2" in db_rule.to_string and db_rule.version != "1.0"
    assert Rule.query.filter_by(title="ed_base").count() == 1


def test_changed_rule_of_someone_else_becomes_a_proposal(app, clients, users):
    from app.core.db_class.rule_proposal import RuleEditProposal
    other = make_rule(users.owner, title="ed_base", to_string=BASE)
    changed = BASE.replace("base_marker", "base_marker_v2")
    plan = clients["user"].post("/editor-api/yara/plan", json=with_id(body(changed), other.id)).json
    assert plan["rules"][0]["status"] == "proposal"
    state = _run_job(app, clients["user"], with_id(body(changed), other.id))
    assert state["ok"] is True and state["rules"][0]["status"] == "proposed"
    assert "base_marker_v2" not in Rule.query.get(other.id).to_string
    proposal = RuleEditProposal.query.filter_by(rule_id=other.id).one()
    assert "base_marker_v2" in proposal.proposed_content
    page = clients["user"].get(state["result_url"]).data.decode()
    assert "Edit proposals" in page


def test_new_rule_with_a_name_already_in_rulezet_is_blocked(clients, users):
    make_rule(users.user, title="ed_base", to_string=BASE)
    changed = BASE.replace("base_marker", "base_marker_v2")
    res = clients["user"].post("/editor-api/yara/import", json=body(changed))
    entry = res.json["rules"][0]
    assert entry["status"] == "error" and "already exists" in entry["errors"][0]["message"]
    assert Rule.query.filter_by(title="ed_base").count() == 1
    assert "base_marker_v2" not in Rule.query.filter_by(title="ed_base").one().to_string


def test_title_already_used_is_blocked(clients, users):
    make_rule(users.owner, title="ed taken title", to_string=BASE)
    payload = body(USES_BASE.replace("ed_base and ", ""))
    payload["rules"][0]["fields"] = {"title": "ed taken title"}
    entry = clients["user"].post("/editor-api/yara/plan", json=payload).json["rules"][0]
    assert entry["status"] == "error" and "already used" in entry["errors"][0]["message"]


# ── Fields panel (title, CVE, tags, ATT&CK...) ────────────────────────────────────────

def test_fields_definitions_and_suggestions(clients, users):
    from app import db
    from app.core.db_class.attack import AttackTechnique
    from tests_new.helpers.tags import make_tag
    db.session.add(AttackTechnique(technique_id="T1059", name="Command and Scripting Interpreter"))
    db.session.commit()
    make_tag(users.user, name="fields:test-family")

    defs = clients["user"].get("/editor-api/fields?format=yara").json["fields"]
    by_id = {d["id"]: d for d in defs}
    assert {"title", "description", "author", "license", "cve", "attack", "tags"} <= set(by_id)
    assert by_id["license"]["options"] and isinstance(by_id["license"]["options"][0], dict)   # Rulezet's licences
    assert by_id["cve"]["meta"]["key"] == "cve" and "title" not in [d.get("meta", {}).get("key") for d in defs]

    attack = clients["user"].get("/editor-api/fields/suggest?format=yara&field=attack&q=T105").json["results"]
    assert attack[0]["value"] == "T1059" and attack[0]["detail"] == "Command and Scripting Interpreter"
    tags = clients["user"].get("/editor-api/fields/suggest?format=yara&field=tags&q=test-fam").json["results"]
    assert tags and tags[0]["label"] == "fields:test-family"
    assert clients["anonymous"].get("/editor-api/fields?format=yara").status_code == 401


def test_created_rule_takes_the_fields(clients, users):
    from app import db
    from app.core.db_class.attack import AttackTechnique
    from tests_new.helpers.tags import make_tag
    db.session.add(AttackTechnique(technique_id="T1105", name="Ingress Tool Transfer"))
    db.session.commit()
    tag = make_tag(users.user, name="fields:created")
    payload = body(BASE)
    payload["rules"][0]["fields"] = {
        "title": "Base rule from the editor", "description": "Typed in the Fields panel", "version": "2.1",
        "cve": [{"value": "cve-2024-3094", "label": "CVE-2024-3094"}, {"value": "not-a-cve", "label": "x"}],
        "attack": [{"value": "T1105", "label": "T1105"}],
        "tags": [{"value": tag.id, "label": tag.name}],
        "unknown_field": "ignored",
    }
    res = clients["user"].post("/editor-api/yara/import", json=payload)
    assert res.json["ok"] is True
    rule = Rule.query.filter_by(title="Base rule from the editor").one()
    assert rule.description == "Typed in the Fields panel" and rule.version == "2.1"
    assert "CVE-2024-3094" in (rule.cve_id or "") and "not-a-cve" not in (rule.cve_id or "")
    from app.core.db_class.tag import RuleTagAssociation
    assert RuleTagAssociation.query.filter_by(rule_id=rule.id, tag_id=tag.id).count() == 1
    from app.features.attack.attack_core import get_techniques_for_rule
    assert [t["technique_id"] for t in get_techniques_for_rule(rule.id)] == ["T1105"]


def test_fields_browse_tags_and_tactics(clients, users):
    from app import db
    from app.core.db_class.attack import AttackTechnique
    from tests_new.helpers.tags import make_tag
    db.session.add(AttackTechnique(technique_id="T1027", name="Obfuscated Files or Information", tactic_keys=["defense-evasion"]))
    db.session.commit()
    tag = make_tag(users.user, name="browse-ns:value-a")
    tag.namespace = "browse-ns"
    db.session.commit()

    tactics = clients["user"].get("/editor-api/fields/browse?format=yara&field=attack").json["folders"]
    assert [f["id"] for f in tactics][:3] == ["reconnaissance", "resource-development", "initial-access"]
    evasion = next(f for f in tactics if f["id"] == "defense-evasion")
    assert evasion["count"] >= 1 and evasion["color"]
    items = clients["user"].get("/editor-api/fields/browse?format=yara&field=attack&path=defense-evasion").json["items"]
    assert any(i["value"] == "T1027" for i in items)

    folders = clients["user"].get("/editor-api/fields/browse?format=yara&field=tags").json["folders"]
    ns = next(f for f in folders if f["label"] == "browse-ns")
    from urllib.parse import quote
    page = clients["user"].get(f"/editor-api/fields/browse?format=yara&field=tags&path={quote(quote(ns['id'], safe=''), safe='')}").json
    assert any(i["label"] == "browse-ns:value-a" for i in page["items"])


def test_check_previews_every_field_of_a_new_rule(clients):
    text = ('rule ed_preview : family_x\n{\n    meta:\n        author = "Alice"\n        description = "From the meta, see CVE-2021-44228"\n'
            '        version = "1.3"\n    strings:\n        $a = "preview_marker"\n    condition:\n        $a\n}')
    payload = body(text)
    payload["rules"][0]["fields"] = {"title": "Preview title", "license": "MIT", "attack": [{"value": "T1059", "label": "T1059"}]}
    res = clients["user"].post("/editor-api/yara/plan", json=payload).json
    rows = {r["id"]: r for r in res["rules"][0]["preview"]}
    assert rows["title"] == {"id": "title", "label": "Title", "value": "Preview title", "origin": "panel"}
    assert rows["author"]["value"] == "Alice" and rows["author"]["origin"] == "rule"
    assert rows["license"]["value"] == "MIT" and rows["license"]["origin"] == "panel"
    assert rows["version"]["value"] == "1.3"
    assert rows["cve"]["value"] == ["CVE-2021-44228"] and rows["cve"]["origin"] == "rule"
    assert rows["attack"]["value"] == ["T1059"]
    assert rows["rule_tags"]["value"] == ["family_x"]
    assert rows["default_tags"]["value"]                     # tlp / pap from the setting
    assert Rule.query.filter_by(title="Preview title").count() == 0     # a check writes nothing


def test_fields_link_rules_and_take_tags_by_name(clients, users):
    from app.core.db_class.rule_relation import RuleRelation
    from app.core.db_class.tag import RuleTagAssociation
    from tests_new.helpers.tags import make_tag
    target = make_rule(users.owner, title="Link_Target", to_string=yara_rule("Link_Target"))
    tag = make_tag(users.user, name="fields:by-name")
    found = clients["user"].get("/editor-api/fields/suggest?format=yara&field=related&q=Link_Tar").json["results"]
    assert found[0]["value"] == target.id and found[0]["label"] == "Link_Target"
    payload = body(BASE)
    payload["rules"][0]["fields"] = {"title": "Linked from the editor",
                                     "related": [{"value": target.id, "label": "Link_Target", "kind": "variant_of"}, {"value": "x"}],
                                     "tags": [{"value": "fields:by-name", "label": "fields:by-name"}]}
    preview = {r["id"]: r for r in clients["user"].post("/editor-api/yara/plan", json=payload).json["rules"][0]["preview"]}
    assert preview["related"]["value"] == ["Link_Target (variant of)"]
    assert clients["user"].post("/editor-api/yara/import", json=payload).json["ok"] is True
    rule = Rule.query.filter_by(title="Linked from the editor").one()
    assert {(r.target_rule_id, r.relation_type) for r in RuleRelation.query.filter_by(source_rule_id=rule.id)} >= {(target.id, "variant_of")}
    assert RuleTagAssociation.query.filter_by(rule_id=rule.id, tag_id=tag.id).count() == 1
