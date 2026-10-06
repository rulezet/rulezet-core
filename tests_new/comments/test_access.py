"""Comments — layer 1: who can do what.

Permission model: a comment thread is exactly as visible as the object it
hangs on — a public rule or bundle's thread is public to read; a private
bundle's thread is for its owner and admins only; a trashed rule's thread is
gone for everyone. Commenting, replying and reacting need an account and a
visible object. A comment is edited or deleted by its author or an admin
(moderation); restoring and permanently deleting are admin-only.

In these tables "owner" is the author of the comment under test, who also owns
the rule / bundle it is posted on; "user" is anyone else.
"""
import pytest

from app import db
from app.core.db_class.db import Comment, RuleCommentReaction, UnifiedComment, UnifiedCommentReaction
from tests_new.helpers.access import FORBIDDEN, LOGIN, NOT_FOUND, OK, assert_outcome, matrix
from tests_new.helpers.comments import (
    API, list_url, make_bundle, make_comment, make_legacy_comment, new_comment, trash,
)
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule

EVERYONE = {"anonymous": OK, "user": OK, "owner": OK, "admin": OK}
LOGGED_IN = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK}
AUTHOR_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}
# A private bundle: its owner and admins see it, nobody else even learns it exists.
PRIVATE_READ = {"anonymous": NOT_FOUND, "user": NOT_FOUND, "owner": OK, "admin": OK}
PRIVATE_WRITE = {"anonymous": LOGIN, "user": NOT_FOUND, "owner": OK, "admin": OK}
# A trashed rule is hidden from everyone, admins included (they use the trash).
TRASHED_READ = {"anonymous": NOT_FOUND, "user": NOT_FOUND, "owner": NOT_FOUND, "admin": NOT_FOUND}
TRASHED_WRITE = {"anonymous": LOGIN, "user": NOT_FOUND, "owner": NOT_FOUND, "admin": NOT_FOUND}


def _public_object(kind, owner):
    return make_rule(owner) if kind == "rule" else make_bundle(owner)


OBJECTS = ["rule", "bundle"]


# ── Reading a thread ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", OBJECTS)
@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_list_comments_on_a_public_object(kind, role, expected, clients, users):
    obj = _public_object(kind, users.owner)
    comment = make_comment(users.owner, obj)

    response = clients[role].get(list_url(obj))

    assert_outcome(response, expected)
    assert [c["uuid"] for c in response.get_json()["items"]] == [comment.uuid]


@pytest.mark.parametrize("role, expected", matrix(PRIVATE_READ))
def test_list_comments_on_a_private_bundle(role, expected, clients, users):
    bundle = make_bundle(users.owner, public=False)
    make_comment(users.owner, bundle, content="owner-only note")

    response = clients[role].get(list_url(bundle))

    assert_outcome(response, expected)
    assert (b"owner-only note" in response.data) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(TRASHED_READ))
def test_list_comments_on_a_trashed_rule(role, expected, clients, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule, content="said before the trash")
    trash(rule)

    response = clients[role].get(list_url(rule))

    assert_outcome(response, expected)
    assert b"said before the trash" not in response.data


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_list_reactors_on_a_public_object(role, expected, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients[role].get(f"{API}/{comment.uuid}/reactors?type=like")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(PRIVATE_READ))
def test_list_reactors_on_a_private_bundle(role, expected, clients, users):
    comment = make_comment(users.owner, make_bundle(users.owner, public=False))

    response = clients[role].get(f"{API}/{comment.uuid}/reactors?type=like")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_resolve_comment_link_on_a_public_object(role, expected, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients[role].get(f"{API}/resolve/{comment.id}")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(PRIVATE_READ))
def test_resolve_comment_link_on_a_private_bundle(role, expected, clients, users):
    comment = make_comment(users.owner, make_bundle(users.owner, public=False))

    response = clients[role].get(f"{API}/resolve/{comment.id}")

    assert_outcome(response, expected)


# ── Creating / replying ───────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", OBJECTS)
@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_comment_on_a_public_object(kind, role, expected, clients, users):
    obj = _public_object(kind, users.owner)

    response = clients[role].post(f"{API}/", json=new_comment(obj))

    assert_outcome(response, expected)
    assert count(UnifiedComment, object_id=obj.id) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(PRIVATE_WRITE))
def test_comment_on_a_private_bundle(role, expected, clients, users):
    bundle = make_bundle(users.owner, public=False)

    response = clients[role].post(f"{API}/", json=new_comment(bundle))

    assert_outcome(response, expected)
    assert count(UnifiedComment, object_type="bundle", object_id=bundle.id) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(TRASHED_WRITE))
