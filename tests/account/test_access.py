"""Account — layer 1: who can do what.

Permission model: "owner" is the account under test. Every logged-in user
manages only their own account — profile, password, API key, favorites —
and no route takes another account's id for that. A profile page and its
public stats are visible to any logged-in user; the private record (email,
admin status, full activity, contributions) only to its owner or an admin.
User management (list, promote / demote, verify, delete, gamification
recompute) is admin-only. Login, registration, password reset, the user card
and the leaderboards are public.
"""
import pytest

from app import db
from app.core.db_class.db import BackgroundJob, Rule, RuleFavoriteUser, User
from tests.helpers.access import FORBIDDEN, LOGIN, NOT_FOUND, OK, assert_outcome, matrix
from tests.helpers.account import captured_mails, give_email_change_token, profile_form
from tests.helpers.db import count, reload
from tests.helpers.rules import make_rule

EVERYONE = {"anonymous": OK, "user": OK, "owner": OK, "admin": OK}
LOGGED_IN = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK}
OWNER_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}


# ── Public pages ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", ["/account/login", "/account/register", "/account/forgot-password"])
def test_open_sign_in_pages_as_anonymous(url, clients):
    response = clients["anonymous"].get(url)

    assert_outcome(response, OK)


@pytest.mark.parametrize("url", ["/account/login", "/account/forgot-password"])
@pytest.mark.parametrize("role", ["user", "admin"])
def test_open_sign_in_pages_when_logged_in_sends_you_away(url, role, clients):
    response = clients[role].get(url)

    assert response.status_code == 302 and "/account/login" not in response.headers["Location"]


def test_register_page_is_gone_when_sign_up_is_disabled(app, clients, monkeypatch):
    monkeypatch.setitem(app.config, "SIGN_UP_ENABLED", False)

    response = clients["anonymous"].get("/account/register")

    assert_outcome(response, NOT_FOUND)


@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_view_user_card(role, expected, clients, users):
    response = clients[role].get(f"/account/user_mini/{users.owner.id}")

    assert_outcome(response, expected)
    assert response.get_json()["id"] == users.owner.id


@pytest.mark.parametrize("role, admin_visible", [("anonymous", False), ("user", False), ("admin", True)])
def test_user_card_shows_admin_status_only_to_admins(role, admin_visible, clients, users):
    response = clients[role].get(f"/account/user_mini/{users.admin.id}")

    assert response.get_json()["is_admin"] is admin_visible


@pytest.mark.parametrize("url", ["/account/leaderboard/global", "/account/leaderboard/category",
                                 "/account/get_total_users"])
@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_view_public_statistics(url, role, expected, clients, users):
    response = clients[role].get(url)

    assert_outcome(response, expected)


# ── Own account ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", ["/account/", "/account/profil", "/account/edit", "/account/favorite",
                                 "/account/contributor", "/account/how_to_earn_points",
                                 "/account/badges_catalog", "/account/my_contributions",
                                 "/account/acces_denied"])
@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_open_own_account_pages(url, role, expected, clients, users):
    response = clients[role].get(url)

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_edit_own_profile(role, expected, clients, users):
    me = getattr(users, role, None)
    form = profile_form(me or users.user, first_name="Renamed")

    response = clients[role].post("/account/edit", data=form)

    assert_outcome(response, expected)
    assert count(User, first_name="Renamed") == (1 if expected is OK else 0)


def test_edit_profile_never_touches_another_account(clients, users):
    """The form has no account id: whatever is posted, only your own changes."""
    form = profile_form(users.owner, first_name="Hijacked")

    clients["user"].post("/account/edit", data=form)

    assert reload(users.owner).first_name == "Owner"


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_regenerate_api_key(role, expected, clients, users):
    response = clients[role].post("/account/regenerate_api_key")

    assert_outcome(response, expected)
    if expected is OK:
        assert reload(getattr(users, role)).api_key == response.get_json()["api_key"] != f"api-key-{role}"


def test_regenerate_api_key_never_changes_another_accounts_key(clients, users):
    clients["user"].post("/account/regenerate_api_key", json={"user_id": users.owner.id})

    assert reload(users.owner).api_key == "api-key-owner"


def test_confirm_email_change_needs_login(clients, users):
    token = give_email_change_token(users.owner, "moved@tests.rulezet")

    response = clients["anonymous"].get(f"/account/confirm-email-change/{token}")

    assert_outcome(response, LOGIN)
    assert reload(users.owner).email == "owner@tests.rulezet"


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_list_own_favorites(role, expected, clients, users):
    response = clients[role].get("/account/favorite/get_rules_page_favorite")

    assert response.status_code in (*expected.statuses, 404)   # 404 = no favorite yet
    if expected is LOGIN:
        assert_outcome(response, LOGIN)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_remove_own_favorite(role, expected, clients, users):
    rule = make_rule(users.admin)
    me = getattr(users, role, None)
    if me:
        db.session.add(RuleFavoriteUser(user_id=me.id, rule_id=rule.id))
        db.session.commit()

    response = clients[role].post(f"/account/favorite/delete_rule?id={rule.id}")

    assert_outcome(response, expected)
    assert count(RuleFavoriteUser, rule_id=rule.id) == 0


