"""Account — layer 4: inputs meant to break Rulezet.

Expected every time: a clean answer (< 500), nothing half-written, no account
taken over, no redirect to another site, and text stored as plain text —
escaped when it is displayed. Field limits follow the DB columns (names and
email: 64 characters) so PostgreSQL never has to refuse a value.
"""
import io

import pytest

from app import db
from app.core.db_class.db import RuleFavoriteUser, User
from tests.helpers.account import (
    NEW_PASSWORD, captured_mails, enable_oidc, give_reset_token, logged_in_user_id, login, make_pending_user,
    password_change, profile_form, register_form,
)
from tests.helpers.db import count, reload
from tests.helpers.inputs import BAD_IDS, BLANK, EMPTY, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests.helpers.rules import make_rule
from tests.helpers.users import PASSWORD, api_headers

WEAK_PASSWORDS = ["short1A", "alllowercase1", "ALLUPPERCASE1", "NoDigitsHere", "A1" + "a" * 63, EMPTY]
BAD_EMAILS = ["not-an-email", "@tests.rulezet", "a@", "a b@tests.rulezet", EMPTY, BLANK,
              "x" * 60 + "@tests.rulezet"]                     # the last one: valid but longer than 64
OPEN_REDIRECTS = ["http://evil.example", "https://evil.example/phish", "//evil.example", "/\\evil.example",
                  "\\\\evil.example", "javascript:alert(1)", "https:evil.example", "/%0d%0aLocation:evil"]
HUGE_ID = 2**63


@pytest.fixture
def browser(app, users):
    return app.test_client()


# ── Register ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("password", WEAK_PASSWORDS)
def test_register_with_a_weak_password_stores_nothing(password, browser):
    form = register_form(password=password)

    response = browser.post("/account/register", data=form)

    assert response.status_code == 200
    assert count(User, email=form["email"]) == 0


@pytest.mark.parametrize("email", BAD_EMAILS)
def test_register_with_a_bad_email_stores_nothing(email, browser):
    response = browser.post("/account/register", data=register_form(email=email))

    assert response.status_code == 200
    assert count(User, is_verified=False) == 0


@pytest.mark.parametrize("name", [EMPTY, BLANK, TOO_LONG, "A" * 65])
def test_register_with_a_missing_or_too_long_name_stores_nothing(name, browser):
    response = browser.post("/account/register", data=register_form(first_name=name))

    assert response.status_code == 200
    assert count(User, is_verified=False) == 0


@pytest.mark.parametrize("name", [*INJECTIONS, *ODD_CHARACTERS])
def test_register_with_a_hostile_name_never_errors(name, browser):
    with captured_mails():
        response = browser.post("/account/register", data=register_form(last_name=name))

    assert response.status_code < 500


def test_register_with_the_same_email_in_capitals_creates_a_second_account(browser, users):
    """Current behaviour, a product decision is pending: emails are compared
    case-sensitively, so "OWNER@…" registers next to "owner@…"."""
    with captured_mails():
        browser.post("/account/register", data=register_form(email=users.owner.email.upper()))

    assert count(User, email=users.owner.email.upper()) == 1


# ── Log in ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("target", OPEN_REDIRECTS)
def test_login_never_redirects_to_another_site(target, browser, users):
    response = login(browser, users.owner.email, next=target)

    assert response.headers["Location"] == "/"


@pytest.mark.parametrize("target", OPEN_REDIRECTS)
def test_sso_login_never_redirects_to_another_site(target, app, browser, monkeypatch):
    enable_oidc(app, monkeypatch)
    browser.get(f"/account/oidc/login?next={target}")

    response = browser.get(f"/account/oidc/authorize?next={target}")

    assert response.headers["Location"] == "/"


@pytest.mark.parametrize("email, password", [(TOO_LONG, PASSWORD), ("owner@tests.rulezet", TOO_LONG),
                                             ("' OR 1=1 --", "' OR 1=1 --"),
                                             ("owner@tests.rulezet", "' OR '1'='1"),
                                             ("owner@tests.rulezet", EMPTY)])
def test_login_with_hostile_credentials_never_logs_in(email, password, browser, users):
    response = login(browser, email, password)

    assert response.status_code < 500
    assert logged_in_user_id(browser) is None


def test_sso_login_with_hostile_claims_never_errors(app, browser, monkeypatch):
    enable_oidc(app, monkeypatch, sub=TOO_LONG, email="x" * 60 + "@idp.example", given_name=TOO_LONG,
                family_name="<script>alert(1)</script>", preferred_username=TOO_LONG)

    response = browser.get("/account/oidc/authorize")

    assert response.status_code < 500


