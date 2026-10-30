"""Bundle forks — every conflict and deletion case, applied for real (bundle_fork_core.py).

Rules are shared between a bundle and its forks: editing a rule changes it everywhere, so a rule
"changed on one side only" means a fork's copy (copy-on-write) or a global edit made after the fork
while the other side removed the rule. Each test: build the situation, open the merge request, pick
a side, merge, check the target.
"""
import pytest

from app import db
from app.core.db_class.bundle import Bundle, BundleNode, BundleRuleAssociation
from app.core.db_class.bundle_fork import BundleMergeRequest
from app.core.db_class.rule import Rule
from app.features.bundle import bundle_core as BundleModel
from app.features.bundle import bundle_fork_core as Fork
from tests_new.helpers.bundles import add_rules, make_bundle
from tests_new.helpers.rules import make_rule


def _setup(clients, users, n=2):
    up = make_bundle(users.owner)
    rules = [make_rule(users.owner) for _ in range(n)]
    add_rules(up, *rules)
    r = clients["user"].post(f"/bundle/{up.id}/fork", json={})
    assert r.status_code == 200, r.get_json()
    return up, db.session.get(Bundle, r.get_json()["bundle_id"]), rules


def _open(clients, fork):
    r = clients["user"].post(f"/bundle/{fork.id}/merge_requests", json={"title": "t"})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["uuid"]


def _items(clients, uuid):
    return {i["id"]: i for i in clients["owner"].get(f"/bundle/merge_request/{uuid}/json").get_json()["items"]}


def _decide(clients, uuid, item_id, decision, mode=None):
    r = clients["owner"].post(f"/bundle/merge_request/{uuid}/decision",
                              json={"item_id": item_id, "decision": decision, "rule_mode": mode})
    assert r.status_code == 200, r.get_json()


def _merge(clients, uuid, expect=200):
    r = clients["owner"].post(f"/bundle/merge_request/{uuid}/merge", json={})
    assert r.status_code == expect, r.get_json()
    db.session.expire_all()
    return r.get_json()


def _rules_of(bundle):
    return {a.rule_id for a in BundleRuleAssociation.query.filter_by(bundle_id=bundle.id)}


def _folder_of(bundle, rule_id):
    node = BundleNode.query.filter_by(bundle_id=bundle.id, rule_id=rule_id).first()
    parent = db.session.get(BundleNode, node.parent_id) if node and node.parent_id else None
    return parent.name if parent else ""


def _edit_rule(rule, text):
    """A global edit (by its owner): every bundle using the rule sees it."""
    rule.to_string = rule.to_string.replace("condition", f"// {text}\n    condition")
    db.session.commit()


def _copy(clients, fork, rule, text):
    r = clients["user"].post(f"/bundle/{fork.id}/fork_rule/{rule.id}",
                             json={"content": rule.to_string.replace("condition", f"// {text}\n    condition")})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["rule_id"]


# ── removed in the fork, changed in the original (modify_delete) ──────────

@pytest.mark.parametrize("side, kept", [("source", False), ("target", True)])
def test_removed_in_fork_changed_in_original(side, kept, clients, users):
    up, fork, (r1, _) = _setup(clients, users)
    BundleModel.remove_rule_from_bundle(fork.id, r1.id)
    _edit_rule(r1, "owner improves it")                      # after the fork: the original's version moved
    uuid = _open(clients, fork)
    item = _items(clients, uuid)[f"rule:{r1.uuid}"]
    assert item["kind"] == "rule_removed" and item["conflict_kind"] == "modify_delete"
    _merge(clients, uuid, expect=400)                         # unresolved conflict blocks the merge
    _decide(clients, uuid, item["id"], side)
    _merge(clients, uuid)
    assert (r1.id in _rules_of(up)) is kept
    assert db.session.get(Rule, r1.id).is_deleted is False    # the rule itself never goes away


# ── changed in the fork (copy), removed in the original (delete_modify) ───

