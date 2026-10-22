"""Portable JSON of a whole bundle — export it on one instance, import it on
another (admin only) and get the same bundle back.

Format ("rulezet-bundle", version 1):
    bundle      name, description, access, uuid, vulnerabilities, tags (names)
    rules       portable rules (rule_portable.rule_to_portable) + "bundle_description"
    structure   the folder tree — folders, custom files (with content) and
                rule nodes {"type": "rule", "ref": <rule uuid>}
    notes       title, content, severity, status, tags
    ai_analyses agent_key, content, meta, model, is_public, created_at
    releases    version, title, notes, snapshot (rule ids remapped on import)

Votes, views, comments and history belong to the source instance's users
and are not carried over. On import every rule is checked like a manual
submission: a rule that already exists here (same uuid or content) is reused
as is, a new valid one is created under the importing user, an invalid one
is left out (its tree nodes too).
"""
import datetime
import json
import uuid as uuid_mod

from app import db
from app.core.db_class.bundle import (Bundle, BundleNode, BundleNote, BundleNoteTag,
                                      BundleRelease, BundleRuleAssociation)
from app.core.db_class.ai import AIGeneration
from app.core.db_class.rule import Rule
from app.core.db_class.tag import BundleTagAssociation, Tag
from app.features.rule.rule_portable import (rule_to_portable, normalize_rule_json, preview_rule,
                                             create_rule_from_portable, find_existing_rule)

FORMAT_NAME = "rulezet-bundle"
FORMAT_VERSION = 1
MAX_IMPORT_BYTES = 30 * 1024 * 1024
MAX_IMPORT_RULES = 5000


def _now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


def _iso(dt):
    return dt.isoformat() if dt else None


def _parse_dt(value):
    try:
        return datetime.datetime.fromisoformat(value) if isinstance(value, str) and value else None
    except ValueError:
        return None


# ── Export ───────────────────────────────────────────────────────────────────

def bundle_to_portable(bundle: Bundle) -> dict:
    from flask import current_app

    assocs = BundleRuleAssociation.query.filter_by(bundle_id=bundle.id).all()
    rules, ref_by_id = [], {}
    for a in assocs:
        if not a.rule or a.rule.is_deleted or a.rule_id in ref_by_id:
            continue
        data = rule_to_portable(a.rule)
        data["bundle_description"] = a.description
        ref_by_id[a.rule_id] = a.rule.uuid
        rules.append(data)

    nodes = BundleNode.query.filter_by(bundle_id=bundle.id).order_by(BundleNode.id).all()
    children = {}
    for n in nodes:
        children.setdefault(n.parent_id, []).append(n)

    def node_json(n):
        if n.rule_id:
            ref = ref_by_id.get(n.rule_id)
            return {"type": "rule", "ref": ref, "name": n.name} if ref else None
        if n.node_type == "folder":
            return {"type": "folder", "name": n.name,
                    "children": [c for c in (node_json(x) for x in children.get(n.id, [])) if c]}
        return {"type": "file", "name": n.name, "content": n.custom_content or ""}

    notes = [{
        "title": n.title, "content": n.content, "severity": n.severity, "status": n.status,
        "tags": [a.tag.name for a in n.tag_assocs if a.tag],
        "created_at": _iso(n.created_at),
    } for n in bundle.notes.order_by(BundleNote.created_at)]

    analyses = [{
        "agent_key": g.agent_key, "content": g.content, "meta": g.meta, "model": g.model,
        "is_public": g.is_public, "created_at": _iso(g.created_at),
    } for g in sorted(bundle.ai_generations, key=lambda g: g.created_at or _now())]

    releases = []
    for r in bundle.releases.order_by(BundleRelease.created_at):
        snap = r.snapshot or {}
        # Rule ids only mean something here — key the snapshot by rule uuid
        snap_rules = {(v or {}).get("uuid") or k: v for k, v in (snap.get("rules") or {}).items()}
        id_to_uuid = {k: (v or {}).get("uuid") for k, v in (snap.get("rules") or {}).items()}

        def remap(tree):
            out = []
            for n in tree or []:
                n = dict(n)
                if n.get("type") == "rule":
                    n["ref"] = id_to_uuid.get(str(n.pop("rule_id", "")))
                elif n.get("children"):
                    n["children"] = remap(n["children"])
                out.append(n)
            return out
        releases.append({
            "version": r.version, "title": r.title, "notes": r.notes, "health_score": r.health_score,
            "created_at": _iso(r.created_at),
            "snapshot": {"bundle": snap.get("bundle"), "rules": snap_rules, "tree": remap(snap.get("tree"))},
        })

    try:
        vulns = json.loads(bundle.vulnerability_identifiers) if bundle.vulnerability_identifiers else []
    except (json.JSONDecodeError, TypeError):
        vulns = []

    return {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "exported_at": _iso(_now()),
        "instance": current_app.config.get("INSTANCE_PUBLIC_URL"),
        "bundle": {
            "uuid": bundle.uuid, "name": bundle.name, "description": bundle.description,
            "access": bool(bundle.access), "created_by": bundle.created_by,
            "created_at": _iso(bundle.created_at),
            "vulnerabilities": vulns,
            "tags": sorted(a.tag.name for a in bundle.tags_assocs if a.tag),
        },
        "rules": rules,
        "structure": [c for c in (node_json(n) for n in children.get(None, [])) if c],
        "notes": notes,
        "ai_analyses": analyses,
        "releases": releases,
    }


