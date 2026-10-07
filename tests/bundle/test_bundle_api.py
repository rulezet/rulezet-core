"""REST API for bundles (/api/bundle/public/*, /api/bundle/private/*).

Covers the backward-compatible fixes on the historical routes (same names,
same parameters, same response fields — only optional additions), the new
routes, the API-key identity (logs / history name the key's owner, not
"System") and, for every private route, that nothing works without a valid
key."""

import io
import json
import zipfile

import pytest

from app import db
from app.core.db_class.db import ActivityLog, Bundle, BundleNode, BundleRuleAssociation

from bundle_helpers import D, F, R, as_anonymous, fresh, login, make_bundle, make_rule, owner, other, admin, save_structure, tag

OWNER_KEY = "api_key_user_rule"   # t@t.t — owner of the bundles below
OTHER_KEY = "user_api_key"        # neo@admin.admin — a second normal user
ADMIN_KEY = "admin_api_key"

H_OWNER = {"X-API-KEY": OWNER_KEY}
H_OTHER = {"X-API-KEY": OTHER_KEY}
H_ADMIN = {"X-API-KEY": ADMIN_KEY}


def _rule(title="Alpha rule"):
    return make_rule(title, "yara", "rule %s { condition: true }" % title.replace(" ", "_"))


def _tree(bundle_id):
    """{rule_id: folder name} of every rule node, + custom file names."""
    db.session.expire_all()
    nodes = BundleNode.query.filter_by(bundle_id=bundle_id).all()
    by_id = {n.id: n for n in nodes}
    rules = {n.rule_id: (by_id[n.parent_id].name if n.parent_id else None) for n in nodes if n.rule_id}
    files = {n.name for n in nodes if n.node_type == "file" and not n.rule_id}
    return rules, files


def _assoc(bundle_id):
    db.session.expire_all()
    return {a.rule_id for a in BundleRuleAssociation.query.filter_by(bundle_id=bundle_id)}


def _last_log(action):
    db.session.expire_all()
    return ActivityLog.query.filter_by(action=action).order_by(ActivityLog.id.desc()).first()


# ── Every private route refuses a request without a valid API key ────────────

PRIVATE_CALLS = [
    ("post", "/api/bundle/private/create", {"json": {"name": "x"}}),
    ("get",  "/api/bundle/private/add_rule_bundle", {"query_string": {"rule_id": 1, "bundle_id": 1, "description": "d"}}),
    ("post", "/api/bundle/private/add_rule_bundle", {"json": {"rule_id": 1, "bundle_id": 1, "description": "d"}}),
    ("post", "/api/bundle/private/add_rules_bundle", {"json": {"bundle_id": 1, "rule_ids": [1]}}),
    ("get",  "/api/bundle/private/remove_rule_bundle", {"query_string": {"rule_id": 1, "bundle_id": 1}}),
    ("post", "/api/bundle/private/remove_rule_bundle", {"json": {"rule_id": 1, "bundle_id": 1}}),
    ("post", "/api/bundle/private/edit_bundle/1", {"json": {"name": "hacked"}}),
    ("post", "/api/bundle/private/1/structure", {"json": {"structure": []}}),
    ("post", "/api/bundle/private/delete_bundle/1", {}),
    ("get",  "/api/bundle/private/my_bundles", {}),
]


@pytest.mark.parametrize("method,url,kwargs", PRIVATE_CALLS)
def test_private_routes_need_a_valid_api_key(client, app, method, url, kwargs):
    with app.app_context():
        b = make_bundle("Target")
        assert b.id == 1
        for headers in ({}, {"X-API-KEY": "not-a-real-key"}):
            as_anonymous()
            resp = getattr(client, method)(url, headers=headers, **kwargs)
            assert resp.status_code == 403, (url, headers, resp.status_code)
        # nothing happened
        b = fresh(Bundle, 1)
        assert b is not None and b.name == "Target"
        assert Bundle.query.count() == 1


# ── API-key identity ─────────────────────────────────────────────────────────

