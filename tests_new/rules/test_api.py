"""Rules — layer 3: the REST API (/api/rule/...), authenticated with X-API-KEY.

Same rights as the web routes: a user's API key never allows what the user
can't do in the UI. "nobody" = no key at all, "bad key" = a key that matches
no account.
"""
import pytest

from app.core.db_class.db import Rule, RuleFavoriteUser
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule, yara_rule
from tests_new.helpers.users import api_headers

PRIVATE = "/api/rule/private"
PUBLIC = "/api/rule/public"
BAD_KEY = {"X-API-KEY": "no-such-key"}


def _headers(who, users):
    if who == "nobody":
        return {}
    if who == "bad key":
        return BAD_KEY
    return api_headers(getattr(users, who))


def _new_rule(**overrides):
    payload = {"title": "API rule", "format": "yara", "license": "MIT", "version": "1",
               "to_string": yara_rule("api_rule"), "description": "Created through the API"}
    payload.update(overrides)
    return payload


# ── Authentication ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("user", 200), ("admin", 200)])
def test_me_needs_a_valid_key(who, status, app, users):
    response = app.test_client().get(f"{PRIVATE}/me", headers=_headers(who, users))

    assert response.status_code == status


def test_me_identifies_the_key_owner(app, users):
    response = app.test_client().get(f"{PRIVATE}/me", headers=api_headers(users.owner))

    assert response.get_json()["user_id"] == users.owner.id


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("user", 200), ("admin", 200)])
def test_create_rule_needs_a_valid_key(who, status, app, users):
    response = app.test_client().post(f"{PRIVATE}/create", json=_new_rule(), headers=_headers(who, users))

    assert response.status_code == status
    assert count(Rule, title="API rule") == (1 if status == 200 else 0)


def test_create_rule_belongs_to_the_key_owner(app, users):
    response = app.test_client().post(f"{PRIVATE}/create", json=_new_rule(), headers=api_headers(users.owner))

    rule = Rule.query.filter_by(title="API rule").one()
    assert response.get_json()["rule"]["id"] == rule.id
    assert rule.user_id == users.owner.id


@pytest.mark.parametrize("missing", ["title", "format", "to_string", "version", "license"])
def test_create_rule_without_a_required_field_is_refused(missing, app, users):
    payload = _new_rule()
    del payload[missing]

    response = app.test_client().post(f"{PRIVATE}/create", json=payload, headers=api_headers(users.owner))

    assert response.status_code == 400 and missing in response.get_json()["message"]
    assert count(Rule) == 0


def test_create_rule_with_invalid_syntax_is_refused(app, users):
    response = app.test_client().post(f"{PRIVATE}/create", json=_new_rule(to_string="rule broken { condition: }"),
                                      headers=api_headers(users.owner))

    assert response.status_code == 400 and count(Rule) == 0


def test_create_rule_with_existing_content_is_a_conflict(app, users):
    existing = make_rule(users.user)

    response = app.test_client().post(f"{PRIVATE}/create", json=_new_rule(to_string=existing.to_string),
                                      headers=api_headers(users.owner))

    assert response.status_code == 409 and response.get_json()["rule"]["id"] == existing.id
    assert count(Rule) == 1


def test_create_rule_with_a_title_already_used_is_a_conflict(app, users):
    existing = make_rule(users.user)

    response = app.test_client().post(f"{PRIVATE}/create", json=_new_rule(title=existing.title),
                                      headers=api_headers(users.owner))

    assert response.status_code == 409
    assert count(Rule, title=existing.title) == 1


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("user", 403), ("owner", 200), ("admin", 200)])
def test_delete_rule(who, status, app, users):
    rule = make_rule(users.owner)

    response = app.test_client().post(f"{PRIVATE}/delete", json={"rule_id": rule.id}, headers=_headers(who, users))

    assert response.status_code == status
    assert reload(rule).is_deleted is (status == 200)


def test_delete_rule_records_who_deleted_it(app, users):
    rule = make_rule(users.owner)

    app.test_client().post(f"{PRIVATE}/delete", json={"rule_id": rule.id}, headers=api_headers(users.admin))

    assert reload(rule).deleted_by_id == users.admin.id


def test_delete_rule_already_in_the_trash_is_not_found(app, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = app.test_client().post(f"{PRIVATE}/delete", json={"rule_id": rule.id}, headers=api_headers(users.owner))

    assert response.status_code == 404


# ── Favorites ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("user", 200)])
def test_favorite_rule(who, status, app, users):
    rule = make_rule(users.owner)

    response = app.test_client().get(f"{PRIVATE}/favorite/{rule.id}", headers=_headers(who, users))

    assert response.status_code == status
    assert count(RuleFavoriteUser, rule_id=rule.id) == (1 if status == 200 else 0)


def test_favorite_a_trashed_rule_is_not_found(app, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = app.test_client().get(f"{PRIVATE}/favorite/{rule.id}", headers=api_headers(users.user))

    assert response.status_code == 404 and count(RuleFavoriteUser) == 0


# ── Search (private) ──────────────────────────────────────────────────────────

def test_private_search_returns_active_rules_only(app, users):
    active = make_rule(users.owner)
    trashed = make_rule(users.owner, is_deleted=True)

    response = app.test_client().post(f"{PRIVATE}/search", json={"page": 1, "per_page": 50},
                                      headers=api_headers(users.user))

    titles = [r["title"] for r in response.get_json()["rules"]]
    assert active.title in titles and trashed.title not in titles


def test_private_search_needs_a_key(app, users):
    response = app.test_client().post(f"{PRIVATE}/search", json={"page": 1})

    assert response.status_code == 403


# ── Public API (no key) ───────────────────────────────────────────────────────

def test_public_detail_of_an_active_rule(app, users):
    rule = make_rule(users.owner)

    response = app.test_client().get(f"{PUBLIC}/detail/{rule.id}")

    assert response.status_code == 200 and rule.title in response.get_data(as_text=True)


def test_public_detail_of_a_rule_without_source(app, users):
    rule = make_rule(users.owner, source="")

    response = app.test_client().get(f"{PUBLIC}/detail/{rule.id}")

    assert response.status_code == 200


def test_public_detail_of_a_trashed_rule_is_not_found(app, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = app.test_client().get(f"{PUBLIC}/detail/{rule.id}")

    assert response.status_code == 404


def test_public_search_returns_active_rules_only(app, users):
    active = make_rule(users.owner)
    trashed = make_rule(users.owner, is_deleted=True)

    response = app.test_client().get(f"{PUBLIC}/searchPage?per_page=50")

    text = response.get_data(as_text=True)
    assert response.status_code == 200 and active.title in text and trashed.title not in text


def test_public_rules_of_a_user_are_active_only(app, users):
    active = make_rule(users.owner)
    trashed = make_rule(users.owner, is_deleted=True)

    response = app.test_client().get(f"{PUBLIC}/all_by_user/{users.owner.id}")

    text = response.get_data(as_text=True)
    assert active.title in text and trashed.title not in text
