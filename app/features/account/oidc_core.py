import datetime

from flask import current_app

from app.core.db_class.db import User
from ... import db
from ...core.utils.utils import generate_api_key



def register_oidc_client(app):
    """(Re)register the authlib OIDC client from the app's current config —
    called at startup and again whenever an admin saves the SSO settings
    (Admin → Settings → Security), so a change applies without a restart.
    authlib reads OIDC_CLIENT_ID / OIDC_CLIENT_SECRET from app.config itself."""
    from app import oauth
    if not app.config.get('OIDC_ENABLED'):
        return
    oauth.register(
        'oidc',
        overwrite=True,
        server_metadata_url=app.config.get('OIDC_DISCOVERY_ENDPOINT'),
        client_kwargs={'scope': app.config.get('OIDC_SCOPE') or 'openid email profile',
                       'code_challenge_method': 'S256'},
    )


def get_or_create_sso_user(user_info):
    """Resolve a OIDC userinfo to a Rulezet User, creating one if needed.

    Returns (user, None) on success or (None, error_message) on failure.
    """

    email = user_info.get("email")
    if not email:
        return None, "No email address found in the OIDC token."

    auth_id = user_info.get("sub")

    groups = user_info.get("groups") or []
    if isinstance(groups, str):
        groups = [groups]
    elif not isinstance(groups, (list, tuple)):
        groups = []   # a malformed claim matches no group

    cfg = current_app.config
    priority_list = [
        (cfg.get("OIDC_GROUP_ADMIN", "RulezetAdmin"), "Admin"),
        (cfg.get("OIDC_GROUP_EDITOR", "RulezetEditor"), "Editor"),
    ]

    configured_groups = [entry[0] for entry in priority_list]
    current_app.logger.debug(
        "OIDC login (sub=%s) — groups received: %s | checking: %s",
        user_info.get("sub"), groups, configured_groups,
    )

    matched_groups = []
    matched_role_names = []
    # Keycloak sends full group paths ("/RulezetAdmin") unless told otherwise.
    received = {str(g).lstrip("/") for g in groups}
    for group_name, role_name in priority_list:
        if group_name.lstrip("/") in received:
            matched_groups.append(group_name)
            matched_role_names.append(role_name)

    if not matched_groups:
        return None, (
            "Your account is not a member of any Rulezet group "
            f"({', '.join(configured_groups)})."
        )

    is_admin = "Admin" in matched_role_names
    current_app.logger.info("OIDC login (sub=%s) — matched group(s) %s → role(s) %s",
                            auth_id, matched_groups, matched_role_names)

    if not auth_id:
        return None, "No subject ('sub') found in the OIDC token."

    # The OIDC subject is the account's stable identity — not the email,
    # which can change at the IdP (and must then follow, see below).
    user = User.query.filter_by(auth_provider="oidc", auth_data=auth_id).first()

    if user:
        changed = []
        # Group membership is re-read on EVERY login: someone removed from the
        # admin group at the IdP loses admin here at their next login (and
        # someone removed from every Rulezet group was already refused above).
        if bool(user.admin) != is_admin:
            user.admin = is_admin
            changed.append(f"admin={is_admin}")
        if email != user.email:
            if User.query.filter(User.email == email, User.id != user.id).first():
                return None, (
                    "Your SSO email address is already used by another Rulezet account. "
                    "Contact an administrator."
                )
            user.email = email
            changed.append("email")
        if user_info.get("email_verified") is not None:
            user.is_verified = bool(user_info.get("email_verified"))
        db.session.commit()
        if changed:
            current_app.logger.info("OIDC user id=%s synced from IdP: %s", user.id, ", ".join(changed))
        return user, None

    # email is unique on User — someone else (a local account, or an OIDC
    # account provisioned under a different `sub`) already holds it. Deny
    # cleanly instead of linking accounts or hitting the unique constraint.
    if User.query.filter_by(email=email).first():
        current_app.logger.warning(
            "OIDC login (sub=%s) denied — email already registered to another account.", auth_id,
        )
        return None, (
            "An account with this email already exists. Log in with your "
            "password, or contact an administrator to link your SSO account."
        )

    # Build username from token claims, with sensible fallbacks.
    first_name = (user_info.get("given_name") or "").strip()
    last_name = (user_info.get("family_name") or "").strip()
    username = (user_info.get("preferred_username") or "").strip()[:64] or None
    if username and User.query.filter_by(username=username).first():
        username = None   # unique column — leave it for the user to pick
    if not first_name and not last_name:
        full_name = (user_info.get("name") or "").strip()
        if full_name:
            parts = full_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
    if not first_name:
        first_name = email.split("@")[0]
    if not last_name:
        last_name = ""

    user = User(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email,
        admin=is_admin,
        api_key=generate_api_key(),
        is_verified=bool(user_info.get("email_verified")),
        auth_provider="oidc",
        auth_data=auth_id,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(user)
    db.session.commit()

    current_app.logger.info("Provisioned new OIDC user id=%s (role: %s)", user.id, matched_role_names)

    return user, None