# ── Import ───────────────────────────────────────────────────────────────────

def parse_bundle_json(raw) -> tuple[dict | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "Paste the bundle JSON first."
    if len(raw.encode("utf-8")) > MAX_IMPORT_BYTES:
        return None, f"That JSON is too large (max {MAX_IMPORT_BYTES // (1024 * 1024)} MB)."
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e.msg} (line {e.lineno}, column {e.colno})."
    if not isinstance(data, dict) or data.get("format") != FORMAT_NAME:
        return None, f'Not a bundle export (expected "format": "{FORMAT_NAME}").'
    if not isinstance(data.get("bundle"), dict) or not str(data["bundle"].get("name") or "").strip():
        return None, "The export has no bundle name."
    if not isinstance(data.get("rules", []), list) or len(data.get("rules", [])) > MAX_IMPORT_RULES:
        return None, f"Invalid rules list (max {MAX_IMPORT_RULES} rules)."
    for key in ("structure", "notes", "ai_analyses", "releases"):
        if not isinstance(data.get(key, []), list):
            return None, f'"{key}" must be a list.'
    return data, None


def _analyse_rules(data) -> list:
    """One entry per exported rule: ref, rule_dict, preview, action
    (create | existing | invalid | trash)."""
    out = []
    for i, raw in enumerate(data.get("rules") or []):
        ref = str((raw or {}).get("uuid") or f"#{i}") if isinstance(raw, dict) else f"#{i}"
        rule_dict, error = normalize_rule_json(raw)
        if error:
            out.append({"ref": ref, "rule_dict": None, "action": "invalid",
                        "title": (raw or {}).get("title") if isinstance(raw, dict) else None, "error": error,
                        "bundle_description": None, "preview": None})
            continue
        preview = preview_rule(rule_dict)
        existing = preview["existing"]
        if existing and existing["kind"] == "trash":
            action = "trash"
        elif existing:
            action = "existing"
        elif preview["valid"]:
            action = "create"
        else:
            action = "invalid"
        out.append({"ref": ref, "rule_dict": rule_dict, "action": action, "title": rule_dict["title"],
                    "error": preview["error"], "preview": preview,
                    "bundle_description": raw.get("bundle_description")})
    return out


def _count_tree(nodes, counts=None):
    counts = counts or {"folders": 0, "files": 0, "rules": 0}
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        kind = n.get("type")
        if kind == "folder":
            counts["folders"] += 1
            _count_tree(n.get("children"), counts)
        elif kind == "file":
            counts["files"] += 1
        elif kind == "rule":
            counts["rules"] += 1
    return counts


def _known_tag_names(names) -> dict:
    names = [n for n in names if isinstance(n, str) and n.strip()]
    if not names:
        return {}
    return {t.name: t for t in Tag.query.filter(Tag.name.in_(names)).all()}


