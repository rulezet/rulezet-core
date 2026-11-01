"""Bundle forks and merge requests (bundle_fork_core.py, bundle_fork_routes.py) — docs/future/bundle_forks.md."""
import pytest

from app import db
from app.core.db_class.bundle import Bundle, BundleNode, BundleRuleAssociation
from app.core.db_class.bundle_fork import BundleForkRule, BundleMergeRequest
from app.core.db_class.notification import Notification
from app.core.db_class.rule import Rule
from app.features.bundle import bundle_fork_core as Fork
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from app.core.db_class.tag import BundleTagAssociation
from app.features.bundle import bundle_core as BundleModel
from tests_new.helpers.bundles import add_rules, make_bundle, make_tag
from tests_new.helpers.rules import make_rule, yara_rule

# owner = owns the upstream; user = forks it
FORK_ACCESS = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK}


def _upstream(users, n=2):
    bundle = make_bundle(users.owner)
    rules = [make_rule(users.owner) for _ in range(n)]
    add_rules(bundle, *rules)
    return bundle, rules


def _fork(client, bundle):
    r = client.post(f"/bundle/{bundle.id}/fork", json={})
    assert r.status_code == 200, r.get_json()
    return db.session.get(Bundle, r.get_json()["bundle_id"])


def _rule_ids(bundle):
    return {a.rule_id for a in BundleRuleAssociation.query.filter_by(bundle_id=bundle.id)}


# ── Fork ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(FORK_ACCESS))
def test_who_can_fork(role, expected, clients, users):
    bundle, _ = _upstream(users)
    assert_outcome(clients[role].post(f"/bundle/{bundle.id}/fork", json={}), expected)


def test_fork_copies_tree_and_shares_rules(clients, users):
    bundle, rules = _upstream(users)
    tag = make_tag("fork-test-tag", users.owner)
    BundleModel.update_bundle_tags(bundle.id, [tag.id], users.owner)
    fork = _fork(clients["user"], bundle)
    assert fork.user_id == users.user.id and fork.forked_from_id == bundle.id
    assert fork.forked_from_uuid == bundle.uuid and fork.fork_base_snapshot
    assert _rule_ids(fork) == {r.id for r in rules}                  # same rules, not copies
    assert BundleTagAssociation.query.filter_by(bundle_id=fork.id, tag_id=tag.id).first().user_id == users.user.id
    assert BundleNode.query.filter_by(bundle_id=fork.id).count() == BundleNode.query.filter_by(bundle_id=bundle.id).count()
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="bundle_forked").count() == 1
    info = clients["anonymous"].get(f"/bundle/{fork.id}/fork_info").get_json()
    assert info["is_fork"] and info["upstream"]["id"] == bundle.id and info["ahead"] == 0 and info["behind"] == 0
    assert clients["anonymous"].get(f"/bundle/{bundle.id}/forks").get_json()["total"] == 1


def test_private_bundle_only_forked_by_admin(clients, users):
    bundle = make_bundle(users.owner, public=False)
    assert clients["user"].post(f"/bundle/{bundle.id}/fork", json={}).status_code == 404
    fork = _fork(clients["admin"], bundle)
    assert fork.access is False                                      # a private bundle's fork stays private


# ── Merge request: contribute ─────────────────────────────────────────────

