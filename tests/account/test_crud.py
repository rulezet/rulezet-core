"""Account — layer 2: the account lifecycle, checked in the DB.

Register → verify the email code → log in / out → reset a forgotten
password → edit the profile (email changes need a confirmation link) →
regenerate the API key → deleted by an admin. Plus single sign-on (OIDC),
favorites and the admin's user management.
"""
import io

import pytest

from app import db
from app.core.db_class.db import Connector, Rule, RuleFavoriteUser, User
from app.features.account import account_core
from tests.helpers.account import (
    NEW_PASSWORD, captured_mails, cookie, drop_cookie, enable_oidc, give_email_change_token, give_reset_token, link_token,
    logged_in_user_id, login, make_pending_user, make_sso_user, password_change, profile_form, register_form,
)
from tests.helpers.db import count, reload
from tests.helpers.rules import make_rule
from tests.helpers.users import PASSWORD


@pytest.fixture
def browser(app, users):
    """A fresh, anonymous browser — for flows that log in for real."""
    return app.test_client()


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_creates_an_unverified_local_account(browser):
    form = register_form()

    with captured_mails():
        response = browser.post("/account/register", data=form)

    user = User.query.filter_by(email=form["email"]).one()
    assert response.headers["Location"] == f"/account/verify/{user.id}"
    assert user.is_verified is False and user.auth_provider == "local"
    assert user.verify_password(form["password"]) and user.api_key


def test_register_mails_the_verification_code(browser):
    form = register_form()

    with captured_mails() as sent:
        browser.post("/account/register", data=form)

    user = User.query.filter_by(email=form["email"]).one()
    assert len(sent) == 1 and sent[0].recipients == [form["email"]]
    assert user.verification_code in sent[0].body


def test_register_does_not_log_you_in(browser):
    with captured_mails():
        browser.post("/account/register", data=register_form())

    assert logged_in_user_id(browser) is None


def test_register_with_an_email_already_used_stores_nothing(browser, users):
    with captured_mails() as sent:
        response = browser.post("/account/register", data=register_form(email=users.owner.email))

    assert response.status_code == 200
    assert count(User, email=users.owner.email) == 1 and sent == []


def test_register_is_refused_when_sign_up_is_disabled(app, browser, monkeypatch):
    monkeypatch.setitem(app.config, "SIGN_UP_ENABLED", False)
    form = register_form()

    response = browser.post("/account/register", data=form)

    assert response.status_code == 404
    assert count(User, email=form["email"]) == 0


# ── Verify the email ──────────────────────────────────────────────────────────

def test_verify_with_the_right_code_verifies_and_logs_in(browser):
    pending = make_pending_user(code="424242")

    response = browser.post(f"/account/verify/{pending.id}", data={"verification_code": "424242"})

    assert response.status_code == 302
    assert reload(pending).is_verified is True
    assert logged_in_user_id(browser) == pending.id


def test_verify_with_a_wrong_code_changes_nothing(browser):
    pending = make_pending_user(code="424242")

    browser.post(f"/account/verify/{pending.id}", data={"verification_code": "000000"})

    assert reload(pending).is_verified is False
    assert logged_in_user_id(browser) is None


def test_verify_after_the_code_expired_deletes_the_pending_account(browser):
    pending = make_pending_user(expired=True)

    response = browser.get(f"/account/verify/{pending.id}")

    assert response.headers["Location"] == "/account/register"
    assert reload(pending) is None


def test_verify_never_deletes_a_verified_account_with_an_old_expiry(browser, users):
    """Regression: anyone could delete a verified account through this page."""
    users.owner.verification_expiration = account_core.datetime.datetime(2000, 1, 1)
    db.session.commit()

    browser.get(f"/account/verify/{users.owner.id}")

    assert reload(users.owner) is not None


