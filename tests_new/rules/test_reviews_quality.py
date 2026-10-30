"""Rule reviews, quality score and the pages around them — who can do what.

Permission model:
  - anyone reads a rule's reviews; a signed-in user writes one (one per user per rule);
  - a review is edited / deleted by its author, or by an admin — not by the rule's owner;
  - "how it was written" becomes the rule's own only from the owner's / an admin's own review;
  - a review links only a scope its author declared on the rule;
  - re-analysing the score and setting "written with" directly: the owner or an admin.
Admin-only pages (workflow health) and the public read-only share link are checked too.
"""
import pytest

from app import db
from app.core.db_class.notification import Notification
from app.core.db_class.rule import RuleReview, RuleScope
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from tests_new.helpers.db import reload
from tests_new.helpers.rules import make_rule

LOGGED_IN = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK}
OWNER_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
AUTHOR_OR_ADMIN = {"anonymous": LOGIN, "user": OK, "owner": FORBIDDEN, "admin": OK}   # review written by "user"
ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}


def _review(client, rule, **body):
    return client.post(f"/rule/{rule.id}/review", json={"verdict": "approved", **body})


# ── Writing a review ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_write_review(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = _review(clients[role], rule, rating=4)

    assert_outcome(response, expected)
    assert (RuleReview.query.filter_by(rule_id=rule.id).count() == 1) is (expected is OK)


def test_reading_reviews_is_public_and_hides_scopes_from_visitors(clients, users):
    rule = make_rule(users.owner)
    _review(clients["user"], rule)

    data = clients["anonymous"].get(f"/rule/{rule.id}/reviews").get_json()

    assert len(data["reviews"]) == 1
    assert data["can_review"] is False and data["can_moderate"] is False
    assert data["my_scopes"] == [] and data["reviews"][0]["can_edit"] is False


def test_review_rejects_bad_input(clients, users):
    rule = make_rule(users.owner)

    assert _review(clients["user"], rule, verdict="nope").status_code == 400
    assert _review(clients["user"], rule, rating=9).status_code == 400
    assert _review(clients["user"], rule, written_with="robot").status_code == 400
    assert _review(clients["user"], rule, verdict="changes_requested").status_code == 400   # needs a comment


def test_one_review_per_user_per_rule(clients, users):
    rule = make_rule(users.owner)

    _review(clients["user"], rule, rating=2)
    _review(clients["user"], rule, rating=5)

    reviews = RuleReview.query.filter_by(rule_id=rule.id).all()
    assert len(reviews) == 1 and reviews[0].rating == 5


def test_review_on_deleted_rule_is_refused(clients, users):
    rule = make_rule(users.owner)
    rule.is_deleted = True
    db.session.commit()

    assert _review(clients["user"], rule).status_code == 404


# ── Editing / deleting someone's review ───────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(AUTHOR_OR_ADMIN))
def test_edit_review(role, expected, clients, users):
    rule = make_rule(users.owner)
    review_uuid = _review(clients["user"], rule, rating=2).get_json()["my_review"]["uuid"]

    response = _review(clients[role], rule, rating=5, review_uuid=review_uuid)

    assert_outcome(response, expected)
    review = RuleReview.query.filter_by(uuid=review_uuid).first()
    assert review.user_id == users.user.id                     # stays the author's
    assert (review.rating == 5) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(AUTHOR_OR_ADMIN))
def test_delete_review(role, expected, clients, users):
    rule = make_rule(users.owner)
    review_uuid = _review(clients["user"], rule).get_json()["my_review"]["uuid"]

    response = clients[role].delete(f"/rule/review/{review_uuid}")

    assert_outcome(response, expected)
    assert (RuleReview.query.filter_by(uuid=review_uuid).first() is None) is (expected is OK)


# ── What a review may change ──────────────────────────────────────────────────

