"""
activity_log.py — Fire-and-forget activity logging helper.

Usage:
    from app.core.utils.activity_log import log_activity

    log_activity("rule.create", f"Created rule '{rule.title}'",
                 target_type="rule", target_id=rule.id, target_uuid=rule.uuid)

Never raises — failures are silently swallowed so a log call never breaks a route.
"""

from __future__ import annotations

import uuid as uuid_mod
from contextlib import suppress
from typing import Any


def log_activity(
    action: str,
    description: str,
    target_type: str | None = None,
    target_id: int | None = None,
    target_uuid: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    with suppress(Exception):
        from app import db
        from app.core.db_class.db import ActivityLog
        from flask import request as freq
        from flask_login import current_user

        user_id = None
        with suppress(Exception):
            if current_user.is_authenticated:
                user_id = current_user.id

        ip = method = url = None
        with suppress(Exception):
            ip     = freq.remote_addr
            url    = freq.path[:512]
            method = freq.method

        entry = ActivityLog(
            uuid        = str(uuid_mod.uuid4()),
            user_id     = user_id,
            action      = action,
            description = description,
            ip_address  = ip,
            url         = url,
            method      = method,
            target_type = target_type,
            target_id   = target_id,
            target_uuid = target_uuid,
            extra       = extra,
        )
        db.session.add(entry)
        db.session.commit()
