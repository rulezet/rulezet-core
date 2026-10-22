"""Workspace -> bundle: the editor's folders and files become a bundle (job editor_yara_import
with a bundle), and a bundle opens back as a workspace."""
from app.core.db_class.bundle import Bundle, BundleNode
from app.features.jobs.job_worker import run_next_job
from tests_new.helpers.rules import make_rule

A = 'rule wb_a\n{\n    strings:\n        $a = "wb_a_marker"\n    condition:\n        $a\n}'
B = 'rule wb_b\n{\n    condition:\n        wb_a\n}'
C = 'rule wb_c\n{\n    strings:\n        $c = "wb_c_marker"\n    condition:\n        $c\n}'

TREE = [{"type": "folder", "name": "Workspace", "children": [
    {"type": "folder", "name": "apt", "children": [
        {"type": "file", "name": "family.yar", "rules": ["wb_a", "wb_b"]},
    ]},
    {"type": "file", "name": "single.yar", "rules": ["wb_c"]},
    {"type": "file", "name": "README.md", "content": "# notes"},
]}]


def payload(bundle, tree=TREE):
    return {"imports": [], "rules": [
        {"name": "wb_a", "text": A, "path": "Workspace/apt/family.yar", "imports": []},
        {"name": "wb_b", "text": B, "path": "Workspace/apt/family.yar", "imports": []},
        {"name": "wb_c", "text": C, "path": "Workspace/single.yar", "imports": []},
    ], "bundle": bundle, "tree": tree}


def run(app, client, body):
    start = client.post("/editor-api/yara/jobs", json=body)
    assert start.status_code == 202, start.json
    with app.app_context():
        run_next_job(app)
    return client.get(f"/editor-api/yara/jobs/{start.json['uuid']}").json


def shape(bundle_id):
    def walk(node):
        if node.node_type == "folder":
            return {node.name: [walk(c) for c in node.children]}
        return node.rule.title if node.rule_id else node.name
    roots = BundleNode.query.filter_by(bundle_id=bundle_id, parent_id=None).order_by(BundleNode.id).all()
    return [walk(n) for n in roots]


def test_create_bundle_from_the_workspace(app, clients, users):
    state = run(app, clients["user"], payload({"mode": "create", "name": "WB bundle", "public": False}))
    assert state["ok"] is True, state
    assert state["steps"][-1]["id"] == "bundle" and state["steps"][-1]["status"] == "ok"
    bundle = Bundle.query.filter_by(name="WB bundle").one()
    assert bundle.user_id == users.user.id and bundle.access is False
    assert shape(bundle.id) == [{"Workspace": [{"apt": [{"family": ["wb_a", "wb_b"]}]}, "wb_c", "README.md"]}]
    assert state["bundle"]["url"] == f"/bundle/detail/{bundle.id}"


def test_bundle_name_taken_is_refused_before_the_job(clients, users):
    clients["user"].post("/editor-api/yara/jobs", json=payload({"mode": "create", "name": "Dup"}))
    from app.features.bundle.bundle_core import create_bundle
    create_bundle({"name": "Taken"}, users.user)
    res = clients["user"].post("/editor-api/yara/jobs", json=payload({"mode": "create", "name": "Taken"}))
    assert res.status_code == 400 and "already have a bundle" in res.json["error"]


def test_update_someone_elses_bundle_is_refused(clients, users):
    from app.features.bundle.bundle_core import create_bundle
    other = create_bundle({"name": "Not mine"}, users.owner)
    res = clients["user"].post("/editor-api/yara/jobs", json=payload({"mode": "update", "bundle_id": other.id}))
    assert res.status_code == 400 and "may not edit this bundle" in res.json["error"]


def test_errors_create_neither_rules_nor_bundle(app, clients):
    body = payload({"mode": "create", "name": "Broken bundle"})
    body["rules"][2]["text"] = 'rule wb_c\n{\n    condition:\n        $nope\n}'
    state = run(app, clients["user"], body)
    assert state["ok"] is False
    assert Bundle.query.filter_by(name="Broken bundle").count() == 0
    assert state["steps"][-1]["status"] == "skipped"


