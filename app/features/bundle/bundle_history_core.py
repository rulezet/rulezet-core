"""
bundle_history_core.py — change history of a bundle (detail page → History tab).

Usage (around any mutation of a bundle):

    from app.features.bundle.bundle_history_core import track_bundle_change

    with track_bundle_change(bundle_id, "tags", user=current_user):
        ...mutate tags...

A snapshot of the bundle is taken before and after the block; if anything
changed, a BundleHistory row is written with the human-readable diff. The
block's own exceptions propagate untouched, and history failures never
break the caller (history is best-effort, like log_activity).

Frequent actions (the structure editor autosaves ~1s after every change)
are coalesced: consecutive changes by the same user and action within
COALESCE_WINDOW update the previous row instead of adding a new one.
"""

from __future__ import annotations

import datetime
import functools
import hashlib
import threading
import uuid as uuid_mod
from contextlib import contextmanager

from flask_login import current_user

from app import db
from app.core.db_class.db import (
    Bundle, BundleHistory, BundleNode, BundleRuleAssociation, BundleTagAssociation, Rule, Tag,
)

COALESCE_WINDOW = datetime.timedelta(minutes=10)
COALESCED_ACTIONS = {"structure", "tags", "rules", "details"}
# Filling a bundle right after creating it (from a RuleList filter, a
# workspace, or by hand) is part of its creation, not N separate edits:
# these actions by the creator, within COALESCE_WINDOW of the "created"
# entry, are folded into it.
FOLD_INTO_CREATION = {"structure", "rules", "tags", "details"}
MAX_LIST_ITEMS = 60          # per added/removed/changed list in `changes`

FIELD_LABELS = {
    "name": "Name",
    "description": "Description",
    "access": "Visibility",
    "tags": "Tags",
    "vulnerabilities": "Vulnerabilities",
    "rules": "Rules",
    "rules_moved": "Rules moved",
    "files": "Files",
    "files_modified": "Files edited",
    "files_renamed": "Files renamed",
    "folders": "Folders",
    "share_link": "Share link",
}


# ── Snapshot ──────────────────────────────────────────────────────────────

def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def snapshot_bundle(bundle_id: int) -> dict | None:
    """Compact, JSON-able picture of everything the history tracks.
    Files are stored as content hashes (never the content itself)."""
    bundle = db.session.get(Bundle, bundle_id)
    if not bundle:
        return None

    tag_names = [
        name for (name,) in db.session.query(Tag.name)
        .join(BundleTagAssociation, BundleTagAssociation.tag_id == Tag.id)
        .filter(BundleTagAssociation.bundle_id == bundle_id)
    ]

    try:
        import json
        vulns = json.loads(bundle.vulnerability_identifiers) if bundle.vulnerability_identifiers else []
    except Exception:
        vulns = []

    nodes = BundleNode.query.filter_by(bundle_id=bundle_id).all()
    by_id = {n.id: n for n in nodes}
    # Rules can be attached without a tree node (API / legacy add_rule_to_bundle)
    assoc_rule_ids = {rid for (rid,) in db.session.query(BundleRuleAssociation.rule_id)
                      .filter(BundleRuleAssociation.bundle_id == bundle_id)}
    all_rule_ids = assoc_rule_ids | {n.rule_id for n in nodes if n.rule_id}
    rule_titles = {
        rid: title for rid, title in db.session.query(Rule.id, Rule.title).filter(Rule.id.in_(all_rule_ids))
    } if all_rule_ids else {}

    def path_of(node):
        parts, cur, guard = [], node, 0
        while cur is not None and guard < 50:
            parts.append(cur.name or "?")
            cur = by_id.get(cur.parent_id)
            guard += 1
        return "/".join(reversed(parts))

    rules, files, folders = {}, {}, []
    for n in nodes:
        if n.node_type == "folder":
            folders.append(path_of(n))
        elif n.rule_id:
            parent = by_id.get(n.parent_id)
            rules[str(n.rule_id)] = {
                "title": rule_titles.get(n.rule_id) or n.name or f"rule #{n.rule_id}",
                "folder": path_of(parent) if parent else "",
            }
        else:
            content = n.custom_content or ""
            files[path_of(n)] = hashlib.sha1(content.encode("utf-8", "replace")).hexdigest()[:16]
    for rid in assoc_rule_ids:
        rules.setdefault(str(rid), {"title": rule_titles.get(rid) or f"rule #{rid}", "folder": "(not placed)"})

    return {
        "name": bundle.name,
        "description": bundle.description or "",
        "access": bool(bundle.access),
        "tags": sorted(tag_names),
        "vulnerabilities": sorted(str(v) for v in vulns),
        "rules": rules,
        "files": files,
        "folders": sorted(folders),
        # Never the token itself (history is visible to viewers) — a short
        # fingerprint so "regenerated" shows up as a change.
        "share_link": ("#" + hashlib.sha1(bundle.share_token.encode()).hexdigest()[:6]) if bundle.share_token else None,
    }


