"""
activity_log.py — Fire-and-forget activity logging helper.

Usage:
    from app.core.utils.activity_log import log_activity

    log_activity("rule.create", f"Created rule '{rule.title}'",
                 target_type="rule", target_id=rule.id, target_uuid=rule.uuid)

`is_public` and `icon` are auto-determined from the action if not provided.
Never raises — failures are silently swallowed.
"""

from __future__ import annotations

import uuid as uuid_mod
from contextlib import suppress
from typing import Any

# ── Default icons per action ──────────────────────────────────────────────────

_ICONS: dict[str, str] = {
    "rule.create":         "fa-solid fa-file-shield",
    "rule.edit":           "fa-solid fa-pen-to-square",
    "rule.delete":         "fa-solid fa-trash",
    "rule.bulk_delete":    "fa-solid fa-trash",
    "rule.vote_up":        "fa-solid fa-thumbs-up",
    "rule.vote_down":      "fa-solid fa-thumbs-down",
    "rule.favorite":       "fa-solid fa-heart",
    "rule.unfavorite":     "fa-regular fa-heart",
    "rule.download":       "fa-solid fa-download",
    "bundle.create":       "fa-solid fa-box",
    "bundle.edit":         "fa-solid fa-pen-to-square",
    "bundle.delete":       "fa-solid fa-box-open",
    "comment.add":         "fa-solid fa-comment",
    "comment.delete":      "fa-solid fa-comment-slash",
    "bundle_comment.add":  "fa-solid fa-comment",
    "user.register":       "fa-solid fa-user-plus",
    "user.login":          "fa-solid fa-right-to-bracket",
    "user.logout":         "fa-solid fa-right-from-bracket",
    "user.edit_profile":   "fa-solid fa-user-pen",
    "tag.create":          "fa-solid fa-tag",
    "tag.edit":            "fa-solid fa-tag",
    "tag.delete":          "fa-solid fa-tag",
    "tag.toggle_visibility": "fa-solid fa-eye",
    "tag.toggle_status":   "fa-solid fa-toggle-on",
    "job.create":          "fa-solid fa-gears",
    "job.cancel":          "fa-solid fa-ban",
    "job.pause":           "fa-solid fa-pause",
    "job.resume":          "fa-solid fa-play",
    "job.delete":          "fa-solid fa-trash",
    "github.import_started": "fa-brands fa-github",
    "github.update_started": "fa-solid fa-rotate",
    "admin.update_misp":   "fa-solid fa-rotate",
    "admin.promote_user":  "fa-solid fa-user-shield",
    "admin.demote_user":   "fa-solid fa-user",
    "admin.delete_user":   "fa-solid fa-user-slash",
    "admin.request_approved": "fa-solid fa-check-circle",
    "admin.request_rejected": "fa-solid fa-times-circle",
    "admin.logs_bulk_delete": "fa-solid fa-trash",
}

# Actions that are public by default
_PUBLIC_ACTIONS: frozenset[str] = frozenset({
    "rule.create",
    "rule.edit",
    "rule.vote_up",
    "rule.vote_down",
    "rule.favorite",
    "rule.download",
    "bundle.create",          # may be overridden to False for private bundles
    "bundle.edit",            # may be overridden to False for private bundles
    "comment.add",
    "user.register",
    "tag.create",
    "github.import_started",  # imports are public — new rules added to the community
    # github.update_started is intentionally NOT here — private operation
})


def _default_icon(action: str) -> str:
    if action in _ICONS:
        return _ICONS[action]
    if action.startswith("admin."):
        return "fa-solid fa-lock"
    if action.startswith("rule."):
        return "fa-solid fa-file-shield"
    if action.startswith("bundle."):
        return "fa-solid fa-box"
    if action.startswith("user."):
        return "fa-solid fa-user"
    if action.startswith("job."):
        return "fa-solid fa-gears"
    if action.startswith("tag."):
        return "fa-solid fa-tag"
    if action.startswith("comment."):
        return "fa-solid fa-comment"
    return "fa-solid fa-circle-dot"


def log_activity(
    action: str,
    description: str,
    target_type: str | None = None,
    target_id: int | None = None,
    target_uuid: str | None = None,
    extra: dict[str, Any] | None = None,
    is_public: bool | None = None,
    icon: str | None = None,
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

        resolved_public = is_public if is_public is not None else (action in _PUBLIC_ACTIONS)
        resolved_icon   = icon if icon is not None else _default_icon(action)

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
            is_public   = resolved_public,
            icon        = resolved_icon,
        )
        db.session.add(entry)
        db.session.commit()