def test_open_a_bundle_as_a_workspace_and_save_it_back(app, clients, users):
    run(app, clients["user"], payload({"mode": "create", "name": "Round trip"}))
    bundle = Bundle.query.filter_by(name="Round trip").one()
    ws = clients["user"].get(f"/editor-api/bundles/{bundle.id}").json
    assert ws["bundle"]["can_edit"] is True
    root = ws["tree"][0]
    files = {f["name"]: f for f in root["children"] if f["type"] == "file"}
    assert files["wb_c.yar"]["rule"]["can_edit"] is True and "wb_c_marker" in files["wb_c.yar"]["content"]
    assert files["README.md"]["content"] == "# notes"
    # someone else sees the rules as not editable (locked in the editor)
    other = clients["owner"].get(f"/editor-api/bundles/{bundle.id}").json
    assert other["bundle"]["can_edit"] is False
    # save back with a new layout
    tree = [{"type": "folder", "name": "Workspace", "children": [{"type": "file", "name": "all.yar", "rules": ["wb_a", "wb_b", "wb_c"]}]}]
    state = run(app, clients["user"], payload({"mode": "update", "bundle_id": bundle.id}, tree))
    assert state["ok"] is True
    assert shape(bundle.id) == [{"Workspace": [{"all": ["wb_a", "wb_b", "wb_c"]}]}]


def test_private_bundle_is_not_readable_by_others(app, clients):
    run(app, clients["user"], payload({"mode": "create", "name": "Secret", "public": False}))
    bundle = Bundle.query.filter_by(name="Secret").one()
    assert clients["owner"].get(f"/editor-api/bundles/{bundle.id}").status_code == 404


def test_workspace_page(clients):
    assert clients["user"].get("/editor/").status_code == 200
    assert clients["anonymous"].get("/editor/").status_code in (302, 401)


def test_bundle_page_offers_open_in_editor(clients, users):
    from app.features.bundle.bundle_core import create_bundle
    bundle = create_bundle({"name": "Shown"}, users.owner)
    page = clients["owner"].get(f"/bundle/detail/{bundle.id}")
    assert page.status_code == 200 and b"/editor/?bundle=" in page.data
    assert clients["user"].get(f"/bundle/detail/{bundle.id}").status_code == 200


def test_scenarios_for_admins(app, clients, users):
    make_rule(users.admin, title="sc_mine", to_string='rule sc_mine\n{\n    strings:\n        $a = "sc_mine_m"\n    condition:\n        $a\n}')
    make_rule(users.owner, title="sc_other", to_string='rule sc_other\n{\n    meta:\n        a = "x"\n    strings:\n        $a = "sc_other_m"\n    condition:\n        $a\n}')
    data = clients["admin"].get("/editor-api/yara/scenarios").json["scenarios"]
    by_id = {s["id"]: s for s in data}
    assert {"new", "syntax", "blocked", "unknown", "rulezet-dep", "exists", "update", "proposal", "locked", "unlock", "bundle", "mixed"} <= set(by_id)
    assert all(s["available"] for s in data)
    # each scenario's rules give the status it announces
    def plan(sid):
        rules = []
        for f in by_id[sid]["files"]:
            if f["path"].endswith(".yar"):
                import re
                for m in re.finditer(r"(?ms)^rule (\w+).*?^\}", f["content"]):
                    rules.append({"name": m.group(1), "text": m.group(0)})
        return {r["name"]: r["status"] for r in clients["admin"].post("/editor-api/yara/plan", json={"rules": rules}).json["rules"]}
    assert set(plan("new").values()) == {"new"}
    assert "error" in plan("syntax").values()
    assert set(plan("blocked").values()) == {"error", "blocked"}
    assert plan("update") == {"sc_mine": "update"}
    # an admin may edit every rule: someone else's rule is updated, and the scenario says so
    assert plan("proposal") == {"sc_other": "update"}
    assert "admin" in by_id["proposal"]["expect"]
    assert plan("exists") == {"sc_other": "exists"}