def test_api_actions_are_logged_with_the_key_owner_not_system(client, app):
    with app.app_context():
        resp = client.post("/api/bundle/private/create", json={"name": "Mine"}, headers=H_OWNER)
        assert resp.status_code == 200
        log = _last_log("bundle.create")
        assert log.user_id == owner().id
        assert log.extra.get("actor_source") == "api_key"
        assert log.to_json()["actor_name"] not in ("System", "Anonymous")


def test_api_key_identity_does_not_leak_into_the_next_request(client, app):
    with app.app_context():
        b = make_bundle("Private one", public=False)
        assert client.get("/api/bundle/private/my_bundles", headers=H_OWNER).status_code == 200
        # next call has no key: must be anonymous again → private bundle hidden
        as_anonymous()
        assert client.get(f"/api/bundle/public/detail/{b.id}").status_code == 403


# ── create ───────────────────────────────────────────────────────────────────

def test_create_keeps_its_contract_and_returns_the_uuid(client, app):
    with app.app_context():
        resp = client.post("/api/bundle/private/create",
                           json={"name": "Plain", "description": "d", "public": False}, headers=H_OWNER)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["message"] == "Bundle created successfully"
        assert isinstance(data["bundle_id"], int) and data["uuid"]
        b = fresh(Bundle, data["bundle_id"])
        assert b.uuid == data["uuid"] and b.access is False and b.user_id == owner().id


def test_create_with_rules_tags_vulnerabilities_and_folder(client, app):
    with app.app_context():
        r1, r2 = _rule("One"), _rule("Two")
        tag("tlp:green")
        resp = client.post("/api/bundle/private/create", headers=H_OWNER, json={
            "name": "Full", "tags": ["TLP:GREEN"], "vulnerabilities": ["CVE-2024-0001"],
            "rule_ids": [r1.id], "rule_uuids": [r2.uuid], "folder": "detections/yara",
        })
        data = resp.get_json()
        assert resp.status_code == 200 and data["rules_added"] == 2
        bid = data["bundle_id"]
        assert _assoc(bid) == {r1.id, r2.id}
        rules, _ = _tree(bid)
        assert rules == {r1.id: "yara", r2.id: "yara"}
        detail = client.get(f"/api/bundle/public/detail/{data['uuid']}").get_json()["bundle"]
        assert detail["tags"] == ["tlp:green"]
        assert detail["vulnerability_identifiers"] == ["CVE-2024-0001"]


def test_create_rejects_unknown_tags_and_rules_before_creating_anything(client, app):
    with app.app_context():
        resp = client.post("/api/bundle/private/create", json={"name": "x", "tags": ["nope:nope"]}, headers=H_OWNER)
        assert resp.status_code == 400 and resp.get_json()["unknown_tags"] == ["nope:nope"]
        resp = client.post("/api/bundle/private/create", json={"name": "x", "rule_ids": [99999]}, headers=H_OWNER)
        assert resp.status_code == 400 and resp.get_json()["missing_rules"] == ["99999"]
        resp = client.post("/api/bundle/private/create", json={"name": "x", "rule_ids": "nope"}, headers=H_OWNER)
        assert resp.status_code == 400
        resp = client.post("/api/bundle/private/create", json={"name": "x", "public": "yes"}, headers=H_OWNER)
        assert resp.status_code == 400
        assert Bundle.query.count() == 0


# ── add_rule_bundle ──────────────────────────────────────────────────────────

def test_add_rule_get_also_places_the_rule_in_the_tree(client, app):
    with app.app_context():
        b, r = make_bundle(), _rule()
        resp = client.get("/api/bundle/private/add_rule_bundle", headers=H_OWNER,
                          query_string={"rule_id": r.id, "bundle_id": b.id, "description": "d"})
        assert resp.status_code == 200 and resp.get_json()["message"] == "Rule added!"
        assert _assoc(b.id) == {r.id}
        assert _tree(b.id)[0] == {r.id: "Unsorted"}
        # visible in the structure + in the structure ZIP
        s = client.get(f"/api/bundle/public/{b.id}/structure").get_json()["structure"]
        assert s[0]["name"] == "Unsorted" and s[0]["children"][0]["rule_id"] == r.id
        log = _last_log("bundle.rule_added")
        assert log.user_id == owner().id