def preview_bundle_import(data: dict, user) -> dict:
    from .bundle_core import bundle_name_taken

    b = data["bundle"]
    name = str(b.get("name")).strip()[:255]
    rules = _analyse_rules(data)
    tag_names = [t for t in (b.get("tags") or []) if isinstance(t, str)]
    known = _known_tag_names(tag_names)
    counts = {a: sum(1 for r in rules if r["action"] == a) for a in ("create", "existing", "invalid", "trash")}
    return {
        "bundle": {
            "name": name, "name_taken": bundle_name_taken(name, user.id),
            "description": b.get("description") or "", "access": bool(b.get("access", True)),
            "vulnerabilities": [v for v in (b.get("vulnerabilities") or []) if isinstance(v, str)],
            "tags": [{"name": t, "found": t in known} for t in tag_names],
            "source_uuid": b.get("uuid"), "instance": data.get("instance"),
            "exported_at": data.get("exported_at"),
        },
        "rules": [{
            "ref": r["ref"], "title": r["title"], "action": r["action"], "error": r["error"],
            "preview": r["preview"],
        } for r in rules],
        "counts": counts,
        "structure": _count_tree(data.get("structure")),
        "notes": len(data.get("notes") or []),
        "ai_analyses": len(data.get("ai_analyses") or []),
        "releases": [str((r or {}).get("version") or "") for r in data.get("releases") or [] if isinstance(r, dict)],
    }


def _structure_for_editor(nodes, rule_ids_by_ref) -> list:
    """Exported tree → the editor's structure (save_workspace input); rule
    nodes whose rule wasn't imported are dropped."""
    out = []
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        kind = n.get("type")
        name = str(n.get("name") or "").strip()[:255]
        if kind == "rule":
            rid = rule_ids_by_ref.get(n.get("ref"))
            if rid:
                out.append({"type": "file", "name": name or "rule", "rule_id": rid, "children": []})
        elif kind == "folder":
            out.append({"type": "folder", "name": name or "folder",
                        "children": _structure_for_editor(n.get("children"), rule_ids_by_ref)})
        elif kind == "file":
            content = n.get("content")
            out.append({"type": "file", "name": name or "file",
                        "content": content if isinstance(content, str) else "", "children": []})
    return out


def _remap_release_snapshot(snap, rule_ids_by_ref):
    if not isinstance(snap, dict):
        return None
    rules = {}
    for ref, r in (snap.get("rules") or {}).items():
        rid = rule_ids_by_ref.get(ref)
        if rid and isinstance(r, dict):
            rules[str(rid)] = r

    def remap(tree):
        out = []
        for n in tree or []:
            if not isinstance(n, dict):
                continue
            n = dict(n)
            if n.get("type") == "rule":
                rid = rule_ids_by_ref.get(n.pop("ref", None))
                if not rid:
                    continue
                n["rule_id"] = rid
            elif n.get("type") == "folder":
                n["children"] = remap(n.get("children"))
            out.append(n)
        return out
    return {"bundle": snap.get("bundle") or {}, "rules": rules, "tree": remap(snap.get("tree"))}


