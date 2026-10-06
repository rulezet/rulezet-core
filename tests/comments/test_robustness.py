"""Comments — layer 4: inputs meant to break Rulezet.

Expected every time: a clean answer (< 500), and either nothing stored or the
text stored as plain text — returned verbatim in JSON, never interpreted.
"""
import pytest

from app.core.db_class.db import Comment, RuleCommentReaction, UnifiedComment, UnifiedCommentReaction
from tests.helpers.comments import API, list_url, make_comment, make_legacy_comment, new_comment
from tests.helpers.db import count, reload
from tests.helpers.inputs import BAD_IDS, BLANK, EMPTY, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests.helpers.rules import make_rule

MAX_LENGTH = 10_000
HOSTILE_TEXT = [*INJECTIONS, *[c for c in ODD_CHARACTERS if "\x00" not in c]]
NOT_A_TEXT = [w for w in WRONG_TYPES if w is not None and not isinstance(w, str)]


# ── Create: content ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("content", [EMPTY, BLANK, TOO_LONG, "A" * (MAX_LENGTH + 1)])
def test_create_comment_with_empty_or_too_long_content_stores_nothing(content, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, content))

    assert response.status_code == 400
    assert count(UnifiedComment) == 0


def test_create_comment_at_the_maximum_length_is_accepted(clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, "A" * MAX_LENGTH))

    assert response.status_code == 201


@pytest.mark.parametrize("content", HOSTILE_TEXT)
def test_create_comment_with_hostile_content_stores_it_verbatim(content, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, content))

    assert response.status_code == 201
    assert UnifiedComment.query.one().content == content.strip()
    assert response.get_json()["comment"]["content"] == content.strip()


def test_create_comment_never_evaluates_a_template(clients, users):
    rule = make_rule(users.owner)
    clients["user"].post(f"{API}/", json=new_comment(rule, "{{7*7}} {% print 7*7 %}"))

    body = clients["anonymous"].get(list_url(rule)).get_json()

    assert body["items"][0]["content"] == "{{7*7}} {% print 7*7 %}"


def test_create_comment_with_a_null_byte_never_stores_it(clients, users):
    """PostgreSQL refuses NUL characters in text — storing one would be a 500 in production."""
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, "null\x00byte"))

    assert response.status_code < 500
    assert all("\x00" not in c.content for c in UnifiedComment.query.all())


@pytest.mark.parametrize("content", NOT_A_TEXT, ids=repr)
def test_create_comment_with_non_text_content_stores_nothing(content, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, content))

    assert response.status_code == 400
    assert count(UnifiedComment) == 0


# ── Create: target and body ───────────────────────────────────────────────────

@pytest.mark.parametrize("object_type", [*NOT_A_TEXT, "", "user", "<script>", "rule; DROP TABLE rule"], ids=repr)
def test_create_comment_on_an_unknown_object_type_stores_nothing(object_type, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, object_type=object_type))

    assert response.status_code == 400
    assert count(UnifiedComment) == 0


@pytest.mark.parametrize("object_id", [*BAD_IDS, None, 1.5, True, [], {}, "²", "１"], ids=repr)
def test_create_comment_on_a_bad_object_id_stores_nothing(object_id, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, object_id=object_id))

    assert 400 <= response.status_code < 500
    assert count(UnifiedComment) == 0


def test_create_comment_on_an_unknown_rule_is_not_found(clients, users):
    response = clients["user"].post(f"{API}/", json={"object_type": "rule", "object_id": 999999, "content": "x"})

    assert response.status_code == 404
    assert count(UnifiedComment) == 0


@pytest.mark.parametrize("parent_id", [*BAD_IDS, 999999, 1.5, [], {}], ids=repr)
def test_create_reply_to_a_bad_parent_stores_nothing(parent_id, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, parent_id=parent_id))

    assert 400 <= response.status_code < 500
    assert count(UnifiedComment) == 0


def test_create_reply_with_the_object_id_as_text_is_threaded_correctly(clients, users):
    """"5" and 5 are the same rule — the parent check must not tell them apart."""
    rule = make_rule(users.owner)
    parent = make_comment(users.owner, rule)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, object_id=str(rule.id), parent_id=parent.id))

    assert response.status_code == 201
    assert UnifiedComment.query.filter_by(parent_id=parent.id).one().object_id == rule.id


@pytest.mark.parametrize("body", ["not json", "[1, 2, 3]", '"text"', "null", "42", ""])
def test_create_comment_with_a_broken_body_stores_nothing(body, clients):
    response = clients["user"].post(f"{API}/", data=body, content_type="application/json")

    assert response.status_code == 400
    assert count(UnifiedComment) == 0


def test_create_comment_ignores_extra_fields(clients, users):
    """Author, state and ids are the server's call, not the client's."""
    rule = make_rule(users.owner)

    clients["user"].post(f"{API}/", json=new_comment(
        rule, created_by=users.admin.id, is_active=False, id=4242, uuid="chosen", depth=7, is_public=False))

    comment = UnifiedComment.query.one()
    assert comment.created_by == users.user.id and comment.is_active
    assert comment.id != 4242 and comment.uuid != "chosen" and comment.depth == 0