def test_fork_changes_proposed_and_merged(clients, users):
    bundle, rules = _upstream(users)
    fork = _fork(clients["user"], bundle)
    new_rule = make_rule(users.user)
    add_rules(fork, new_rule)
    Fork_rm = __import__("app.features.bundle.bundle_core", fromlist=["x"]).remove_rule_from_bundle
    Fork_rm(fork.id, rules[0].id)

    info = clients["user"].get(f"/bundle/{fork.id}/fork_info").get_json()
    assert info["ahead"] == 2 and info["can_open_mr"]
    r = clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={"title": "More rules"})
    assert r.status_code == 200, r.get_json()
    uuid = r.get_json()["uuid"]
    data = clients["anonymous"].get(f"/bundle/merge_request/{uuid}/json").get_json()
    kinds = sorted(i["kind"] for i in data["items"])
    assert kinds == ["rule_added", "rule_removed"] and not data["can_review"]
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="bundle_mr_opened").count() == 1

    # only the target's owner (or an admin) merges
    assert clients["user"].post(f"/bundle/merge_request/{uuid}/merge", json={}).status_code == 403
    removed = next(i for i in data["items"] if i["kind"] == "rule_removed")
    assert clients["owner"].post(f"/bundle/merge_request/{uuid}/decision",
                                 json={"item_id": removed["id"], "decision": "reject"}).status_code == 200
    r = clients["owner"].post(f"/bundle/merge_request/{uuid}/merge", json={"note": "thanks"})
    assert r.status_code == 200, r.get_json()
    db.session.expire_all()
    assert _rule_ids(bundle) == {rules[0].id, rules[1].id, new_rule.id}   # added, removal rejected
    mr = BundleMergeRequest.query.filter_by(uuid=uuid).first()
    assert mr.status == "merged" and mr.reviewed_by_id == users.owner.id
    assert Notification.query.filter_by(user_id=users.user.id, notif_type="bundle_mr_merged").count() == 1


def test_no_merge_request_without_changes_or_twice(clients, users):
    bundle, _ = _upstream(users)
    fork = _fork(clients["user"], bundle)
    assert clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={}).status_code == 400
    add_rules(fork, make_rule(users.user))
    assert clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={}).status_code == 200
    assert clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={}).status_code == 403
    # someone else can't propose the fork's changes
    assert clients["admin"].post(f"/bundle/{bundle.id}/merge_requests", json={}).status_code == 403


def test_closed_to_merge_requests(clients, users):
    bundle, _ = _upstream(users)
    fork = _fork(clients["user"], bundle)
    add_rules(fork, make_rule(users.user))
    assert clients["user"].post(f"/bundle/{bundle.id}/accepts_proposals", json={"value": False}).status_code == 403
    assert clients["owner"].post(f"/bundle/{bundle.id}/accepts_proposals", json={"value": False}).status_code == 200
    r = clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={})
    assert r.status_code == 403 and "does not take" in r.get_json()["message"]


# ── Conflicts ─────────────────────────────────────────────────────────────

def test_file_conflict_must_be_resolved(clients, users):
    bundle, _ = _upstream(users, n=1)
    db.session.add(BundleNode(bundle_id=bundle.id, name="README.md", node_type="file", custom_content="v1"))
    db.session.commit()
    fork = _fork(clients["user"], bundle)
    BundleNode.query.filter_by(bundle_id=fork.id, name="README.md").first().custom_content = "fork version"
    BundleNode.query.filter_by(bundle_id=bundle.id, name="README.md").first().custom_content = "upstream version"
    db.session.commit()

    uuid = clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={}).get_json()["uuid"]
    data = clients["owner"].get(f"/bundle/merge_request/{uuid}/json").get_json()
    item = data["items"][0]
    assert item["conflict"] and item["conflict_kind"] == "content" and data["blockers"]
    assert clients["owner"].post(f"/bundle/merge_request/{uuid}/merge", json={}).status_code == 400
    assert clients["owner"].post(f"/bundle/merge_request/{uuid}/decision",
                                 json={"item_id": item["id"], "decision": "accept"}).status_code == 400
    clients["owner"].post(f"/bundle/merge_request/{uuid}/decision", json={"item_id": item["id"], "decision": "source"})
    assert clients["owner"].post(f"/bundle/merge_request/{uuid}/merge", json={}).status_code == 200
    db.session.expire_all()
    assert BundleNode.query.filter_by(bundle_id=bundle.id, name="README.md").first().custom_content == "fork version"


