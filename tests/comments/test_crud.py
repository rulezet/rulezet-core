"""Comments — layer 2: create / read / edit / delete, reactions, mentions and
notifications, checked in the database."""
import pytest

from app import db
from app.core.db_class.db import (
    ActivityLog, Comment, Notification, RuleCommentReaction, UnifiedComment, UnifiedCommentReaction,
)
from tests.helpers.comments import (
    API, list_url, make_bundle, make_comment, make_legacy_comment, mention, new_comment, trash,
)
from tests.helpers.db import count, reload
from tests.helpers.rules import make_rule
from tests.helpers.users import make_user


def _notifications(user, notif_type):
    db.session.expire_all()
    return Notification.query.filter_by(user_id=user.id, notif_type=notif_type).all()


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", ["rule", "bundle"])
def test_create_comment_stores_it_by_the_author_on_the_object(kind, clients, users):
    obj = make_rule(users.owner) if kind == "rule" else make_bundle(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(obj, "  Nice one  "))

    comment = UnifiedComment.query.one()
    assert response.status_code == 201
    assert (comment.object_type, comment.object_id) == (kind, obj.id)
    assert comment.created_by == users.user.id
    assert comment.content == "Nice one"
    assert comment.parent_id is None and comment.depth == 0 and comment.is_active


def test_create_comment_returns_the_new_comment(clients, users):
    rule = make_rule(users.owner)

    body = clients["user"].post(f"{API}/", json=new_comment(rule, "Hello")).get_json()

    stored = UnifiedComment.query.one()
    assert body["comment"]["uuid"] == stored.uuid
    assert body["comment"]["content"] == "Hello"
    assert body["comment"]["author"]["id"] == users.user.id


def test_create_comment_logs_the_activity(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post(f"{API}/", json=new_comment(rule))

    assert count(ActivityLog, action="comment.add", user_id=users.user.id) == 1


def test_reply_is_threaded_under_its_parent(clients, users):
    rule = make_rule(users.owner)
    root = make_comment(users.owner, rule)
    child = make_comment(users.owner, rule, parent=root)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, parent_id=child.id))

    reply = UnifiedComment.query.filter_by(parent_id=child.id).one()
    assert response.status_code == 201
    assert reply.depth == 2 and reply.root_id == root.id


def test_reply_to_a_comment_of_another_object_stores_nothing(clients, users):
    rule, other = make_rule(users.owner), make_rule(users.owner)
    parent = make_comment(users.owner, other)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, parent_id=parent.id))

    assert response.status_code == 400
    assert count(UnifiedComment, object_id=rule.id) == 0


def test_reply_to_a_deleted_comment_stores_nothing(clients, users):
    rule = make_rule(users.owner)
    parent = make_comment(users.owner, rule, active=False)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, parent_id=parent.id))

    assert response.status_code == 404
    assert count(UnifiedComment, parent_id=parent.id) == 0


# ── Read ──────────────────────────────────────────────────────────────────────

def test_list_shows_root_comments_oldest_first(clients, users):
    rule = make_rule(users.owner)
    first, second = make_comment(users.owner, rule), make_comment(users.user, rule)
    make_comment(users.user, rule, parent=first)

    body = clients["anonymous"].get(list_url(rule)).get_json()

    assert [c["uuid"] for c in body["items"]] == [first.uuid, second.uuid]
    assert body["total"] == 2
    assert body["items"][0]["reply_count"] == 1


def test_list_with_parent_id_shows_the_replies(clients, users):
    rule = make_rule(users.owner)
    root = make_comment(users.owner, rule)
    reply = make_comment(users.user, rule, parent=root)

    body = clients["anonymous"].get(list_url(rule, parent_id=root.id)).get_json()

    assert [c["uuid"] for c in body["items"]] == [reply.uuid]


def test_list_hides_deleted_comments(clients, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule, active=False, content="removed")

    body = clients["admin"].get(list_url(rule)).get_json()

    assert body["items"] == [] and body["total"] == 0


def test_list_only_shows_the_requested_object(clients, users):
    rule, bundle = make_rule(users.owner), make_bundle(users.owner)
    make_comment(users.owner, bundle)

    body = clients["anonymous"].get(list_url(rule)).get_json()

    assert body["items"] == []


