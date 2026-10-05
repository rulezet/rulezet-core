import datetime

from flask import current_app

from app.core.db_class.db import User
from ... import db
from ...core.utils.utils import generate_api_key



def get_or_create_sso_user(user_info):
    """Resolve a OIDC userinfo to a Rulezet User, creating one if needed.

    Returns (user, None) on success or (None, error_message) on failure.
    """

    email = user_info.get("email")
    if not email:
        return None, "No email address found in the OIDC token."

    auth_id = user_info.get("sub")

    groups = user_info.get("groups", [])

    cfg = current_app.config
    priority_list = [
        (cfg.get("OIDC_GROUP_ADMIN", "RulezetAdmin"), "Admin"),
        (cfg.get("OIDC_GROUP_EDITOR", "RulezetEditor"), "Editor"),
    ]

    configured_groups = [entry[0] for entry in priority_list]
    current_app.logger.info(
        "OIDC login for '%s' — groups received: %s | checking: %s",
        email, groups, configured_groups,
    )

    matched_groups = []
    matched_role_names = []
    for group_name, role_name in priority_list:
        if group_name in groups:
            matched_groups.append(group_name)
            matched_role_names.append(role_name)

    if not matched_groups:
        return None, (
            "Your account is not a member of any Rulezet group "
            f"({', '.join(configured_groups)})."
        )

    current_app.logger.info("OIDC login for '%s' — matched group '%s' → role '%s'", email, matched_groups, matched_role_names)

    user = User.query.filter_by(email=email, auth_data=auth_id).first()

    if user:
        return user, None

    # email is unique on User — someone else (a local account, or an OIDC
    # account provisioned under a different `sub`) already holds it. Deny
    # cleanly instead of falling through to the INSERT below, which would
    # hit that unique constraint and raise an unhandled IntegrityError.
    if User.query.filter_by(email=email).first():
        current_app.logger.warning(
            "OIDC login for '%s' (sub=%s) denied — email already registered to another account.",
            email, auth_id,
        )
        return None, (
            "An account with this email already exists. Log in with your "
            "password, or contact an administrator to link your SSO account."
        )

    # Build username from token claims, with sensible fallbacks.
    first_name = (user_info.get("given_name") or "").strip()
    last_name = (user_info.get("family_name") or "").strip()
    username = (user_info.get("preferred_username") or "").strip()
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

    is_admin = False
    if "Admin" in matched_role_names:
        is_admin = True

    user = User(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email,
        admin=is_admin,
        api_key=generate_api_key(),
        is_verified=user_info.get("email_verified"),
        auth_provider="oidc",
        auth_data=auth_id,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(user)
    db.session.commit()

    current_app.logger.info("Provisioned new OIDC user: %s (role: %s)", email, matched_role_names)

    return user, None