def test_add_rule_post_by_uuids_into_a_folder_and_idempotent(client, app):
    with app.app_context():
        b, r = make_bundle(), _rule()
        body = {"rule_uuid": r.uuid, "bundle_uuid": b.uuid, "description": "d", "folder": "yara"}
        assert client.post("/api/bundle/private/add_rule_bundle", json=body, headers=H_OWNER).status_code == 200
        assert client.post("/api/bundle/private/add_rule_bundle", json=body, headers=H_OWNER).status_code == 200
        assert _tree(b.id)[0] == {r.id: "yara"}
        assert BundleNode.query.filter_by(bundle_id=b.id, rule_id=r.id).count() == 1


def test_add_rule_errors(client, app):
    with app.app_context():
        b, r = make_bundle(), _rule()
        url = "/api/bundle/private/add_rule_bundle"
        # unknown rule: 404 (was a 500)
        resp = client.get(url, headers=H_OWNER, query_string={"rule_id": 99999, "bundle_id": b.id, "description": "d"})
        assert resp.status_code == 404 and resp.get_json()["message"] == "Rule not found"
        # deleted rule: 404
        r.is_deleted = True
        db.session.commit()
        resp = client.get(url, headers=H_OWNER, query_string={"rule_id": r.id, "bundle_id": b.id, "description": "d"})
        assert resp.status_code == 404
        # not the owner: 401 (unchanged contract), admin: ok
        r2 = _rule("Other")
        q = {"rule_id": r2.id, "bundle_id": b.id, "description": "d"}
        assert client.get(url, headers=H_OTHER, query_string=q).status_code == 403
        assert client.get(url, headers=H_ADMIN, query_string=q).status_code == 200
        assert _assoc(b.id) == {r2.id}


# ── add_rules_bundle (bulk) ──────────────────────────────────────────────────

def test_add_rules_bulk(client, app):
    with app.app_context():
        b = make_bundle()
        r1, r2, r3 = _rule("A"), _rule("B"), _rule("C")
        url = "/api/bundle/private/add_rules_bundle"
        resp = client.post(url, headers=H_OWNER, json={"bundle_id": b.id, "rule_ids": [r1.id, r2.id]})
        assert resp.get_json()["added"] == 2
        resp = client.post(url, headers=H_OWNER, json={
            "bundle_uuid": b.uuid, "rule_ids": [r1.id], "rule_uuids": [r3.uuid, "missing-uuid"], "folder": "c"})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["added"] == 1 and data["already_present"] == 1 and data["missing_rules"] == ["missing-uuid"]
        assert _assoc(b.id) == {r1.id, r2.id, r3.id}
        assert _tree(b.id)[0] == {r1.id: "Unsorted", r2.id: "Unsorted", r3.id: "c"}
        assert client.post(url, headers=H_OTHER, json={"bundle_id": b.id, "rule_ids": [r1.id]}).status_code == 403
        assert client.post(url, headers=H_OWNER, json={"bundle_id": b.id}).status_code == 400
        assert client.post(url, headers=H_OWNER, json={"bundle_id": 999, "rule_ids": [r1.id]}).status_code == 404


# ── remove_rule_bundle ───────────────────────────────────────────────────────

def test_remove_rule_also_takes_it_out_of_the_tree(client, app):
    with app.app_context():
        b, r1, r2 = make_bundle(), _rule("A"), _rule("B")
        login(client, owner())
        save_structure(client, b.id, [D("Pack", [R(r1.id), R(r2.id)])])
        as_anonymous()
        url = "/api/bundle/private/remove_rule_bundle"
        resp = client.get(url, headers=H_OWNER, query_string={"rule_id": r1.id, "bundle_id": b.id})
        assert resp.status_code == 200 and resp.get_json()["message"] == "Rule removed!"
        assert _assoc(b.id) == {r2.id}
        assert _tree(b.id)[0] == {r2.id: "Pack"}
        # by uuids, POST
        resp = client.post(url, headers=H_OWNER, json={"rule_uuid": r2.uuid, "bundle_uuid": b.uuid})
        assert resp.status_code == 200 and _assoc(b.id) == set() and _tree(b.id)[0] == {}
        # not in the bundle anymore: 404 (was a 500)
        resp = client.get(url, headers=H_OWNER, query_string={"rule_id": r1.id, "bundle_id": b.id})
        assert resp.status_code == 404
        assert client.get(url, headers=H_OTHER, query_string={"rule_id": r1.id, "bundle_id": b.id}).status_code == 403
        assert client.get(url, headers=H_OWNER, query_string={"bundle_id": b.id}).status_code == 400