@pytest.mark.parametrize("side", ["source", "target"])
def test_changed_in_fork_removed_in_original(side, clients, users):
    up, fork, (r1, _) = _setup(clients, users)
    copy_id = _copy(clients, fork, r1, "fork version")
    BundleModel.remove_rule_from_bundle(up.id, r1.id)
    uuid = _open(clients, fork)
    item = _items(clients, uuid)[f"rule:{r1.uuid}"]
    assert item["kind"] == "rule_modified" and item["conflict_kind"] == "delete_modify"
    _decide(clients, uuid, item["id"], side)
    _merge(clients, uuid)
    if side == "source":
        assert copy_id in _rules_of(up) and r1.id not in _rules_of(up)      # the fork's version comes in
    else:
        assert copy_id not in _rules_of(up) and r1.id not in _rules_of(up)  # stays removed


# ── changed on both sides differently (content) ───────────────────────────

@pytest.mark.parametrize("side", ["source", "target"])
def test_rule_changed_on_both_sides(side, clients, users):
    up, fork, (r1, _) = _setup(clients, users)
    copy_id = _copy(clients, fork, r1, "fork version")
    _edit_rule(r1, "original version")                       # the original's rule moved too
    before = db.session.get(Rule, r1.id).to_string
    uuid = _open(clients, fork)
    item = _items(clients, uuid)[f"rule:{r1.uuid}"]
    assert item["conflict_kind"] == "content"
    _decide(clients, uuid, item["id"], side)
    _merge(clients, uuid)
    rule = db.session.get(Rule, r1.id)
    if side == "source":                                      # owner merges → the rule gets the fork's content
        assert "fork version" in rule.to_string and "original version" not in rule.to_string
    else:
        assert rule.to_string == before
    assert r1.id in _rules_of(up) and copy_id not in _rules_of(up)


def test_changed_rule_applied_by_link_or_proposal(clients, users):
    up, fork, (r1, r2) = _setup(clients, users)
    c1, c2 = _copy(clients, fork, r1, "one"), _copy(clients, fork, r2, "two")
    uuid = _open(clients, fork)
    items = _items(clients, uuid)
    _decide(clients, uuid, items[f"rule:{r1.uuid}"]["id"], "accept", "link")
    _decide(clients, uuid, items[f"rule:{r2.uuid}"]["id"], "accept", "propose")
    out = _merge(clients, uuid)
    assert c1 in _rules_of(up) and r1.id not in _rules_of(up)                # link: the copy replaces it here
    assert r2.id in _rules_of(up) and "two" not in db.session.get(Rule, r2.id).to_string
    assert any("proposal" in x for x in out["summary"]["proposals"])          # propose: an edit proposal instead
    from app.core.db_class.rule_proposal import RuleEditProposal
    assert RuleEditProposal.query.filter_by(rule_id=r2.id, status="pending").count() == 1


def test_rule_owned_by_someone_else_is_never_overwritten(clients, users):
    """The target's owner merges a change of a rule they don't own: default = use the fork's copy."""
    up = make_bundle(users.owner)
    foreign = make_rule(users.admin)                          # owned by someone else than the bundle owner
    add_rules(up, foreign)
    fork = db.session.get(Bundle, clients["user"].post(f"/bundle/{up.id}/fork", json={}).get_json()["bundle_id"])
    before = foreign.to_string
    copy_id = _copy(clients, fork, foreign, "better")
    uuid = _open(clients, fork)
    _merge(clients, uuid)
    assert db.session.get(Rule, foreign.id).to_string == before
    assert copy_id in _rules_of(up)


# ── moves ─────────────────────────────────────────────────────────────────

def _move(bundle, rule_id, folder):
    node = BundleNode.query.filter_by(bundle_id=bundle.id, rule_id=rule_id).first()
    dest = BundleNode(bundle_id=bundle.id, name=folder, node_type="folder")
    db.session.add(dest)
    db.session.flush()
    node.parent_id = dest.id
    db.session.commit()


