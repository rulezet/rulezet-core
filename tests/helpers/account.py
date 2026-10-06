"""Account factories and helpers: accounts in every state (awaiting
verification, single sign-on), the forms the account pages post, a real login
through /account/login, mail capture and a fake OIDC provider.

No mail ever leaves a test: wrap the call in `captured_mails()` to read what
would have been sent (verification codes, reset / confirmation links).
"""
import datetime
import hashlib
import itertools
import re
import uuid
from contextlib import contextmanager
from unittest.mock import patch

from app import db, mail
from app.core.db_class.db import User
from tests.helpers.users import PASSWORD, make_user

_counter = itertools.count(1)

NEW_PASSWORD = "N3w-Passw0rd"


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


@contextmanager
def captured_mails():
    """Collect every mail the app sends in this block instead of sending it."""
    sent = []
    with patch.object(mail, "send", side_effect=sent.append):
        yield sent


def link_token(message, route):
    """The token of the `/account/<route>/<token>` link in a captured mail."""
    found = re.search(rf"/account/{route}/([A-Za-z0-9_\-]+)", message.body)
    return found.group(1) if found else None


# ── Accounts in other states ──────────────────────────────────────────────────

def make_pending_user(name=None, *, code="123456", expired=False):
    """A local account just registered: not verified yet, with a code."""
    user = make_user(name or f"pending{next(_counter)}")
    user.is_verified = False
    user.verification_code = code
    user.verification_expiration = _now() + datetime.timedelta(minutes=-1 if expired else 30)
    db.session.commit()
    return user


def make_sso_user(name=None, *, sub=None, admin=False):
    """An account provisioned by single sign-on: no Rulezet password."""
    name = name or f"sso{next(_counter)}"
    user = User(
        first_name=name.capitalize(), last_name="Sso", email=f"{name}@sso.rulezet",
        admin=admin, api_key=f"api-key-{name}", is_verified=True,
        auth_provider="oidc", auth_data=sub or f"sub-{name}",
    )
    db.session.add(user)
    db.session.commit()
    return user


def give_reset_token(user, *, expired=False):
    """A password-reset link for `user` (what the reset mail contains)."""
    raw = uuid.uuid4().hex
    user.password_reset_token = hashlib.sha256(raw.encode()).hexdigest()
    user.password_reset_expiration = _now() + datetime.timedelta(hours=-1 if expired else 1)
    db.session.commit()
    return raw


def give_email_change_token(user, new_email, *, expired=False):
    """An email-change confirmation link for `user` → `new_email`."""
    raw = uuid.uuid4().hex
    user.pending_email = new_email
    user.email_change_token = hashlib.sha256(raw.encode()).hexdigest()
    user.email_change_expiration = _now() + datetime.timedelta(hours=-1 if expired else 1)
    db.session.commit()
    return raw


# ── Forms ─────────────────────────────────────────────────────────────────────

def register_form(**overrides):
    """What the registration form (or the register API) sends."""
    n = next(_counter)
    form = dict(first_name="New", last_name=f"Member{n}", email=f"new{n}@tests.rulezet", password=PASSWORD)
    form.update(overrides)
    return form


def profile_form(user, **changes):
    """What the "edit profile" form posts for `user`, with `changes` applied."""
    form = dict(
        first_name=user.first_name, last_name=user.last_name, email=user.email,
        username=user.username or "", bio=user.bio or "", location=user.location or "",
        website_url=user.website_url or "", github_url=user.github_url or "",
        twitter_url=user.twitter_url or "",
    )
    form.update(changes)
    return form


def password_change(new_password=NEW_PASSWORD, confirm=None):
    """The extra fields of the edit form that change the password."""
    return dict(change_password="y", password=new_password,
                password2=new_password if confirm is None else confirm)


# ── Logging in for real ───────────────────────────────────────────────────────

def login(client, email, password=PASSWORD, *, remember=False, next=None):
    """POST the login form, as a browser would."""
    data = {"email": email, "password": password}
    if remember:
        data["remember_me"] = "y"
    url = "/account/login" + (f"?next={next}" if next is not None else "")
    return client.post(url, data=data)


def logged_in_user_id(client):
    """Who the session of `client` belongs to (None = nobody)."""
    with client.session_transaction() as session:
        user_id = session.get("_user_id")
    return int(user_id) if user_id else None


# ── Fake single sign-on provider ──────────────────────────────────────────────

class FakeOIDC:
    """Stands in for authlib's `oauth.oidc`: the provider hands back `claims`
    (already validated, as authlib exposes them in token["userinfo"])."""

    def __init__(self, claims):
        self.claims = claims
        self.redirects = []
        self.error = None

    def authorize_redirect(self, redirect_uri):
        from flask import redirect
        self.redirects.append(redirect_uri)
        return redirect(f"https://idp.example.com/authorize?redirect_uri={redirect_uri}")

    def authorize_access_token(self):
        if self.error:
            raise self.error
        return {"access_token": "fake", "userinfo": self.claims} if self.claims is not None else {"access_token": "fake"}


def enable_oidc(app, monkeypatch, *, role="editor", **claims):
    """Turn single sign-on on, with a fake provider answering `claims`.
    `role`: "admin", "editor" or "none" — the IdP group the person is in."""
    monkeypatch.setitem(app.config, "OIDC_ENABLED", True)
    groups = {
        "admin": [app.config.get("OIDC_GROUP_ADMIN", "RulezetAdmin")],
        "editor": [app.config.get("OIDC_GROUP_EDITOR", "RulezetEditor")],
        "none": ["some-unrelated-group"],
    }[role]
    full_claims = {"sub": "sso-sub", "email": "sso@idp.example", "email_verified": True,
                   "given_name": "Single", "family_name": "SignOn", "groups": groups}
    full_claims.update(claims)
    fake = FakeOIDC({k: v for k, v in full_claims.items() if v is not None})
    from app import oauth
    monkeypatch.setattr(oauth, "oidc", fake, raising=False)
    return fake