@pytest.mark.parametrize("groups", ["RulezetEditor", None, 42, {"a": 1}])
def test_sso_login_with_oddly_typed_groups_never_errors(groups, app, browser, monkeypatch):
    enable_oidc(app, monkeypatch, groups=groups)

    response = browser.get("/account/oidc/authorize")

    assert response.status_code < 500


# ── Verify / resend ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("code", [EMPTY, TOO_LONG, "12345", "1234567", *INJECTIONS])
def test_verify_with_a_bad_code_verifies_nothing(code, browser):
    pending = make_pending_user(code="424242")

    response = browser.post(f"/account/verify/{pending.id}", data={"verification_code": code})

    assert response.status_code < 500
    assert reload(pending).is_verified is False and logged_in_user_id(browser) is None


@pytest.mark.parametrize("url", ["/account/verify/{id}", "/account/resend-verification-code/{id}"])
@pytest.mark.parametrize("user_id", [999999, HUGE_ID])
def test_verify_or_resend_for_an_unknown_account_never_errors(url, user_id, browser):
    response = browser.post(url.format(id=user_id))

    assert response.status_code < 500


# ── Password reset ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("token", ["not-a-token", "A" * 5000, "%00", "..%2F..%2Fetc"])
def test_reset_password_with_a_bad_link_changes_nothing(token, browser, users):
    response = browser.post(f"/account/reset-password/{token}", data={"password": NEW_PASSWORD,
                                                                      "confirm": NEW_PASSWORD})

    assert response.status_code < 500
    assert reload(users.owner).verify_password(PASSWORD)


@pytest.mark.parametrize("password", WEAK_PASSWORDS)
def test_reset_password_to_a_weak_password_changes_nothing(password, browser, users):
    token = give_reset_token(users.owner)

    browser.post(f"/account/reset-password/{token}", data={"password": password, "confirm": password})

    owner = reload(users.owner)
    assert owner.verify_password(PASSWORD) and owner.password_reset_token is not None


@pytest.mark.parametrize("email", [TOO_LONG, *INJECTIONS])
def test_forgot_password_with_a_hostile_email_never_errors(email, browser, users):
    with captured_mails() as sent:
        response = browser.post("/account/forgot-password", data={"email": email})

    assert response.status_code < 500 and sent == []


# ── Edit the profile ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["website_url", "github_url", "twitter_url"])
@pytest.mark.parametrize("url", ["javascript:alert(document.cookie)", "JavaScript:alert(1)",
                                 " javascript:alert(1)", "data:text/html,<script>alert(1)</script>",
                                 "vbscript:msgbox(1)", "not a url"])
def test_profile_links_must_be_web_addresses(field, url, clients, users):
    """A profile link is shown to every visitor as a clickable href."""
    clients["owner"].post("/account/edit", data=profile_form(users.owner, **{field: url}))

    assert getattr(reload(users.owner), field) is None


@pytest.mark.parametrize("field, value", [("first_name", "A" * 65), ("last_name", TOO_LONG), ("first_name", BLANK),
                                          ("bio", "B" * 501), ("location", "L" * 129), ("username", "ab"),
                                          ("website_url", "https://x.example/" + "a" * 300),
                                          ("username", "bad name!"), ("username", "u" * 65)])
def test_edit_profile_with_an_out_of_limits_value_changes_nothing(field, value, clients, users):
    form = profile_form(users.owner, location="Changed")
    form[field] = value

    response = clients["owner"].post("/account/edit", data=form)

    assert response.status_code == 200
    owner = reload(users.owner)
    assert owner.location is None and owner.first_name == "Owner"


@pytest.mark.parametrize("value", [*INJECTIONS, *ODD_CHARACTERS])
def test_edit_profile_with_hostile_text_never_errors(value, clients, users):
    response = clients["owner"].post("/account/edit", data=profile_form(users.owner, bio=value, location=value[:128],
                                                                        last_name=value[:64]))

    assert response.status_code < 500


def test_hostile_profile_text_is_escaped_on_the_profile_page(clients, users):
    users.owner.bio = "<script>alert('bio')</script>"
    users.owner.location = '"><img src=x onerror=alert(1)>'
    db.session.commit()

    page = clients["user"].get(f"/account/detail_user/{users.owner.id}").get_data(as_text=True)

    assert "<script>alert('bio')</script>" not in page and "<img src=x onerror" not in page