def test_comment_on_a_trashed_rule(role, expected, clients, users):
    rule = trash(make_rule(users.owner))

    response = clients[role].post(f"{API}/", json=new_comment(rule))

    assert_outcome(response, expected)
    assert count(UnifiedComment, object_type="rule", object_id=rule.id) == 0


@pytest.mark.parametrize("kind", OBJECTS)
@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_reply_on_a_public_object(kind, role, expected, clients, users):
    obj = _public_object(kind, users.owner)
    parent = make_comment(users.owner, obj)

    response = clients[role].post(f"{API}/", json=new_comment(obj, parent_id=parent.id))

    assert_outcome(response, expected)
    assert count(UnifiedComment, parent_id=parent.id) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(PRIVATE_WRITE))
def test_reply_on_a_private_bundle(role, expected, clients, users):
    bundle = make_bundle(users.owner, public=False)
    parent = make_comment(users.owner, bundle)

    response = clients[role].post(f"{API}/", json=new_comment(bundle, parent_id=parent.id))

    assert_outcome(response, expected)
    assert count(UnifiedComment, parent_id=parent.id) == (1 if expected is OK else 0)


# ── Editing / deleting a comment ──────────────────────────────────────────────

@pytest.mark.parametrize("kind", OBJECTS)
@pytest.mark.parametrize("role, expected", matrix(AUTHOR_OR_ADMIN))
def test_edit_comment(kind, role, expected, clients, users):
    comment = make_comment(users.owner, _public_object(kind, users.owner))

    response = clients[role].put(f"{API}/{comment.uuid}", json={"content": "Edited"})

    assert_outcome(response, expected)
    assert (reload(comment).content == "Edited") is (expected is OK)


@pytest.mark.parametrize("kind", OBJECTS)
@pytest.mark.parametrize("role, expected", matrix(AUTHOR_OR_ADMIN))
def test_delete_comment(kind, role, expected, clients, users):
    comment = make_comment(users.owner, _public_object(kind, users.owner))

    response = clients[role].delete(f"{API}/{comment.uuid}")

    assert_outcome(response, expected)
    assert reload(comment).is_active is not (expected is OK)


def test_edit_own_comment_on_a_bundle_made_private_is_not_found(clients, users):
    """Losing access to the object means losing access to its thread, your own comments included."""
    bundle = make_bundle(users.owner)
    comment = make_comment(users.user, bundle)
    bundle.access = False
    db.session.commit()

    response = clients["user"].put(f"{API}/{comment.uuid}", json={"content": "Edited"})

    assert_outcome(response, NOT_FOUND)
    assert reload(comment).content != "Edited"


def test_delete_own_comment_on_a_bundle_made_private_is_not_found(clients, users):
    bundle = make_bundle(users.owner)
    comment = make_comment(users.user, bundle)
    bundle.access = False
    db.session.commit()

    response = clients["user"].delete(f"{API}/{comment.uuid}")

    assert_outcome(response, NOT_FOUND)
    assert reload(comment).is_active


def test_edit_own_comment_on_a_trashed_rule_is_not_found(clients, users):
    rule = make_rule(users.owner)
    comment = make_comment(users.user, rule)
    trash(rule)

    response = clients["user"].put(f"{API}/{comment.uuid}", json={"content": "Edited"})

    assert_outcome(response, NOT_FOUND)
    assert reload(comment).content != "Edited"


def test_bundle_owner_cannot_delete_someone_elses_comment_on_their_bundle(clients, users):
    """Moderation is for admins — owning the bundle doesn't make you a moderator of its thread."""
    comment = make_comment(users.user, make_bundle(users.owner))

    response = clients["owner"].delete(f"{API}/{comment.uuid}")

    assert_outcome(response, FORBIDDEN)
    assert reload(comment).is_active


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_restore_deleted_comment(role, expected, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), active=False)

    response = clients[role].post(f"{API}/{comment.uuid}/restore")

    assert_outcome(response, expected)
    assert reload(comment).is_active is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_delete_comment_permanently(role, expected, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients[role].delete(f"{API}/{comment.uuid}/hard_delete")

    assert_outcome(response, expected)
    assert (reload(comment) is None) is (expected is OK)


# ── Reactions ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", OBJECTS)
@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_react_to_comment_on_a_public_object(kind, role, expected, clients, users):
    comment = make_comment(users.owner, _public_object(kind, users.owner))

    response = clients[role].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"})

    assert_outcome(response, expected)
    assert count(UnifiedCommentReaction, comment_id=comment.id) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(PRIVATE_WRITE))