# ── edit_bundle ──────────────────────────────────────────────────────────────

def test_edit_is_a_partial_update(client, app):
    with app.app_context():
        created = client.post("/api/bundle/private/create", headers=H_OWNER, json={
            "name": "Before", "description": "keep me", "vulnerabilities": ["CVE-2024-0001"]}).get_json()
        bid = created["bundle_id"]
        url = f"/api/bundle/private/edit_bundle/{bid}"
        # name only: used to 500 (KeyError) and wipe the CVEs
        resp = client.post(url, headers=H_OWNER, json={"name": "After"})
        assert resp.status_code == 200 and resp.get_json()["message"] == "Bundle updated successfully"
        b = fresh(Bundle, bid)
        assert b.name == "After" and b.description == "keep me" and b.access is True
        assert json.loads(b.vulnerability_identifiers) == ["CVE-2024-0001"]
        resp = client.post(url, headers=H_OWNER, json={"public": False, "vulnerabilities": []})
        b = fresh(Bundle, bid)
        assert resp.status_code == 200 and b.access is False and json.loads(b.vulnerability_identifiers) == []
        assert b.name == "After"


def test_edit_tags_and_validation(client, app):
    with app.app_context():
        b = make_bundle()
        tag("tlp:green")
        url = f"/api/bundle/private/edit_bundle/{b.id}"
        assert client.post(url, headers=H_OWNER, json={"tags": ["tlp:green"]}).status_code == 200
        assert client.get(f"/api/bundle/public/detail/{b.id}").get_json()["bundle"]["tags"] == ["tlp:green"]
        assert client.post(url, headers=H_OWNER, json={"tags": []}).status_code == 200
        assert client.get(f"/api/bundle/public/detail/{b.id}").get_json()["bundle"]["tags"] == []
        assert client.post(url, headers=H_OWNER, json={"tags": ["nope:nope"]}).status_code == 400
        assert client.post(url, headers=H_OWNER, json={"name": ""}).status_code == 400
        assert client.post(url, headers=H_OWNER, json={"public": "yes"}).status_code == 400
        assert client.post(url, headers=H_OWNER, json={}).status_code == 400
        assert client.post(url, headers=H_OWNER, data="not json").status_code == 400
        assert client.post(url, headers=H_OTHER, json={"name": "x"}).status_code == 403
        assert client.post("/api/bundle/private/edit_bundle/999", headers=H_OWNER, json={"name": "x"}).status_code == 404
        assert fresh(Bundle, b.id).name == "Test bundle"


# ── structure ────────────────────────────────────────────────────────────────

def test_structure_replace_round_trip(client, app):
    with app.app_context():
        b, r1, r2 = make_bundle(), _rule("A"), _rule("B")
        url = f"/api/bundle/private/{b.uuid}/structure"
        resp = client.post(url, headers=H_OWNER, json={"structure": [
            {"type": "file", "name": "README.md", "content": "# hello"},
            {"type": "folder", "name": "windows", "children": [
                {"type": "rule", "rule_id": r1.id},
                {"type": "rule", "rule_uuid": r2.uuid},
            ]},
        ]})
        assert resp.status_code == 200, resp.get_json()
        assert _assoc(b.id) == {r1.id, r2.id}
        rules, files = _tree(b.id)
        assert rules == {r1.id: "windows", r2.id: "windows"} and files == {"README.md"}

        # GET returns the same format → send it back after removing a rule
        tree = client.get(f"/api/bundle/public/{b.id}/structure").get_json()["structure"]
        tree[1]["children"] = [n for n in tree[1]["children"] if n["rule_id"] != r2.id]
        assert client.post(url, headers=H_OWNER, json={"structure": tree}).status_code == 200
        assert _assoc(b.id) == {r1.id}
        assert _tree(b.id) == ({r1.id: "windows"}, {"README.md"})