def test_verification_code_cannot_log_into_an_account_already_verified(browser):
    """Once verified, the code from the mail must not be a second password."""
    pending = make_pending_user(code="424242")
    first = pending.id
    browser.post(f"/account/verify/{first}", data={"verification_code": "424242"})
    attacker = browser.application.test_client()

    attacker.post(f"/account/verify/{first}", data={"verification_code": "424242"})

    assert logged_in_user_id(attacker) is None


def test_resend_code_gives_a_new_code_by_mail(browser):
    pending = make_pending_user(code="111111")

    with captured_mails() as sent:
        browser.post(f"/account/resend-verification-code/{pending.id}")

    new_code = reload(pending).verification_code
    assert new_code != "111111" and len(sent) == 1 and new_code in sent[0].body


def test_resend_code_for_a_verified_account_does_nothing(browser, users):
    with captured_mails() as sent:
        browser.post(f"/account/resend-verification-code/{users.owner.id}")

    assert reload(users.owner).verification_code is None and sent == []


# ── Log in / log out ──────────────────────────────────────────────────────────

def test_login_with_the_right_password_logs_you_in(browser, users):
    response = login(browser, users.owner.email)

    assert response.headers["Location"] == "/"
    assert logged_in_user_id(browser) == users.owner.id
    assert reload(users.owner).is_connected is True


@pytest.mark.parametrize("email, password", [("owner@tests.rulezet", "Wr0ng-password"),
                                             ("nobody@tests.rulezet", PASSWORD)])
def test_login_with_wrong_credentials_does_not_log_in(email, password, browser, users):
    response = login(browser, email, password)

    assert response.status_code == 200 and b"Invalid email or password" in response.data
    assert logged_in_user_id(browser) is None


def test_login_before_verifying_the_email_sends_you_to_the_verify_page(browser):
    pending = make_pending_user()

    response = login(browser, pending.email)

    assert response.headers["Location"] == f"/account/verify/{pending.id}"
    assert logged_in_user_id(browser) is None


def test_login_of_an_sso_account_with_a_password_is_refused(browser):
    sso = make_sso_user()

    login(browser, sso.email, PASSWORD)

    assert logged_in_user_id(browser) is None


def test_login_goes_back_to_the_page_you_came_from(browser, users):
    response = login(browser, users.owner.email, next="/rule/rules_list")

    assert response.headers["Location"] == "/rule/rules_list"


def test_login_when_already_logged_in_keeps_the_current_account(client_as, users):
    client = client_as(users.user)

    login(client, users.owner.email)

    assert logged_in_user_id(client) == users.user.id


def test_login_is_blocked_after_five_failures_even_with_the_right_password(browser, users):
    for _ in range(5):
        login(browser, users.owner.email, "Wr0ng-password")

    response = login(browser, users.owner.email)

    assert b"Too many failed login attempts" in response.data
    assert logged_in_user_id(browser) is None


def test_login_block_survives_dropping_the_session_cookie(browser, users):
    """The counter is kept on the server, not in the cookie the client controls."""
    for _ in range(5):
        login(browser, users.owner.email, "Wr0ng-password")
        drop_cookie(browser, "session")

    response = login(browser, users.owner.email)

    assert b"Too many failed login attempts" in response.data


def test_successful_login_resets_the_failure_count(browser, users):
    for _ in range(4):
        login(browser, users.owner.email, "Wr0ng-password")
    login(browser, users.owner.email)
    browser.get("/account/logout")
    for _ in range(4):
        login(browser, users.owner.email, "Wr0ng-password")

    login(browser, users.owner.email)

    assert logged_in_user_id(browser) == users.owner.id


def test_logout_ends_the_session(browser, users):
    login(browser, users.owner.email)

    browser.get("/account/logout")

    assert logged_in_user_id(browser) is None
    assert reload(users.owner).is_connected is False
    assert browser.get("/account/edit").status_code == 302


def test_remember_me_sets_a_lasting_cookie(browser, users):
    login(browser, users.owner.email, remember=True)

    assert cookie(browser, "remember_token") is not None


