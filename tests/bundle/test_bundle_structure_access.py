"""Bundle structure validation, lazy tree, ZIP safety, access rules,
share links and POST-only (CSRF) endpoints."""

import io
import zipfile

from app import db
from app.core.db_class.db import Bundle, BundleNode

from bundle_helpers import D, F, R, fresh, login, make_bundle, make_rule, other, owner, save_structure


# ── validate_structure ────────────────────────────────────────────────────

def test_validate_rejects_path_traversal_and_bad_shapes(app):
    from app.features.bundle.bundle_core import validate_structure
    with app.app_context():
        assert validate_structure([F("../evil.md")]).startswith("Invalid name")
        assert validate_structure([D("..", [])]).startswith("Invalid name")
        assert validate_structure([F("a\\b.txt")]).startswith("Invalid name")
        assert validate_structure({"not": "a list"}) == "Invalid structure"
        assert validate_structure([{"name": "x", "type": "exe", "children": []}]) == "Invalid item in structure"
        assert "can't contain" in validate_structure([{"name": "a.md", "type": "file", "children": [F("b.md")]}])
        assert "too large" in validate_structure([F("big.txt", "x" * (1024 * 1024 + 1))])


def test_validate_accepts_rule_titles_with_slashes(app):
    """Rule node names are just the rule title — '/' is fine there (regression:
    'Invalid name: PraisonAI … step.target …' blocked every save)."""
    from app.features.bundle.bundle_core import validate_structure
    with app.app_context():
        r = make_rule("Path traversal (CVE-2026-1 / GHSA-x)", "yara", "rule a { condition: true }")
        assert validate_structure([D("Main", [R(r.id, r.title + ".yar")])]) is None


def test_validate_prunes_trashed_rules(app):
    from app.features.bundle.bundle_core import validate_structure
    with app.app_context():
        keep = make_rule("keep", "yara", "rule keep { condition: true }")
        gone = make_rule("gone", "yara", "rule gone { condition: true }")
        gone.is_deleted = True
        db.session.commit()
        st = [D("Main", [R(keep.id), R(gone.id), F("README.md", "hi")])]
        assert validate_structure(st) is None
        assert [n.get("rule_id") for n in st[0]["children"]] == [keep.id, None]


def test_save_workspace_rejects_invalid_structure(client, app):
    with app.app_context():
        b = make_bundle()
        login(client, owner())
        r = save_structure(client, b.id, [F("../x.md")])
        assert r.status_code == 400
        assert "Invalid name" in r.get_json()["message"]


def test_zip_entry_names_are_sanitised(app):
    from app.features.bundle.bundle import _safe_zip_name
    with app.app_context():
        assert _safe_zip_name("..") == "untitled"
        assert _safe_zip_name(".") == "untitled"
        assert _safe_zip_name("a/b") == "a_b"
        assert _safe_zip_name("x\x00y‮.txt") == "xy.txt"


def test_structure_zip_never_escapes_its_folder(client, app):
    with app.app_context():
        b = make_bundle()
        # bypass validation on purpose (legacy / API-created data)
        folder = BundleNode(bundle_id=b.id, name="..", node_type="folder")
        db.session.add(folder)
        db.session.flush()
        db.session.add(BundleNode(bundle_id=b.id, parent_id=folder.id, name="../../etc/passwd", node_type="file", custom_content="x"))
        db.session.commit()
        r = client.get(f"/bundle/download_structure?bundle_id={b.id}")
        names = zipfile.ZipFile(io.BytesIO(r.data)).namelist()
        assert all(".." not in n.split("/") and not n.startswith("/") for n in names), names


# ── lazy tree ─────────────────────────────────────────────────────────────

def test_tree_is_light_and_keeps_display_order(client, app):
    with app.app_context():
        r1 = make_rule("r1", "yara", "rule r1 { condition: true }")
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [F("README.md", "read me"), R(r1.id), D("docs", [F("a.txt", "a")])])])
        tree = client.get(f"/bundle/get_bundle_json/{b.id}").get_json()["structure"]
        main = tree[0]
        assert [c["name"] for c in main["children"]] == ["README.md", "r1.yar", "docs"]
        rule_node = main["children"][1]
        assert rule_node["lazy"] is True and "content" not in rule_node
        assert main["children"][0]["content"] == "read me"      # custom files keep their content

        d = client.get(f"/bundle/{b.id}/rule_content/{r1.id}").get_json()
        assert d["success"] and "rule r1" in d["content"]


def test_rule_content_only_for_rules_of_the_bundle(client, app):
    with app.app_context():
        outsider = make_rule("outsider", "yara", "rule o { condition: true }")
        b = make_bundle()
        assert client.get(f"/bundle/{b.id}/rule_content/{outsider.id}").status_code == 404


def test_trashed_rule_content_never_exposed(client, app):
    with app.app_context():
        r = make_rule("secret", "yara", "rule secret { strings: $a = \"TOPSECRET\" condition: $a }")
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(r.id)])])
        r.is_deleted = True
        db.session.commit()
        body = client.get(f"/bundle/get_bundle_json/{b.id}?full=1").get_data(as_text=True)
        assert "TOPSECRET" not in body
        assert client.get(f"/bundle/{b.id}/rule_content/{r.id}").status_code == 404


# ── access ────────────────────────────────────────────────────────────────

