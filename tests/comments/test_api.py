"""Comments — layer 3: the REST API (/api/comments/...).

The comment API is the backend of the in-app comment thread (hidden from
Swagger): it works with the browser session only. An X-API-KEY is not a login
here — whatever the key, the request is anonymous, so a key never allows more
than an anonymous visitor gets. "nobody" = no key at all, "bad key" = a key
that matches no account.
"""
import pytest

from app.core.db_class.db import UnifiedComment, UnifiedCommentReaction
from tests.helpers.comments import API, list_url, make_bundle, make_comment, new_comment
from tests.helpers.db import count, reload
from tests.helpers.rules import make_rule
from tests.helpers.users import api_headers

BAD_KEY = {"X-API-KEY": "no-such-key"}
KEYS = ["nobody", "bad key", "user", "owner", "admin"]

COMMENT_FIELDS = {
    "id", "uuid", "content", "parent_id", "depth", "root_id", "object_type", "object_id", "is_public",
    "created_at", "updated_at", "created_by", "is_active", "is_deleted", "deleted_at", "reply_count",
    "like_count", "dislike_count", "user_reaction", "author", "is_admin", "github_issue_url",
    "github_issue_number",
}


def _headers(who, users):
    if who == "nobody":
        return {}
    if who == "bad key":
        return BAD_KEY
    return api_headers(getattr(users, who))


# ── An API key is not a login ─────────────────────────────────────────────────

@pytest.mark.parametrize("who", KEYS)
def test_create_comment_with_only_an_api_key_needs_login(who, app, users):
    rule = make_rule(users.owner)

    response = app.test_client().post(f"{API}/", json=new_comment(rule), headers=_headers(who, users))

    assert response.status_code == 401
    assert count(UnifiedComment) == 0


@pytest.mark.parametrize("who", KEYS)
def test_edit_comment_with_only_an_api_key_needs_login(who, app, users):
    comment = make_comment(users.owner, make_rule(users.owner), content="Original")

    response = app.test_client().put(f"{API}/{comment.uuid}", json={"content": "Edited"},
                                     headers=_headers(who, users))

    assert response.status_code == 401
    assert reload(comment).content == "Original"


@pytest.mark.parametrize("who", KEYS)
def test_delete_comment_with_only_an_api_key_needs_login(who, app, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = app.test_client().delete(f"{API}/{comment.uuid}", headers=_headers(who, users))

    assert response.status_code == 401
    assert reload(comment).is_active


@pytest.mark.parametrize("who", KEYS)
def test_react_with_only_an_api_key_needs_login(who, app, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = app.test_client().post(f"{API}/{comment.uuid}/react", json={"reaction": "like"},
                                      headers=_headers(who, users))

    assert response.status_code == 401
    assert count(UnifiedCommentReaction) == 0


@pytest.mark.parametrize("who", KEYS)
def test_moderation_with_only_an_api_key_needs_login(who, app, users):
    comment = make_comment(users.owner, make_rule(users.owner), active=False)

    restore = app.test_client().post(f"{API}/{comment.uuid}/restore", headers=_headers(who, users))
    hard_delete = app.test_client().delete(f"{API}/{comment.uuid}/hard_delete", headers=_headers(who, users))

    assert restore.status_code == 401 and hard_delete.status_code == 401
    assert reload(comment) is not None and not reload(comment).is_active


@pytest.mark.parametrize("who", KEYS)
def test_private_bundle_thread_stays_hidden_whatever_the_key(who, app, users):
    bundle = make_bundle(users.owner, public=False)
    make_comment(users.owner, bundle)

    response = app.test_client().get(list_url(bundle), headers=_headers(who, users))

    assert response.status_code == 404


@pytest.mark.parametrize("who", KEYS)
def test_public_thread_is_readable_whatever_the_key(who, app, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule)

    response = app.test_client().get(list_url(rule), headers=_headers(who, users))

    assert response.status_code == 200
    assert response.get_json()["total"] == 1


@pytest.mark.parametrize("who", KEYS)
def test_hub_and_counter_with_only_an_api_key_need_login(who, app, users):
    hub = app.test_client().get(f"{API}/hub", headers=_headers(who, users))
    my_count = app.test_client().get(f"{API}/my_count", headers=_headers(who, users))

    assert hub.status_code == 401 and my_count.status_code == 401


# ── Response shapes ───────────────────────────────────────────────────────────

def test_list_response_shape(clients, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule)

    body = clients["user"].get(list_url(rule)).get_json()

    assert set(body) == {"items", "total", "page", "per_page", "has_next"}
    assert set(body["items"][0]) == COMMENT_FIELDS
    assert set(body["items"][0]["author"]) == {"id", "name", "avatar", "initials", "handle"}


def test_list_never_exposes_the_author_email(clients, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule)

    response = clients["anonymous"].get(list_url(rule))

    assert users.owner.email.encode() not in response.data
    assert users.owner.api_key.encode() not in response.data


def test_list_tells_the_viewer_their_own_reaction(clients, users):
    rule = make_rule(users.owner)
    comment = make_comment(users.owner, rule)
    clients["user"].post(f"{API}/{comment.uuid}/react", json={"reaction": "dislike"})

    mine = clients["user"].get(list_url(rule)).get_json()["items"][0]
    theirs = clients["admin"].get(list_url(rule)).get_json()["items"][0]

    assert (mine["user_reaction"], mine["dislike_count"]) == ("dislike", 1)
    assert theirs["user_reaction"] is None


def test_create_response_shape(clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule))

    assert response.status_code == 201
    body = response.get_json()
    assert set(body) == {"message", "comment"}
    assert set(body["comment"]) == COMMENT_FIELDS


def test_edit_response_returns_the_updated_comment(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    body = clients["owner"].put(f"{API}/{comment.uuid}", json={"content": "Edited"}).get_json()

    assert body["comment"]["uuid"] == comment.uuid and body["comment"]["content"] == "Edited"


def test_hub_response_shape(clients, users):
    make_comment(users.owner, make_rule(users.owner))

    body = clients["user"].get(f"{API}/hub").get_json()

    assert {"items", "total", "page", "per_page", "total_pages"} <= set(body)
    assert {"object_type", "object_id", "title", "link", "comment_count", "participants", "preview"} \
        <= set(body["items"][0])


def test_errors_answer_json_with_a_message(clients, users):
    response = clients["user"].post(f"{API}/", json={"object_type": "nope", "object_id": 1, "content": "x"})

    assert response.status_code == 400
    assert "message" in response.get_json()