def test_structure_validation_and_permissions(client, app):
    with app.app_context():
        b, r = make_bundle(), _rule()
        url = f"/api/bundle/private/{b.id}/structure"
        resp = client.post(url, headers=H_OWNER, json={"structure": [{"type": "rule", "rule_id": 99999}]})
        assert resp.status_code == 400 and resp.get_json()["missing_rules"] == ["99999"]
        assert client.post(url, headers=H_OWNER, json={"structure": [{"type": "file", "name": "a/b"}]}).status_code == 400
        assert client.post(url, headers=H_OWNER, json={"structure": [{"type": "weird", "name": "x"}]}).status_code == 400
        assert client.post(url, headers=H_OWNER, json={"structure": "nope"}).status_code == 400
        assert client.post(url, headers=H_OTHER, json={"structure": []}).status_code == 403
        assert client.post("/api/bundle/private/999/structure", headers=H_OWNER, json={"structure": []}).status_code == 404
        assert _tree(b.id) == ({}, set())


# ── delete_bundle ────────────────────────────────────────────────────────────

def test_delete_bundle(client, app):
    with app.app_context():
        b, b2 = make_bundle("A"), make_bundle("B")
        assert client.post(f"/api/bundle/private/delete_bundle/{b.id}", headers=H_OTHER).status_code == 403
        assert fresh(Bundle, b.id) is not None
        assert client.post(f"/api/bundle/private/delete_bundle/{b.id}", headers=H_OWNER).status_code == 200
        assert fresh(Bundle, b.id) is None
        assert client.post(f"/api/bundle/private/delete_bundle/{b.id}", headers=H_OWNER).status_code == 404
        assert client.post(f"/api/bundle/private/delete_bundle/{b2.uuid}", headers=H_ADMIN).status_code == 200
        assert _last_log("bundle.delete").user_id == admin().id


# ── my_bundles ───────────────────────────────────────────────────────────────

def test_my_bundles_lists_mine_including_private(client, app):
    with app.app_context():
        make_bundle("Mine public")
        make_bundle("Mine private", public=False)
        make_bundle("Not mine", u=other())
        data = client.get("/api/bundle/private/my_bundles", headers=H_OWNER).get_json()
        assert {b["name"] for b in data["bundle_list"]} == {"Mine public", "Mine private"}
        assert data["total"] == 2 and data["page"] == 1
        data = client.get("/api/bundle/private/my_bundles", headers=H_OWNER,
                          query_string={"search": "private", "per_page": 1}).get_json()
        assert [b["name"] for b in data["bundle_list"]] == ["Mine private"]


# ── public: search ───────────────────────────────────────────────────────────

def test_search_keeps_its_response_and_gains_optional_pagination(client, app):
    with app.app_context():
        make_bundle("Detect alpha")
        make_bundle("Detect beta")
        make_bundle("Detect secret", public=False)
        data = client.get("/api/bundle/public/search", query_string={"search": "detect"}).get_json()
        assert set(data) == {"message", "bundle_list"}
        assert {b["name"] for b in data["bundle_list"]} == {"Detect alpha", "Detect beta"}
        # search is optional now
        assert len(client.get("/api/bundle/public/search").get_json()["bundle_list"]) == 2
        data = client.get("/api/bundle/public/search",
                          query_string={"page": 1, "per_page": 1, "sort": "name"}).get_json()
        assert data["total"] == 2 and data["total_pages"] == 2
        assert [b["name"] for b in data["bundle_list"]] == ["Detect alpha"]
        assert client.get("/api/bundle/public/search", query_string={"sort": "bad"}).status_code == 400


# ── public: detail / rules / structure / releases visibility ────────────────

@pytest.mark.parametrize("path", ["detail/{ref}", "{ref}/rules", "{ref}/structure", "{ref}/releases",
                                  "{ref}/download"])