def test_logout_also_ends_a_remember_me_login(browser, users):
    """Regression: the remember-me cookie logged the user straight back in."""
    login(browser, users.owner.email, remember=True)

    browser.get("/account/logout")

    assert cookie(browser, "remember_token") is None
    assert browser.get("/account/edit").status_code == 302


# ── Forgotten password ────────────────────────────────────────────────────────

def test_forgot_password_mails_a_reset_link(browser, users):
    with captured_mails() as sent:
        browser.post("/account/forgot-password", data={"email": users.owner.email})

    assert len(sent) == 1 and sent[0].recipients == [users.owner.email]
    token = link_token(sent[0], "reset-password")
    assert token and reload(users.owner).password_reset_token not in (None, token)   # stored hashed


@pytest.mark.parametrize("email", ["nobody@tests.rulezet", "pending"])
def test_forgot_password_answers_the_same_without_mailing(email, browser, users):
    """No mail for an unknown or unverified address — and no way to tell."""
    if email == "pending":
        email = make_pending_user().email

    with captured_mails() as sent:
        response = browser.post("/account/forgot-password", data={"email": email})

    assert response.headers["Location"] == "/account/forgot-password" and sent == []


def test_forgot_password_never_gives_an_sso_account_a_password(browser):
    sso = make_sso_user()

    with captured_mails() as sent:
        browser.post("/account/forgot-password", data={"email": sso.email})

    assert sent == [] and reload(sso).password_reset_token is None


def test_reset_password_with_a_valid_link_sets_the_new_password(browser, users):
    token = give_reset_token(users.owner)

    response = browser.post(f"/account/reset-password/{token}", data={"password": NEW_PASSWORD,
                                                                      "confirm": NEW_PASSWORD})

    assert response.headers["Location"] == "/account/login"
    owner = reload(users.owner)
    assert owner.verify_password(NEW_PASSWORD) and owner.password_reset_token is None


def test_reset_password_link_works_only_once(browser, users):
    token = give_reset_token(users.owner)
    browser.post(f"/account/reset-password/{token}", data={"password": NEW_PASSWORD, "confirm": NEW_PASSWORD})

    browser.post(f"/account/reset-password/{token}", data={"password": "Th1rd-password", "confirm": "Th1rd-password"})

    assert reload(users.owner).verify_password(NEW_PASSWORD)


def test_reset_password_with_an_expired_link_keeps_the_old_password(browser, users):
    token = give_reset_token(users.owner, expired=True)

    browser.post(f"/account/reset-password/{token}", data={"password": NEW_PASSWORD, "confirm": NEW_PASSWORD})

    owner = reload(users.owner)
    assert owner.verify_password(PASSWORD) and owner.password_reset_token is None


def test_reset_password_never_gives_an_sso_account_a_password(browser):
    sso = make_sso_user()
    token = give_reset_token(sso)

    browser.post(f"/account/reset-password/{token}", data={"password": NEW_PASSWORD, "confirm": NEW_PASSWORD})

    assert reload(sso).password_hash is None


def test_reset_password_with_a_mismatched_confirmation_keeps_the_old_password(browser, users):
    token = give_reset_token(users.owner)

    browser.post(f"/account/reset-password/{token}", data={"password": NEW_PASSWORD, "confirm": "Other-pass1"})

    assert reload(users.owner).verify_password(PASSWORD)


# ── Edit the profile ──────────────────────────────────────────────────────────

def test_edit_profile_stores_every_field(clients, users):
    form = profile_form(users.owner, first_name="Ada", last_name="Lovelace", username="ada.l",
                        bio="Detection engineer", location="Luxembourg",
                        website_url="https://ada.example", github_url="https://github.com/ada",
                        twitter_url="https://x.com/ada")

    response = clients["owner"].post("/account/edit", data=form)

    assert response.headers["Location"] == "/account"
    owner = reload(users.owner)
    assert (owner.first_name, owner.last_name, owner.username) == ("Ada", "Lovelace", "ada.l")
    assert (owner.bio, owner.location) == ("Detection engineer", "Luxembourg")
    assert (owner.website_url, owner.github_url, owner.twitter_url) == (
        "https://ada.example", "https://github.com/ada", "https://x.com/ada")


