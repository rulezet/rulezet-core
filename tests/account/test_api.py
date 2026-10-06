"""Account — layer 3: the REST API (/api/account/...).

Public: register. Private (X-API-KEY): edit your own account, list and remove
your favorites. Same rights as the web pages: a key acts only on the account
it belongs to. "nobody" = no key at all, "bad key" = a key that matches no
account.
"""
import pytest

from app import db
from app.core.db_class.db import RuleFavoriteUser, User
from tests.helpers.account import captured_mails, make_sso_user, register_form
from tests.helpers.db import count, reload
from tests.helpers.rules import make_rule
from tests.helpers.users import PASSWORD, api_headers

PUBLIC = "/api/account/public"
PRIVATE = "/api/account/private"
BAD_KEY = {"X-API-KEY": "no-such-key"}
API_PASSWORD = "Passw0rd@api"   # the API also wants one of @$!%*?&


def _headers(who, users):
    if who == "nobody":
        return {}
    if who == "bad key":
        return BAD_KEY
    return api_headers(getattr(users, who))


def _edit(user, **changes):
    payload = {"first_name": user.first_name, "last_name": user.last_name, "email": user.email}
    payload.update(changes)
    return payload


def _favorite(user, rule):
    db.session.add(RuleFavoriteUser(user_id=user.id, rule_id=rule.id))
    db.session.commit()


@pytest.fixture
def api(app, users):
    return app.test_client()


# ── Register (public) ─────────────────────────────────────────────────────────

def test_register_creates_an_unverified_account_and_returns_its_key(api):
    form = register_form()

    with captured_mails() as sent:
        response = api.post(f"{PUBLIC}/register", json=form)

    user = User.query.filter_by(email=form["email"]).one()
    assert response.status_code == 201 and response.get_json()["X-API-KEY"] == user.api_key
    assert user.is_verified is False and user.verify_password(form["password"])
    assert len(sent) == 1 and user.verification_code in sent[0].body


def test_register_with_an_email_already_used_is_a_conflict(api, users):
    response = api.post(f"{PUBLIC}/register", json=register_form(email=users.owner.email))

    assert response.status_code == 409
    assert count(User, email=users.owner.email) == 1


@pytest.mark.parametrize("missing", ["email", "password", "first_name", "last_name"])
def test_register_without_a_required_field_is_refused(missing, api):
    form = register_form()
    del form[missing]

    response = api.post(f"{PUBLIC}/register", json=form)

    assert response.status_code == 400
    assert count(User, auth_provider="local", is_verified=False) == 0


def test_register_is_refused_when_sign_up_is_disabled(app, api, monkeypatch):
    """The API must not be a way around a closed sign-up."""
    monkeypatch.setitem(app.config, "SIGN_UP_ENABLED", False)
    form = register_form()

    response = api.post(f"{PUBLIC}/register", json=form)

    assert response.status_code in (403, 404)
    assert count(User, email=form["email"]) == 0


# ── Edit your account (private) ───────────────────────────────────────────────

@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("owner", 200), ("admin", 200)])
def test_edit_needs_a_valid_key(who, status, api, users):
    me = users.owner if who in ("nobody", "bad key") else getattr(users, who)

    response = api.post(f"{PRIVATE}/edit", json=_edit(me, first_name="Renamed"), headers=_headers(who, users))

    assert response.status_code == status
    assert count(User, first_name="Renamed") == (1 if status == 200 else 0)


def test_edit_changes_only_the_key_owners_account(api, users):
    response = api.post(f"{PRIVATE}/edit", json=_edit(users.owner, first_name="Hijacked"),
                        headers=api_headers(users.user))

    assert response.status_code in (200, 409)
    assert reload(users.owner).first_name == "Owner"


def test_edit_keeps_the_profile_fields_it_does_not_send(api, users):
    users.owner.username, users.owner.bio, users.owner.website_url = "owner.name", "My bio", "https://o.example"
    db.session.commit()

    api.post(f"{PRIVATE}/edit", json=_edit(users.owner, first_name="Renamed"), headers=api_headers(users.owner))

    owner = reload(users.owner)
    assert owner.first_name == "Renamed"
    assert (owner.username, owner.bio, owner.website_url) == ("owner.name", "My bio", "https://o.example")


def test_edit_changes_the_password(api, users):
    response = api.post(f"{PRIVATE}/edit", json=_edit(users.owner, password=API_PASSWORD),
                        headers=api_headers(users.owner))

    assert response.status_code == 200 and reload(users.owner).verify_password(API_PASSWORD)


def test_edit_email_waits_for_the_confirmation_link(api, users):
    with captured_mails() as sent:
        response = api.post(f"{PRIVATE}/edit", json=_edit(users.owner, email="moved@tests.rulezet"),
                            headers=api_headers(users.owner))

    owner = reload(users.owner)
    assert response.status_code == 200
    assert owner.email == "owner@tests.rulezet" and owner.pending_email == "moved@tests.rulezet"
    assert len(sent) == 1 and sent[0].recipients == ["moved@tests.rulezet"]


def test_edit_email_already_used_is_a_conflict(api, users):
    response = api.post(f"{PRIVATE}/edit", json=_edit(users.owner, email=users.user.email),
                        headers=api_headers(users.owner))

    assert response.status_code == 409
    assert reload(users.owner).pending_email is None


def test_edit_never_gives_an_sso_account_a_password_or_a_new_email(api):
    sso = make_sso_user()

    with captured_mails() as sent:
        api.post(f"{PRIVATE}/edit", json=_edit(sso, email="elsewhere@tests.rulezet", password=API_PASSWORD),
                 headers=api_headers(sso))

    sso = reload(sso)
    assert sso.password_hash is None and sso.pending_email is None and sent == []


# ── Favorites (private) ───────────────────────────────────────────────────────

@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("owner", 200)])
def test_list_favorites_needs_a_valid_key(who, status, api, users):
    _favorite(users.owner, make_rule(users.admin))

    response = api.get(f"{PRIVATE}/favorite/get_rules_page_favorite", headers=_headers(who, users))

    assert response.status_code == status


def test_list_favorites_returns_the_key_owners_active_favorites(api, users):
    mine, trashed, theirs = make_rule(users.admin), make_rule(users.admin, is_deleted=True), make_rule(users.admin)
    _favorite(users.owner, mine)
    _favorite(users.owner, trashed)
    _favorite(users.user, theirs)

    response = api.get(f"{PRIVATE}/favorite/get_rules_page_favorite", headers=api_headers(users.owner))

    assert [r["id"] for r in response.get_json()["rule"]] == [mine.id]


def test_list_favorites_when_there_is_none_is_empty(api, users):
    response = api.get(f"{PRIVATE}/favorite/get_rules_page_favorite", headers=api_headers(users.owner))

    assert response.status_code == 200 and response.get_json()["rule"] == []


@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("owner", 200)])
def test_remove_favorite_needs_a_valid_key(who, status, api, users):
    rule = make_rule(users.admin)
    _favorite(users.owner, rule)

    response = api.post(f"{PRIVATE}/favorite/delete_rule?id={rule.id}", headers=_headers(who, users))

    assert response.status_code == status
    assert count(RuleFavoriteUser, user_id=users.owner.id) == (0 if status == 200 else 1)


def test_remove_favorite_never_touches_another_users_favorite(api, users):
    rule = make_rule(users.admin)
    _favorite(users.owner, rule)

    api.post(f"{PRIVATE}/favorite/delete_rule?id={rule.id}", headers=api_headers(users.user))

    assert count(RuleFavoriteUser, user_id=users.owner.id) == 1