def test_private_bundle_read_routes(client, app, path):
    with app.app_context():
        b = make_bundle("Hidden", public=False)
        r = _rule()
        db.session.add(BundleRuleAssociation(bundle_id=b.id, rule_id=r.id))
        db.session.commit()
        for ref in (b.id, b.uuid):
            url = "/api/bundle/public/" + path.format(ref=ref)
            as_anonymous()
            assert client.get(url).status_code == 403
            assert client.get(url, headers={"X-API-KEY": "bogus"}).status_code == 403
            assert client.get(url, headers=H_OTHER).status_code == 403
            assert client.get(url, headers=H_OWNER).status_code == 200, url
            assert client.get(url, headers=H_ADMIN).status_code == 200
        assert client.get("/api/bundle/public/" + path.format(ref=999)).status_code == 404


def test_detail_and_rules_content(client, app):
    with app.app_context():
        b = make_bundle()
        rules = [_rule(f"R{i}") for i in range(3)]
        login(client, owner())
        save_structure(client, b.id, [F("README.md", "hi"), D("yara", [R(r.id) for r in rules])])
        as_anonymous()
        d = client.get(f"/api/bundle/public/detail/{b.id}").get_json()["bundle"]
        assert d["uuid"] == b.uuid and d["release_count"] == 0
        assert {r["uuid"] for r in d["rules"]} == {r.uuid for r in rules}
        assert d["structure"][0] == {"type": "file", "name": "README.md", "content": "hi"}
        assert [n["rule_uuid"] for n in d["structure"][1]["children"]] == [r.uuid for r in rules]
        page = client.get(f"/api/bundle/public/{b.uuid}/rules", query_string={"per_page": 2, "page": 2}).get_json()
        assert page["total"] == 3 and page["total_pages"] == 2 and len(page["rules"]) == 1
        assert page["rules"][0]["uuid"] == rules[2].uuid


# ── public: download ─────────────────────────────────────────────────────────

def test_download_parts(client, app):
    with app.app_context():
        b, r = make_bundle(), _rule()
        login(client, owner())
        save_structure(client, b.id, [F("README.md", "hi"), D("yara", [R(r.id)])])
        as_anonymous()
        base = f"/api/bundle/public/{b.id}/download"

        resp = client.get(base)   # default: full
        assert resp.status_code == 200 and resp.mimetype == "application/zip"
        names = zipfile.ZipFile(io.BytesIO(resp.data)).namelist()
        assert "README.md" in names and "bundle.json" in names

        names = zipfile.ZipFile(io.BytesIO(client.get(base + "?part=structure").data)).namelist()
        assert "README.md" in names and any(n.startswith("yara/") for n in names)
        assert zipfile.ZipFile(io.BytesIO(client.get(base + "?part=files").data)).namelist() == ["README.md"]
        assert any(n.endswith(".yar") or n.endswith(".yara") for n in
                   zipfile.ZipFile(io.BytesIO(client.get(base + "?part=rules").data)).namelist())
        misp = client.get(base + "?part=misp")
        assert misp.status_code == 200 and misp.mimetype == "application/json"

        assert client.get(base + "?part=nope").status_code == 400
        assert client.get(base + "?release=v9").status_code == 404
        empty = make_bundle("Empty")
        assert client.get(f"/api/bundle/public/{empty.id}/download?part=rules").status_code == 400
        assert client.get(f"/api/bundle/public/{empty.id}/download?part=files").status_code == 404
        assert fresh(Bundle, b.id).download_count == 2   # full + rules


def test_download_is_logged_with_the_api_user(client, app):
    with app.app_context():
        b, r = make_bundle(), _rule()
        db.session.add(BundleRuleAssociation(bundle_id=b.id, rule_id=r.id))
        db.session.commit()
        client.get(f"/api/bundle/public/{b.id}/download?part=rules", headers=H_OTHER)
        log = _last_log("bundle.download")
        assert log.user_id == other().id and log.extra.get("actor_source") == "api_key"
        as_anonymous()
        client.get(f"/api/bundle/public/{b.id}/download?part=rules")
        log = _last_log("bundle.download")
        assert log.user_id is None and log.to_json()["actor_name"] == "Anonymous"