def import_bundle(data: dict, user, name: str | None = None) -> tuple[Bundle | None, dict]:
    """Create the bundle (and its missing rules). Returns (bundle, report)."""
    from .bundle_core import bundle_name_taken, create_bundle, validate_structure, save_workspace, \
        place_rules_in_structure
    from app.core.utils.activity_log import log_activity

    b = data["bundle"]
    name = (name or str(b.get("name"))).strip()[:255]
    if not name:
        return None, {"error": "The bundle needs a name."}
    if bundle_name_taken(name, user.id):
        return None, {"error": f'You already have a bundle called "{name}" — pick another name.'}

    report = {"created": [], "reused": [], "skipped": []}
    rule_ids_by_ref, descriptions = {}, {}
    for r in _analyse_rules(data):
        if r["action"] == "create":
            new_rule, message = create_rule_from_portable(r["rule_dict"], user, record_activity=False)
            if new_rule:
                rule_ids_by_ref[r["ref"]] = new_rule.id
                report["created"].append({"id": new_rule.id, "title": new_rule.title})
            else:
                # Same content twice in the export → the first copy is reused
                kind, existing = find_existing_rule(r["rule_dict"])
                if existing is not None and kind != "trash":
                    rule_ids_by_ref[r["ref"]] = existing.id
                    report["reused"].append({"id": existing.id, "title": existing.title})
                else:
                    report["skipped"].append({"title": r["title"], "reason": str(message)})
        elif r["action"] == "existing":
            rid = r["preview"]["existing"]["id"]
            rule_ids_by_ref[r["ref"]] = rid
            report["reused"].append({"id": rid, "title": r["preview"]["existing"]["title"]})
        else:
            reason = "in the trash on this instance" if r["action"] == "trash" else (r["error"] or "invalid")
            report["skipped"].append({"title": r["title"], "reason": reason})
        if r["ref"] in rule_ids_by_ref:
            descriptions[rule_ids_by_ref[r["ref"]]] = r["bundle_description"]

    vulns = [v for v in (b.get("vulnerabilities") or []) if isinstance(v, str)]
    bundle = create_bundle({
        "name": name,
        "description": b.get("description") if isinstance(b.get("description"), str) else "",
        "public": bool(b.get("access", True)),
        "vulnerability_identifiers": vulns,
    }, user)

    for tag in _known_tag_names(b.get("tags") or []).values():
        db.session.add(BundleTagAssociation(uuid=str(uuid_mod.uuid4()), bundle_id=bundle.id,
                                            tag_id=tag.id, user_id=user.id, added_at=_now()))

    for rid in dict.fromkeys(rule_ids_by_ref.values()):
        db.session.add(BundleRuleAssociation(
            bundle_id=bundle.id, rule_id=rid, added_at=_now(),
            description=descriptions.get(rid) or f"Imported from JSON on {_now():%Y-%m-%d}"))
    db.session.commit()

    structure = _structure_for_editor(data.get("structure"), rule_ids_by_ref)
    error = validate_structure(structure)
    if error:
        report["structure_error"] = error
    elif structure:
        save_workspace(bundle.id, structure)
    placed = {n.rule_id for n in BundleNode.query.filter_by(bundle_id=bundle.id) if n.rule_id}
    missing = [rid for rid in dict.fromkeys(rule_ids_by_ref.values()) if rid not in placed]
    if missing:
        place_rules_in_structure(bundle.id, missing)
        db.session.commit()

    for n in data.get("notes") or []:
        if not isinstance(n, dict) or not str(n.get("title") or "").strip() or not isinstance(n.get("content"), str):
            continue
        note = BundleNote(
            uuid=str(uuid_mod.uuid4()), bundle_id=bundle.id, user_id=user.id,
            title=str(n["title"]).strip()[:200], content=n["content"],
            severity=n.get("severity") if n.get("severity") in ("info", "warning", "critical") else "warning",
            status=n.get("status") if n.get("status") in ("open", "resolved") else "open",
            created_at=_parse_dt(n.get("created_at")) or _now(), updated_at=_now(),
        )
        db.session.add(note)
        db.session.flush()
        for tag in _known_tag_names(n.get("tags") or []).values():
            db.session.add(BundleNoteTag(note_id=note.id, tag_id=tag.id))

    for g in data.get("ai_analyses") or []:
        if not isinstance(g, dict) or not isinstance(g.get("content"), str) or not g.get("agent_key"):
            continue
        db.session.add(AIGeneration(
            uuid=str(uuid_mod.uuid4()), agent_key=str(g["agent_key"])[:50], bundle_id=bundle.id,
            user_id=user.id, content=g["content"], meta=g.get("meta") if isinstance(g.get("meta"), dict) else None,
            model=str(g.get("model"))[:128] if g.get("model") else None, is_public=bool(g.get("is_public", True)),
            created_at=_parse_dt(g.get("created_at")) or _now(),
        ))

    seen_versions = set()
    for r in data.get("releases") or []:
        if not isinstance(r, dict) or not r.get("version") or str(r["version"]) in seen_versions:
            continue
        snap = _remap_release_snapshot(r.get("snapshot"), rule_ids_by_ref)
        if snap is None:
            continue
        seen_versions.add(str(r["version"]))
        files = _count_tree(snap["tree"])["files"]
        db.session.add(BundleRelease(
            uuid=str(uuid_mod.uuid4()), bundle_id=bundle.id, user_id=user.id,
            version=str(r["version"])[:40], title=(str(r.get("title"))[:255] if r.get("title") else None),
            notes=r.get("notes") if isinstance(r.get("notes"), str) else None,
            rule_count=len(snap["rules"]), file_count=files,
            health_score=r.get("health_score") if isinstance(r.get("health_score"), int) else None,
            snapshot=snap, created_at=_parse_dt(r.get("created_at")) or _now(),
        ))
    db.session.commit()

    log_activity("bundle.import", f"Imported bundle '{bundle.name}' from JSON "
                 f"({len(report['created'])} rule(s) created, {len(report['reused'])} reused, "
                 f"{len(report['skipped'])} skipped)",
                 target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid,
                 is_public=bool(bundle.access))
    return bundle, report
