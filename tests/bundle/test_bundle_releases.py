"""Bundle releases: frozen snapshots, version rules, comparisons, release
mode (?release=…) on every read endpoint, and the awkward cases — rules
edited, soft-deleted or hard-deleted after a release, bundle deleted."""

import io
import zipfile

from app import db
from app.core.db_class.db import Bundle, BundleRelease, Rule

from bundle_helpers import D, F, R, as_anonymous, login, make_bundle, make_rule, other, owner, save_structure


def _setup(client):
    r1 = make_rule("Alpha rule", "yara", "rule alpha { condition: true }")
    r2 = make_rule("Beta rule", "yara", "rule beta { condition: true }")
    b = make_bundle()
    login(client, owner())
    save_structure(client, b.id, [D("Pack", [F("README.md", "v1 readme"), R(r1.id), R(r2.id)])])
    return b, r1, r2


def _publish(client, b, version, notes="notes"):
    return client.post(f"/bundle/{b.id}/releases", json={"version": version, "notes": notes})


def _zip(resp):
    return zipfile.ZipFile(io.BytesIO(resp.data))


def test_publish_validates_versions(client, app):
    with app.app_context():
        b, *_ = _setup(client)
        d = client.get(f"/bundle/{b.id}/releases/draft").get_json()
        assert d["suggested_version"] == "v1.0.0" and "2 rules" in d["notes"]
        assert _publish(client, b, "v1.0.0").status_code == 201
        assert "already exists" in _publish(client, b, "v1.0.0").get_json()["message"]
        assert _publish(client, b, "latest!!").status_code == 400
        empty = make_bundle("empty")
        assert "empty" in client.post(f"/bundle/{empty.id}/releases", json={"version": "v1"}).get_json()["message"]


def test_only_owner_or_admin_publishes_or_deletes(client, app):
    with app.app_context():
        b, *_ = _setup(client)
        rel = _publish(client, b, "v1.0.0").get_json()["release"]
        login(client, other())
        assert _publish(client, b, "v2.0.0").status_code == 403
        assert client.delete(f"/bundle/{b.id}/releases/{rel['id']}").status_code == 403
        assert client.get(f"/bundle/{b.id}/releases").status_code == 200      # public bundle: readable


def test_release_is_frozen_against_later_edits(client, app):
    with app.app_context():
        b, r1, r2 = _setup(client)
        _publish(client, b, "v1.0.0")
        # edit a rule upstream + the README + remove r2 from the bundle
        db.session.get(Rule, r1.id).to_string = "rule alpha { condition: false }  // edited"
        db.session.commit()
        save_structure(client, b.id, [D("Pack", [F("README.md", "v2 readme"), R(r1.id)])])

        z = _zip(client.get(f"/bundle/download_full?bundle_id={b.id}&release=v1.0.0"))
        readme = z.read("structure/Pack/README.md").decode()
        alpha = [n for n in z.namelist() if n.startswith("structure/") and "Alpha" in n][0]
        assert readme == "v1 readme"
        assert "edited" not in z.read(alpha).decode()
        assert any("Beta" in n for n in z.namelist())                        # still in the release

        view = client.get(f"/bundle/{b.id}/releases/v1.0.0/view").get_json()
        st = {r["title"]: r for r in view["rules"]}
        assert st["Alpha rule"]["status"] == "updated"
        assert st["Beta rule"]["status"] == "unchanged" and st["Beta rule"]["in_bundle_now"] is False

        # per-rule diff: frozen vs current
        rid = view["release"]["id"]
        d = client.get(f"/bundle/{b.id}/releases/{rid}/rule/{r1.id}/diff?against=current").get_json()
        assert "edited" not in d["old"] and "edited" in d["new"]

        # "N changes since" + suggested bump (a rule was removed → major)
        lst = client.get(f"/bundle/{b.id}/releases").get_json()
        ch = lst["latest_changes"]
        assert len(ch["rules_removed"]) == 1 and len(ch["rules_changed"]) == 1 and ch["files_changed"]
        assert client.get(f"/bundle/{b.id}/releases/draft").get_json()["suggested_version"] == "v2.0.0"