def test_edit_profile_with_empty_optional_fields_clears_them(clients, users):
    users.owner.bio, users.owner.location = "old bio", "old place"
    db.session.commit()

    clients["owner"].post("/account/edit", data=profile_form(users.owner, bio="", location=""))

    owner = reload(users.owner)
    assert owner.bio is None and owner.location is None


def test_edit_profile_with_a_username_already_taken_changes_nothing(clients, users):
    users.user.username = "taken"
    db.session.commit()

    response = clients["owner"].post("/account/edit", data=profile_form(users.owner, username="taken",
                                                                        first_name="Changed"))

    assert response.status_code == 200
    assert reload(users.owner).username is None and reload(users.owner).first_name == "Owner"


def test_change_password_from_the_profile(clients, users):
    clients["owner"].post("/account/edit", data={**profile_form(users.owner), **password_change()})

    assert reload(users.owner).verify_password(NEW_PASSWORD)


def test_password_fields_are_ignored_without_the_change_password_box(clients, users):
    form = {**profile_form(users.owner), "password": NEW_PASSWORD, "password2": NEW_PASSWORD}

    clients["owner"].post("/account/edit", data=form)

    assert reload(users.owner).verify_password(PASSWORD)


def test_change_password_with_a_mismatched_confirmation_changes_nothing(clients, users):
    form = {**profile_form(users.owner, first_name="Changed"), **password_change(confirm="Other-pass1")}

    response = clients["owner"].post("/account/edit", data=form)

    assert response.status_code == 200
    owner = reload(users.owner)
    assert owner.verify_password(PASSWORD) and owner.first_name == "Owner"


def test_sso_account_cannot_set_a_password_or_change_its_email(client_as):
    sso = make_sso_user()
    form = {**profile_form(sso, email="elsewhere@tests.rulezet", first_name="Renamed"), **password_change()}

    with captured_mails() as sent:
        client_as(sso).post("/account/edit", data=form)

    sso = reload(sso)
    assert sso.first_name == "Renamed"
    assert sso.password_hash is None and sso.email.endswith("@sso.rulezet") and sso.pending_email is None
    assert sent == []


def test_upload_an_avatar(clients, users, tmp_path, monkeypatch):
    monkeypatch.setattr(account_core, "AVATAR_UPLOAD_FOLDER", str(tmp_path))
    form = {**profile_form(users.owner), "profile_picture": (io.BytesIO(b"\x89PNG fake"), "me.png")}

    clients["owner"].post("/account/edit", data=form, content_type="multipart/form-data")

    picture = reload(users.owner).profile_picture
    assert picture.endswith(".png") and picture != "me.png" and (tmp_path / picture).exists()


def test_remove_the_avatar(clients, users, tmp_path, monkeypatch):
    monkeypatch.setattr(account_core, "AVATAR_UPLOAD_FOLDER", str(tmp_path))
    (tmp_path / "old.png").write_bytes(b"x")
    users.owner.profile_picture = "old.png"
    db.session.commit()

    clients["owner"].post("/account/edit", data={**profile_form(users.owner), "remove_avatar": "1"})

    assert reload(users.owner).profile_picture is None and not (tmp_path / "old.png").exists()


# ── Change the email (confirmation link) ──────────────────────────────────────

def test_email_change_waits_for_the_confirmation_link(clients, users):
    with captured_mails() as sent:
        clients["owner"].post("/account/edit", data=profile_form(users.owner, email="moved@tests.rulezet"))

    owner = reload(users.owner)
    assert owner.email == "owner@tests.rulezet" and owner.pending_email == "moved@tests.rulezet"
    assert len(sent) == 1 and sent[0].recipients == ["moved@tests.rulezet"]
    assert link_token(sent[0], "confirm-email-change")