# ── Diff ──────────────────────────────────────────────────────────────────

def _clip(items):
    items = sorted(items)
    if len(items) > MAX_LIST_ITEMS:
        return items[:MAX_LIST_ITEMS] + [f"… +{len(items) - MAX_LIST_ITEMS} more"]
    return items


def _excerpt(text, n=70):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


def _text_change_excerpts(old: str, new: str, width: int = 90):
    """Excerpts of both texts starting just before their first difference —
    so an edit deep inside a long description doesn't render as two
    identical openings. Returns (old_excerpt, new_excerpt, stats)."""
    import difflib
    o = " ".join((old or "").split())
    n = " ".join((new or "").split())
    i = 0
    while i < min(len(o), len(n)) and o[i] == n[i]:
        i += 1
    start = max(0, i - 25)
    # step back to a word boundary for readability
    if start:
        sp = o.rfind(" ", 0, start + 1)
        start = sp + 1 if sp != -1 and start - sp < 15 else start

    def cut(t):
        chunk = t[start:start + width]
        return ("…" if start else "") + chunk + ("…" if start + width < len(t) else "")

    ol, nl = (old or "").splitlines(), (new or "").splitlines()
    added = removed = 0
    for line in difflib.ndiff(ol, nl):
        if line.startswith("+ "):
            added += 1
        elif line.startswith("- "):
            removed += 1
    stats = f"+{added} / −{removed} line{'s' if max(added, removed) != 1 else ''}"
    return (cut(o) or "—"), (cut(n) or "—"), stats


def diff_snapshots(old: dict | None, new: dict | None) -> list:
    """Human-readable changes for meta-change-list:
    scalar → {field, label, type:'scalar', old, new}
    list   → {field, label, type:'list', added, removed, changed?}"""
    if not old or not new:
        return []
    changes = []

    def scalar(field, o, n):
        changes.append({"field": field, "label": FIELD_LABELS[field], "type": "scalar", "old": o, "new": n})

    def listing(field, added=(), removed=(), changed=()):
        if added or removed or changed:
            entry = {"field": field, "label": FIELD_LABELS[field], "type": "list",
                     "added": _clip(added), "removed": _clip(removed)}
            if changed:
                entry["changed"] = _clip(changed)
            changes.append(entry)

    if old.get("name") != new.get("name"):
        scalar("name", old.get("name"), new.get("name"))
    if (old.get("description") or "") != (new.get("description") or ""):
        o_ex, n_ex, stats = _text_change_excerpts(old.get("description"), new.get("description"))
        changes.append({"field": "description", "label": f"Description ({stats})", "type": "scalar",
                        "old": o_ex, "new": n_ex})
    if old.get("access") != new.get("access"):
        scalar("access", "Public" if old.get("access") else "Private", "Public" if new.get("access") else "Private")

    for field in ("tags", "vulnerabilities"):
        o, n = set(old.get(field) or []), set(new.get(field) or [])
        listing(field, added=n - o, removed=o - n)

    o_rules, n_rules = old.get("rules") or {}, new.get("rules") or {}
    listing("rules",
            added=[n_rules[k]["title"] for k in n_rules.keys() - o_rules.keys()],
            removed=[o_rules[k]["title"] for k in o_rules.keys() - n_rules.keys()])
    moved = [f"{n_rules[k]['title']} → {n_rules[k]['folder'] or '/'}"
             for k in n_rules.keys() & o_rules.keys() if n_rules[k]["folder"] != o_rules[k]["folder"]]
    listing("rules_moved", changed=moved)

    o_files, n_files = old.get("files") or {}, new.get("files") or {}
    added_f = set(n_files) - set(o_files)
    removed_f = set(o_files) - set(n_files)
    # Same content under a new path = rename/move, not remove + add
    renamed = []
    by_hash_removed = {}
    for p in removed_f:
        by_hash_removed.setdefault(o_files[p], []).append(p)
    for p in sorted(added_f):
        h = n_files[p]
        if by_hash_removed.get(h):
            src = by_hash_removed[h].pop()
            renamed.append(f"{src} → {p}")
            removed_f.discard(src)
            added_f.discard(p)
    listing("files", added=added_f, removed=removed_f)
    listing("files_renamed", changed=renamed)
    listing("files_modified", changed=[p for p in set(n_files) & set(o_files) if n_files[p] != o_files[p]])

    o_dirs, n_dirs = set(old.get("folders") or []), set(new.get("folders") or [])
    listing("folders", added=n_dirs - o_dirs, removed=o_dirs - n_dirs)

    if "share_link" in old or "share_link" in new:
        if old.get("share_link") != new.get("share_link"):
            scalar("share_link", f"Active {old['share_link']}" if old.get("share_link") else "None",
                   f"Active {new['share_link']}" if new.get("share_link") else "Revoked")
    return changes