def test_written_with_is_official_only_from_owner_or_admin(clients, users):
    rule = make_rule(users.owner)

    _review(clients["user"], rule, written_with="ai")
    assert reload(rule).written_with is None

    _review(clients["owner"], rule, written_with="human")
    assert reload(rule).written_with == "human"

    # an admin editing the user's review does not make the user's opinion official
    review_uuid = RuleReview.query.filter_by(rule_id=rule.id, user_id=users.user.id).first().uuid
    _review(clients["admin"], rule, written_with="ai", review_uuid=review_uuid)
    assert reload(rule).written_with == "human"


def test_review_links_only_its_authors_scope(clients, users):
    rule = make_rule(users.owner)
    mine = RuleScope(uuid="s-mine", rule_id=rule.id, user_id=users.user.id, works=True, entries=[])
    theirs = RuleScope(uuid="s-theirs", rule_id=rule.id, user_id=users.owner.id, works=True, entries=[])
    db.session.add_all([mine, theirs])
    db.session.commit()

    assert _review(clients["user"], rule, scope_id=theirs.id).status_code == 400
    assert _review(clients["user"], rule, scope_id=mine.id).status_code == 200


def test_owner_is_notified_of_reviews_by_others_only(clients, users):
    rule = make_rule(users.owner)

    _review(clients["owner"], rule)
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="rule_review").count() == 0

    _review(clients["user"], rule, rating=4)
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="rule_review").count() == 1


def test_review_raises_the_quality_score(clients, users):
    rule = make_rule(users.owner)
    before = clients["anonymous"].get(f"/rule/get_current_rule?rule_id={rule.id}").get_json()["rule"]["quality_score"]

    data = _review(clients["user"], rule).get_json()

    assert data["quality_score"] > before
    assert data["quality_score_breakdown"]["categories"]["review"]["checks"]["approved_by_reviewer"] is True


# ── Owner / admin actions on the score ────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_reanalyse_quality(role, expected, clients, users):
    rule = make_rule(users.owner)

    assert_outcome(clients[role].post(f"/rule/{rule.id}/quality/recompute"), expected)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_set_written_with(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].post(f"/rule/{rule.id}/written_with", json={"written_with": "human_ai"})

    assert_outcome(response, expected)
    assert (reload(rule).written_with == "human_ai") is (expected is OK)


def test_score_is_recomputed_only_when_something_changed(app, users):
    from app.features.rule.rule_quality.quality_score_core import ensure_fresh_quality
    rule = make_rule(users.owner)

    assert ensure_fresh_quality(rule) is True          # never scored
    assert ensure_fresh_quality(rule) is False         # nothing changed
    db.session.add(RuleScope(uuid="s-x", rule_id=rule.id, user_id=users.user.id, works=True, entries=[]))
    db.session.commit()
    assert ensure_fresh_quality(rule) is True          # a scope was declared
    assert rule.quality_score_breakdown["categories"]["field_reports"]["checks"]["works_somewhere"] is True


# ── Admin-only pages and the public share link ────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_workflow_health_is_admin_only(role, expected, clients):
    assert_outcome(clients[role].get("/admin/tasks/workflows/health"), expected)


def test_unknown_share_key_shows_nothing(clients):
    assert clients["anonymous"].get("/workflow/shared/" + "x" * 43).status_code == 404
    assert clients["anonymous"].get("/workflow/shared/short").status_code == 404


@pytest.mark.parametrize("role", ["anonymous", "user", "owner"])
def test_server_settings_env_keys_are_admin_only(role, clients):
    response = clients[role].post("/admin/settings/update_env",
                                  json={"key": "MALWAREBAZAAR_API_KEY", "value": "x"})
    assert response.status_code in (302, 401, 403)


def test_navbar_counters_only_for_signed_in_users(clients):
    page = clients["anonymous"].get("/").get_data(as_text=True)
    assert "window.RZ_NAV" not in page
    page = clients["user"].get("/").get_data(as_text=True)
    assert "window.RZ_NAV" in page and '"reports_to_check": 0' in page