@pytest.mark.parametrize("email", BAD_EMAILS)
def test_edit_profile_with_a_bad_email_changes_nothing(email, clients, users):
    with captured_mails() as sent:
        clients["owner"].post("/account/edit", data=profile_form(users.owner, email=email))

    owner = reload(users.owner)
    assert owner.email == "owner@tests.rulezet" and owner.pending_email is None and sent == []


@pytest.mark.parametrize("password", WEAK_PASSWORDS[:-1])
def test_change_to_a_weak_password_changes_nothing(password, clients, users):
    clients["owner"].post("/account/edit", data={**profile_form(users.owner), **password_change(password)})

    assert reload(users.owner).verify_password(PASSWORD)


@pytest.mark.parametrize("filename", ["shell.php", "page.html", "image.svg", "noextension", "../../../evil.png"])
def test_avatar_upload_never_stores_a_dangerous_file(filename, clients, users, tmp_path, monkeypatch):
    from app.features.account import account_core
    monkeypatch.setattr(account_core, "AVATAR_UPLOAD_FOLDER", str(tmp_path))
    form = {**profile_form(users.owner), "profile_picture": (io.BytesIO(b"<?php system($_GET['c']); ?>"), filename)}

    response = clients["owner"].post("/account/edit", data=form, content_type="multipart/form-data")

    assert response.status_code < 500
    picture = reload(users.owner).profile_picture
    assert picture is None or (picture.endswith(".png") and "/" not in picture and ".." not in picture)
    assert all(p.parent == tmp_path for p in tmp_path.rglob("*"))


# ── Ids and parameters of the JSON routes ─────────────────────────────────────

@pytest.mark.parametrize("url", ["/account/detail_user/{id}", "/account/user_mini/{id}",
                                 "/account/user_activity_stats/{id}", "/account/user_edit_proposals/{id}",
                                 "/account/user_contributions/{id}"])
@pytest.mark.parametrize("user_id", [999999, HUGE_ID])
def test_profile_routes_with_an_unknown_id_never_error(url, user_id, clients):
    response = clients["admin"].get(url.format(id=user_id))

    assert response.status_code < 500


@pytest.mark.parametrize("url", ["/account/get_user", "/account/get_user_donne"])
@pytest.mark.parametrize("user_id", [*BAD_IDS, 999999])
def test_account_record_with_a_bad_id_never_errors(url, user_id, clients):
    response = clients["admin"].get(url, query_string={"user_id": user_id})

    assert response.status_code < 500


@pytest.mark.parametrize("route, field", [("/account/promote_remove_admin", "userId"),
                                          ("/account/toggle_user_verified", "userId"),
                                          ("/account/delete_user", "id")])
@pytest.mark.parametrize("bad_id", [*BAD_IDS, *WRONG_TYPES])
def test_user_management_with_a_bad_id_changes_nothing(route, field, bad_id, clients, users):
    before = count(User)

    response = clients["admin"].post(route, json={field: bad_id, "action": "promote"})

    assert response.status_code < 500
    assert count(User) == before and count(User, admin=True) == 1
    assert reload(users.owner).is_verified is True


@pytest.mark.parametrize("route", ["/account/promote_remove_admin", "/account/toggle_user_verified",
                                   "/account/delete_user"])
@pytest.mark.parametrize("body", ["not json", "[1, 2]", "null", '"text"'])
def test_user_management_with_a_broken_body_never_errors(route, body, clients):
    response = clients["admin"].post(route, data=body, content_type="application/json")

    assert response.status_code < 500


@pytest.mark.parametrize("action", ["", "PROMOTE", "delete", None, 1, ["promote"]])
def test_promote_with_an_unknown_action_changes_nothing(action, clients, users):
    response = clients["admin"].post("/account/promote_remove_admin", json={"userId": users.owner.id,
                                                                            "action": action})

    assert response.status_code < 500
    assert reload(users.owner).admin is False


@pytest.mark.parametrize("params", [{"page": "abc"}, {"page": -1}, {"per_page": -5}, {"per_page": 10**9},
                                    {"sort": "password_hash"}, {"dir": "sideways"}, {"admin": "maybe"},
                                    {"search": TOO_LONG}, {"search": "%' OR 1=1 --"}])
def test_users_table_with_odd_parameters_never_errors(params, clients):
    response = clients["admin"].get("/account/users_data_table", query_string=params)

    assert response.status_code < 500


@pytest.mark.parametrize("params", [{"page": -1}, {"search": TOO_LONG}, {"admin": "x"}, {"connected": "x"}])
def test_all_users_with_odd_parameters_never_errors(params, clients):
    response = clients["admin"].get("/account/get_all_users", query_string=params)

    assert response.status_code < 500


