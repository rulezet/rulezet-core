"""The rule editor's server side (/editor-api, app/features/editor): logged-in users only,
answers from this Rulezet (its compiler and its rules), never from rulezet.org."""
from tests_new.helpers.rules import make_rule, yara_rule

VALID = 'rule editor_ok { strings: $a = "abcd" condition: $a }'
BROKEN = 'rule editor_broken {\n  condition:\n    $missing\n}'


def test_anonymous_is_refused(clients):
    res = clients["anonymous"].post("/editor-api/validate", json={"format": "yara", "content": VALID})
    assert res.status_code == 401
    assert clients["anonymous"].get("/editor-api/rules?format=yara&q=x").status_code == 401
    assert clients["anonymous"].get("/editor-api/assets/rulezet-editor.js").status_code == 401


def test_validate_uses_rulezet_compiler(clients):
    ok = clients["user"].post("/editor-api/validate", json={"format": "yara", "content": VALID})
    assert ok.status_code == 200 and ok.json["valid"] is True
    bad = clients["user"].post("/editor-api/validate", json={"format": "yara", "content": BROKEN})
    assert bad.status_code == 200 and bad.json["valid"] is False
    assert bad.json["items"][0]["severity"] == "error"


def test_validate_unknown_format_is_404(clients):
    res = clients["user"].post("/editor-api/validate", json={"format": "not-a-format", "content": "x"})
    assert res.status_code == 404


def test_rule_lookup_reads_the_database(clients, users):
    rule = make_rule(users.owner, title="Editor_Lookup_Rule", to_string=yara_rule("Editor_Lookup_Rule"))
    found = clients["user"].get("/editor-api/rules?format=yara&q=Lookup")
    assert [r["name"] for r in found.json["results"]] == ["Editor_Lookup_Rule"]
    one = clients["user"].get("/editor-api/rules/Editor_Lookup_Rule?format=yara")
    assert one.status_code == 200 and one.json["uuid"] == rule.uuid
    assert clients["user"].get("/editor-api/rules/Nope?format=yara").status_code == 404


def test_deleted_rules_are_not_suggested(clients, users):
    rule = make_rule(users.owner, title="Editor_Deleted_Rule", to_string=yara_rule("Editor_Deleted_Rule"))
    rule.is_deleted = True
    from app import db
    db.session.commit()
    assert clients["user"].get("/editor-api/rules?format=yara&q=Editor_Deleted").json["results"] == []


def test_editor_assets_are_served(clients):
    res = clients["user"].get("/editor-api/assets/rulezet-editor.js")
    assert res.status_code == 200 and b"RulezetEditor" in res.data


def test_create_page_has_the_yara_editor_tab(clients):
    page = clients["user"].get("/rule/create_rule?tab=yara_editor")
    assert page.status_code == 200
    assert b"yara-editor-panel" in page.data


def test_rule_lookup_says_who_may_edit(clients, users):
    make_rule(users.owner, title="Editor_Owned_Rule", to_string=yara_rule("Editor_Owned_Rule"))
    assert clients["owner"].get("/editor-api/rules/Editor_Owned_Rule?format=yara").json["can_edit"] is True
    assert clients["admin"].get("/editor-api/rules/Editor_Owned_Rule?format=yara").json["can_edit"] is True
    assert clients["user"].get("/editor-api/rules/Editor_Owned_Rule?format=yara").json["can_edit"] is False


def test_rule_dependencies_for_the_edit_page(clients, users):
    from app.features.rule_relation.rule_relation_core import add_relation
    base = make_rule(users.user, title="Dep_Base", to_string=yara_rule("Dep_Base"))
    mid = make_rule(users.owner, title="Dep_Mid",
                    to_string='rule Dep_Mid { strings: $a = "m" condition: $a and Dep_Base }')
    top = make_rule(users.owner, title="Dep_Top",
                    to_string='rule Dep_Top { strings: $a = "t" condition: $a and Dep_Mid }')
    add_relation(mid.id, base.id, 'yara_condition_ref', source='auto')
    add_relation(top.id, mid.id, 'yara_condition_ref', source='auto')

    data = clients["owner"].get(f"/editor-api/yara/rules/{top.id}/dependencies").json
    assert data["rule"]["name"] == "Dep_Top" and data["rule"]["can_edit"] is True
    # needed ones first, in compile order; each says whether this user may edit it
    assert [(d["name"], d["can_edit"]) for d in data["dependencies"]] == [("Dep_Base", False), ("Dep_Mid", True)]
    assert clients["admin"].get(f"/editor-api/yara/rules/{top.id}/dependencies").json["dependencies"][0]["can_edit"] is True
    assert clients["anonymous"].get(f"/editor-api/yara/rules/{top.id}/dependencies").status_code == 401
    assert clients["owner"].get("/editor-api/yara/rules/999999/dependencies").status_code == 404