def test_confirmation_link_applies_the_new_email(clients, users):
    token = give_email_change_token(users.owner, "moved@tests.rulezet")

    clients["owner"].get(f"/account/confirm-email-change/{token}")

    owner = reload(users.owner)
    assert owner.email == "moved@tests.rulezet" and owner.pending_email is None and owner.email_change_token is None


def test_expired_confirmation_link_keeps_the_old_email(clients, users):
    token = give_email_change_token(users.owner, "moved@tests.rulezet", expired=True)

    clients["owner"].get(f"/account/confirm-email-change/{token}")

    owner = reload(users.owner)
    assert owner.email == "owner@tests.rulezet" and owner.pending_email is None


def test_confirmation_link_refused_when_the_address_was_taken_meanwhile(clients, users):
    token = give_email_change_token(users.owner, users.user.email)

    clients["owner"].get(f"/account/confirm-email-change/{token}")

    assert reload(users.owner).email == "owner@tests.rulezet"


def test_confirmation_link_of_another_account_changes_nothing(clients, users):
    """The link is for the account that asked for the change, opened while
    logged into it — never applied from someone else's session."""
    token = give_email_change_token(users.owner, "moved@tests.rulezet")

    clients["user"].get(f"/account/confirm-email-change/{token}")

    assert reload(users.owner).email == "owner@tests.rulezet"
    assert reload(users.user).email == "user@tests.rulezet"


def test_email_change_to_an_address_already_used_is_refused(clients, users):
    with captured_mails() as sent:
        response = clients["owner"].post("/account/edit", data=profile_form(users.owner, email=users.user.email))

    assert response.status_code == 200
    assert reload(users.owner).pending_email is None and sent == []


# ── API key ───────────────────────────────────────────────────────────────────

def test_regenerated_api_key_replaces_the_old_one(app, clients, users):
    new_key = clients["owner"].post("/account/regenerate_api_key").get_json()["api_key"]
    api = app.test_client()

    old = api.get("/api/rule/private/me", headers={"X-API-KEY": "api-key-owner"})
    new = api.get("/api/rule/private/me", headers={"X-API-KEY": new_key})

    assert old.status_code == 403 and new.status_code == 200


# ── Favorites ─────────────────────────────────────────────────────────────────

def _favorite(user, rule):
    db.session.add(RuleFavoriteUser(user_id=user.id, rule_id=rule.id))
    db.session.commit()


def test_favorites_list_shows_your_favorite_rules(clients, users):
    rule = make_rule(users.admin)
    _favorite(users.owner, rule)

    listed = clients["owner"].get("/account/favorite/get_rules_page_favorite").get_json()["rule"]

    assert [r["id"] for r in listed] == [rule.id]


def test_favorites_list_hides_trashed_rules(clients, users):
    kept, trashed = make_rule(users.admin), make_rule(users.admin, is_deleted=True)
    _favorite(users.owner, kept)
    _favorite(users.owner, trashed)

    listed = clients["owner"].get("/account/favorite/get_rules_page_favorite").get_json()["rule"]

    assert [r["id"] for r in listed] == [kept.id]


def test_remove_a_favorite(clients, users):
    rule = make_rule(users.admin)
    _favorite(users.owner, rule)

    response = clients["owner"].post(f"/account/favorite/delete_rule?id={rule.id}")

    assert response.get_json()["success"] is True
    assert count(RuleFavoriteUser, user_id=users.owner.id) == 0


# ── Profile data ──────────────────────────────────────────────────────────────

def test_account_record_counts_only_active_rules(clients, users):
    make_rule(users.owner)
    make_rule(users.owner, is_deleted=True)

    data = clients["owner"].get(f"/account/get_user_donne?user_id={users.owner.id}").get_json()["donne"]

    assert data["rule_count"] == 1


def test_activity_stats_count_only_active_rules(clients, users):
    make_rule(users.owner, vote_up=3)
    make_rule(users.owner, is_deleted=True, vote_up=5)

    stats = clients["user"].get(f"/account/user_activity_stats/{users.owner.id}").get_json()["activity_stats"]

    assert stats["total_rules"] == 1 and stats["rules_likes"] == 3


