"""
bundle_health_fix_core.py — "Fix it for me" for the bundle Health tab.

attach_fixes(health, bundle_id)  adds a `fix` descriptor to every finding a
                                 one-click action can resolve:
    {"action": ..., "label": ..., "confirm": bool, ...params}
apply_fix(bundle_id, fix, user)  validates and applies one of them.

Actions (all scoped to the bundle — ids are re-checked on apply):
    remove_rule    take a rule out of the bundle (tree + association)
    dedupe_rule    keep only the first placement of a rule placed several times
    add_rule       add a library rule the bundle depends on (flowbit setter,
                   custom Wazuh parent, Sigma correlation target), next to the
                   rule that needs it
    place_rule     put an attached-but-unplaced rule into the structure
    remove_node    delete an empty folder / empty file
    set_marking    raise the bundle's TLP / PAP tag to the given level

Every change goes through track_bundle_change(), so it shows in History.
"""

from __future__ import annotations

import re
import uuid as uuid_mod

from sqlalchemy import func

from app import db
from app.core.db_class.db import (
    Bundle, BundleNode, BundleRuleAssociation, BundleTagAssociation, Rule, Tag,
)
from .bundle_history_core import track_bundle_change

TLP_FAMILY = ("tlp:",)
PAP_FAMILY = ("pap:",)


# ── Finding → fix ─────────────────────────────────────────────────────────

def _active_rules():
    return Rule.query.filter(Rule.is_deleted == False)


def _find_flowbit_setter(bit: str, fmt: str):
    esc = bit.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    q = _active_rules().filter(func.lower(Rule.format) == (fmt or "suricata"))
    for op in ("set", "setx"):
        r = q.filter(Rule.to_string.ilike(f"%flowbits:{op},{esc}%", escape="\\")).order_by(Rule.id.desc()).first() \
            or q.filter(Rule.to_string.ilike(f"%flowbits: {op},{esc}%", escape="\\")).order_by(Rule.id.desc()).first()
        if r:
            return r
    return None


def _find_wazuh_rule(rule_id: str):
    return (_active_rules().filter(func.lower(Rule.format) == "wazuh",
                                   Rule.to_string.ilike(f'%<rule id="{rule_id}"%'))
            .order_by(Rule.id.desc()).first())


def _find_sigma_rule(ref: str):
    q = _active_rules().filter(func.lower(Rule.format) == "sigma")
    return (q.filter(func.lower(Rule.title) == ref.lower()).first()
            or q.filter(Rule.to_string.ilike(f"%name: {ref}%")).first()
            or q.filter(Rule.to_string.ilike(f"%id: {ref}%")).first())


def _fix_for(check_key: str, item: dict):
    meta = item.get("meta") or {}
    rid = item.get("rule_id")

    if check_key in ("collisions", "syntax") and rid:
        return {"action": "remove_rule", "rule_id": rid, "label": "Remove from bundle", "confirm": True}

    if check_key == "dependencies" and rid:
        target = None
        if meta.get("flowbit"):
            target = _find_flowbit_setter(meta["flowbit"], meta.get("fmt"))
        elif meta.get("wazuh_parent"):
            target = _find_wazuh_rule(meta["wazuh_parent"])
        elif meta.get("sigma_ref"):
            target = _find_sigma_rule(meta["sigma_ref"])
        if target and target.id != rid:
            return {"action": "add_rule", "rule_id": target.id, "near_rule_id": rid,
                    "label": f"Add '{(target.title or '')[:60]}'", "confirm": False}
        return None

    if check_key == "marking" and meta.get("marking"):
        return {"action": "set_marking", "tag": meta["marking"],
                "label": f"Mark the bundle {meta['marking'].upper()}", "confirm": True}

    if check_key == "duplicates" and rid:
        if meta.get("placed_times"):
            return {"action": "dedupe_rule", "rule_id": rid, "label": "Keep one copy", "confirm": False}
        if meta.get("identical_to"):
            return {"action": "remove_rule", "rule_id": rid, "label": "Remove this copy", "confirm": True}

    if check_key == "structure":
        if meta.get("unplaced") and rid:
            return {"action": "place_rule", "rule_id": rid, "label": "Place in the structure", "confirm": False}
        if meta.get("node_id"):
            return {"action": "remove_node", "node_id": meta["node_id"],
                    "label": f"Delete empty {meta.get('empty', 'item')}", "confirm": False}
    return None


def attach_fixes(health: dict, bundle_id: int) -> None:
    """Add `fix` to fixable findings (live bundle only — never on a release)."""
    if not health:
        return
    for check in health["checks"]:
        for item in check["items"]:
            try:
                fx = _fix_for(check["key"], item)
            except Exception:
                fx = None
            if fx:
                item["fix"] = fx


# ── Apply ────────────────────────────────────────────────────────────────

def _bundle_rule_nodes(bundle_id, rule_id):
    return (BundleNode.query.filter_by(bundle_id=bundle_id, rule_id=rule_id)
            .order_by(BundleNode.id).all())


def _root_folder(bundle_id):
    root = (BundleNode.query.filter_by(bundle_id=bundle_id, parent_id=None, node_type="folder")
            .order_by(BundleNode.id).first())
    if root is None:
        root = BundleNode(bundle_id=bundle_id, parent_id=None, name="Main Bundle", node_type="folder")
        db.session.add(root)
        db.session.flush()
    return root


