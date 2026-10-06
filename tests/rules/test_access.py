"""Rules — layer 1: who can do what.

Permission model: every active rule is public to read. Creating, voting,
favoriting and proposing edits need an account. Editing, deleting and
changing a rule's status or metadata are for the owner or an admin. The trash
(restore, permanent delete) is admin-only. `rule.tag_any` adds tagging any
rule, nothing more.
"""
import pytest

from app import db
from app.core.db_class.db import Rule, RuleEditProposal, RuleFavoriteUser, RuleTagAssociation, RuleVote, Tag
from tests.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from tests.helpers.db import count, reload
from tests.helpers.rules import edit_form, make_rule, new_rule_form, yara_rule
from tests.helpers.users import make_user_with_permission

EVERYONE = {"anonymous": OK, "user": OK, "owner": OK, "admin": OK}
LOGGED_IN = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK}
OWNER_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}


def _trashed_rule(owner, admin):
    rule = make_rule(owner)
    rule.is_deleted = True
    rule.deleted_by_id = admin.id
    db.session.commit()
    return rule


# ── Reading ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_view_rule(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].get(f"/rule/detail_rule/{rule.id}")

    assert_outcome(response, expected)
    assert rule.title.encode() in response.data


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_download_rule(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].get(f"/rule/download_rule?rule_id={rule.id}&format=txt")

    assert_outcome(response, expected)
    assert response.get_json()["success"] is True


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_list_my_rules(role, expected, clients, users):
    response = clients[role].get("/rule/get_rules_page_owner?page=1")

    assert_outcome(response, expected)


# ── Creating ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_create_rule(role, expected, clients, users):
    form = new_rule_form()

    response = clients[role].post("/rule/create_rule", data=form)

    assert_outcome(response, expected)
    assert count(Rule, title=form["title"]) == (1 if expected is OK else 0)


# ── Editing ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_open_edit_page(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].get(f"/rule/edit_rule/{rule.id}")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_edit_rule(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, title="Renamed rule"))

    assert_outcome(response, expected)
    assert (reload(rule).title == "Renamed rule") is (expected is OK)


def test_tag_manager_can_only_change_the_metadata_of_someone_elses_rule(client_as, users):
    tagger = make_user_with_permission("rule.tag_any")
    rule = make_rule(users.owner)
    tag = Tag.query.filter_by(name="tlp:clear").one()

    form = edit_form(rule, title="Renamed by the tagger")
    form["tags"] = f'[{{"id": {tag.id}}}]'
    response = client_as(tagger).post(f"/rule/edit_rule/{rule.id}", data=form)

    assert_outcome(response, OK)
    assert reload(rule).title != "Renamed by the tagger"
    assert count(RuleTagAssociation, rule_id=rule.id, tag_id=tag.id) == 1


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_change_rule_status(role, expected, clients, users):
    rule = make_rule(users.owner, status="draft")

    response = clients[role].patch(f"/rule/{rule.id}/status", json={"status": "production"})

    assert_outcome(response, expected)
    assert (reload(rule).status == "production") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_set_rule_tags_quickly(role, expected, clients, users):
    rule = make_rule(users.owner)
    tag = Tag.query.filter_by(name="tlp:clear").one()

    response = clients[role].patch(f"/rule/{rule.id}/quick_meta", json={"tag_ids": [tag.id]})

    assert_outcome(response, expected)
    assert (count(RuleTagAssociation, rule_id=rule.id, tag_id=tag.id) == 1) is (expected is OK)


def test_tag_manager_can_set_tags_but_not_other_metadata(client_as, users):
    tagger = make_user_with_permission("rule.tag_any")
    rule = make_rule(users.owner)
    tag = Tag.query.filter_by(name="tlp:clear").one()

    tags_response = client_as(tagger).patch(f"/rule/{rule.id}/quick_meta", json={"tag_ids": [tag.id]})
    cve_response = client_as(tagger).patch(f"/rule/{rule.id}/quick_meta", json={"cve_ids": ["CVE-2024-1234"]})

    assert_outcome(tags_response, OK)
    assert_outcome(cve_response, FORBIDDEN)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_lock_rule_against_updates(role, expected, clients, users):
    """The "manual submit" lock keeps GitHub updates from overwriting a rule."""
    rule = make_rule(users.owner)

    response = clients[role].get(f"/rule/update_lock/{rule.id}?manuel_submit=true")

    assert_outcome(response, expected)


# ── Deleting (trash) ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_delete_rule(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].post("/rule/delete_rule", json={"id": rule.id})

    assert_outcome(response, expected)
    assert reload(rule).is_deleted is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_delete_several_rules(role, expected, clients, users):
    rules = [make_rule(users.owner), make_rule(users.owner)]

    response = clients[role].post("/rule/delete_rule_list", json={"ids": [r.id for r in rules]})

    assert_outcome(response, expected)
    assert all(reload(r).is_deleted is (expected is OK) for r in rules)


def test_delete_several_rules_refused_when_one_is_not_yours(clients, users):
    mine, theirs = make_rule(users.user), make_rule(users.owner)

    response = clients["user"].post("/rule/delete_rule_list", json={"ids": [mine.id, theirs.id]})

    assert_outcome(response, FORBIDDEN)
    assert not reload(mine).is_deleted and not reload(theirs).is_deleted


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_open_trash(role, expected, clients):
    response = clients[role].get("/rule/trash")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_list_trash(role, expected, clients, users):
    _trashed_rule(users.owner, users.admin)

    response = clients[role].get("/rule/get_trash_rules")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_restore_rule(role, expected, clients, users):
    rule = _trashed_rule(users.owner, users.admin)

    response = clients[role].post(f"/rule/restore/{rule.id}")

    assert_outcome(response, expected)
    assert reload(rule).is_deleted is not (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_delete_rule_permanently(role, expected, clients, users):
    rule = _trashed_rule(users.owner, users.admin)

    response = clients[role].post(f"/rule/permanent_delete/{rule.id}")

    assert_outcome(response, expected)
    assert (reload(rule) is None) is (expected is OK)


# ── Community actions ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_vote_on_rule(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].post("/rule/vote_rule", json={"id": rule.id, "vote_type": "up"})

    assert_outcome(response, expected)
    assert (count(RuleVote, rule_id=rule.id) == 1) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_favorite_rule(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].post(f"/rule/favorite/{rule.id}")

    assert_outcome(response, expected)
    assert (count(RuleFavoriteUser, rule_id=rule.id) == 1) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_propose_an_edit(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].post(f"/rule/propose_edit/{rule.id}",
                                  data={"rule_content": yara_rule("proposed_change"), "message": "fix"})

    assert_outcome(response, expected)
    assert (count(RuleEditProposal, rule_id=rule.id) == 1) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_accept_an_edit_proposal(role, expected, clients, users):
    rule = make_rule(users.owner)
    proposed = yara_rule("accepted_change")
    proposal = RuleEditProposal(rule_id=rule.id, user_id=users.user.id, proposed_content=proposed,
                                old_content=rule.to_string, message="fix", status="pending")
    db.session.add(proposal)
    db.session.commit()

    response = clients[role].get(
        f"/rule/validate_proposal?ruleId={rule.id}&decision=accepted&ruleproposalId={proposal.id}")

    assert_outcome(response, expected)
    assert (reload(rule).to_string == proposed) is (expected is OK)