@pytest.mark.parametrize("query", [str(HUGE_ID), "9" * 40, TOO_LONG, "%_%", *INJECTIONS])
def test_mention_search_with_odd_text_never_errors(query, clients, users):
    response = clients["user"].get("/account/search_mentionable_users", query_string={"q": query})

    assert response.status_code == 200


@pytest.mark.parametrize("url", ["/account/leaderboard/global", "/account/leaderboard/category"])
@pytest.mark.parametrize("params, status", [({"sort_by": "password_hash"}, 400), ({"active_since": "forever"}, 400),
                                            ({"page": -1}, 200), ({"per_page": -1}, 200), ({"dir": "up"}, 200),
                                            ({"search": TOO_LONG}, 200)])
def test_leaderboard_with_odd_parameters(url, params, status, clients):
    response = clients["anonymous"].get(url, query_string=params)

    assert response.status_code == status


# ── Favorites ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", ["", "?id=", "?id=abc", f"?id={HUGE_ID}", "?id=-1"])
def test_remove_favorite_without_a_valid_id_removes_nothing(query, clients, users):
    rule = make_rule(users.admin)
    db.session.add(RuleFavoriteUser(user_id=users.owner.id, rule_id=rule.id))
    db.session.commit()

    response = clients["owner"].post(f"/account/favorite/delete_rule{query}")

    assert 400 <= response.status_code < 500
    assert count(RuleFavoriteUser, user_id=users.owner.id) == 1


@pytest.mark.parametrize("params", [{"page": -1}, {"page": "abc"}, {"sort_by": "evil"}, {"search": TOO_LONG}])
def test_favorites_list_with_odd_parameters_never_errors(params, clients):
    response = clients["owner"].get("/account/favorite/get_rules_page_favorite", query_string=params)

    assert response.status_code < 500


# ── API ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["email", "password", "first_name", "last_name"])
@pytest.mark.parametrize("value", [v for v in WRONG_TYPES if v is not None])
def test_api_register_with_a_wrongly_typed_field_is_refused(field, value, app, users):
    form = register_form()
    form[field] = value

    response = app.test_client().post("/api/account/public/register", json=form)

    assert response.status_code == 400
    assert count(User, is_verified=False) == 0


@pytest.mark.parametrize("field, value", [("first_name", TOO_LONG), ("last_name", "A" * 65), ("first_name", BLANK),
                                          ("email", "x" * 60 + "@tests.rulezet"), ("password", "weak")])
def test_api_register_with_an_out_of_limits_value_is_refused(field, value, app, users):
    response = app.test_client().post("/api/account/public/register", json=register_form(**{field: value}))

    assert response.status_code == 400
    assert count(User, is_verified=False) == 0


@pytest.mark.parametrize("body", ["not json", "[1, 2]", "null", '"text"', "{}"])
def test_api_register_with_a_broken_body_is_refused(body, app, users):
    response = app.test_client().post("/api/account/public/register", data=body, content_type="application/json")

    assert response.status_code == 400


@pytest.mark.parametrize("field", ["email", "first_name", "last_name", "password"])
@pytest.mark.parametrize("value", [v for v in WRONG_TYPES if v not in (None, [], {})])
def test_api_edit_with_a_wrongly_typed_field_is_refused(field, value, app, users):
    payload = {"first_name": "Renamed", "last_name": "Tester", "email": users.owner.email, field: value}

    response = app.test_client().post("/api/account/private/edit", json=payload, headers=api_headers(users.owner))

    assert response.status_code == 400
    assert reload(users.owner).first_name == "Owner"


@pytest.mark.parametrize("field, value", [("first_name", TOO_LONG), ("last_name", "A" * 65), ("first_name", BLANK)])
def test_api_edit_with_an_out_of_limits_value_is_refused(field, value, app, users):
    payload = {"first_name": "Owner", "last_name": "Tester", "email": users.owner.email, field: value}

    response = app.test_client().post("/api/account/private/edit", json=payload, headers=api_headers(users.owner))

    assert response.status_code == 400
    assert reload(users.owner).last_name == "Tester"


@pytest.mark.parametrize("body", ["not json", "[1, 2]", "null", '"text"'])
def test_api_edit_with_a_broken_body_is_refused(body, app, users):
    response = app.test_client().post("/api/account/private/edit", data=body, content_type="application/json",
                                      headers=api_headers(users.owner))

    assert response.status_code == 400