def test_list_page_size_is_capped(clients, users):
    rule = make_rule(users.owner)
    for _ in range(55):
        make_comment(users.owner, rule)

    body = clients["anonymous"].get(list_url(rule, per_page=1000)).get_json()

    assert len(body["items"]) == 50 and body["has_next"] is True


def test_resolve_returns_the_ancestor_chain(clients, users):
    rule = make_rule(users.owner)
    root = make_comment(users.owner, rule)
    child = make_comment(users.owner, rule, parent=root)
    grandchild = make_comment(users.owner, rule, parent=child)

    body = clients["anonymous"].get(f"{API}/resolve/{grandchild.id}").get_json()

    assert body == {"id": grandchild.id, "root_id": root.id, "ancestors": [root.id, child.id]}


def test_resolve_a_deleted_comment_is_not_found(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), active=False)

    response = clients["anonymous"].get(f"{API}/resolve/{comment.id}")

    assert response.status_code == 404


def test_my_count_counts_only_my_active_comments(clients, users):
    rule = make_rule(users.owner)
    make_comment(users.user, rule)
    make_comment(users.user, rule)
    make_comment(users.user, rule, active=False)
    make_comment(users.owner, rule)

    body = clients["user"].get(f"{API}/my_count").get_json()

    assert body == {"count": 2}


# ── Edit ──────────────────────────────────────────────────────────────────────

def test_edit_comment_keeps_the_original_text(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), content="First version")

    clients["owner"].put(f"{API}/{comment.uuid}", json={"content": "Second version"})
    clients["owner"].put(f"{API}/{comment.uuid}", json={"content": "Third version"})

    stored = reload(comment)
    assert stored.content == "Third version"
    assert stored.content_original == "First version"


def test_edit_deleted_comment_is_refused(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), active=False, content="Gone")

    response = clients["owner"].put(f"{API}/{comment.uuid}", json={"content": "Back"})

    assert response.status_code == 400
    assert reload(comment).content == "Gone"


def test_edit_unknown_comment_is_not_found(clients):
    response = clients["admin"].put(f"{API}/no-such-uuid", json={"content": "x"})

    assert response.status_code == 404


# ── Delete / restore ──────────────────────────────────────────────────────────

def test_delete_comment_is_a_soft_delete(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients["admin"].delete(f"{API}/{comment.uuid}")

    stored = reload(comment)
    assert response.status_code == 200
    assert stored.is_active is False
    assert stored.deleted_by == users.admin.id and stored.deleted_at is not None


def test_delete_comment_twice_is_refused(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), active=False)

    response = clients["owner"].delete(f"{API}/{comment.uuid}")

    assert response.status_code == 400


def test_deleted_reply_no_longer_counts_as_a_reply(clients, users):
    rule = make_rule(users.owner)
    root = make_comment(users.owner, rule)
    reply = make_comment(users.user, rule, parent=root)

    clients["user"].delete(f"{API}/{reply.uuid}")

    body = clients["anonymous"].get(list_url(rule)).get_json()
    assert body["items"][0]["reply_count"] == 0


def test_restore_comment_brings_it_back(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), active=False)

    response = clients["admin"].post(f"{API}/{comment.uuid}/restore")

    stored = reload(comment)
    assert response.status_code == 200
    assert stored.is_active and stored.deleted_at is None and stored.deleted_by is None


