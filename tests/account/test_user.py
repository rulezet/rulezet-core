#####################
#   register case   #
#####################

# API_KEY = "admin_api_key"

def test_create_user(client, email="test@example.com") -> None:
    """Create an User test"""
    response = client.post("/api/account/public/register",
        content_type='application/json',
        json={
            "email": email,
            "password": "password1@A",
            "first_name": "Test",
            "last_name": "User"
        })
    data = response.get_json()
    assert response.status_code == 201
    assert "X-API-KEY" in data
    return(data["X-API-KEY"])


def test_register_and_reject_duplicate(client):
    # First registration
    test_create_user(client, email="test@example.com")

    # Second registration with same email
    response = client.post("/api/account/public/register", json={
        "email": "test@example.com",
        "password": "password1Q@",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 409
    assert b"Email already exists" in response.data


def test_register_with_bad_email(client):
    response = client.post("/api/account/public/register", json={
        "email": "invalideEmail",
        "password": "password1Q@",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 400
    assert b"Invalid email" in response.data

def test_register_with_bad_password_miss_uppercase(client):
    response = client.post("/api/account/public/register", json={
        "email": "a@a.a",
        "password": "password1@",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 400
    assert b"Password must contain at least one uppercase letter." in response.data

def test_register_with_bad_password_miss_lowercase(client):
    response = client.post("/api/account/public/register", json={
        "email": "a@a.a",
        "password": "PASSWORD1@",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 400
    assert b"Password must contain at least one lowercase letter." in response.data 

def test_register_with_bad_password_miss_digit(client):
    response = client.post("/api/account/public/register", json={
        "email": "a@a.a",
        "password": "Password@",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 400
    assert b"Password must contain at least one digit." in response.data    

def test_register_with_bad_password_too_short(client):
    response = client.post("/api/account/public/register", json={
        "email": "a@a.a",
        "password": "P1@a",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 400
    assert b"Password must be between 8 and 64 characters." in response.data    
def test_register_with_bad_password_too_long(client):
    response = client.post("/api/account/public/register", json={
        "email": "a@a.a",
        "password": "P1@" + "a"*62,
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 400
    assert b"Password must be between 8 and 64 characters." in response.data    
# #####################
# #   login case      #
# #####################

def _verify_user(client, email):
    """Mark a user as email-verified so the web login gate passes."""
    from app import db
    from app.core.db_class.db import User
    with client.application.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_verified = True
            db.session.commit()


def test_login_success(client):
    api_key = test_create_user(client)
    _verify_user(client, "test@example.com")
    response = client.post("/account/login", data={
        "email": "test@example.com",
        "password": "password1@A",
    }, follow_redirects=False)
    assert response.status_code == 302
    return api_key


def test_login_invalid_email_format(client):
    test_create_user(client)
    response = client.post("/account/login", data={
        "email": "invalid-email",
        "password": "password1@A",
    })
    assert response.status_code == 200  # form re-rendered with validation error


def test_login_missing_fields(client):
    test_create_user(client)
    response = client.post("/account/login", data={
        "email": "test@example.com",
        # password omitted
    })
    assert response.status_code == 200  # form re-rendered with validation error


def test_login_wrong_password(client):
    test_create_user(client)
    _verify_user(client, "test@example.com")
    response = client.post("/account/login", data={
        "email": "test@example.com",
        "password": "WrongPass1@",
    })
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_login_email_not_found(client):
    response = client.post("/account/login", data={
        "email": "notfound@example.com",
        "password": "password1@A",
    })
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


#############
#   logout  #
#############

def test_logout(client):
    test_login_success(client)
    response = client.get("/account/logout", follow_redirects=False)
    assert response.status_code == 302

#############
#   Edit    #
#############

def test_edit_user_success(client):
    api_key = test_login_success(client)
    response = client.post("/api/account/private/edit", json={
        "email": "newemail@example.com",
        "first_name": "NewFirst",
        "last_name": "NewLast"
    },headers={"X-API-KEY": api_key})
    assert response.status_code == 200
    assert b"User updated successfully" in response.data


def test_edit_user_missing_field(client):
    api_key = test_login_success(client)
    response = client.post("/api/account/private/edit", json={
        "email": "newemail@example.com",
        "first_name": "OnlyFirst"
        # missing last_name
    },headers={"X-API-KEY": api_key})
    assert response.status_code == 400
    assert b"last_name is required" in response.data


def test_edit_user_invalid_email_format(client):
    api_key = test_login_success(client)
    response = client.post("/api/account/private/edit", json={
        "email": "invalid-email",
        "first_name": "First",
        "last_name": "Last"
    },headers={"X-API-KEY": api_key})
    assert response.status_code == 400
    assert b"Invalid email format" in response.data


def test_edit_user_email_already_used(client):
    api_key = test_login_success(client)
    response = client.post("/api/account/private/edit", json={
        "email": "t@t.t",
        "first_name": "Test",
        "last_name": "User"
    },headers={"X-API-KEY": api_key})
    assert response.status_code == 409
    assert b"Email already registered" in response.data


def test_edit_user_same_email_allowed(client):
    api_key = test_login_success(client)
    # Reuse the same email: should be OK
    response = client.post("/api/account/private/edit", json={
        "email": "test@example.com",  # unchanged
        "first_name": "Updated",
        "last_name": "User"
    },headers={"X-API-KEY": api_key})
    assert response.status_code == 200
    assert b"User updated successfully" in response.data


def test_edit_user_without_authentication(client):
    api_key = "invalide_api_key"
    # Not logged in
    response = client.post("/api/account/private/edit", json={
        "email": "unauth@example.com",
        "first_name": "A",
        "last_name": "B"
    },headers={"X-API-KEY": api_key})
    assert response.status_code in (401, 403, 302)  # an unknown key is refused


#############
#   OIDC    #
#############
#
# A dev's local .env (loaded unconditionally by load_dotenv()) can set
# OIDC_ENABLED/OIDC_GROUP_ADMIN/OIDC_GROUP_EDITOR to whatever their own IdP
# uses — these tests never rely on that env bleeding in or on it being
# absent. Each test sets OIDC_ENABLED explicitly, and group names are always
# read back from live app.config rather than assumed to be the code's
# "RulezetAdmin"/"RulezetEditor" defaults.
#
# The real authlib client talks to a live IdP, which tests don't have, so
# `oauth.oidc` — the same object account.py imports as `from ... import
# oauth` — is swapped for a fake that returns canned claims.

class _FakeOIDCClient:
    """Stand-in for authlib's `oauth.oidc` — only the subset of its API that
    app/features/account/account.py actually calls.
    """

    def __init__(self, user_info=None):
        self.user_info = user_info or {}
        self.authorize_redirect_calls = []

    def authorize_redirect(self, redirect_uri):
        self.authorize_redirect_calls.append(redirect_uri)
        from flask import redirect as flask_redirect
        return flask_redirect(f"https://idp.example.com/authorize?redirect_uri={redirect_uri}")

    def authorize_access_token(self):
        # authlib validates the ID token (incl. nonce) inside this call and
        # exposes its claims as token["userinfo"] — the app reads only that.
        return {"access_token": "fake-access-token", "id_token": "fake-id-token",
                "userinfo": self.user_info}


def _enable_oidc(client, monkeypatch, *, email="sso@example.com", sub="sso-sub-1",
                  role="editor", email_verified=True, groups=None, include_email=True):
    """Enable OIDC on the app under test and install a fake authlib client
    that returns the given claims.

    `role` resolves to whichever group name this app instance is actually
    configured with ("editor" -> OIDC_GROUP_EDITOR, "admin" -> OIDC_GROUP_ADMIN,
    "none" -> a group that matches neither) — pass `groups` directly to
    bypass that and set the claim's groups list verbatim.
    """
    app = client.application
    app.config["OIDC_ENABLED"] = True

    if groups is None:
        if role == "editor":
            groups = [app.config.get("OIDC_GROUP_EDITOR", "RulezetEditor")]
        elif role == "admin":
            groups = [app.config.get("OIDC_GROUP_ADMIN", "RulezetAdmin")]
        else:
            groups = ["some-unrelated-group"]

    info = {
        "sub": sub,
        "given_name": "SSO",
        "family_name": "User",
        "groups": groups,
    }
    if include_email:
        info["email"] = email
        info["email_verified"] = email_verified

    fake = _FakeOIDCClient(user_info=info)
    from app import oauth
    monkeypatch.setattr(oauth, "oidc", fake, raising=False)
    return fake


def test_oidc_login_disabled_returns_404(client):
    client.application.config["OIDC_ENABLED"] = False
    response = client.get("/account/oidc/login")
    assert response.status_code == 404


def test_oidc_callback_disabled_returns_404(client):
    client.application.config["OIDC_ENABLED"] = False
    response = client.get("/account/oidc/authorize")
    assert response.status_code == 404


def test_oidc_login_redirects_to_provider(client, monkeypatch):
    fake = _enable_oidc(client, monkeypatch)
    response = client.get("/account/oidc/login", follow_redirects=False)
    assert response.status_code == 302
    assert len(fake.authorize_redirect_calls) == 1
    # The redirect_uri we hand authlib must point back at our own callback.
    assert "/account/oidc/authorize" in fake.authorize_redirect_calls[0]


def test_oidc_callback_provisions_new_editor_user(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="neweditor@example.com", sub="sub-editor-1", role="editor")

    response = client.get("/account/oidc/authorize", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    from app.core.db_class.db import User
    with client.application.app_context():
        user = User.query.filter_by(email="neweditor@example.com").first()
        assert user is not None
        assert user.auth_provider == "oidc"
        assert user.auth_data == "sub-editor-1"
        assert user.admin is False
        assert user.is_verified is True


def test_oidc_callback_provisions_new_admin_user(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="newadmin@example.com", sub="sub-admin-1", role="admin")

    response = client.get("/account/oidc/authorize", follow_redirects=False)
    assert response.status_code == 302

    from app.core.db_class.db import User
    with client.application.app_context():
        user = User.query.filter_by(email="newadmin@example.com").first()
        assert user is not None
        assert user.admin is True


def test_oidc_callback_denied_without_matching_group(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="outsider@example.com", sub="sub-outsider-1", role="none")

    response = client.get("/account/oidc/authorize", follow_redirects=False)
    assert response.status_code == 302
    assert "/account/login" in response.headers["Location"]

    from app.core.db_class.db import User
    with client.application.app_context():
        assert User.query.filter_by(email="outsider@example.com").first() is None


def test_oidc_callback_without_email_claim_is_denied(client, monkeypatch):
    _enable_oidc(client, monkeypatch, sub="sub-no-email", role="editor", include_email=False)

    response = client.get("/account/oidc/authorize", follow_redirects=False)
    assert response.status_code == 302
    assert "/account/login" in response.headers["Location"]


def test_oidc_callback_logs_in_existing_user_without_duplicating(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="repeat@example.com", sub="sub-repeat-1", role="editor")

    first = client.get("/account/oidc/authorize", follow_redirects=False)
    assert first.status_code == 302

    client.get("/account/logout", follow_redirects=False)

    second = client.get("/account/oidc/authorize", follow_redirects=False)
    assert second.status_code == 302

    from app.core.db_class.db import User
    with client.application.app_context():
        assert User.query.filter_by(email="repeat@example.com").count() == 1


def test_oidc_callback_rejects_open_redirect_next_param(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="redirtest@example.com", sub="sub-redir-1", role="editor")

    response = client.get(
        "/account/oidc/authorize?next=http://evil.example.com/phish",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_oidc_callback_honors_safe_relative_next_param(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="redirtest2@example.com", sub="sub-redir-2", role="editor")

    response = client.get("/account/oidc/authorize?next=/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"


def test_oidc_user_matching_requires_both_email_and_sub(client, monkeypatch):
    """Regression guard: a returning OIDC user must be matched by email AND
    the token's `sub` (auth_data) together — matching by email alone would
    let anyone who controls that email at the IdP log in as an existing
    account (see get_or_create_sso_user in oidc_core.py).
    """
    _enable_oidc(client, monkeypatch, email="matchme@example.com", sub="sub-match-1", role="editor")

    first = client.get("/account/oidc/authorize", follow_redirects=False)
    assert first.status_code == 302

    from app.core.db_class.db import User
    with client.application.app_context():
        provisioned = User.query.filter_by(email="matchme@example.com").first()
        assert provisioned is not None
        provisioned_id = provisioned.id

    client.get("/account/logout", follow_redirects=False)

    # Same email, different `sub` — get_or_create_sso_user's
    # filter_by(email=..., auth_data=...) must miss and refuse to log in as
    # the first user's row. It must also not try to provision a second row
    # with the same email (that would hit the unique constraint) — it should
    # deny cleanly instead.
    _enable_oidc(client, monkeypatch, email="matchme@example.com", sub="sub-match-2", role="editor")

    second = client.get("/account/oidc/authorize", follow_redirects=False)
    assert second.status_code == 302
    assert "/account/login" in second.headers["Location"]

    from app.core.db_class.db import User
    with client.application.app_context():
        # Still exactly one user for this email — the original — and no
        # second row was ever provisioned for sub-match-2.
        matches = User.query.filter_by(email="matchme@example.com").all()
        assert len(matches) == 1
        assert matches[0].id == provisioned_id
        assert matches[0].auth_data == "sub-match-1"


def test_oidc_login_denied_when_email_taken_by_local_account(client, monkeypatch):
    """An OIDC identity must not be able to log in as — or silently take over
    — a pre-existing local/password account just because it shares an email.
    """
    test_create_user(client, email="localonly@example.com")

    _enable_oidc(client, monkeypatch, email="localonly@example.com", sub="sub-local-collide", role="editor")

    response = client.get("/account/oidc/authorize", follow_redirects=False)
    assert response.status_code == 302
    assert "/account/login" in response.headers["Location"]

    from app.core.db_class.db import User
    with client.application.app_context():
        matches = User.query.filter_by(email="localonly@example.com").all()
        assert len(matches) == 1
        assert matches[0].auth_provider == "local"


# ── fixes on top of PR #71 ────────────────────────────────────────────────────

def test_oidc_admin_rights_follow_idp_groups(client, monkeypatch):
    """Removed from the admin group at the IdP → no longer admin at the next login."""
    _enable_oidc(client, monkeypatch, email="demote@example.com", sub="sub-demote", role="admin")
    client.get("/account/oidc/authorize", follow_redirects=False)
    client.get("/account/logout", follow_redirects=False)

    from app.core.db_class.db import User
    with client.application.app_context():
        assert User.query.filter_by(auth_data="sub-demote").first().admin is True

    _enable_oidc(client, monkeypatch, email="demote@example.com", sub="sub-demote", role="editor")
    client.get("/account/oidc/authorize", follow_redirects=False)
    with client.application.app_context():
        assert User.query.filter_by(auth_data="sub-demote").first().admin is False


def test_oidc_email_change_at_idp_follows_the_same_account(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="old@example.com", sub="sub-mail", role="editor")
    client.get("/account/oidc/authorize", follow_redirects=False)
    client.get("/account/logout", follow_redirects=False)
    _enable_oidc(client, monkeypatch, email="new@example.com", sub="sub-mail", role="editor")
    client.get("/account/oidc/authorize", follow_redirects=False)

    from app.core.db_class.db import User
    with client.application.app_context():
        assert User.query.filter_by(auth_data="sub-mail").count() == 1
        assert User.query.filter_by(auth_data="sub-mail").first().email == "new@example.com"


def test_oidc_keycloak_group_paths_match(client, monkeypatch):
    app = client.application
    _enable_oidc(client, monkeypatch, email="path@example.com", sub="sub-path",
                 groups=["/" + app.config.get("OIDC_GROUP_ADMIN", "RulezetAdmin")])
    client.get("/account/oidc/authorize", follow_redirects=False)
    from app.core.db_class.db import User
    with app.app_context():
        assert User.query.filter_by(auth_data="sub-path").first().admin is True


def test_oidc_callback_error_redirects_instead_of_500(client, monkeypatch):
    fake = _enable_oidc(client, monkeypatch)

    def _boom():
        raise RuntimeError("mismatching_state")
    fake.authorize_access_token = _boom
    response = client.get("/account/oidc/authorize", follow_redirects=False)
    assert response.status_code == 302
    assert "/account/login" in response.headers["Location"]


def test_oidc_callback_without_validated_id_token_is_denied(client, monkeypatch):
    fake = _enable_oidc(client, monkeypatch)
    fake.authorize_access_token = lambda: {"access_token": "x"}
    response = client.get("/account/oidc/authorize", follow_redirects=False)
    assert "/account/login" in response.headers["Location"]


def test_oidc_next_kept_across_idp_round_trip(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="next@example.com", sub="sub-next", role="editor")
    client.get("/account/oidc/login?next=/rule/rules_list", follow_redirects=False)
    response = client.get("/account/oidc/authorize", follow_redirects=False)
    assert response.headers["Location"] == "/rule/rules_list"


def test_oidc_backslash_next_is_rejected(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="bs@example.com", sub="sub-bs", role="editor")
    response = client.get("/account/oidc/authorize?next=/\\evil.example.com", follow_redirects=False)
    assert response.headers["Location"] == "/"


def test_sso_account_cannot_get_a_password_by_reset(client, monkeypatch):
    _enable_oidc(client, monkeypatch, email="nopass@example.com", sub="sub-nopass", role="editor")
    client.get("/account/oidc/authorize", follow_redirects=False)

    from app.core.db_class.db import User
    from app.features.account import account_core
    with client.application.app_context():
        assert account_core.request_password_reset_core("nopass@example.com") is True
        user = User.query.filter_by(auth_data="sub-nopass").first()
        assert user.password_reset_token is None
        import hashlib
        user.password_reset_token = hashlib.sha256(b"tok").hexdigest()   # even with a token…
        from app import db
        db.session.commit()
        ok, _ = account_core.reset_password_core("tok", "NewPassw0rd")
        assert ok is False
        assert User.query.filter_by(auth_data="sub-nopass").first().password_hash is None


def test_login_rate_limit_survives_dropping_the_session_cookie(client):
    for _ in range(5):
        client.post("/account/login", data={"email": "neo@admin.admin", "password": "Wrong-pass1"})
        client.delete_cookie("session")
    response = client.post("/account/login", data={"email": "neo@admin.admin", "password": "Wrong-pass1"})
    assert b"Too many failed login attempts" in response.data



# ── SSO settings from Admin → Settings → Security ────────────────────────────

def _admin_client(client):
    from app.core.db_class.db import User
    with client.application.app_context():
        admin = User.query.filter_by(email="admin@admin.admin").first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True
    return client


def test_sso_settings_save_applies_without_restart(client, monkeypatch):
    written = {}
    monkeypatch.setattr("app.features.admin.admin_core.write_env_value",
                        lambda k, v: written.__setitem__(k, v) or True)
    c = _admin_client(client)
    res = c.post("/admin/settings/sso", json={
        "oidc_enabled": True, "oidc_discovery_endpoint": "https://sso.example.org/realms/r/.well-known/openid-configuration",
        "oidc_client_id": "rulezet", "oidc_client_secret": "s3cret", "sign_up_enabled": False})
    assert res.status_code == 200 and res.get_json()["success"]
    assert written["OIDC_ENABLED"] == "true" and written["SIGN_UP_ENABLED"] == "false"
    app = client.application
    assert app.config["OIDC_ENABLED"] is True and app.config["SIGN_UP_ENABLED"] is False
    assert c.get("/account/register").status_code == 404
    cfg = c.get("/admin/settings/config").get_json()
    assert "s3cret" not in str(cfg) and cfg["sso"]["oidc_client_secret_set"] is True


def test_sso_settings_refuse_enabling_without_config_and_non_admins(client):
    c = _admin_client(client)
    assert c.post("/admin/settings/sso", json={"oidc_enabled": True}).status_code == 400
    c.get("/account/logout")
    from app.core.db_class.db import User
    with client.application.app_context():
        neo = User.query.filter_by(email="neo@admin.admin").first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(neo.id)
    assert client.post("/admin/settings/sso", json={"oidc_enabled": False}).status_code == 403


def test_logout_also_ends_a_remember_me_login(client):
    """Regression: session.clear() after logout_user() used to wipe Flask-Login's
    "delete the remember cookie" flag, so a remembered user stayed logged in."""
    client.post("/account/login", data={"email": "t@t.t", "password": "password1@A", "remember_me": "y"})
    client.get("/account/logout")
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is None
    response = client.get("/account/edit", follow_redirects=False)
    assert response.status_code in (302, 401)