# ── Edit ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("content", [EMPTY, BLANK, TOO_LONG, *NOT_A_TEXT], ids=repr)
def test_edit_comment_with_bad_content_leaves_it_unchanged(content, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), content="Original")

    response = clients["owner"].put(f"{API}/{comment.uuid}", json={"content": content})

    assert response.status_code == 400
    assert reload(comment).content == "Original"


@pytest.mark.parametrize("content", HOSTILE_TEXT)
def test_edit_comment_with_hostile_content_stores_it_verbatim(content, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients["owner"].put(f"{API}/{comment.uuid}", json={"content": content})

    assert response.status_code == 200
    assert reload(comment).content == content.strip()


def test_edit_comment_with_a_null_byte_never_stores_it(clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients["owner"].put(f"{API}/{comment.uuid}", json={"content": "null\x00byte"})

    assert response.status_code < 500
    assert "\x00" not in reload(comment).content


@pytest.mark.parametrize("body", ["not json", "[1, 2, 3]", "null", ""])
def test_edit_comment_with_a_broken_body_leaves_it_unchanged(body, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner), content="Original")

    response = clients["owner"].put(f"{API}/{comment.uuid}", data=body, content_type="application/json")

    assert response.status_code == 400
    assert reload(comment).content == "Original"


@pytest.mark.parametrize("uuid", ["no-such-uuid", "A" * 5000, "' OR 1=1 --", "%00", "..%2F..%2Fetc"])
def test_actions_on_an_odd_comment_uuid_are_not_found(uuid, clients):
    responses = [
        clients["admin"].put(f"{API}/{uuid}", json={"content": "x"}),
        clients["admin"].delete(f"{API}/{uuid}"),
        clients["admin"].post(f"{API}/{uuid}/restore"),
        clients["admin"].delete(f"{API}/{uuid}/hard_delete"),
        clients["admin"].post(f"{API}/{uuid}/react", json={"reaction": "like"}),
        clients["admin"].get(f"{API}/{uuid}/reactors"),
    ]

    assert [r.status_code for r in responses] == [404] * len(responses)


# ── Reactions ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("reaction", ["", "love", "LIKE", "<script>", "like" * 100, *NOT_A_TEXT], ids=repr)
def test_react_with_an_unknown_reaction_stores_nothing(reaction, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients["user"].post(f"{API}/{comment.uuid}/react", json={"reaction": reaction})

    assert response.status_code == 400
    assert count(UnifiedCommentReaction) == 0


@pytest.mark.parametrize("body", ["not json", "[1]", "null", ""])
def test_react_with_a_broken_body_stores_nothing(body, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients["user"].post(f"{API}/{comment.uuid}/react", data=body, content_type="application/json")

    assert response.status_code == 400
    assert count(UnifiedCommentReaction) == 0


@pytest.mark.parametrize("reaction_type", ["", "love", "<script>"])
def test_reactors_with_an_unknown_type_is_refused(reaction_type, clients, users):
    comment = make_comment(users.owner, make_rule(users.owner))

    response = clients["anonymous"].get(f"{API}/{comment.uuid}/reactors?type={reaction_type}")

    assert response.status_code == 400


# ── Reading with bad parameters ───────────────────────────────────────────────

@pytest.mark.parametrize("object_id", BAD_IDS, ids=repr)
def test_list_comments_with_a_bad_object_id_never_errors(object_id, clients):
    response = clients["anonymous"].get(f"{API}/?object_type=rule&object_id={object_id}")

    assert 400 <= response.status_code < 500


@pytest.mark.parametrize("object_type", ["", "user", "<script>", "rule'--"])
def test_list_comments_of_an_unknown_object_type_is_refused(object_type, clients, users):
    rule = make_rule(users.owner)

    response = clients["anonymous"].get(f"{API}/?object_type={object_type}&object_id={rule.id}")

    assert response.status_code == 400


@pytest.mark.parametrize("param", ["page", "per_page", "parent_id"])
@pytest.mark.parametrize("value", ["0", "-1", "abc", str(2**31), str(2**63), "1.5"])
def test_list_comments_with_bad_paging_never_errors(param, value, clients, users):
    rule = make_rule(users.owner)
    make_comment(users.owner, rule)

    response = clients["anonymous"].get(list_url(rule, **{param: value}))

    assert response.status_code < 500


@pytest.mark.parametrize("comment_id", ["0", "-1", "abc", str(2**31), str(2**63)])
def test_resolve_a_bad_comment_id_is_not_found(comment_id, clients):
    response = clients["anonymous"].get(f"{API}/resolve/{comment_id}")

    assert response.status_code == 404


@pytest.mark.parametrize("params", [
    "page=0", "page=-1", "page=abc", f"page={2**63}", "per_page=0", "per_page=-5", f"per_page={2**63}",
    "min_comments=-1", f"min_comments={2**63}", "date_from=yesterday", "date_to=2024-13-45",
    "date_from=9999-12-31", "sort=<script>", "dir=sideways", "scope=everything",
    "search=%25", "search=_", "search=%27%20OR%201=1%20--", "search=" + "A" * 5000, "mine=yes",
])
def test_hub_with_bad_parameters_never_errors(params, clients, users):
    make_comment(users.owner, make_rule(users.owner))

    response = clients["user"].get(f"{API}/hub?{params}")

    assert response.status_code < 500


@pytest.mark.parametrize("q", ["%", "_", "' OR 1=1 --", "A" * 5000, "\x00\x00", str(2**63), "²²"])
def test_mention_picker_with_odd_queries_never_errors(q, clients):
    response = clients["user"].get("/account/search_mentionable_users", query_string={"q": q})

    assert response.status_code == 200


# ── Mentions ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("token", ["@[x](0)", "@[x](-1)", f"@[x]({2**63})", "@[x](999999999999)", "@[](1)",
                                   "@[" + "x" * 300 + "](1)", "@[x](abc)"])
def test_odd_mention_tokens_never_error(token, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"{API}/", json=new_comment(rule, f"hey {token}"))

    assert response.status_code == 201


# ── Legacy rule comments (/rule/...) ──────────────────────────────────────────

@pytest.mark.parametrize("rule_id", BAD_IDS, ids=repr)
def test_legacy_add_comment_on_a_bad_rule_id_stores_nothing(rule_id, clients):
    response = clients["user"].get(f"/rule/comment_add?rule_id={rule_id}&content=Hello")

    assert 400 <= response.status_code < 500
    assert count(Comment) == 0


@pytest.mark.parametrize("content", [BLANK, TOO_LONG])
def test_legacy_add_comment_with_blank_or_too_long_content_stores_nothing(content, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].get("/rule/comment_add", query_string={"rule_id": rule.id, "content": content})

    assert response.status_code == 400
    assert count(Comment) == 0


@pytest.mark.parametrize("content", HOSTILE_TEXT)
def test_legacy_add_comment_with_hostile_content_stores_it_verbatim(content, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].get("/rule/comment_add", query_string={"rule_id": rule.id, "content": content})

    assert response.status_code == 200
    assert Comment.query.one().content == content.strip()


def test_legacy_add_comment_with_a_null_byte_never_stores_it(clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].get("/rule/comment_add", query_string={"rule_id": rule.id, "content": "a\x00b"})

    assert response.status_code < 500
    assert all("\x00" not in c.content for c in Comment.query.all())


@pytest.mark.parametrize("parent", ["unknown", "other rule", "abc", str(2**63)])
def test_legacy_reply_to_a_bad_parent_stores_nothing(parent, clients, users):
    rule = make_rule(users.owner)
    if parent == "unknown":
        parent_id = 999999
    elif parent == "other rule":
        parent_id = make_legacy_comment(users.owner, make_rule(users.owner)).id
    else:
        parent_id = parent

    response = clients["user"].get(f"/rule/comment_add?rule_id={rule.id}&content=Reply&parent_comment_id={parent_id}")

    assert 400 <= response.status_code < 500
    assert count(Comment, rule_id=rule.id) == 0


@pytest.mark.parametrize("content", [EMPTY, BLANK, TOO_LONG])
def test_legacy_edit_comment_with_blank_or_too_long_content_leaves_it_unchanged(content, clients, users):
    comment = make_legacy_comment(users.owner, make_rule(users.owner), content="Original")

    response = clients["owner"].get("/rule/edit_comment", query_string={"comment_id": comment.id, "content": content})

    assert response.status_code == 400
    assert reload(comment).content == "Original"


@pytest.mark.parametrize("comment_id", BAD_IDS, ids=repr)
def test_legacy_actions_on_a_bad_comment_id_never_error(comment_id, clients):
    responses = [
        clients["admin"].get(f"/rule/edit_comment?comment_id={comment_id}&content=x"),
        clients["admin"].get(f"/rule/delete_comment?comment_id={comment_id}"),
        clients["admin"].get(f"/rule/add_reaction?comment_id={comment_id}&reaction_type=like"),
    ]

    assert all(400 <= r.status_code < 500 for r in responses), [r.status_code for r in responses]


@pytest.mark.parametrize("reaction_type", ["x" * 51, BLANK])
def test_legacy_react_with_a_bad_reaction_type_stores_nothing(reaction_type, clients, users):
    comment = make_legacy_comment(users.owner, make_rule(users.owner))

    response = clients["user"].get("/rule/add_reaction",
                                   query_string={"comment_id": comment.id, "reaction_type": reaction_type})

    assert response.status_code == 400
    assert count(RuleCommentReaction) == 0


@pytest.mark.parametrize("rule_id", BAD_IDS, ids=repr)
def test_legacy_list_comments_with_a_bad_rule_id_never_errors(rule_id, clients):
    response = clients["anonymous"].get(f"/rule/get_comments?rule_id={rule_id}")

    assert 400 <= response.status_code < 500


@pytest.mark.parametrize("page", ["0", "-1", "abc", str(2**63)])
def test_legacy_list_comments_with_a_bad_page_never_errors(page, clients, users):
    rule = make_rule(users.owner)

    response = clients["anonymous"].get(f"/rule/get_comments?rule_id={rule.id}&page={page}")

    assert response.status_code < 500