def test_private_bundle_is_403_not_500_for_anonymous(client, app):
    with app.app_context():
        b = make_bundle(public=False)
        assert client.get(f"/bundle/detail/{b.id}").status_code == 403
        assert client.get(f"/bundle/detail/{b.uuid}").status_code == 403
        for url in (f"/bundle/get_bundle_json/{b.id}", f"/bundle/get_bundle_tags_display/{b.id}",
                    f"/bundle/get_bundle_vulnerabilities_display/{b.id}", f"/bundle/history/{b.id}",
                    f"/bundle/download_full?bundle_id={b.id}", f"/bundle/{b.id}/health"):
            assert client.get(url).status_code in (401, 403), url


def test_mutating_routes_are_post_only(client, app):
    """They used to be GET — an <img src> in a comment could trigger them (CSRF)."""
    with app.app_context():
        b = make_bundle()
        login(client, owner())
        for path in (f"/bundle/delete?id={b.id}", f"/bundle/edit_access?id={b.id}",
                     f"/bundle/evaluate?bundleId={b.id}&voteType=up", "/bundle/add_rule_bundle?rule_id=1&bundle_id=1",
                     "/bundle/remove?rule_id=1&bundle_id=1", "/bundle/change_description?association_id=1",
                     "/bundle/update_bundle_from_structure?id=1"):
            assert client.get(path).status_code == 405, path
        assert fresh(Bundle, b.id) is not None


# ── share links ───────────────────────────────────────────────────────────

def test_share_link_full_flow(client, app):
    with app.app_context():
        r = make_rule("r", "yara", "rule r { condition: true }")
        b = make_bundle(public=False)
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(r.id), F("README.md", "hi")])])
        url = client.post(f"/bundle/{b.id}/share").get_json()["url"]
        token = url.split("share=")[1]

    viewer = app.test_client()
    with app.app_context():
        login(viewer, other())
        assert viewer.get(f"/bundle/detail/{b.id}").status_code == 403
        assert viewer.get(f"/bundle/detail/{b.id}?share=wrong").status_code == 403

        page = viewer.get(f"/bundle/detail/{b.id}?share={token}")
        assert page.status_code == 200 and "Shared with you" in page.get_data(as_text=True)
        for u in (f"/bundle/get_bundle_json/{b.id}", f"/bundle/download_full?bundle_id={b.id}",
                  f"/bundle/download_structure?bundle_id={b.id}", f"/bundle/history/{b.id}", f"/bundle/{b.id}/health"):
            assert viewer.get(u).status_code == 200, u

        # read-only: every write is refused
        assert viewer.post(f"/bundle/edit_access?id={b.id}").status_code == 401
        assert viewer.post(f"/bundle/delete?id={b.id}").status_code == 401
        assert viewer.post(f"/bundle/save_workspace/{b.id}", json={"structure": []}).status_code == 401
        assert viewer.post(f"/bundle/{b.id}/share").status_code == 403
        assert viewer.get(f"/bundle/{b.id}/share").status_code == 403
        assert viewer.post(f"/bundle/{b.id}/releases", json={"version": "v1.0.0"}).status_code == 403

        # regenerate → the old key stops working immediately
        login(client, owner())
        new_url = client.post(f"/bundle/{b.id}/share").get_json()["url"]
        login(viewer, other())
        assert viewer.get(f"/bundle/detail/{b.id}").status_code == 403
        assert viewer.get(f"/bundle/detail/{b.id}?share={new_url.split('share=')[1]}").status_code == 200

        # revoke
        login(client, owner())
        client.delete(f"/bundle/{b.id}/share")
        login(viewer, other())
        assert viewer.get(f"/bundle/detail/{b.id}").status_code == 403


def test_share_link_requires_an_account(client, app):
    with app.app_context():
        b = make_bundle(public=False)
        login(client, owner())
        token = client.post(f"/bundle/{b.id}/share").get_json()["url"].split("share=")[1]
    anon = app.test_client()
    r = anon.get(f"/bundle/detail/{b.id}?share={token}")
    assert r.status_code == 302 and "/account/login" in r.headers["Location"]


def test_share_token_never_leaks_in_json(client, app):
    with app.app_context():
        b = make_bundle(public=False)
        login(client, owner())
        token = client.post(f"/bundle/{b.id}/share").get_json()["url"].split("share=")[1]
        for u in (f"/bundle/get_bundle?bundle_id={b.id}", f"/bundle/history/{b.id}"):
            assert token not in client.get(u).get_data(as_text=True), u


def test_share_key_never_leaks_in_referer_or_activity_log(client, app):
    from app.core.db_class.db import ActivityLog
    with app.app_context():
        b = make_bundle(public=False)
        login(client, owner())
        token = client.post(f"/bundle/{b.id}/share").get_json()["url"].split("share=")[1]
        viewer = app.test_client()
        login(viewer, other())
        viewer.get(f"/bundle/share/{token}")
        page = viewer.get(f"/bundle/detail/{b.id}?share={token}")
        assert page.status_code == 200
        assert page.headers.get("Referrer-Policy") == "same-origin"
        db.session.expire_all()
        logs = ActivityLog.query.all()
        assert any(l.action == "bundle.share_open" for l in logs)
        assert not any(token in (l.url or "") + (l.description or "") + str(l.extra or "") for l in logs)