def _rule_node_name(rule):
    return (rule.title or f"rule {rule.id}")[:255]


def apply_fix(bundle_id: int, fix: dict, user) -> tuple[bool, str]:
    """Returns (ok, message). The caller checked the user may manage the bundle."""
    bundle = db.session.get(Bundle, bundle_id)
    if not bundle or not isinstance(fix, dict):
        return False, "Invalid fix"
    action = fix.get("action")

    def rule_in_bundle(rid):
        return (BundleRuleAssociation.query.filter_by(bundle_id=bundle_id, rule_id=rid).first() is not None
                or BundleNode.query.filter_by(bundle_id=bundle_id, rule_id=rid).first() is not None)

    try:
        rid = int(fix["rule_id"]) if fix.get("rule_id") is not None else None
    except (TypeError, ValueError):
        return False, "Invalid rule"

    if action == "remove_rule":
        if not rid or not rule_in_bundle(rid):
            return False, "This rule is not in the bundle"
        with track_bundle_change(bundle_id, "rules", user=user):
            for n in _bundle_rule_nodes(bundle_id, rid):
                db.session.delete(n)
            BundleRuleAssociation.query.filter_by(bundle_id=bundle_id, rule_id=rid).delete(synchronize_session=False)
            db.session.commit()
        return True, "Rule removed from the bundle"

    if action == "dedupe_rule":
        nodes = _bundle_rule_nodes(bundle_id, rid) if rid else []
        if len(nodes) < 2:
            return False, "Nothing to deduplicate"
        with track_bundle_change(bundle_id, "structure", user=user):
            for n in nodes[1:]:
                db.session.delete(n)
            db.session.commit()
        return True, f"Kept one copy, removed {len(nodes) - 1}"

    if action == "add_rule":
        rule = db.session.get(Rule, rid) if rid else None
        if not rule or rule.is_deleted:
            return False, "That rule is no longer available"
        if rule_in_bundle(rid):
            return True, "Already in the bundle"
        near = None
        if fix.get("near_rule_id"):
            try:
                near_nodes = _bundle_rule_nodes(bundle_id, int(fix["near_rule_id"]))
            except (TypeError, ValueError):
                near_nodes = []
            near = near_nodes[0] if near_nodes else None
        with track_bundle_change(bundle_id, "rules", user=user):
            parent_id = near.parent_id if near is not None else _root_folder(bundle_id).id
            db.session.add(BundleNode(bundle_id=bundle_id, parent_id=parent_id, name=_rule_node_name(rule),
                                      node_type="file", rule_id=rule.id))
            db.session.add(BundleRuleAssociation(bundle_id=bundle_id, rule_id=rule.id,
                                                 description="Added by the health check (missing dependency)"))
            db.session.commit()
        return True, f"Added '{rule.title}' next to the rule that needs it"

    if action == "place_rule":
        rule = db.session.get(Rule, rid) if rid else None
        if not rule or rule.is_deleted or not BundleRuleAssociation.query.filter_by(bundle_id=bundle_id, rule_id=rid).first():
            return False, "This rule is not attached to the bundle"
        if _bundle_rule_nodes(bundle_id, rid):
            return True, "Already placed"
        with track_bundle_change(bundle_id, "structure", user=user):
            db.session.add(BundleNode(bundle_id=bundle_id, parent_id=_root_folder(bundle_id).id,
                                      name=_rule_node_name(rule), node_type="file", rule_id=rule.id))
            db.session.commit()
        return True, "Rule placed in the structure"

    if action == "remove_node":
        try:
            node = db.session.get(BundleNode, int(fix.get("node_id")))
        except (TypeError, ValueError):
            node = None
        if not node or node.bundle_id != bundle_id or node.rule_id:
            return False, "Not an item of this bundle"
        if node.node_type == "folder" and BundleNode.query.filter_by(parent_id=node.id).first():
            return False, "This folder is no longer empty"
        if node.node_type == "file" and (node.custom_content or "").strip():
            return False, "This file is no longer empty"
        with track_bundle_change(bundle_id, "structure", user=user):
            db.session.delete(node)
            db.session.commit()
        return True, f"Deleted '{node.name}'"

    if action == "set_marking":
        name = str(fix.get("tag") or "").strip().lower()
        if not re.match(r"^(tlp|pap):[a-z+\-]+$", name):
            return False, "Invalid marking"
        tag = Tag.query.filter(func.lower(Tag.name) == name).first()
        if not tag:
            return False, f"The tag {name} doesn't exist on this instance"
        prefix = name.split(":")[0] + ":"
        with track_bundle_change(bundle_id, "tags", user=user):
            same_family = (db.session.query(BundleTagAssociation.id)
                           .join(Tag, Tag.id == BundleTagAssociation.tag_id)
                           .filter(BundleTagAssociation.bundle_id == bundle_id, func.lower(Tag.name).like(prefix + "%")))
            ids = [i for (i,) in same_family]
            if ids:
                BundleTagAssociation.query.filter(BundleTagAssociation.id.in_(ids)).delete(synchronize_session=False)
            db.session.add(BundleTagAssociation(uuid=str(uuid_mod.uuid4()), bundle_id=bundle_id, tag_id=tag.id,
                                                user_id=getattr(user, "id", None)))
            db.session.commit()
        return True, f"Bundle marked {name.upper()}"

    return False, "Unknown fix"
