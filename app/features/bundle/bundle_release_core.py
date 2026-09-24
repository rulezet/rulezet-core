"""
bundle_release_core.py — versioned, frozen releases of a bundle.

A release ("v1.2") freezes *exactly* what was published: bundle metadata,
the structure tree, every custom file and every rule's content. A SOC that
deployed v1.2 can always re-download that exact content, see what changed
upstream since (rule edited by its author, rule removed…), and compare two
releases.

    build_snapshot(bundle_id)            -> dict   (also used for "current")
    compare_snapshots(old, new)          -> dict   rules/files added/removed/changed
    draft_release(bundle_id)             -> {suggested_version, notes}
    create_release(bundle_id, user, …)   -> BundleRelease
    release_zip(release)                 -> BytesIO
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import re
import uuid as uuid_mod
import zipfile

from app import db
from app.core.db_class.db import (
    Bundle, BundleNode, BundleRelease, BundleRuleAssociation, BundleTagAssociation, Rule, Tag,
)

VERSION_RE = re.compile(r"^v?\d+(\.\d+){0,2}([-+][0-9A-Za-z.\-]+)?$")


def _hash(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8", "replace")).hexdigest()


def _ext(fmt) -> str:
    return Rule(format=fmt).get_extension()


def _safe(name, fallback="untitled"):
    clean = "".join(c for c in str(name or "") if c.isprintable())
    clean = clean.replace("/", "_").replace("\\", "_").replace(":", "_").strip()
    return fallback if clean in ("", ".", "..") else clean[:200]


# ── Snapshot ──────────────────────────────────────────────────────────────

def build_snapshot(bundle_id: int) -> dict | None:
    bundle = db.session.get(Bundle, bundle_id)
    if not bundle:
        return None
    nodes = BundleNode.query.filter_by(bundle_id=bundle_id).order_by(BundleNode.id).all()
    assoc_ids = {rid for (rid,) in db.session.query(BundleRuleAssociation.rule_id)
                 .filter(BundleRuleAssociation.bundle_id == bundle_id)}
    rule_ids = assoc_ids | {n.rule_id for n in nodes if n.rule_id}
    rules = {}
    for r in (Rule.query.filter(Rule.id.in_(rule_ids), Rule.is_deleted == False).all() if rule_ids else []):
        rules[str(r.id)] = {
            "uuid": r.uuid, "title": r.title, "format": r.format or "", "license": r.license or "",
            "author": r.author or "", "version": r.version or "",
            "content": r.to_string or "", "hash": _hash(r.to_string),
        }

    children = {}
    for n in nodes:
        children.setdefault(n.parent_id, []).append(n)

    def to_json(n):
        if n.rule_id:
            if str(n.rule_id) not in rules:
                return None                     # trashed rule — not part of the release
            return {"type": "rule", "rule_id": n.rule_id}
        if n.node_type == "folder":
            return {"type": "folder", "name": n.name,
                    "children": [c for c in (to_json(x) for x in children.get(n.id, [])) if c]}
        return {"type": "file", "name": n.name, "content": n.custom_content or ""}

    tree = [c for c in (to_json(n) for n in children.get(None, [])) if c]

    tags = sorted(name for (name,) in db.session.query(Tag.name)
                  .join(BundleTagAssociation, BundleTagAssociation.tag_id == Tag.id)
                  .filter(BundleTagAssociation.bundle_id == bundle_id))
    try:
        vulns = json.loads(bundle.vulnerability_identifiers) if bundle.vulnerability_identifiers else []
    except Exception:
        vulns = []

    return {
        "bundle": {"uuid": bundle.uuid, "name": bundle.name, "description": bundle.description or "",
                   "tags": tags, "vulnerabilities": vulns},
        "rules": rules,
        "tree": tree,
    }


def _files(tree, prefix=""):
    """{path: content} of the custom files in a snapshot tree."""
    out = {}
    for n in tree or []:
        if n["type"] == "folder":
            out.update(_files(n.get("children"), f"{prefix}{n['name']}/"))
        elif n["type"] == "file":
            out[f"{prefix}{n['name']}"] = n.get("content") or ""
    return out


# ── Compare ───────────────────────────────────────────────────────────────

def compare_snapshots(old: dict, new: dict) -> dict:
    o_rules, n_rules = old.get("rules") or {}, new.get("rules") or {}
    rule = lambda d, k: {"rule_id": int(k), "title": d[k]["title"], "format": d[k]["format"]}
    added = [rule(n_rules, k) for k in n_rules.keys() - o_rules.keys()]
    removed = [rule(o_rules, k) for k in o_rules.keys() - n_rules.keys()]
    changed = [rule(n_rules, k) for k in n_rules.keys() & o_rules.keys() if n_rules[k]["hash"] != o_rules[k]["hash"]]

    o_files, n_files = _files(old.get("tree")), _files(new.get("tree"))
    f_added = sorted(n_files.keys() - o_files.keys())
    f_removed = sorted(o_files.keys() - n_files.keys())
    f_changed = sorted(p for p in n_files.keys() & o_files.keys() if n_files[p] != o_files[p])

    ob, nb = old.get("bundle") or {}, new.get("bundle") or {}
    meta = []
    if ob.get("name") != nb.get("name"):
        meta.append("name")
    if (ob.get("description") or "") != (nb.get("description") or ""):
        meta.append("description")
    if set(ob.get("tags") or []) != set(nb.get("tags") or []):
        meta.append("tags")
    if set(ob.get("vulnerabilities") or []) != set(nb.get("vulnerabilities") or []):
        meta.append("vulnerabilities")

    by_title = lambda xs: sorted(xs, key=lambda x: (x["title"] or "").lower())
    return {
        "rules_added": by_title(added), "rules_removed": by_title(removed), "rules_changed": by_title(changed),
        "files_added": f_added, "files_removed": f_removed, "files_changed": f_changed,
        "metadata_changed": meta,
        "total": len(added) + len(removed) + len(changed) + len(f_added) + len(f_removed) + len(f_changed) + len(meta),
    }


def changelog_markdown(diff: dict) -> str:
    def rules(title, xs):
        if not xs:
            return []
        out = [f"### {title} ({len(xs)})", ""]
        out += [f"- {x['title']} _({x['format'] or 'unknown'})_" for x in xs[:200]]
        if len(xs) > 200:
            out.append(f"- … and {len(xs) - 200} more")
        return out + [""]

    def files(title, xs):
        return ([f"### {title} ({len(xs)})", ""] + [f"- `{p}`" for p in xs[:200]] + [""]) if xs else []

    lines = []
    lines += rules("Rules added", diff["rules_added"])
    lines += rules("Rules updated", diff["rules_changed"])
    lines += rules("Rules removed", diff["rules_removed"])
    lines += files("Files added", diff["files_added"])
    lines += files("Files updated", diff["files_changed"])
    lines += files("Files removed", diff["files_removed"])
    if diff["metadata_changed"]:
        lines += ["### Bundle", "", "- Updated: " + ", ".join(diff["metadata_changed"]), ""]
    return "\n".join(lines).strip() or "_No changes since the previous release._"


# ── Versions / drafts ─────────────────────────────────────────────────────

def latest_release(bundle_id: int):
    return (BundleRelease.query.filter_by(bundle_id=bundle_id)
            .order_by(BundleRelease.created_at.desc(), BundleRelease.id.desc()).first())


def suggest_next_version(previous: str | None, diff: dict | None) -> str:
    if not previous:
        return "v1.0.0"
    m = re.match(r"^(v?)(\d+)(?:\.(\d+))?(?:\.(\d+))?", previous)
    if not m:
        return previous + "-next"
    prefix, major, minor, patch = m.group(1), int(m.group(2)), int(m.group(3) or 0), int(m.group(4) or 0)
    if diff and (diff["rules_removed"] or diff["files_removed"]):
        major, minor, patch = major + 1, 0, 0          # something consumers relied on is gone
    elif diff and (diff["rules_added"] or diff["files_added"]):
        minor, patch = minor + 1, 0                    # new detections
    else:
        patch += 1                                     # fixes / tuning
    return f"{prefix}{major}.{minor}.{patch}"


def draft_release(bundle_id: int) -> dict:
    current = build_snapshot(bundle_id)
    last = latest_release(bundle_id)
    if last:
        diff = compare_snapshots(last.snapshot, current)
        notes = changelog_markdown(diff)
    else:
        diff = None
        n_r, n_f = len(current["rules"]), len(_files(current["tree"]))
        notes = f"First release — {n_r} rule{'s' if n_r != 1 else ''}" + (f" and {n_f} file{'s' if n_f != 1 else ''}." if n_f else ".")
    return {
        "previous_version": last.version if last else None,
        "suggested_version": suggest_next_version(last.version if last else None, diff),
        "notes": notes,
        "diff": diff,
    }


def create_release(bundle_id: int, user, version: str, title: str | None, notes: str | None):
    """Returns (release, error_message)."""
    version = (version or "").strip()
    if not VERSION_RE.match(version):
        return None, "Version must look like v1.2.0 (or 1.2, 2.0.0-beta…)"
    if BundleRelease.query.filter_by(bundle_id=bundle_id, version=version).first():
        return None, f"Version {version} already exists for this bundle"
    snap = build_snapshot(bundle_id)
    if snap is None:
        return None, "Bundle not found"
    if not snap["rules"] and not _files(snap["tree"]):
        return None, "The bundle is empty — add rules or files before releasing it"

    health_score = None
    try:
        from .bundle_health_core import bundle_health
        h = bundle_health(bundle_id)
        health_score = h["score"] if h else None
    except Exception:
        pass

    rel = BundleRelease(
        uuid=str(uuid_mod.uuid4()), bundle_id=bundle_id, user_id=getattr(user, "id", None),
        version=version, title=(title or "").strip()[:255] or None, notes=(notes or "").strip()[:100000],
        rule_count=len(snap["rules"]), file_count=len(_files(snap["tree"])),
        health_score=health_score, snapshot=snap,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.session.add(rel)
    db.session.commit()

    try:   # history entry (not a snapshot diff — a release doesn't change the bundle)
        from app.core.db_class.db import BundleHistory
        db.session.add(BundleHistory(
            uuid=str(uuid_mod.uuid4()), bundle_id=bundle_id, user_id=getattr(user, "id", None),
            action="release", summary=f"Published release {version}" + (f" — {rel.title}" if rel.title else ""),
            changes=[{"field": "release", "label": "Release", "type": "scalar", "old": "", "new": version}],
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
    return rel, None


def status_since(release) -> dict:
    """What changed in the live bundle since this release."""
    current = build_snapshot(release.bundle_id)
    return compare_snapshots(release.snapshot, current) if current else None


# ── Frozen ZIP ────────────────────────────────────────────────────────────

def release_zip(release) -> io.BytesIO:
    snap = release.snapshot or {}
    rules = snap.get("rules") or {}
    meta = snap.get("bundle") or {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        created = release.created_at.strftime("%Y-%m-%d %H:%M UTC")
        readme = [
            f"# {meta.get('name', 'Bundle')} — {release.version}", "",
            f"> Frozen release published {created}" + (f" by {release.user.first_name}" if release.user else "") + ".",
            "> This archive is exactly what was released; later edits to the bundle or its rules are not included.", "",
            f"- **Bundle UUID**: `{meta.get('uuid', '')}`",
            f"- **Rules**: {release.rule_count}",
            f"- **Files**: {release.file_count}",
        ]
        if release.health_score is not None:
            readme.append(f"- **Health score at release**: {release.health_score}/100")
        readme += ["", "## Tags", ""] + ([f"- `{t}`" for t in meta.get("tags") or []] or ["_None_"])
        readme += ["", "## Vulnerabilities", ""] + ([f"- {v}" for v in meta.get("vulnerabilities") or []] or ["_None_"])
        readme += ["", "## Description", "", (meta.get("description") or "_No description._").strip(), "",
                   "---", "> ⚠️ Community content: rules and files are user-submitted and not reviewed by Rulezet. "
                   "Inspect them before running or deploying.", ""]
        zf.writestr("README.md", "\n".join(readme))
        zf.writestr("CHANGELOG.md", f"# {release.version}" + (f" — {release.title}" if release.title else "") + "\n\n" + (release.notes or ""))
        zf.writestr("release.json", json.dumps({
            "release": release.to_json(),
            "bundle": meta,
            "rules": [{"id": int(k), **{f: v[f] for f in ("uuid", "title", "format", "license", "author", "version", "hash")}}
                      for k, v in rules.items()],
        }, indent=2, default=str))

        def walk(nodes, path):
            for n in nodes or []:
                if n["type"] == "folder":
                    sub = f"{path}/{_safe(n['name'])}"
                    if not n.get("children"):
                        zf.writestr(sub + "/", "")
                    walk(n.get("children"), sub)
                elif n["type"] == "file":
                    zf.writestr(f"{path}/{_safe(n['name'])}", n.get("content") or "")
                else:
                    r = rules.get(str(n["rule_id"]))
                    if r:
                        zf.writestr(f"{path}/{_safe((r['title'] or '').rstrip('.'), 'rule')}.{_ext(r['format'])}", r["content"])
        walk(snap.get("tree"), "structure")

        for rid, r in rules.items():
            base = f"rules/{_safe((r['title'] or '').replace(' ', '_').rstrip('.'), 'rule')}_{rid}"
            zf.writestr(f"{base}.{_ext(r['format'])}", r["content"])
    buf.seek(0)
    return buf


# ── Viewing a release (bundle detail page in "release mode") ─────────────

def get_release(bundle_id: int, ref):
    """A release of this bundle by version string, UUID or numeric id."""
    if ref in (None, ""):
        return None
    q = BundleRelease.query.filter_by(bundle_id=bundle_id)
    ref = str(ref).strip()
    rel = q.filter_by(version=ref).first()
    if rel is None and len(ref) == 36:
        rel = q.filter_by(uuid=ref).first()
    if rel is None and ref.isdigit():
        rel = q.filter_by(id=int(ref)).first()
    return rel


def snapshot_tree_json(snapshot: dict) -> list:
    """The frozen tree in the same shape as bundle_core.build_tree_json(),
    so the page renders it with the same components. Rule nodes are lazy
    (content served from the snapshot by rule_content?release=…)."""
    rules = snapshot.get("rules") or {}
    counter = [0]

    def nid(prefix):
        counter[0] += 1
        return f"{prefix}_{counter[0]}"

    def walk(nodes):
        out = []
        for n in nodes or []:
            if n["type"] == "folder":
                out.append({"id": nid("rel_dir"), "name": n["name"], "type": "folder",
                            "children": walk(n.get("children"))})
            elif n["type"] == "file":
                out.append({"id": nid("rel_file"), "name": n["name"], "type": "file",
                            "content": n.get("content") or "", "children": []})
            else:
                r = rules.get(str(n["rule_id"]))
                if not r:
                    continue
                out.append({"id": f"rule_{n['rule_id']}_{nid('rel')}", "rule_id": n["rule_id"],
                            "name": f"{(r['title'] or '').rstrip('.')}.{_ext(r['format'])}",
                            "type": "file", "format": r["format"], "size": len(r["content"] or ""),
                            "lazy": True, "children": []})
        return out

    return walk(snapshot.get("tree"))


def release_rule_statuses(release) -> list:
    """Every rule of the release + what happened to it since, compared with
    the live library and the live bundle. Never fails on rules that were
    deleted (soft or hard) since — the snapshot holds their content."""
    rules = (release.snapshot or {}).get("rules") or {}
    ids = [int(k) for k in rules.keys()]
    live = {rid: (deleted, content) for rid, deleted, content in
            db.session.query(Rule.id, Rule.is_deleted, Rule.to_string).filter(Rule.id.in_(ids))} if ids else {}
    in_bundle_now = {rid for (rid,) in db.session.query(BundleRuleAssociation.rule_id)
                     .filter(BundleRuleAssociation.bundle_id == release.bundle_id)} | \
                    {rid for (rid,) in db.session.query(BundleNode.rule_id)
                     .filter(BundleNode.bundle_id == release.bundle_id, BundleNode.rule_id.isnot(None))}
    out = []
    for k, r in rules.items():
        rid = int(k)
        state = live.get(rid)
        if state is None or state[0]:
            status = "deleted"                      # removed from the library since
        elif _hash(state[1]) != r["hash"]:
            status = "updated"                      # author edited it since
        else:
            status = "unchanged"
        out.append({"rule_id": rid, "uuid": r["uuid"], "title": r["title"], "format": r["format"],
                    "license": r.get("license") or "", "author": r.get("author") or "",
                    "status": status, "in_bundle_now": rid in in_bundle_now,
                    "rule_exists": state is not None and not state[0]})
    out.sort(key=lambda x: (x["title"] or "").lower())
    return out


def release_view(release) -> dict:
    snap = release.snapshot or {}
    statuses = release_rule_statuses(release)
    counts = {s: sum(1 for x in statuses if x["status"] == s) for s in ("unchanged", "updated", "deleted")}
    counts["not_in_bundle_now"] = sum(1 for x in statuses if not x["in_bundle_now"])
    return {
        "release": release.to_json(),
        "bundle": snap.get("bundle") or {},
        "structure": snapshot_tree_json(snap),
        "rules": statuses,
        "rule_counts": counts,
    }


def release_zip_part(release, part: str) -> io.BytesIO:
    """Frozen equivalents of the live per-section downloads:
    'structure' (tree only), 'rules' (flat rules), 'files' (custom files only)."""
    snap = release.snapshot or {}
    rules = snap.get("rules") or {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        def walk(nodes, path, files_only=False):
            for n in nodes or []:
                if n["type"] == "folder":
                    sub = f"{path}/{_safe(n['name'])}".strip("/")
                    if not n.get("children") and not files_only:
                        zf.writestr(sub + "/", "")
                    walk(n.get("children"), sub, files_only)
                elif n["type"] == "file":
                    zf.writestr(f"{path}/{_safe(n['name'])}".strip("/"), n.get("content") or "")
                elif not files_only:
                    r = rules.get(str(n["rule_id"]))
                    if r:
                        zf.writestr(f"{path}/{_safe((r['title'] or '').rstrip('.'), 'rule')}.{_ext(r['format'])}".strip("/"), r["content"])
        if part == "structure":
            zf.writestr("release.json", json.dumps({"release": release.to_json(), "bundle": snap.get("bundle")}, indent=2, default=str))
            walk(snap.get("tree"), "")
        elif part == "files":
            walk(snap.get("tree"), "", files_only=True)
        else:  # rules
            for rid, r in rules.items():
                base = f"{_safe((r['title'] or '').replace(' ', '_').rstrip('.'), 'rule')}_{rid}"
                zf.writestr(f"{base}.{_ext(r['format'])}", r["content"])
                zf.writestr(f"{base}.json", json.dumps({"id": int(rid), **{f: r.get(f) for f in ("uuid", "title", "format", "license", "author", "version", "hash")}}, indent=2))
    buf.seek(0)
    return buf
