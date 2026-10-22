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

A bundle already imported (its source uuid is kept in remote_bundle_uuid)
or the same bundle on its own instance can be updated in place instead of
copied: fields, tags, rules, tree replaced; notes, AI analyses and releases
not there yet added. Rules found by uuid whose content/fields changed are
updated (with a history entry).

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
                                             create_rule_from_portable, find_existing_rule,
                                             rule_changes, update_rule_from_portable)

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
    (create | update | existing | invalid | trash)."""
    out = []
    for i, raw in enumerate(data.get("rules") or []):
        ref = str((raw or {}).get("uuid") or f"#{i}") if isinstance(raw, dict) else f"#{i}"
        rule_dict, error = normalize_rule_json(raw)
        if error:
            out.append({"ref": ref, "rule_dict": None, "action": "invalid", "changes": [],
                        "title": (raw or {}).get("title") if isinstance(raw, dict) else None, "error": error,
                        "bundle_description": None, "preview": None})
            continue
        preview = preview_rule(rule_dict)
        existing = preview["existing"]
        changes = []
        if existing and existing["kind"] == "uuid" and preview["valid"]:
            changes = rule_changes(rule_dict, db.session.get(Rule, existing["id"]))
        if existing and existing["kind"] == "trash":
            action = "trash"
        elif changes:
            action = "update"
        elif existing:
            action = "existing"
        elif preview["valid"]:
            action = "create"
        else:
            action = "invalid"
        out.append({"ref": ref, "rule_dict": rule_dict, "action": action, "title": rule_dict["title"],
                    "error": preview["error"], "preview": preview, "changes": changes,
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


def find_existing_bundle(data: dict):
    """The bundle this export was already imported as (remote_bundle_uuid),
    or the exported bundle itself when it comes from this instance."""
    from sqlalchemy import or_
    src = str(data["bundle"].get("uuid") or "").strip()
    if not src:
        return None
    return Bundle.query.filter(or_(Bundle.uuid == src, Bundle.remote_bundle_uuid == src)) \
        .order_by(Bundle.id).first()


def preview_bundle_import(data: dict, user) -> dict:
    from .bundle_core import bundle_name_taken

    b = data["bundle"]
    name = str(b.get("name")).strip()[:255]
    rules = _analyse_rules(data)
    tag_names = [t for t in (b.get("tags") or []) if isinstance(t, str)]
    known = _known_tag_names(tag_names)
    counts = {a: sum(1 for r in rules if r["action"] == a)
              for a in ("create", "update", "existing", "invalid", "trash")}
    existing = find_existing_bundle(data)
    existing_json = None
    if existing:
        owner = existing.user
        existing_json = {
            "id": existing.id, "name": existing.name,
            "owner": f"{owner.first_name} {owner.last_name}".strip() if owner else None,
            "rules": existing.rules_assoc.count(),
            "notes": existing.notes.count(),
            "releases": [r.version for r in existing.releases],
            "can_update": user.is_admin() or existing.user_id == user.id,
            "name_taken": existing.name != name and bundle_name_taken(name, existing.user_id, exclude_id=existing.id),
        }
    return {
        "existing_bundle": existing_json,
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
            "preview": r["preview"], "changes": r["changes"],
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


def _import_rules(data, user, report):
    """Create / update / reuse every exported rule → {ref: rule id}, {rule id: description}."""
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
        elif r["action"] in ("update", "existing"):
            rid = r["preview"]["existing"]["id"]
            rule_ids_by_ref[r["ref"]] = rid
            if r["action"] == "update":
                ok, why = update_rule_from_portable(r["rule_dict"], db.session.get(Rule, rid), user)
                (report["updated"] if ok else report["skipped"]).append(
                    {"id": rid, "title": r["title"], **({} if ok else {"reason": f"not updated: {why}"})})
                if not ok:      # still part of the bundle, just not updated
                    report["reused"].append({"id": rid, "title": r["title"]})
            else:
                report["reused"].append({"id": rid, "title": r["preview"]["existing"]["title"]})
        else:
            reason = "in the trash on this instance" if r["action"] == "trash" else (r["error"] or "invalid")
            report["skipped"].append({"title": r["title"], "reason": reason})
        if r["ref"] in rule_ids_by_ref:
            descriptions[rule_ids_by_ref[r["ref"]]] = r["bundle_description"]
    return rule_ids_by_ref, descriptions


def _release_before_update(bundle, user) -> str | None:
    """Freeze the bundle as it is before an import updates it — a release
    to go back to. None when there's nothing new since the last release
    (or nothing at all); the version created otherwise."""
    from .bundle_release_core import draft_release, create_release
    draft = draft_release(bundle.id)
    diff = draft["diff"]
    if diff is not None and not diff["total"]:
        return None
    version = draft["suggested_version"]
    if BundleRelease.query.filter_by(bundle_id=bundle.id, version=version).first():
        version = f"{version}-pre-import"
    release, error = create_release(bundle.id, user, version, "Before JSON import update",
                                    draft["notes"] + "\n\nAutomatic release made just before a JSON import updated the bundle.")
    return release.version if release else None


def import_bundle(data: dict, user, name: str | None = None, mode: str = "create",
                  release_before: bool = True) -> tuple[Bundle | None, dict]:
    """Create the bundle (mode "create") or update the one it was already
    imported as (mode "update"), creating / updating its rules — after a
    release of its current state (release_before). Returns (bundle, report)."""
    from .bundle_core import bundle_name_taken, create_bundle
    from .bundle_history_core import track_bundle_change
    from app.core.utils.activity_log import log_activity

    b = data["bundle"]
    name = (name or str(b.get("name"))).strip()[:255]
    if not name:
        return None, {"error": "The bundle needs a name."}
    report = {"created": [], "updated": [], "reused": [], "skipped": []}
    vulns = [v for v in (b.get("vulnerabilities") or []) if isinstance(v, str)]
    description = b.get("description") if isinstance(b.get("description"), str) else ""

    if mode == "update":
        bundle = find_existing_bundle(data)
        if bundle is None:
            return None, {"error": "No existing bundle to update — import it as a new bundle."}
        if not (user.is_admin() or bundle.user_id == user.id):
            return None, {"error": "You can't update this bundle."}
        if name != bundle.name and bundle_name_taken(name, bundle.user_id, exclude_id=bundle.id):
            return None, {"error": f'The owner already has a bundle called "{name}" — pick another name.'}
        if release_before:
            report["release_before"] = _release_before_update(bundle, user)
        with track_bundle_change(bundle.id, "import", user=user):
            rule_ids_by_ref, descriptions = _import_rules(data, user, report)
            bundle.name, bundle.description = name, description
            bundle.access = bool(b.get("access", True))
            bundle.vulnerability_identifiers = json.dumps(vulns)
            bundle.updated_at = _now()
            BundleTagAssociation.query.filter_by(bundle_id=bundle.id).delete()
            wanted = set(dict.fromkeys(rule_ids_by_ref.values()))
            for a in BundleRuleAssociation.query.filter_by(bundle_id=bundle.id).all():
                if a.rule_id not in wanted:
                    db.session.delete(a)
                else:
                    wanted.discard(a.rule_id)
                    if descriptions.get(a.rule_id):
                        a.description = descriptions[a.rule_id]
            db.session.flush()
            _fill_bundle(bundle, data, user, rule_ids_by_ref, descriptions, report, new_rule_ids=wanted)
        action = "updated"
    else:
        if bundle_name_taken(name, user.id):
            return None, {"error": f'You already have a bundle called "{name}" — pick another name.'}
        rule_ids_by_ref, descriptions = _import_rules(data, user, report)
        bundle = create_bundle({"name": name, "description": description,
                                "public": bool(b.get("access", True)),
                                "vulnerability_identifiers": vulns}, user)
        src = str(b.get("uuid") or "").strip()
        if src and src != bundle.uuid:
            bundle.remote_bundle_uuid = src[:36]
        _fill_bundle(bundle, data, user, rule_ids_by_ref, descriptions, report,
                     new_rule_ids=set(rule_ids_by_ref.values()))
        action = "imported"

    log_activity(f"bundle.import", f"{action.capitalize()} bundle '{bundle.name}' from JSON "
                 f"({len(report['created'])} rule(s) created, {len(report['updated'])} updated, "
                 f"{len(report['reused'])} reused, {len(report['skipped'])} skipped)",
                 target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid,
                 is_public=bool(bundle.access))
    report["mode"] = mode
    return bundle, report


def _fill_bundle(bundle, data, user, rule_ids_by_ref, descriptions, report, new_rule_ids):
    """Tags, rule links, tree, notes, AI analyses, releases — on a new bundle,
    or on an existing one (its tags and stale rule links already removed;
    notes / analyses / releases it already has are not duplicated)."""
    from .bundle_core import validate_structure, save_workspace, place_rules_in_structure

    b = data["bundle"]
    for tag in _known_tag_names(b.get("tags") or []).values():
        db.session.add(BundleTagAssociation(uuid=str(uuid_mod.uuid4()), bundle_id=bundle.id,
                                            tag_id=tag.id, user_id=user.id, added_at=_now()))

    for rid in [r for r in dict.fromkeys(rule_ids_by_ref.values()) if r in new_rule_ids]:
        db.session.add(BundleRuleAssociation(
            bundle_id=bundle.id, rule_id=rid, added_at=_now(),
            description=descriptions.get(rid) or f"Imported from JSON on {_now():%Y-%m-%d}"))
    db.session.commit()

    structure = _structure_for_editor(data.get("structure"), rule_ids_by_ref)
    error = validate_structure(structure)
    if error:
        report["structure_error"] = error
    elif structure or BundleNode.query.filter_by(bundle_id=bundle.id).first():
        save_workspace(bundle.id, structure)
    placed = {n.rule_id for n in BundleNode.query.filter_by(bundle_id=bundle.id) if n.rule_id}
    missing = [rid for rid in dict.fromkeys(rule_ids_by_ref.values()) if rid not in placed]
    if missing:
        place_rules_in_structure(bundle.id, missing)
        db.session.commit()

    have_notes = {(n.title, n.content) for n in bundle.notes}
    for n in data.get("notes") or []:
        if not isinstance(n, dict) or not str(n.get("title") or "").strip() or not isinstance(n.get("content"), str):
            continue
        if (str(n["title"]).strip()[:200], n["content"]) in have_notes:
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

    have_ai = {(g.agent_key, g.content) for g in bundle.ai_generations}
    for g in data.get("ai_analyses") or []:
        if not isinstance(g, dict) or not isinstance(g.get("content"), str) or not g.get("agent_key"):
            continue
        if (str(g["agent_key"])[:50], g["content"]) in have_ai:
            continue
        db.session.add(AIGeneration(
            uuid=str(uuid_mod.uuid4()), agent_key=str(g["agent_key"])[:50], bundle_id=bundle.id,
            user_id=user.id, content=g["content"], meta=g.get("meta") if isinstance(g.get("meta"), dict) else None,
            model=str(g.get("model"))[:128] if g.get("model") else None, is_public=bool(g.get("is_public", True)),
            created_at=_parse_dt(g.get("created_at")) or _now(),
        ))

    seen_versions = {r.version for r in bundle.releases}
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