def test_three_way_engine_cases():
    base = {"meta": {"description": "d", "tags": ["a"], "vulnerabilities": []},
            "rules": {"r1": {"hash": "1", "folder": "x"}, "r2": {"hash": "2", "folder": "x"}, "r3": {"hash": "3", "folder": "x"}},
            "files": {"f": {"hash": "f1"}}, "folders": ["x"]}
    source = {"meta": {"description": "d", "tags": ["a", "b"], "vulnerabilities": []},
              "rules": {"r1": {"hash": "1b", "folder": "x"}, "r2": {"hash": "2", "folder": "y"},
                        "r4": {"hash": "4", "folder": "x"}},          # r1 changed, r2 moved, r3 removed, r4 added
              "files": {"f": {"hash": "f1"}}, "folders": ["x", "y"]}
    target = {"meta": {"description": "d2", "tags": ["a"], "vulnerabilities": []},
              "rules": {"r1": {"hash": "1c", "folder": "x"}, "r2": {"hash": "2", "folder": "x"},
                        "r3": {"hash": "3", "folder": "x"}},
              "files": {"f": {"hash": "f1"}}, "folders": ["x"]}
    items = {i["id"]: i for i in Fork.compute_changes(base, source, target)}
    assert items["rule:r1"]["conflict_kind"] == "content"            # changed on both sides
    assert items["move:r2"]["kind"] == "rule_moved" and not items["move:r2"]["conflict"]
    assert items["rule:r3"]["kind"] == "rule_removed" and not items["rule:r3"]["conflict"]
    assert items["rule:r4"]["kind"] == "rule_added"
    assert items["folder:y"]["kind"] == "folder_added"
    assert items["meta:tags"]["source"]["add"] == ["b"]
    assert "meta:description" not in items                            # only the target changed it
    assert "file:f" not in items                                      # unchanged
    assert Fork.compute_changes(base, base, base) == []


# ── Copy-on-write and sync ────────────────────────────────────────────────

def test_editing_a_foreign_rule_in_a_fork_makes_a_copy(clients, users):
    bundle, rules = _upstream(users, n=1)
    fork = _fork(clients["user"], bundle)
    original = rules[0]
    before = original.to_string
    # a copy keeps the original's YARA rule name (normally unique on Rulezet)
    same_name = original.to_string.replace('$a', '$changed')
    r = clients["user"].post(f"/bundle/{fork.id}/fork_rule/{original.id}", json={"content": same_name})
    assert r.status_code == 200, r.get_json()
    copy_id = r.get_json()["rule_id"]
    db.session.expire_all()
    assert db.session.get(Rule, original.id).to_string == before          # original untouched
    assert _rule_ids(fork) == {copy_id} and _rule_ids(bundle) == {original.id}
    assert BundleForkRule.query.filter_by(bundle_id=fork.id, copy_rule_id=copy_id).first().original_rule_uuid == original.uuid
    # the copy is seen as a change of the original, not as remove + add
    uuid = clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={}).get_json()["uuid"]
    items = clients["owner"].get(f"/bundle/merge_request/{uuid}/json").get_json()["items"]
    assert [i["kind"] for i in items] == ["rule_modified"]
    # the owner of the original merges: the original rule gets the new content (default "update")
    assert clients["owner"].post(f"/bundle/merge_request/{uuid}/merge", json={}).status_code == 200
    db.session.expire_all()
    assert "$changed" in db.session.get(Rule, original.id).to_string
    assert _rule_ids(bundle) == {original.id}
    # a rule of your own is edited directly, and only in forks
    assert clients["user"].post(f"/bundle/{fork.id}/fork_rule/{copy_id}", json={"content": "x"}).status_code == 400
    assert clients["owner"].post(f"/bundle/{bundle.id}/fork_rule/{original.id}", json={"content": "x"}).status_code == 400