def _creation_content(after: dict) -> tuple[str, list]:
    """Summary + change rows describing what a bundle was created with."""
    empty = {**after, "rules": {}, "files": {}, "folders": [], "tags": [], "vulnerabilities": []}
    changes = [c for c in diff_snapshots(empty, after) if c["field"] in ("rules", "files", "folders", "tags", "vulnerabilities")]
    n_rules, n_files, n_dirs = len(after.get("rules") or {}), len(after.get("files") or {}), len(after.get("folders") or [])
    parts = []
    if n_rules:
        parts.append(f"{n_rules} rule{'s' if n_rules > 1 else ''}")
    if n_files:
        parts.append(f"{n_files} file{'s' if n_files > 1 else ''}")
    summary = "Bundle created" + (" with " + " and ".join(parts) if parts else "")
    if n_dirs and parts:
        summary += f" in {n_dirs} folder{'s' if n_dirs > 1 else ''}"
    return summary, changes


def summarize(action: str, changes: list) -> str:
    if action == "created":
        return "Bundle created"
    if not changes:
        return "No visible change"

    def count(field, key):
        for c in changes:
            if c["field"] == field:
                return len([x for x in c.get(key, []) if not str(x).startswith("… +")])
        return 0

    parts = []
    for field, verb in (("rules", "rule"), ("files", "file")):
        a, r = count(field, "added"), count(field, "removed")
        if a:
            parts.append(f"added {a} {verb}{'s' if a > 1 else ''}")
        if r:
            parts.append(f"removed {r} {verb}{'s' if r > 1 else ''}")
    edited = count("files_modified", "changed")
    if edited:
        parts.append(f"edited {edited} file{'s' if edited > 1 else ''}")
    for field, label in (("rules_moved", "moved rules"), ("files_renamed", "renamed files"),
                         ("folders", "reorganized folders"), ("name", "renamed the bundle"),
                         ("description", "updated the description"), ("tags", "updated tags"),
                         ("vulnerabilities", "updated vulnerabilities")):
        if any(c["field"] == field for c in changes):
            parts.append(label)
    for c in changes:
        if c["field"] == "access":
            parts.append(f"made the bundle {c['new'].lower()}")
        if c["field"] == "share_link":
            parts.append("revoked the share link" if c["new"] == "Revoked"
                         else ("regenerated the share link" if c["old"] != "None" else "created a share link"))
    text = ", ".join(dict.fromkeys(parts)) or "Updated the bundle"
    return (text[0].upper() + text[1:])[:500]


# ── Recording ─────────────────────────────────────────────────────────────

def _actor_id(user):
    try:
        if user is not None and getattr(user, "id", None):
            return user.id
        if current_user and current_user.is_authenticated:
            return current_user.id
    except Exception:
        pass
    return None