@pytest.mark.parametrize("side, folder", [("source", "fork_dir"), ("target", "orig_dir")])
def test_moved_differently_on_both_sides(side, folder, clients, users):
    up, fork, (r1, _) = _setup(clients, users)
    _move(fork, r1.id, "fork_dir")
    _move(up, r1.id, "orig_dir")
    uuid = _open(clients, fork)
    item = _items(clients, uuid)[f"move:{r1.uuid}"]
    assert item["conflict_kind"] == "move"
    _decide(clients, uuid, item["id"], side)
    _merge(clients, uuid)
    assert _folder_of(up, r1.id) == folder


@pytest.mark.parametrize("side", ["source", "target"])
def test_moved_in_fork_removed_in_original(side, clients, users):
    up, fork, (r1, _) = _setup(clients, users)
    _move(fork, r1.id, "fork_dir")
    BundleModel.remove_rule_from_bundle(up.id, r1.id)
    uuid = _open(clients, fork)
    item = _items(clients, uuid)[f"move:{r1.uuid}"]
    assert item["conflict_kind"] == "delete_move"
    _decide(clients, uuid, item["id"], side)
    _merge(clients, uuid)
    if side == "source":
        assert r1.id in _rules_of(up) and _folder_of(up, r1.id) == "fork_dir"
    else:
        assert r1.id not in _rules_of(up)


def test_changed_and_moved_are_two_decisions(clients, users):
    up, fork, (r1, _) = _setup(clients, users)
    copy_id = _copy(clients, fork, r1, "fork version")
    _move(fork, copy_id, "fork_dir")
    uuid = _open(clients, fork)
    items = _items(clients, uuid)
    assert {f"rule:{r1.uuid}", f"move:{r1.uuid}"} <= set(items)
    _decide(clients, uuid, f"move:{r1.uuid}", "reject")       # take the change, not the move
    _merge(clients, uuid)
    assert "fork version" in db.session.get(Rule, r1.id).to_string
    assert _folder_of(up, r1.id) != "fork_dir"


# ── rules that disappear, folders, files, atomicity ───────────────────────

def test_rule_deleted_everywhere_before_merge(clients, users):
    up, fork, (r1, r2) = _setup(clients, users)
    new = make_rule(users.user)
    add_rules(fork, new)
    uuid = _open(clients, fork)
    new.is_deleted = True                                     # sent to the trash before the merge
    db.session.commit()
    out = _merge(clients, uuid)                               # the merge recomputes: nothing to add anymore
    assert new.id not in _rules_of(up)
    mr = BundleMergeRequest.query.filter_by(uuid=uuid).first()
    assert mr.status == "merged" and not any(i["key"] == new.uuid for i in mr.items)


def test_folder_removed_in_fork_but_filled_in_original_is_kept(clients, users):
    up, fork, _ = _setup(clients, users)
    for b in (up, fork):
        db.session.add(BundleNode(bundle_id=b.id, name="docs", node_type="folder"))
    db.session.commit()
    fork.fork_base_snapshot = Fork.snapshot(up.id, with_content=False)
    db.session.commit()
    BundleNode.query.filter_by(bundle_id=fork.id, name="docs").delete()
    docs = BundleNode.query.filter_by(bundle_id=up.id, name="docs").first()
    db.session.add(BundleNode(bundle_id=up.id, parent_id=docs.id, name="new.md", node_type="file", custom_content="x"))
    db.session.commit()
    uuid = _open(clients, fork)
    out = _merge(clients, uuid)
    assert BundleNode.query.filter_by(bundle_id=up.id, name="docs").first() is not None
    assert any("kept" in x for x in out["summary"]["applied"])