def test_my_contributions_creates_the_points_profile(clients, users):
    data = clients["owner"].get("/account/my_contributions").get_json()

    assert data["user_stats"]["user_id"] == users.owner.id


# ── User management (admin) ───────────────────────────────────────────────────

def test_admin_promotes_then_demotes_a_user(clients, users):
    clients["admin"].post("/account/promote_remove_admin", json={"userId": users.owner.id, "action": "promote"})
    promoted = reload(users.owner).admin
    clients["admin"].post("/account/promote_remove_admin", json={"userId": users.owner.id, "action": "remove"})

    assert promoted is True and reload(users.owner).admin is False


def test_admin_toggles_the_verified_badge(clients, users):
    response = clients["admin"].post("/account/toggle_user_verified", json={"userId": users.owner.id})

    assert response.get_json()["verified"] is False and reload(users.owner).is_verified is False


def test_deleting_a_user_hands_their_rules_to_the_default_account(clients, users):
    rule = make_rule(users.owner)
    default_user = account_core.get_default_user()

    response = clients["admin"].post("/account/delete_user", json={"id": users.owner.id})

    assert response.status_code == 200
    assert reload(users.owner) is None
    assert reload(rule).user_id == default_user.id


def test_deleting_a_system_connectors_account_is_refused(clients, users):
    db.session.add(Connector(uuid="c-1", name="Official", connector_type="rulezet", instance_url="https://x",
                             owner_id=users.admin.id, shadow_user_id=users.owner.id, is_system=True))
    db.session.commit()

    response = clients["admin"].post("/account/delete_user", json={"id": users.owner.id})

    assert response.status_code == 400 and reload(users.owner) is not None


def test_users_table_searches_by_name_or_email(clients, users):
    items = clients["admin"].get("/account/users_data_table?search=owner@").get_json()["items"]

    assert [u["id"] for u in items] == [users.owner.id]


def test_users_table_counts_only_active_rules(clients, users):
    make_rule(users.owner)
    make_rule(users.owner, is_deleted=True)

    items = clients["admin"].get("/account/users_data_table?search=owner@").get_json()["items"]

    assert items[0]["rule_count"] == 1


def test_users_table_filters_admins(clients, users):
    items = clients["admin"].get("/account/users_data_table?admin=true").get_json()["items"]

    assert {u["id"] for u in items} == {u.id for u in User.query.filter_by(admin=True)}


# ── Single sign-on (OIDC) ─────────────────────────────────────────────────────

def test_sso_login_redirects_to_the_provider(app, browser, monkeypatch):
    fake = enable_oidc(app, monkeypatch)

    response = browser.get("/account/oidc/login")

    assert response.status_code == 302 and response.headers["Location"].startswith("https://idp.example.com/")
    assert fake.redirects[0].endswith("/account/oidc/authorize")


@pytest.mark.parametrize("url", ["/account/oidc/login", "/account/oidc/authorize"])
def test_sso_routes_do_not_exist_when_sso_is_off(url, app, browser, monkeypatch):
    monkeypatch.setitem(app.config, "OIDC_ENABLED", False)

    assert browser.get(url).status_code == 404


@pytest.mark.parametrize("role, is_admin", [("editor", False), ("admin", True)])
def test_first_sso_login_creates_the_account(role, is_admin, app, browser, monkeypatch):
    enable_oidc(app, monkeypatch, role=role, sub="sub-new", email="new@idp.example")

    response = browser.get("/account/oidc/authorize")

    user = User.query.filter_by(auth_data="sub-new").one()
    assert response.headers["Location"] == "/"
    assert user.auth_provider == "oidc" and user.email == "new@idp.example" and user.admin is is_admin
    assert user.is_verified is True and user.password_hash is None
    assert logged_in_user_id(browser) == user.id


def test_sso_login_again_reuses_the_same_account(app, browser, monkeypatch):
    enable_oidc(app, monkeypatch, sub="sub-1")
    browser.get("/account/oidc/authorize")
    browser.get("/account/logout")

    browser.get("/account/oidc/authorize")

    assert count(User, auth_data="sub-1") == 1