def test_restore_active_comment_is_refused(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients["admin"].post(f"{API}/{comment.uuid}/restore")

    assert response.status_code == 400


def test_hard_delete_removes_the_whole_reply_subtree(clients, users):
    """Reactions go with them through the foreign key's ON DELETE CASCADE (PostgreSQL)."""
    rule = make_rule(users.owner)
    root = make_comment(users.owner, rule)
    reply = make_comment(users.user, rule, parent=root)
    nested = make_comment(users.owner, rule, parent=reply)
    sibling = make_comment(users.user, rule)

    subtree = sorted([root.id, reply.id, nested.id])

    response = clients["admin"].delete(f"{API}/{root.uuid}/hard_delete")

    assert response.status_code == 200
    assert sorted(response.get_json()["deleted_ids"]) == subtree
    assert count(UnifiedComment) == 1 and reload(sibling) is not None


def test_permanently_deleting_a_rule_removes_its_comments(clients, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule)
    trash(rule)

    clients["admin"].post(f"/rule/permanent_delete/{rule.id}")

    assert count(UnifiedComment, object_type="rule", object_id=rule.id) == 0


def test_deleting_a_bundle_removes_its_comments(clients, users):
    bundle = make_bundle(users.owner)
    make_comment(users.user, bundle)

    clients["owner"].post(f"/bundle/delete?id={bundle.id}")

    assert count(UnifiedComment, object_type="bundle", object_id=bundle.id) == 0


# ── Reactions ─────────────────────────────────────────────────────────────────

def test_react_like_then_like_again_toggles_it_off(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    first = clients["user"].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"}).get_json()
    second = clients["user"].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"}).get_json()

    assert first == {"like_count": 1, "dislike_count": 0, "user_reaction": "like"}
    assert second == {"like_count": 0, "dislike_count": 0, "user_reaction": None}
    assert count(UnifiedCommentReaction, comment_id=comment.id) == 0


def test_react_dislike_replaces_a_like(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))
    clients["user"].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"})

    body = clients["user"].post(f"{API}/{comment.uuid}/react", json={"reaction": "dislike"}).get_json()

    assert body == {"like_count": 0, "dislike_count": 1, "user_reaction": "dislike"}
    assert UnifiedCommentReaction.query.filter_by(comment_id=comment.id).one().reaction == "dislike"


def test_reactions_of_several_users_add_up(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    for role in ("user", "owner", "admin"):
        clients[role].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"})

    assert count(UnifiedCommentReaction, comment_id=comment.id, reaction="like") == 3


def test_react_to_deleted_comment_is_refused(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), active=False)

    response = clients["user"].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"})

    assert response.status_code == 400
    assert count(UnifiedCommentReaction) == 0


def test_reactors_lists_who_reacted_without_private_fields(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))
    clients["user"].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"})

    body = clients["anonymous"].get(f"{API}/{comment.uuid}/reactors?type=like").get_json()

    assert body["total"] == 1
    assert [u["id"] for u in body["users"]] == [users.user.id]
    assert set(body["users"][0]) == {"id", "username", "avatar"}


# ── Notifications and mentions ────────────────────────────────────────────────