def test_remove_favorite_never_removes_another_users_favorite(clients, users):
    rule = make_rule(users.admin)
    db.session.add(RuleFavoriteUser(user_id=users.owner.id, rule_id=rule.id))
    db.session.commit()

    clients["user"].post(f"/account/favorite/delete_rule?id={rule.id}")

    assert count(RuleFavoriteUser, user_id=users.owner.id, rule_id=rule.id) == 1


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_search_users_to_mention(role, expected, clients, users):
    response = clients[role].get("/account/search_mentionable_users?q=Own")

    assert_outcome(response, expected)


def test_mention_search_leaks_no_email_or_admin_status(clients, users):
    found = clients["user"].get("/account/search_mentionable_users?q=Admin").get_json()["users"]

    assert found and all(set(u) == {"id", "username", "avatar"} for u in found)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_logout(role, expected, clients, users):
    response = clients[role].get("/account/logout")

    assert_outcome(response, expected)


# ── Someone's profile ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_view_profile_page(role, expected, clients, users):
    response = clients[role].get(f"/account/detail_user/{users.owner.id}")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, email_visible", [("user", False), ("owner", True), ("admin", True)])
def test_profile_page_shows_the_email_only_to_owner_or_admin(role, email_visible, clients, users):
    page = clients[role].get(f"/account/detail_user/{users.owner.id}").get_data(as_text=True)

    assert ("owner@tests.rulezet" in page) is email_visible


@pytest.mark.parametrize("url", ["/account/get_user?user_id={id}", "/account/get_user_donne?user_id={id}",
                                 "/account/user_contributions/{id}"])
@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_read_private_account_record(url, role, expected, clients, users):
    response = clients[role].get(url.format(id=users.owner.id))

    assert_outcome(response, expected)
    if expected is not OK:
        assert b"owner@tests.rulezet" not in response.data


@pytest.mark.parametrize("url", ["/account/user_activity_stats/{id}", "/account/user_edit_proposals/{id}"])
@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_read_public_profile_stats(url, role, expected, clients, users):
    response = clients[role].get(url.format(id=users.owner.id))

    assert_outcome(response, expected)


# ── User management (admin) ───────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_open_user_management_page(role, expected, clients):
    response = clients[role].get("/account/admin/all_users")

    assert_outcome(response, expected)


@pytest.mark.parametrize("url", ["/account/users_data_table", "/account/get_all_users"])
@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_list_all_users(url, role, expected, clients, users):
    response = clients[role].get(url)

    assert_outcome(response, expected)
    assert (b"owner@tests.rulezet" in response.data) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_promote_user_to_admin(role, expected, clients, users):
    response = clients[role].post("/account/promote_remove_admin",
                                  json={"userId": users.owner.id, "action": "promote"})

    assert_outcome(response, expected)
    assert reload(users.owner).admin is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix({"anonymous": LOGIN, "user": FORBIDDEN, "admin": OK}))
def test_demote_admin(role, expected, clients, users):
    users.owner.admin = True
    db.session.commit()

    response = clients[role].post("/account/promote_remove_admin",
                                  json={"userId": users.owner.id, "action": "remove"})

    assert_outcome(response, expected)
    assert reload(users.owner).admin is not (expected is OK)


def test_admin_cannot_demote_themselves(clients, users):
    """Keeps an instance from losing its last admin by mistake."""
    response = clients["admin"].post("/account/promote_remove_admin",
                                     json={"userId": users.admin.id, "action": "remove"})

    assert response.get_json()["success"] is False
    assert reload(users.admin).admin is True


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_toggle_user_verified(role, expected, clients, users):
    response = clients[role].post("/account/toggle_user_verified", json={"userId": users.owner.id})

    assert_outcome(response, expected)
    assert reload(users.owner).is_verified is not (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_delete_user(role, expected, clients, users):
    victim = users.user if role == "owner" else users.owner

    response = clients[role].post("/account/delete_user", json={"id": victim.id})

    assert_outcome(response, expected)
    assert (reload(victim) is None) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_recompute_gamification(role, expected, clients, users):
    response = clients[role].get("/account/refresh")

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="recompute_gamification") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix({**ADMIN_ONLY, "anonymous": FORBIDDEN}))
def test_ask_whether_you_are_admin(role, expected, clients):
    """A probe used by the frontend: anonymous gets a plain 403, no login page."""
    response = clients[role].get("/account/admin")

    assert_outcome(response, expected)


@pytest.mark.parametrize("url", ["/account/admin/instances", "/account/admin/instances/some-uuid/pulls"])
@pytest.mark.parametrize("role, expected", matrix({"anonymous": LOGIN, "user": NOT_FOUND, "owner": NOT_FOUND,
                                                   "admin": OK}))
def test_registered_instances_on_the_official_instance(url, role, expected, app, clients, monkeypatch):
    monkeypatch.setitem(app.config, "IS_OFFICIAL_INSTANCE", True)

    response = clients[role].get(url)

    assert_outcome(response, expected)


def test_registered_instances_do_not_exist_on_other_instances(app, clients, monkeypatch):
    monkeypatch.setitem(app.config, "IS_OFFICIAL_INSTANCE", False)

    response = clients["admin"].get("/account/admin/instances")

    assert_outcome(response, NOT_FOUND)


# ── Verification codes (anonymous by design: you aren't logged in yet) ────────

def test_resend_code_for_someone_elses_account_is_refused(clients, users):
    from tests.helpers.account import make_pending_user
    pending = make_pending_user(code="111111")

    with captured_mails() as sent:
        clients["user"].post(f"/account/resend-verification-code/{pending.id}")

    assert reload(pending).verification_code == "111111" and sent == []
