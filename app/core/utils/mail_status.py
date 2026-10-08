"""
mail_status.py — one answer to "can this instance send user-facing email?".

Two conditions, both required:
  - enabled:    the admin hasn't switched email features off
                (Admin → Settings → Email, InstanceConfig.email_enabled);
  - configured: SMTP is actually set up. config.py defaults MAIL_SERVER to
                smtp.gmail.com, so a server name alone proves nothing — a
                sender (MAIL_DEFAULT_SENDER or MAIL_USERNAME) is required too.

Every email-backed feature (alert emails, digests...) checks
is_email_available() both to hide its UI and to refuse server-side.
"""

from flask import current_app


_UNSET = object()


def email_status(instance_config=_UNSET) -> dict:
    """`instance_config` lets a caller that already loaded the InstanceConfig
    row (e.g. the global template context processor) skip a second query."""
    from app.core.db_class.db import InstanceConfig

    enabled = True
    try:
        cfg = InstanceConfig.query.first() if instance_config is _UNSET else instance_config
        if cfg is not None:
            enabled = bool(cfg.email_enabled)
    except Exception:
        # Column not migrated yet — behave as before the switch existed.
        from app import db
        db.session.rollback()

    conf = current_app.config
    configured = bool(conf.get('MAIL_SERVER')) and bool(
        conf.get('MAIL_DEFAULT_SENDER') or conf.get('MAIL_USERNAME')
    )
    return {
        'enabled':    enabled,
        'configured': configured,
        'available':  enabled and configured,
    }


def is_email_available(instance_config=_UNSET) -> bool:
    return email_status(instance_config)['available']