def test_releases_list_and_release_download(client, app):
    with app.app_context():
        b, r = make_bundle(), _rule()
        login(client, owner())
        save_structure(client, b.id, [D("yara", [R(r.id)])])
        assert client.post(f"/bundle/{b.id}/releases", json={"version": "v1.0.0", "notes": "n"}).status_code == 201
        as_anonymous()
        rels = client.get(f"/api/bundle/public/{b.id}/releases").get_json()["releases"]
        assert [x["version"] for x in rels] == ["v1.0.0"]
        resp = client.get(f"/api/bundle/public/{b.id}/download?part=rules&release=v1.0.0")
        assert resp.status_code == 200 and "v1.0.0" in resp.headers["Content-Disposition"]
        assert client.get(f"/api/bundle/public/{b.id}/download?part=misp&release=v1.0.0").status_code == 400


# ── private bundle + share key ───────────────────────────────────────────────

@pytest.mark.parametrize("path", ["detail/{ref}", "{ref}/rules", "{ref}/structure", "{ref}/releases",
                                  "{ref}/download"])
def test_private_bundle_readable_with_its_share_key(client, app, path):
    with app.app_context():
        b = make_bundle("Hidden", public=False)
        r = _rule()
        db.session.add(BundleRuleAssociation(bundle_id=b.id, rule_id=r.id))
        b.share_token = "s3cr3t-share-token"
        db.session.commit()
        url = "/api/bundle/public/" + path.format(ref=b.id)

        # right key + an identified user (any API key): allowed
        assert client.get(url, headers=H_OTHER, query_string={"share_key": "s3cr3t-share-token"}).status_code == 200
        # wrong key, or no API key at all (same rule as the web share link): denied
        assert client.get(url, headers=H_OTHER, query_string={"share_key": "wrong"}).status_code == 403
        as_anonymous()
        assert client.get(url, query_string={"share_key": "s3cr3t-share-token"}).status_code == 403
        # link regenerated → the old key stops working; revoked → too
        b = fresh(Bundle, b.id)
        b.share_token = "new-token"
        db.session.commit()
        assert client.get(url, headers=H_OTHER, query_string={"share_key": "s3cr3t-share-token"}).status_code == 403
        b.share_token = None
        db.session.commit()
        assert client.get(url, headers=H_OTHER, query_string={"share_key": "new-token"}).status_code == 403
        # the owner / an admin never need it
        assert client.get(url, headers=H_OWNER).status_code == 200
        assert client.get(url, headers=H_ADMIN).status_code == 200


def test_share_key_never_grants_write_access(client, app):
    with app.app_context():
        b = make_bundle("Hidden", public=False)
        b.share_token = "s3cr3t-share-token"
        db.session.commit()
        resp = client.post(f"/api/bundle/private/edit_bundle/{b.id}?share_key=s3cr3t-share-token",
                           headers=H_OTHER, json={"name": "hacked"})
        assert resp.status_code == 403
        assert fresh(Bundle, b.id).name == "Hidden"


def test_private_bundle_never_leaks_through_search_or_public_logs(client, app):
    with app.app_context():
        resp = client.post("/api/bundle/private/create", json={"name": "Secret", "public": False}, headers=H_OWNER)
        assert resp.status_code == 200
        assert _last_log("bundle.create").is_public is False
        client.post("/api/bundle/private/create", json={"name": "Open"}, headers=H_OWNER)
        assert _last_log("bundle.create").is_public is True
        as_anonymous()
        names = [b["name"] for b in client.get("/api/bundle/public/search").get_json()["bundle_list"]]
        assert names == ["Open"]
        # even the owner's key doesn't make search list private bundles (my_bundles does)
        names = [b["name"] for b in client.get("/api/bundle/public/search", headers=H_OWNER).get_json()["bundle_list"]]
        assert names == ["Open"]


def test_share_key_in_a_header(client, app):
    """X-Share-Key header — kept out of URLs (proxy logs, Referer)."""
    with app.app_context():
        b = make_bundle("Hidden", public=False)
        b.share_token = "hdr-share-token"
        db.session.commit()
        url = f"/api/bundle/public/detail/{b.id}"
        assert client.get(url, headers={**H_OTHER, "X-Share-Key": "hdr-share-token"}).status_code == 200
        assert client.get(url, headers={**H_OTHER, "X-Share-Key": "wrong"}).status_code == 403
        as_anonymous()
        assert client.get(url, headers={"X-Share-Key": "hdr-share-token"}).status_code == 403