def test_release_survives_soft_and_hard_deleted_rules(client, app):
    with app.app_context():
        b, r1, r2 = _setup(client)
        _publish(client, b, "v1.0.0")
        r1_id, r2_id = r1.id, r2.id
        db.session.get(Rule, r1_id).is_deleted = True                        # soft delete
        db.session.delete(db.session.get(Rule, r2_id))                       # hard delete
        db.session.commit()

        view = client.get(f"/bundle/{b.id}/releases/v1.0.0/view").get_json()
        assert view["success"]
        st = {r["rule_id"]: r for r in view["rules"]}
        assert st[r1_id]["status"] == "deleted" and st[r2_id]["status"] == "deleted"
        assert not st[r2_id]["rule_exists"]

        # the frozen content is still served, zipped and checked
        assert "alpha" in client.get(f"/bundle/{b.id}/rule_content/{r1_id}?release=v1.0.0").get_json()["content"]
        assert "beta" in client.get(f"/bundle/{b.id}/rule_content/{r2_id}?release=v1.0.0").get_json()["content"]
        for url in (f"/bundle/download_full?bundle_id={b.id}&release=v1.0.0",
                    f"/bundle/download?bundle_id={b.id}&release=v1.0.0",
                    f"/bundle/download_structure?bundle_id={b.id}&release=v1.0.0",
                    f"/bundle/download_files?bundle_id={b.id}&release=v1.0.0"):
            r = client.get(url)
            assert r.status_code == 200 and _zip(r).namelist(), url
        assert client.get(f"/bundle/{b.id}/health?release=v1.0.0").get_json()["health"]["rules"] == 2
        assert client.get(f"/bundle/attack_coverage/{b.id}?release=v1.0.0").status_code == 200

        # the live bundle keeps working too, and a new release skips the trashed rules
        assert client.get(f"/bundle/get_bundle_json/{b.id}").status_code == 200
        assert _publish(client, b, "v1.0.1").status_code in (201, 400)     # 400 = now empty of rules but has README


def test_compare_two_releases(client, app):
    with app.app_context():
        b, r1, r2 = _setup(client)
        rel1 = _publish(client, b, "v1.0.0").get_json()["release"]
        r3 = make_rule("Gamma rule", "yara", "rule gamma { condition: true }")
        save_structure(client, b.id, [D("Pack", [F("README.md", "v1 readme"), R(r1.id), R(r2.id), R(r3.id)])])
        rel2 = _publish(client, b, "v1.1.0").get_json()["release"]
        d = client.get(f"/bundle/{b.id}/releases/{rel1['id']}/changes?against={rel2['id']}").get_json()
        assert [x["title"] for x in d["diff"]["rules_added"]] == ["Gamma rule"]
        assert d["diff"]["total"] == 1 and "Gamma rule" in d["markdown"]


def test_unknown_release_is_a_clean_404(client, app):
    with app.app_context():
        b, *_ = _setup(client)
        assert client.get(f"/bundle/{b.id}/releases/v9.9.9/view").status_code == 404
        assert client.get(f"/bundle/download_full?bundle_id={b.id}&release=v9.9.9").status_code == 404
        assert client.get(f"/bundle/{b.id}/health?release=nope").status_code == 404


def test_release_of_another_bundle_is_not_reachable(client, app):
    with app.app_context():
        b, *_ = _setup(client)
        _publish(client, b, "v1.0.0")
        other_bundle, *_ = _setup(client)
        assert client.get(f"/bundle/{other_bundle.id}/releases/v1.0.0/view").status_code == 404


def test_releases_follow_bundle_access_and_deletion(client, app):
    with app.app_context():
        b, *_ = _setup(client)
        rel = _publish(client, b, "v1.0.0").get_json()["release"]
        db.session.get(Bundle, b.id).access = False
        db.session.commit()
        anon = app.test_client()
        as_anonymous()
        assert anon.get(f"/bundle/{b.id}/releases").status_code == 403
        assert anon.get(f"/bundle/{b.id}/releases/{rel['id']}/download").status_code == 403

        login(client, owner())
        client.post(f"/bundle/delete?id={b.id}")
        db.session.expire_all()
        assert BundleRelease.query.filter_by(bundle_id=b.id).count() == 0


def test_every_release_has_its_own_uuid_usable_as_reference(client, app):
    with app.app_context():
        b, *_ = _setup(client)
        r1 = _publish(client, b, "v1.0.0").get_json()["release"]
        save_structure(client, b.id, [D("Pack", [F("README.md", "changed")])])
        r2 = _publish(client, b, "v1.0.1").get_json()["release"]
        assert r1["uuid"] and r2["uuid"] and r1["uuid"] != r2["uuid"]
        assert client.get(f"/bundle/{b.id}/releases/{r1['uuid']}/view").get_json()["release"]["version"] == "v1.0.0"
        z = zipfile.ZipFile(io.BytesIO(client.get(f"/bundle/download_full?bundle_id={b.id}&release={r2['uuid']}").data))
        import json
        assert json.loads(z.read("release.json"))["release"]["uuid"] == r2["uuid"]


def test_bundle_list_exposes_files_and_latest_release(client, app):
    with app.app_context():
        b, *_ = _setup(client)
        _publish(client, b, "v1.0.0")
        save_structure(client, b.id, [D("Pack", [F("README.md", "x"), F("notes.txt", "y")])])
        _publish(client, b, "v1.1.0")
        item = [i for i in client.get("/bundle/data_table?per_page=50").get_json()["items"] if i["id"] == b.id][0]
        assert item["number_of_files"] == 2 and item["number_of_folders"] == 1
        assert item["latest_release"]["version"] == "v1.1.0" and item["release_count"] == 2
        assert "view_count" not in item
        assert client.get("/bundle/data_table?sort=download_count&dir=desc").status_code == 200