def test_sync_brings_upstream_changes(clients, users):
    bundle, _ = _upstream(users, n=1)
    fork = _fork(clients["user"], bundle)
    later = make_rule(users.owner)
    add_rules(bundle, later)
    assert clients["user"].get(f"/bundle/{fork.id}/fork_info").get_json()["behind"] == 1
    assert clients["owner"].post(f"/bundle/{fork.id}/sync").status_code == 403
    r = clients["user"].post(f"/bundle/{fork.id}/sync")
    assert r.status_code == 200, r.get_json()
    db.session.expire_all()
    assert later.id in _rule_ids(fork)
    info = clients["user"].get(f"/bundle/{fork.id}/fork_info").get_json()
    assert info["behind"] == 0 and info["ahead"] == 0
    assert "up to date" in clients["user"].post(f"/bundle/{fork.id}/sync").get_json()["message"]


def test_merge_request_visibility_and_close(clients, users):
    bundle, _ = _upstream(users)
    fork = _fork(clients["user"], bundle)
    add_rules(fork, make_rule(users.user))
    uuid = clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={}).get_json()["uuid"]
    assert clients["anonymous"].get(f"/bundle/merge_request/{uuid}").status_code == 200
    assert clients["user"].post(f"/bundle/merge_request/{uuid}/close", json={}).status_code == 200
    assert clients["user"].post(f"/bundle/merge_request/{uuid}/reopen", json={}).status_code == 200
    assert clients["owner"].post(f"/bundle/merge_request/{uuid}/close", json={"note": "no"}).status_code == 200
    assert Notification.query.filter_by(user_id=users.user.id, notif_type="bundle_mr_closed").count() == 1
    assert clients["user"].post(f"/bundle/merge_request/{uuid}/reopen", json={}).status_code == 200
    # the fork goes private: its open merge request goes stale, hidden from others, still seen by both sides
    assert clients["user"].post("/bundle/edit_access", query_string={"id": fork.id}).status_code == 200
    db.session.expire_all()
    assert BundleMergeRequest.query.filter_by(uuid=uuid).first().status == "stale"
    assert clients["anonymous"].get(f"/bundle/merge_request/{uuid}").status_code == 404
    assert clients["user"].get(f"/bundle/merge_request/{uuid}").status_code == 200
    assert clients["owner"].get(f"/bundle/merge_request/{uuid}").status_code == 200


def test_deleting_the_original_makes_the_oldest_fork_the_original(clients, users):
    bundle, _ = _upstream(users)
    first = _fork(clients["user"], bundle)
    second = _fork(clients["admin"], bundle)
    assert clients["owner"].post("/bundle/delete", query_string={"id": bundle.id}).status_code == 200
    db.session.expire_all()
    first, second = db.session.get(Bundle, first.id), db.session.get(Bundle, second.id)
    assert first.forked_from_id is None and first.forked_from_uuid is None          # now an original
    assert second.forked_from_id == first.id and second.forked_from_uuid == first.uuid
    assert clients["user"].get(f"/bundle/{first.id}/fork_info").get_json()["is_fork"] is False


def test_bundle_list_shows_originals_with_their_forks(clients, users):
    bundle, _ = _upstream(users)
    fork = _fork(clients["user"], bundle)
    items = {i["id"]: i for i in clients["anonymous"].get("/bundle/data_table?per_page=100").get_json()["items"]}
    assert bundle.id in items and fork.id not in items                       # the fork hangs under its original
    assert items[bundle.id]["fork_count"] == 1
    found = clients["anonymous"].get("/bundle/data_table?per_page=100&search=" + fork.name).get_json()["items"]
    assert any(i["id"] == fork.id and i["forked_from_name"] == bundle.name for i in found)   # a search lists it


def test_admin_deletes_any_fork(clients, users):
    from tests_new.helpers.bundles import make_bundle
    from app import db
    from app.core.db_class.bundle import Bundle
    upstream = make_bundle(users.owner)
    fork_id = clients["user"].post(f"/bundle/{upstream.id}/fork", json={}).get_json()["bundle_id"]
    assert clients["owner"].post(f"/bundle/delete?id={fork_id}").status_code == 403    # the upstream owner can't
    assert clients["admin"].post(f"/bundle/delete?id={fork_id}").status_code == 200    # an admin can
    assert db.session.get(Bundle, fork_id) is None