def test_file_removed_in_fork_changed_in_original(clients, users):
    up, fork, _ = _setup(clients, users)
    for b in (up, fork):
        db.session.add(BundleNode(bundle_id=b.id, name="README.md", node_type="file", custom_content="v1"))
    db.session.commit()
    fork.fork_base_snapshot = Fork.snapshot(up.id, with_content=False)
    db.session.commit()
    BundleNode.query.filter_by(bundle_id=fork.id, name="README.md").delete()
    BundleNode.query.filter_by(bundle_id=up.id, name="README.md").first().custom_content = "v2"
    db.session.commit()
    uuid = _open(clients, fork)
    item = _items(clients, uuid)["file:README.md"]
    assert item["conflict_kind"] == "modify_delete"
    _decide(clients, uuid, item["id"], "target")
    _merge(clients, uuid)
    assert BundleNode.query.filter_by(bundle_id=up.id, name="README.md").first().custom_content == "v2"


def test_description_conflict(clients, users):
    up, fork, _ = _setup(clients, users)
    fork.description, up.description = "fork text", "original text"
    db.session.commit()
    uuid = _open(clients, fork)
    _decide(clients, uuid, "meta:description", "source")
    _merge(clients, uuid)
    assert db.session.get(Bundle, up.id).description == "fork text"


def test_merge_is_all_or_nothing(clients, users, monkeypatch):
    up, fork, _ = _setup(clients, users)
    a, b = make_rule(users.user), make_rule(users.user)
    add_rules(fork, a, b)
    uuid = _open(clients, fork)
    real, calls = Fork._apply_item, {"n": 0}

    def boom(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("database went away")
        return real(*args, **kwargs)
    monkeypatch.setattr(Fork, "_apply_item", boom)
    _merge(clients, uuid, expect=500)
    assert not ({a.id, b.id} & _rules_of(up))                  # the first item was rolled back too
    assert BundleMergeRequest.query.filter_by(uuid=uuid).first().status == "open"


def test_decision_kept_only_while_the_change_is_the_same(clients, users):
    up, fork, (r1, _) = _setup(clients, users)
    copy_id = _copy(clients, fork, r1, "v1")
    uuid = _open(clients, fork)
    _decide(clients, uuid, f"rule:{r1.uuid}", "reject")
    clients["owner"].get(f"/bundle/merge_request/{uuid}/json?refresh=1")
    assert _items(clients, uuid)[f"rule:{r1.uuid}"]["decision"] == "reject"     # same change: kept
    copy = db.session.get(Rule, copy_id)
    copy.to_string = copy.to_string.replace("v1", "v2")      # the author changed it again
    db.session.commit()
    clients["owner"].get(f"/bundle/merge_request/{uuid}/json?refresh=1")
    assert _items(clients, uuid)[f"rule:{r1.uuid}"]["decision"] == "accept"     # a new change: decided again


def test_source_deleted_makes_the_merge_request_stale(clients, users):
    up, fork, _ = _setup(clients, users)
    add_rules(fork, make_rule(users.user))
    uuid = _open(clients, fork)
    assert clients["user"].post("/bundle/delete", query_string={"id": fork.id}).status_code == 200
    db.session.expire_all()
    mr = BundleMergeRequest.query.filter_by(uuid=uuid).first()
    assert mr.status == "stale"
    _merge(clients, uuid, expect=400)


def test_merge_by_an_admin_tells_the_author_and_the_owner(clients, users):
    from app.core.db_class.notification import Notification
    up, fork, _ = _setup(clients, users)
    add_rules(fork, make_rule(users.user))
    uuid = _open(clients, fork)
    assert clients["admin"].post(f"/bundle/merge_request/{uuid}/merge", json={}).status_code == 200
    assert Notification.query.filter_by(user_id=users.user.id, notif_type="bundle_mr_merged").count() == 1   # author
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="bundle_mr_merged").count() == 1  # owner
    assert Notification.query.filter_by(user_id=users.admin.id, notif_type="bundle_mr_merged").count() == 0  # not the actor