def test_sso_login_without_a_rulezet_group_is_refused(app, browser, monkeypatch):
    enable_oidc(app, monkeypatch, role="none", sub="sub-outsider")

    response = browser.get("/account/oidc/authorize")

    assert "/account/login" in response.headers["Location"]
    assert count(User, auth_data="sub-outsider") == 0


@pytest.mark.parametrize("missing", ["email", "sub"])
def test_sso_login_without_email_or_subject_is_refused(missing, app, browser, monkeypatch):
    enable_oidc(app, monkeypatch, **{missing: None})

    response = browser.get("/account/oidc/authorize")

    assert "/account/login" in response.headers["Location"] and count(User, auth_provider="oidc") == 0


def test_sso_login_never_takes_over_a_local_account_with_the_same_email(app, browser, monkeypatch, users):
    enable_oidc(app, monkeypatch, email=users.owner.email)

    response = browser.get("/account/oidc/authorize")

    assert "/account/login" in response.headers["Location"]
    assert logged_in_user_id(browser) is None and count(User, email=users.owner.email) == 1


def test_sso_login_with_another_subject_never_logs_into_an_existing_sso_account(app, browser, monkeypatch):
    existing = make_sso_user("first", sub="sub-first")
    enable_oidc(app, monkeypatch, email=existing.email, sub="sub-other")

    browser.get("/account/oidc/authorize")

    assert logged_in_user_id(browser) is None and count(User, email=existing.email) == 1


def test_sso_admin_rights_follow_the_idp_groups(app, browser, monkeypatch):
    sso = make_sso_user(sub="sub-demote", admin=True)
    enable_oidc(app, monkeypatch, role="editor", sub="sub-demote", email=sso.email)

    browser.get("/account/oidc/authorize")

    assert reload(sso).admin is False


def test_sso_email_change_at_the_idp_follows_the_same_account(app, browser, monkeypatch):
    sso = make_sso_user(sub="sub-mail")
    enable_oidc(app, monkeypatch, sub="sub-mail", email="changed@idp.example")

    browser.get("/account/oidc/authorize")

    assert reload(sso).email == "changed@idp.example" and count(User, auth_data="sub-mail") == 1


def test_sso_email_change_to_an_address_already_used_is_refused(app, browser, monkeypatch, users):
    sso = make_sso_user(sub="sub-clash")
    enable_oidc(app, monkeypatch, sub="sub-clash", email=users.owner.email)

    browser.get("/account/oidc/authorize")

    assert logged_in_user_id(browser) is None and reload(sso).email.endswith("@sso.rulezet")


def test_sso_keycloak_group_paths_are_understood(app, browser, monkeypatch):
    enable_oidc(app, monkeypatch, sub="sub-path", groups=["/" + app.config.get("OIDC_GROUP_ADMIN", "RulezetAdmin")])

    browser.get("/account/oidc/authorize")

    assert User.query.filter_by(auth_data="sub-path").one().admin is True


def test_sso_failure_at_the_provider_goes_back_to_login(app, browser, monkeypatch):
    fake = enable_oidc(app, monkeypatch)
    fake.error = RuntimeError("mismatching_state")

    response = browser.get("/account/oidc/authorize")

    assert "/account/login" in response.headers["Location"] and logged_in_user_id(browser) is None


def test_sso_without_a_validated_id_token_is_refused(app, browser, monkeypatch):
    fake = enable_oidc(app, monkeypatch)
    fake.claims = None

    response = browser.get("/account/oidc/authorize")

    assert "/account/login" in response.headers["Location"] and logged_in_user_id(browser) is None


def test_sso_comes_back_to_the_page_you_started_from(app, browser, monkeypatch):
    enable_oidc(app, monkeypatch)
    browser.get("/account/oidc/login?next=/rule/rules_list")

    response = browser.get("/account/oidc/authorize")

    assert response.headers["Location"] == "/rule/rules_list"
