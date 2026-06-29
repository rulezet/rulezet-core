"""
activity_log.py — Fire-and-forget activity logging helper.

Usage:
    from app.core.utils.activity_log import log_activity

    log_activity("rule.create", f"Created rule '{rule.title}'",
                 target_type="rule", target_id=rule.id, target_uuid=rule.uuid)

`is_public`, `icon`, `title`, `category` and `level` are auto-determined
from the action if not provided. Never raises — failures are silently swallowed.
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
    "github.import_started":  "fa-brands fa-github",
    "github.update_started":  "fa-solid fa-rotate",
    "github.source_deleted":  "fa-brands fa-github",
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
    "bundle.create",
    "bundle.edit",
    "comment.add",
    "user.register",
    "tag.create",
    "github.import_started",
})

# Human-readable titles for known actions
_TITLES: dict[str, str] = {
    "rule.create":              "Rule Created",
    "rule.edit":                "Rule Edited",
    "rule.delete":              "Rule Deleted",
    "rule.bulk_delete":         "Rules Bulk Deleted",
    "rule.permanent_delete":    "Rule Permanently Deleted",
    "rule.permanent_delete_bulk": "Rules Permanently Deleted",
    "rule.restore":             "Rule Restored",
    "rule.restore_bulk":        "Rules Bulk Restored",
    "rule.conflict_resolved":   "Trash Conflict Resolved",
    "rule.vote_up":             "Rule Upvoted",
    "rule.vote_down":           "Rule Downvoted",
    "rule.favorite":            "Rule Favorited",
    "rule.unfavorite":          "Rule Unfavorited",
    "rule.download":            "Rule Downloaded",
    "rule.scope_add":           "Environment Scope Added",
    "rule.scope_update":        "Environment Scope Updated",
    "rule.scope_delete":        "Environment Scope Removed",
    "rule.propose_edit":        "Edit Proposal Submitted",
    "rule.proposal_approved":   "Edit Proposal Approved",
    "rule.proposal_rejected":   "Edit Proposal Rejected",
    "rule.bad_rule_edited":     "Invalid Rule Fixed",
    "rule.bad_rule_deleted":    "Invalid Rule Deleted",
    "rule.report":              "Rule Reported",
    "bundle.create":            "Bundle Created",
    "bundle.edit":              "Bundle Edited",
    "bundle.delete":            "Bundle Deleted",
    "bundle.tags_updated":      "Bundle Tags Updated",
    "bundle.rule_added":        "Rule Added to Bundle",
    "comment.add":              "Comment Added",
    "comment.delete":           "Comment Deleted",
    "bundle_comment.add":       "Bundle Comment Added",
    "bundle_comment.delete":    "Bundle Comment Deleted",
    "user.register":            "User Registered",
    "user.login":               "User Logged In",
    "user.logout":              "User Logged Out",
    "user.edit_profile":        "Profile Updated",
    "user.verified":            "Account Verified",
    "user.owner_request":       "Ownership Request Submitted",
    "tag.create":               "Tag Created",
    "tag.edit":                 "Tag Edited",
    "tag.delete":               "Tag Deleted",
    "tag.bulk_delete":          "Tags Bulk Deleted",
    "tag.family_delete":        "Tag Family Deleted",
    "tag.toggle_visibility":    "Tag Visibility Toggled",
    "tag.toggle_status":        "Tag Status Toggled",
    "job.create":               "Job Created",
    "job.cancel":               "Job Cancelled",
    "job.pause":                "Job Paused",
    "job.resume":               "Job Resumed",
    "job.delete":               "Job Deleted",
    "github.import_started":    "GitHub Import Started",
    "github.update_started":    "GitHub Update Started",
    "github.source_deleted":    "GitHub Source Deleted",
    "admin.update_misp":        "MISP Data Updated",
    "admin.promote_user":       "User Promoted to Admin",
    "admin.demote_user":        "Admin Rights Removed",
    "admin.delete_user":        "User Deleted",
    "admin.request_approved":   "Ownership Request Approved",
    "admin.request_rejected":   "Ownership Request Rejected",
    "admin.owner_request":      "Ownership Request Submitted",
    "admin.logs_bulk_delete":   "Logs Bulk Delete Queued",
    "admin.submodule_update":   "Submodules Updated",
    "admin.settings_changed":   "Admin Settings Changed",
    "admin.test_email_sent":    "Test Email Sent",
    "admin.instance_init":      "Instance Config Refreshed",
    "admin.import_tag_families":"Tag Families Imported",
    "connector.create":         "Connector Created",
    "connector.update":         "Connector Updated",
    "connector.delete":         "Connector Deleted",
    "connector.test_ok":        "Connector Test Passed",
    "connector.pull_triggered": "Connector Pull Triggered",
    "connector.pull_done":      "Connector Pull Completed",
    "admin.replace_format":     "Rule Format Replaced",
    "admin.delete_reports":     "Reports Bulk Deleted",
    "api.request":              "API Request",
}

# Known category prefixes (first segment of action)
_KNOWN_CATEGORIES = frozenset({
    'rule', 'bundle', 'bundle_comment', 'user', 'tag', 'job',
    'github', 'admin', 'comment', 'connector', 'api',
})

# Prefix to display category mapping
_CATEGORY_MAP: dict[str, str] = {
    'bundle_comment': 'comment',
}

_WARNING_KEYWORDS = (
    'delete', 'trash', 'demote', 'reject', 'ban', 'bulk_delete', 'logs_bulk_delete',
    'source_deleted', 'remove_user', 'family_delete',
)
_SUCCESS_KEYWORDS = (
    'create', 'register', 'add', 'approved', 'promote', 'import_started', 'pull_done',
    'restored', 'verified',
)


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
    if action.startswith(("comment.", "bundle_comment.")):
        return "fa-solid fa-comment"
    if action.startswith("connector."):
        return "fa-solid fa-plug"
    return "fa-solid fa-circle-dot"


def _auto_category(action: str) -> str:
    prefix = action.split('.')[0] if '.' in action else 'system'
    if prefix not in _KNOWN_CATEGORIES:
        return 'system'
    return _CATEGORY_MAP.get(prefix, prefix)


def _auto_level(action: str) -> str:
    a = action.lower()
    if any(k in a for k in _WARNING_KEYWORDS):
        return 'warning'
    if any(k in a for k in _SUCCESS_KEYWORDS):
        return 'success'
    return 'info'


def _auto_title(action: str) -> str:
    if action in _TITLES:
        return _TITLES[action]
    parts = action.replace('.', ' ').replace('_', ' ').split()
    return ' '.join(p.capitalize() for p in parts)


def log_activity(
    action: str,
    description: str,
    target_type: str | None = None,
    target_id: int | None = None,
    target_uuid: str | None = None,
    extra: dict[str, Any] | None = None,
    is_public: bool | None = None,
    icon: str | None = None,
    title: str | None = None,
    category: str | None = None,
    level: str | None = None,
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

        ip = method = url = user_agent = None
        with suppress(Exception):
            remote_addr = freq.remote_addr
            xff = (freq.headers.get('X-Forwarded-For') or '').strip()
            if xff:
                # First entry is the original client IP; subsequent entries are proxies
                ip = xff.split(',')[0].strip()[:45]
            else:
                ip = remote_addr
            url        = freq.path[:512]
            method     = freq.method
            user_agent = (freq.headers.get('User-Agent') or '')[:256] or None

        # Merge network metadata into extra without overwriting caller-supplied keys
        with suppress(Exception):
            net_meta: dict[str, Any] = {}
            if xff:
                net_meta['x_forwarded_for'] = xff[:512]
            if remote_addr and remote_addr != ip:
                net_meta['remote_addr'] = remote_addr
            if net_meta:
                extra = {**net_meta, **(extra or {})}

        resolved_public    = is_public if is_public is not None else (action in _PUBLIC_ACTIONS)
        resolved_icon      = icon if icon is not None else _default_icon(action)
        resolved_title     = title if title is not None else _auto_title(action)
        resolved_category  = category if category is not None else _auto_category(action)
        resolved_level     = level if level is not None else _auto_level(action)

        entry = ActivityLog(
            uuid        = str(uuid_mod.uuid4()),
            user_id     = user_id,
            action      = action,
            title       = resolved_title,
            description = description,
            category    = resolved_category,
            level       = resolved_level,
            ip_address  = ip,
            url         = url,
            method      = method,
            user_agent  = user_agent,
            target_type = target_type,
            target_id   = target_id,
            target_uuid = target_uuid,
            extra       = extra,
            is_public   = resolved_public,
            icon        = resolved_icon,
        )
        db.session.add(entry)
        db.session.commit()