def record_bundle_change(bundle_id: int, action: str, before: dict | None, after: dict | None, user=None):
    """Write (or coalesce into) a BundleHistory row. Returns the row or None."""
    try:
        user_id = _actor_id(user)
        if action == "created":
            row = BundleHistory(uuid=str(uuid_mod.uuid4()), bundle_id=bundle_id, user_id=user_id,
                                action="created", summary="Bundle created", changes=[],
                                old_snapshot=None, new_snapshot=after)
            db.session.add(row)
            db.session.commit()
            return row

        if before is None or after is None:
            return None

        last = (BundleHistory.query.filter_by(bundle_id=bundle_id)
                .order_by(BundleHistory.updated_at.desc(), BundleHistory.id.desc()).first())
        now = _now()

        def _recent(row):
            ts = row.updated_at or row.created_at
            return ts is not None and now - ts.replace(tzinfo=ts.tzinfo or datetime.timezone.utc) < COALESCE_WINDOW

        if (action in FOLD_INTO_CREATION and last is not None and last.action == "created"
                and last.user_id == user_id and _recent(last)):
            last.new_snapshot = after
            last.summary, last.changes = _creation_content(after)
            last.updated_at = now
            db.session.commit()
            return last
        if (action in COALESCED_ACTIONS and last is not None and last.action == action
                and last.user_id == user_id and last.updated_at is not None
                and now - last.updated_at.replace(tzinfo=last.updated_at.tzinfo or datetime.timezone.utc) < COALESCE_WINDOW):
            changes = diff_snapshots(last.old_snapshot, after)
            if not changes:
                db.session.delete(last)          # the edits cancelled out
            else:
                last.new_snapshot = after
                last.changes = changes
                last.summary = summarize(action, changes)
                last.updated_at = now
            db.session.commit()
            return last

        changes = diff_snapshots(before, after)
        if not changes:
            return None
        row = BundleHistory(uuid=str(uuid_mod.uuid4()), bundle_id=bundle_id, user_id=user_id,
                            action=action, summary=summarize(action, changes), changes=changes,
                            old_snapshot=before, new_snapshot=after, created_at=now, updated_at=now)
        db.session.add(row)
        db.session.commit()
        return row
    except Exception:
        db.session.rollback()
        return None


_tracking = threading.local()


@contextmanager
def track_bundle_change(bundle_id, action: str, user=None):
    """Snapshot before/after the wrapped block and record the difference.
    Nested tracking (a tracked function calling another one) only records
    once, at the outermost level."""
    depth = getattr(_tracking, "depth", 0)
    if depth:
        _tracking.depth = depth + 1
        try:
            yield
        finally:
            _tracking.depth = depth
        return

    try:
        before = snapshot_bundle(bundle_id) if bundle_id else None
    except Exception:
        before = None
    _tracking.depth = 1
    try:
        yield
    finally:
        _tracking.depth = 0
    if before is None:
        return
    try:
        after = snapshot_bundle(bundle_id)   # the block committed → objects already expired
    except Exception:
        return
    record_bundle_change(bundle_id, action, before, after, user)


def tracked(action: str, user_arg: int | None = None):
    """Decorator for bundle_core functions whose first argument is bundle_id.
    `user_arg` = positional index of a User argument, if the function has one."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(bundle_id, *args, **kwargs):
            user = kwargs.get("user")
            if user is None and user_arg is not None and len(args) >= user_arg:
                user = args[user_arg - 1]
            with track_bundle_change(bundle_id, action, user=user):
                return fn(bundle_id, *args, **kwargs)
        return wrapper
    return deco


def record_bundle_created(bundle_id: int, user=None):
    try:
        record_bundle_change(bundle_id, "created", None, snapshot_bundle(bundle_id), user)
    except Exception:
        pass


# ── Reading ───────────────────────────────────────────────────────────────

def get_bundle_history_page(bundle_id: int, page: int = 1, per_page: int = 30):
    return (BundleHistory.query.filter_by(bundle_id=bundle_id)
            .order_by(BundleHistory.updated_at.desc(), BundleHistory.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False))


def get_bundle_history_entry(bundle_id: int, entry_id: int):
    return BundleHistory.query.filter_by(bundle_id=bundle_id, id=entry_id).first()