def test_react_to_comment_on_a_private_bundle(role, expected, clients, users):
    comment = make_comment(users.owner, make_bundle(users.owner, public=False))

    response = clients[role].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"})

    assert_outcome(response, expected)
    assert count(UnifiedCommentReaction, comment_id=comment.id) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(TRASHED_WRITE))
def test_react_to_comment_on_a_trashed_rule(role, expected, clients, users):
    rule = make_rule(users.owner)
    comment = make_comment(users.owner, rule)
    trash(rule)

    response = clients[role].post(f"{API}/{comment.uuid}/react", json={"reaction": "like"})

    assert_outcome(response, expected)
    assert count(UnifiedCommentReaction, comment_id=comment.id) == 0


# ── Comments hub, counters, mention picker ────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_open_comments_hub_page(role, expected, clients):
    response = clients[role].get("/community/comments")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_list_comments_hub(role, expected, clients, users):
    response = clients[role].get(f"{API}/hub")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_count_my_comments(role, expected, clients):
    response = clients[role].get(f"{API}/my_count")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_search_mentionable_users(role, expected, clients):
    response = clients[role].get("/account/search_mentionable_users?q=Tester")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(PRIVATE_READ))
def test_hub_shows_a_private_bundle_thread_only_to_its_owner_and_admins(role, expected, clients, users):
    bundle = make_bundle(users.owner, public=False)
    make_comment(users.owner, bundle)

    response = clients[role].get(f"{API}/hub?scope=all")

    items = response.get_json()["items"] if response.status_code == 200 else []
    assert any(i["object_type"] == "bundle" and i["object_id"] == bundle.id for i in items) is (expected is OK)


def test_hub_never_shows_a_trashed_rule_thread(clients, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule)
    trash(rule)

    items = clients["admin"].get(f"{API}/hub?scope=all").get_json()["items"]

    assert not any(i["object_type"] == "rule" and i["object_id"] == rule.id for i in items)


# ── Legacy rule comments (/rule/...) ──────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_legacy_list_comments(role, expected, clients, users):
    rule = make_rule(users.owner)
    make_legacy_comment(users.owner, rule)

    response = clients[role].get(f"/rule/get_comments?rule_id={rule.id}")

    assert_outcome(response, expected)
    assert response.get_json()["total_comments"] == 1


@pytest.mark.parametrize("role, expected", matrix(TRASHED_READ))
def test_legacy_list_comments_on_a_trashed_rule(role, expected, clients, users):
    rule = make_rule(users.owner)
    make_legacy_comment(users.owner, rule, content="said before the trash")
    trash(rule)

    response = clients[role].get(f"/rule/get_comments?rule_id={rule.id}")

    assert_outcome(response, expected)
    assert b"said before the trash" not in response.data


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_legacy_add_comment(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].get(f"/rule/comment_add?rule_id={rule.id}&content=Hello")

    assert_outcome(response, expected)
    assert count(Comment, rule_id=rule.id) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(TRASHED_WRITE))
def test_legacy_add_comment_on_a_trashed_rule(role, expected, clients, users):
    rule = trash(make_rule(users.owner))

    response = clients[role].get(f"/rule/comment_add?rule_id={rule.id}&content=Hello")

    assert_outcome(response, expected)
    assert count(Comment, rule_id=rule.id) == 0


@pytest.mark.parametrize("role, expected", matrix(AUTHOR_OR_ADMIN))
def test_legacy_edit_comment(role, expected, clients, users):
    comment = make_legacy_comment(users.owner, make_rule(users.owner))

    response = clients[role].get(f"/rule/edit_comment?comment_id={comment.id}&content=Edited")

    assert_outcome(response, expected)
    assert (reload(comment).content == "Edited") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(AUTHOR_OR_ADMIN))
def test_legacy_delete_comment(role, expected, clients, users):
    comment = make_legacy_comment(users.owner, make_rule(users.owner))

    response = clients[role].get(f"/rule/delete_comment?comment_id={comment.id}")

    assert_outcome(response, expected)
    assert (reload(comment) is None) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_legacy_react_to_comment(role, expected, clients, users):
    comment = make_legacy_comment(users.owner, make_rule(users.owner))

    response = clients[role].get(f"/rule/add_reaction?comment_id={comment.id}&reaction_type=like")

    assert_outcome(response, expected)
    assert count(RuleCommentReaction, comment_id=comment.id) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(TRASHED_WRITE))
def test_legacy_react_to_comment_on_a_trashed_rule(role, expected, clients, users):
    rule = make_rule(users.owner)
    comment = make_legacy_comment(users.owner, rule)
    trash(rule)

    response = clients[role].get(f"/rule/add_reaction?comment_id={comment.id}&reaction_type=like")

    assert_outcome(response, expected)
    assert count(RuleCommentReaction, comment_id=comment.id) == 0