def test_comment_notifies_the_rule_owner(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post(f"{API}/", json=new_comment(rule))

    assert len(_notifications(users.owner, "rule_comment")) == 1


def test_comment_on_own_rule_notifies_nobody(clients, users):
    rule = make_rule(users.owner)

    clients["owner"].post(f"{API}/", json=new_comment(rule))

    assert count(Notification) == 0


def test_reply_notifies_the_parent_author(clients, users):
    rule = make_rule(users.owner)
    parent = make_comment(users.user, rule)

    clients["admin"].post(f"{API}/", json=new_comment(rule, parent_id=parent.id))

    assert len(_notifications(users.user, "comment_reply")) == 1


def test_mention_notifies_the_mentioned_user(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post(f"{API}/", json=new_comment(rule, f"cc {mention(users.admin)} please look"))

    notifications = _notifications(users.admin, "user_mentioned")
    assert len(notifications) == 1 and f"/rule/detail_rule/{rule.id}" in notifications[0].link


def test_mention_of_yourself_notifies_nobody(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post(f"{API}/", json=new_comment(rule, f"note to self {mention(users.user)}"))

    assert _notifications(users.user, "user_mentioned") == []


def test_mentioning_the_same_user_twice_notifies_once(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post(f"{API}/", json=new_comment(rule, f"{mention(users.admin)} and {mention(users.admin)}"))

    assert len(_notifications(users.admin, "user_mentioned")) == 1


def test_mention_of_an_unknown_user_notifies_nobody(clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, "hello @[Ghost](999999)"))

    assert response.status_code == 201
    assert count(Notification, notif_type="user_mentioned") == 0


def test_mention_on_a_private_bundle_skips_users_who_cannot_see_it(clients, users):
    """A notification would leak the private bundle's name to someone who can't open it."""
    bundle = make_bundle(users.owner, public=False)

    clients["owner"].post(f"{API}/", json=new_comment(bundle, f"hey {mention(users.user)}"))

    assert _notifications(users.user, "user_mentioned") == []


def test_mention_on_a_private_bundle_reaches_who_can_see_it(clients, users):
    bundle = make_bundle(users.owner, public=False)

    clients["admin"].post(f"{API}/", json=new_comment(bundle, f"hey {mention(users.owner)}"))
    clients["owner"].post(f"{API}/", json=new_comment(bundle, f"hey {mention(users.admin)}"))

    assert len(_notifications(users.owner, "user_mentioned")) == 1
    assert len(_notifications(users.admin, "user_mentioned")) == 1


def test_mention_picker_finds_users_but_never_the_requester(clients, users):
    body = clients["user"].get("/account/search_mentionable_users?q=Tester").get_json()

    ids = {u["id"] for u in body["users"]}
    assert users.owner.id in ids and users.admin.id in ids
    assert users.user.id not in ids


def test_mention_picker_returns_only_public_fields(clients, users):
    body = clients["user"].get("/account/search_mentionable_users?q=Owner").get_json()

    assert body["users"] and all(set(u) == {"id", "username", "avatar"} for u in body["users"])


def test_mention_picker_needs_two_characters(clients, users):
    body = clients["user"].get("/account/search_mentionable_users?q=O").get_json()

    assert body == {"users": []}


# ── Comments hub ──────────────────────────────────────────────────────────────

def _hub_groups(client, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(f"{API}/hub?{query}").get_json()["items"]


def test_hub_groups_comments_by_object(clients, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule)
    make_comment(users.user, rule)

    groups = _hub_groups(clients["user"], scope="main")

    assert [(g["object_type"], g["object_id"]) for g in groups] == [("rule", rule.id)]


def test_hub_main_scope_ignores_threads_with_only_replies_matching(clients, users):
    rule = make_rule(users.owner)
    root = make_comment(users.owner, rule, content="plain root")
    make_comment(users.user, rule, parent=root, content="needle in a reply")

    main = _hub_groups(clients["user"], scope="main", search="needle")
    everything = _hub_groups(clients["user"], scope="all", search="needle")

    assert main == [] and len(everything) == 1


def test_hub_never_shows_deleted_comments(clients, users):
    make_comment(users.owner, make_rule(users.owner), active=False)

    assert _hub_groups(clients["admin"], scope="all") == []


# ── Legacy rule comments (/rule/...) ──────────────────────────────────────────

def test_legacy_add_comment_stores_it(clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].get(f"/rule/comment_add?rule_id={rule.id}&content=Hello")

    comment = Comment.query.one()
    assert response.status_code == 200
    assert (comment.rule_id, comment.user_id, comment.content) == (rule.id, users.user.id, "Hello")


def test_legacy_reply_is_listed_under_its_parent(clients, users):
    rule = make_rule(users.owner)
    parent = make_legacy_comment(users.owner, rule)

    clients["user"].get(f"/rule/comment_add?rule_id={rule.id}&content=Reply&parent_comment_id={parent.id}")

    body = clients["anonymous"].get(f"/rule/get_comments?rule_id={rule.id}").get_json()
    assert body["total_comments"] == 1
    assert [r["content"] for r in body["comments"][0]["replies"]] == ["Reply"]


def test_legacy_edit_comment_changes_the_content(clients, users):
    comment = make_legacy_comment(users.owner, make_rule(users.owner))

    clients["owner"].get(f"/rule/edit_comment?comment_id={comment.id}&content=Edited")

    assert reload(comment).content == "Edited"


def test_legacy_delete_comment_removes_it_with_its_replies(clients, users):
    rule = make_rule(users.owner)
    parent = make_legacy_comment(users.owner, rule)
    make_legacy_comment(users.user, rule, parent=parent)

    clients["owner"].get(f"/rule/delete_comment?comment_id={parent.id}")

    assert count(Comment, rule_id=rule.id) == 0


def test_legacy_reaction_toggles_and_switches(clients, users):
    comment = make_legacy_comment(users.owner, make_rule(users.owner))
    url = f"/rule/add_reaction?comment_id={comment.id}&reaction_type="

    clients["user"].get(url + "like")
    clients["user"].get(url + "dislike")

    stored = reload(comment)
    assert (stored.likes, stored.dislikes) == (0, 1)
    assert count(RuleCommentReaction, comment_id=comment.id) == 1

    clients["user"].get(url + "dislike")

    assert (reload(comment).likes, reload(comment).dislikes) == (0, 0)
    assert count(RuleCommentReaction, comment_id=comment.id) == 0


def test_legacy_comment_notifies_the_rule_owner(clients, users):
    rule = make_rule(users.owner)

    clients["user"].get(f"/rule/comment_add?rule_id={rule.id}&content=Hello")

    assert len(_notifications(users.owner, "rule_comment")) == 1
