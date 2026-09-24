"""
bundle_health_core.py — "is this bundle safe to deploy?" checks
(bundle detail page → Health tab, GET /bundle/<id>/health).

Each check returns:
    {key, title, level: 'ok' | 'info' | 'warning' | 'error', message,
     items: [{rule_id?, name, detail}]}

The things a SOC otherwise only discovers when loading the bundle into its
sensors: ID collisions (Suricata/Sagan SIDs, YARA identifiers, Wazuh rule
ids, Sigma ids), dependencies pointing outside the bundle (flowbits,
Wazuh if_sid, Sigma correlations), rules that don't parse, TLP/PAP
inconsistencies, quality and hygiene issues.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from app import cache, db
from app.core.db_class.db import (
    Bundle, BundleNode, BundleRuleAssociation, BundleTagAssociation,
    Rule, RuleAttackAssociation, RuleTagAssociation, Tag,
)

MAX_ITEMS = 200                 # per check, returned to the UI
SYNTAX_CACHE_TTL = 7 * 24 * 3600
LOW_QUALITY = 40                # quality_score below this is flagged
WAZUH_CUSTOM_MIN = 100000       # Wazuh: ids below this are the built-in ruleset

LEVEL_PENALTY = {"error": 18, "warning": 7, "info": 0, "ok": 0}

# higher rank = more restricted sharing
TLP_RANK = {"tlp:clear": 0, "tlp:white": 0, "tlp:green": 1, "tlp:amber": 2, "tlp:amber+strict": 3, "tlp:red": 4}
PAP_RANK = {"pap:clear": 0, "pap:white": 0, "pap:green": 1, "pap:amber": 2, "pap:red": 3}


# ── Loading ───────────────────────────────────────────────────────────────

def _load(bundle_id: int):
    nodes = BundleNode.query.filter_by(bundle_id=bundle_id).all()
    assoc_ids = {rid for (rid,) in db.session.query(BundleRuleAssociation.rule_id)
                 .filter(BundleRuleAssociation.bundle_id == bundle_id)}
    node_rule_ids = [n.rule_id for n in nodes if n.rule_id]
    rule_ids = assoc_ids | set(node_rule_ids)
    rules = {r.id: r for r in Rule.query.filter(Rule.id.in_(rule_ids), Rule.is_deleted == False).all()} if rule_ids else {}

    tags_by_rule = defaultdict(set)
    if rules:
        for rid, name in (db.session.query(RuleTagAssociation.rule_id, Tag.name)
                          .join(Tag, Tag.id == RuleTagAssociation.tag_id)
                          .filter(RuleTagAssociation.rule_id.in_(rules.keys()))):
            tags_by_rule[rid].add((name or "").lower())
    attack_rules = {rid for (rid,) in db.session.query(RuleAttackAssociation.rule_id)
                    .filter(RuleAttackAssociation.rule_id.in_(rules.keys())).distinct()} if rules else set()
    bundle_tags = {(n or "").lower() for (n,) in db.session.query(Tag.name)
                   .join(BundleTagAssociation, BundleTagAssociation.tag_id == Tag.id)
                   .filter(BundleTagAssociation.bundle_id == bundle_id)}
    return nodes, assoc_ids, node_rule_ids, rules, tags_by_rule, attack_rules, bundle_tags


def _load_snapshot(release):
    """Same data as _load(), built from a frozen release: rules come from the
    snapshot (content at release time); live tags / ATT&CK / quality are
    looked up by rule id when the rule still exists."""
    from types import SimpleNamespace
    snap = release.snapshot or {}
    srules = snap.get("rules") or {}
    ids = [int(k) for k in srules]
    live = {r.id: r for r in Rule.query.filter(Rule.id.in_(ids)).all()} if ids else {}
    rules = {}
    for k, v in srules.items():
        rid = int(k)
        lr = live.get(rid)
        rules[rid] = SimpleNamespace(id=rid, title=v.get("title") or "", format=v.get("format") or "",
                                     to_string=v.get("content") or "", license=v.get("license") or "",
                                     quality_score=lr.quality_score if lr is not None else None)

    nodes, counter = [], [0]
    def walk(tree, parent):
        for n in tree or []:
            counter[0] += 1
            nid = counter[0]
            if n["type"] == "folder":
                nodes.append(SimpleNamespace(id=nid, parent_id=parent, node_type="folder", name=n["name"], custom_content=None, rule_id=None))
                walk(n.get("children"), nid)
            elif n["type"] == "file":
                nodes.append(SimpleNamespace(id=nid, parent_id=parent, node_type="file", name=n["name"], custom_content=n.get("content") or "", rule_id=None))
            else:
                nodes.append(SimpleNamespace(id=nid, parent_id=parent, node_type="file", name="", custom_content=None, rule_id=int(n["rule_id"])))
    walk(snap.get("tree"), None)

    node_rule_ids = [n.rule_id for n in nodes if n.rule_id]
    tags_by_rule = defaultdict(set)
    if ids:
        for rid, name in (db.session.query(RuleTagAssociation.rule_id, Tag.name)
                          .join(Tag, Tag.id == RuleTagAssociation.tag_id)
                          .filter(RuleTagAssociation.rule_id.in_(ids))):
            tags_by_rule[rid].add((name or "").lower())
    attack_rules = {rid for (rid,) in db.session.query(RuleAttackAssociation.rule_id)
                    .filter(RuleAttackAssociation.rule_id.in_(ids)).distinct()} if ids else set()
    bundle_tags = {(t or "").lower() for t in (snap.get("bundle") or {}).get("tags") or []}
    return nodes, set(ids), node_rule_ids, rules, tags_by_rule, attack_rules, bundle_tags


def _fmt(rule):
    return (rule.format or "").lower()


def _item(rule, detail="", name=None, **meta):
    """One finding. `meta` = structured facts (flowbit name, missing Wazuh
    parent id, tag…) used by bundle_health_fix_core to offer a one-click fix."""
    it = {"rule_id": rule.id if rule else None, "name": name or (rule.title if rule else ""), "detail": detail}
    if meta:
        it["meta"] = meta
    return it


# How to resolve each kind of finding — shown under the check's message
FIX = {
    "syntax": "Open the rule (Detail) and fix it, or propose an edit to its author — or remove it from the bundle.",
    "collisions": "Keep only one of the rules sharing an identifier (they are usually two versions of the same rule), or remove the older one from the bundle.",
    "dependencies": "Add the missing parent / setter rule to the bundle, or remove the rule that depends on it.",
    "marking": "Raise the bundle's TLP/PAP tag to the strictest rule's level, or remove the restricted rules.",
    "duplicates": "Open the structure editor and delete the extra copy (or one of the two identical rules).",
    "quality": "Low-scored rules usually lack a description, references or metadata — improve them or replace them.",
    "license": "Pick rules with an explicit license, or check the redistribution terms with their authors.",
    "attack": "Map the rules to ATT&CK techniques (rule edit page) so they appear in the coverage matrix.",
    "structure": "Place the rules in a folder of the structure editor, and delete empty folders / files.",
}


def _check(key, title, level, message, items=None):
    items = items or []
    return {"key": key, "title": title, "level": level,
            "message": message, "fix": FIX.get(key) if items else None,
            "count": len(items), "items": items[:MAX_ITEMS]}


# ── Identifier extraction ─────────────────────────────────────────────────

_RE_SID = re.compile(r"\bsid\s*:\s*(\d+)\s*;")
_RE_YARA_RULE = re.compile(r"^\s*(?:(?:private|global)\s+)*rule\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
_RE_WAZUH_ID = re.compile(r"<rule\s+[^>]*\bid\s*=\s*\"(\d+)\"", re.I)
_RE_SIGMA_ID = re.compile(r"^id:\s*['\"]?([0-9a-fA-F-]{8,})['\"]?\s*$", re.M)
_RE_SIGMA_NAME = re.compile(r"^name:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", re.M)

_RE_FLOWBITS = re.compile(r"flowbits\s*:\s*(set|setx|toggle|unset|isset|isnotset)\s*,\s*([^;]+);", re.I)
_RE_WAZUH_IF = re.compile(r"<(if_sid|if_matched_sid)>\s*([^<]+?)\s*</\1>", re.I)
_RE_YARA_INCLUDE = re.compile(r"^\s*include\s+\"([^\"]+)\"", re.M)


def _identifiers(rule):
    """(kind, identifier) pairs a deployment would load under one namespace."""
    f, text = _fmt(rule), rule.to_string or ""
    if f in ("suricata", "sagan", "snort"):
        return [("SID", s) for s in _RE_SID.findall(text)]
    if f == "yara":
        return [("YARA rule name", n) for n in _RE_YARA_RULE.findall(text)]
    if f == "wazuh":
        return [("Wazuh rule id", i) for i in _RE_WAZUH_ID.findall(text)]
    if f == "sigma":
        m = _RE_SIGMA_ID.findall(text)
        return [("Sigma id", i.lower()) for i in m[:1]]
    return []


# ── Checks ────────────────────────────────────────────────────────────────

def check_collisions(rules):
    seen = defaultdict(list)        # (kind, id) -> [rule]
    for r in rules.values():
        for kind, ident in set(_identifiers(r)):
            seen[(kind, ident)].append(r)
    items = []
    for (kind, ident), rs in sorted(seen.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if len(rs) > 1:
            for r in rs:
                others = ", ".join(f"'{x.title}'" for x in rs if x is not r)[:200]
                items.append(_item(r, f"Uses {kind} {ident}, which is also used by {others}. A sensor loads only one of them.",
                                   kind=kind, ident=ident))
    if not items:
        return _check("collisions", "Identifier collisions", "ok",
                      "No duplicate SIDs, YARA rule names, Wazuh ids or Sigma ids.")
    n = len({(i['detail'].split(' also')[0]) for i in items})
    return _check("collisions", "Identifier collisions", "error",
                  f"{n} identifier{'s are' if n > 1 else ' is'} used by several rules — sensors will reject or silently override them.",
                  items)


def check_dependencies(rules):
    """Dependencies that the bundle itself doesn't satisfy."""
    items = []

    # Suricata / Sagan flowbits: isset/isnotset need a rule that sets the bit
    set_bits, need_bits = set(), defaultdict(list)
    for r in rules.values():
        if _fmt(r) not in ("suricata", "sagan", "snort"):
            continue
        for op, names in _RE_FLOWBITS.findall(r.to_string or ""):
            bits = [b.strip() for b in re.split(r"[|&]", names.split(",")[0]) if b.strip()]
            if op.lower() in ("set", "setx", "toggle"):
                set_bits.update(bits)
            elif op.lower() in ("isset", "isnotset"):
                for b in bits:
                    need_bits[b].append(r)
    for bit, rs in need_bits.items():
        if bit not in set_bits:
            for r in rs:
                items.append(_item(r, f"Checks flowbit '{bit}' (flowbits:isset), but no rule of the bundle sets it — this rule can never fire.",
                                   flowbit=bit, fmt=_fmt(r)))

    # Wazuh if_sid / if_matched_sid → a rule id present in the bundle.
    # Ids below 100000 are Wazuh's own default ruleset, shipped with every
    # manager (custom rules live in 100000-120000) — not a missing dependency.
    wazuh_ids = {i for r in rules.values() if _fmt(r) == "wazuh" for i in _RE_WAZUH_ID.findall(r.to_string or "")}
    builtin_refs = set()
    for r in rules.values():
        if _fmt(r) != "wazuh":
            continue
        for tag, ids in _RE_WAZUH_IF.findall(r.to_string or ""):
            for i in re.split(r"[,\s]+", ids.strip()):
                if not (i and i.isdigit()) or i in wazuh_ids:
                    continue
                if int(i) < WAZUH_CUSTOM_MIN:
                    builtin_refs.add(i)
                    continue
                items.append(_item(r, f"Depends on custom Wazuh rule {i} (<{tag}>), which is not in the bundle — this rule can never fire.",
                                   wazuh_parent=i))

    # Sigma correlations → referenced rules by name or id
    sigma_refs = set()
    for r in rules.values():
        if _fmt(r) == "sigma":
            t = r.to_string or ""
            sigma_refs.update(x.lower() for x in _RE_SIGMA_ID.findall(t))
            sigma_refs.update(x.strip().lower() for x in _RE_SIGMA_NAME.findall(t))
    for r in rules.values():
        if _fmt(r) != "sigma" or "correlation:" not in (r.to_string or ""):
            continue
        block = (r.to_string or "").split("correlation:", 1)[1]
        m = re.search(r"^\s+rules:\s*\n((?:\s+-\s*.+\n?)+)", block, re.M)
        if m:
            for ref in re.findall(r"-\s*['\"]?([^'\"\n]+?)['\"]?\s*$", m.group(1), re.M):
                if ref.strip().lower() not in sigma_refs:
                    items.append(_item(r, f"This correlation needs the rule '{ref.strip()}', which is not in the bundle.",
                                       sigma_ref=ref.strip()))

    # YARA include "..." — files that won't exist next to the bundle
    for r in rules.values():
        if _fmt(r) == "yara":
            for inc in _RE_YARA_INCLUDE.findall(r.to_string or ""):
                items.append(_item(r, f'Includes the external file "{inc}", which is not shipped with the bundle — compilation will fail.'))

    builtin_note = (f" {len(builtin_refs)} Wazuh parent rule{'s' if len(builtin_refs) > 1 else ''} "
                    f"({', '.join(sorted(builtin_refs, key=int)[:8])}{'…' if len(builtin_refs) > 8 else ''}) "
                    "come from Wazuh's default ruleset (ids < 100000), shipped with every manager — not counted.") if builtin_refs else ""
    if not items:
        return _check("dependencies", "Missing dependencies", "ok",
                      "Every flowbit, custom Wazuh parent rule and Sigma correlation reference is satisfied inside the bundle." + builtin_note)
    return _check("dependencies", "Missing dependencies", "error",
                  f"{len(items)} reference{'s' if len(items) > 1 else ''} point{'' if len(items) > 1 else 's'} to rules that are not in the bundle — those rules will never fire (or fail to load)." + builtin_note,
                  items)


def _syntax_of(rule, refresh=False):
    """(ok, error) — cached per content, validation can be slow (YARA compile…).
    refresh=True re-validates (owner/admin "Re-run")."""
    from app.features.rule.rule_format.main_format import verify_syntax_rule_by_format
    content = rule.to_string or ""
    key = "bundle_health_syntax:" + hashlib.sha1(f"{_fmt(rule)}\0{content}".encode("utf-8", "replace")).hexdigest()
    try:
        hit = None if refresh else cache.get(key)
    except Exception:
        hit = None
    if hit is not None:
        return tuple(hit)
    try:
        ok, err = verify_syntax_rule_by_format({"format": rule.format or "", "to_string": content})
    except Exception as e:           # a validator crashing must not break the whole report
        ok, err = False, f"validator error: {e}"
    if not ok and "not supported" in (err or ""):
        ok, err = True, ""           # formats without a validator aren't "invalid"
    try:
        cache.set(key, [ok, err], timeout=SYNTAX_CACHE_TTL)
    except Exception:
        pass
    return ok, err


def check_syntax(rules, refresh=False):
    items = []
    for r in rules.values():
        ok, err = _syntax_of(r, refresh)
        if not ok:
            items.append(_item(r, (err or "invalid syntax")[:300], invalid=True))
    if not items:
        return _check("syntax", "Syntax", "ok", "Every rule passes its format's validator.")
    return _check("syntax", "Syntax", "error",
                  f"{len(items)} rule{'s' if len(items) > 1 else ''} fail{'' if len(items) > 1 else 's'} validation — they will not load.",
                  items)


def _strictest(tags, ranks):
    best = None
    for t in tags:
        if t in ranks and (best is None or ranks[t] > ranks[best]):
            best = t
    return best


def check_marking(rules, tags_by_rule, bundle_tags):
    """A bundle can't be shared more widely than its most restricted rule.

    A bundle without a TLP (or PAP) tag is treated as CLEAR — the platform's
    default marking — so only rules *more* restricted than clear (green,
    amber, red…) are flagged; tlp:clear / tlp:white rules never are."""
    items, messages = [], []
    for label, ranks in (("TLP", TLP_RANK), ("PAP", PAP_RANK)):
        b = _strictest(bundle_tags, ranks)
        b_rank = ranks[b] if b else 0
        flagged = 0
        for r in rules.values():
            rt = _strictest(tags_by_rule.get(r.id, ()), ranks)
            if rt and ranks[rt] > b_rank:
                flagged += 1
                where = f"marked {b.upper()}" if b else f"not marked with any {label} (treated as {label}:CLEAR)"
                items.append(_item(r, f"This rule is {rt.upper()} but the bundle is {where} — sharing the bundle would leak it.",
                                   marking=rt, family=label))
        if b is None and flagged:
            messages.append(f"the bundle has no {label} tag")
    if not items:
        return _check("marking", "TLP / PAP consistency", "ok",
                      "No rule is more restricted than the bundle's own TLP/PAP marking (no marking = CLEAR).")
    msg = (f"{len(items)} rule{'s are' if len(items) > 1 else ' is'} more restricted than the bundle — "
           "sharing the bundle at its marking would leak them. Raise the bundle's TLP/PAP or remove those rules.")
    if messages:
        msg += " (" + ", ".join(messages) + ")"
    return _check("marking", "TLP / PAP consistency", "error", msg, items)


def _folder_paths(nodes):
    by_id = {n.id: n for n in nodes}
    def path(n):
        parts, cur, guard = [], by_id.get(n.parent_id), 0
        while cur is not None and guard < 50:
            parts.append(cur.name or "?")
            cur = by_id.get(cur.parent_id)
            guard += 1
        return "/".join(reversed(parts)) or "(root)"
    return path


def check_duplicates(rules, node_rule_ids, nodes=()):
    items = []
    where = defaultdict(list)
    path = _folder_paths(nodes)
    for n in nodes:
        if n.rule_id:
            where[n.rule_id].append(path(n))
    counts = defaultdict(int)
    for rid in node_rule_ids:
        counts[rid] += 1
    for rid, n in counts.items():
        if n > 1 and rid in rules:
            locs = where.get(rid) or []
            detail = f"The same rule appears {n} times in the structure"
            if locs:
                detail += " — in " + ", ".join(f"'{l}'" for l in locs[:6])
            items.append(_item(rules[rid], detail + ". Keep one copy.", placed_times=n))
    by_content = defaultdict(list)
    for r in rules.values():
        body = re.sub(r"\s+", " ", (r.to_string or "")).strip()
        if body:
            by_content[hashlib.sha1(body.encode("utf-8", "replace")).hexdigest()].append(r)
    for rs in by_content.values():
        if len(rs) > 1:
            for r in rs:
                items.append(_item(r, "Identical content to another rule of the bundle: " + ", ".join(x.title for x in rs if x is not r)[:160],
                                   identical_to=[x.id for x in rs if x is not r]))
    if not items:
        return _check("duplicates", "Duplicates", "ok", "No rule is included twice, no two rules have the same content.")
    return _check("duplicates", "Duplicates", "warning",
                  f"{len(items)} rule{'s are' if len(items) > 1 else ' is'} included more than once, or identical to another rule of the bundle.", items)


def check_quality(rules):
    scored = [r for r in rules.values() if r.quality_score is not None]
    low = sorted((r for r in scored if r.quality_score < LOW_QUALITY), key=lambda r: r.quality_score)
    items = [_item(r, f"Quality score {round(r.quality_score)}/100 (below {LOW_QUALITY}).") for r in low]
    avg = round(sum(r.quality_score for r in scored) / len(scored)) if scored else None
    avg_txt = f"Average quality {avg}/100 over {len(scored)} scored rule{'s' if len(scored) != 1 else ''}." if avg is not None else "No rule has a quality score yet."
    if not items:
        return _check("quality", "Rule quality", "ok", avg_txt)
    return _check("quality", "Rule quality", "warning",
                  f"{avg_txt} {len(items)} rule{'s are' if len(items) > 1 else ' is'} below {LOW_QUALITY}.", items)


def check_metadata(rules, attack_rules):
    no_license = [r for r in rules.values() if not (r.license or "").strip()]
    no_attack = [r for r in rules.values() if r.id not in attack_rules]
    licenses = sorted({(r.license or "").strip() for r in rules.values() if (r.license or "").strip()})
    checks = []
    checks.append(
        _check("license", "Licenses", "warning",
               f"{len(no_license)} rule{'s have' if len(no_license) > 1 else ' has'} no license — redistribution terms are unclear.",
               [_item(r, "No license set — redistribution terms unknown.") for r in no_license])
        if no_license else
        _check("license", "Licenses", "ok" if len(licenses) <= 1 else "info",
               ("Licenses in this bundle: " + ", ".join(licenses)) if licenses else "No rules.")
    )
    checks.append(
        _check("attack", "ATT&CK mapping", "info",
               f"{len(no_attack)} rule{'s are' if len(no_attack) > 1 else ' is'} not mapped to any ATT&CK technique — they won't appear in the coverage matrix.",
               [_item(r, "Not mapped to any ATT&CK technique.") for r in no_attack])
        if no_attack else
        _check("attack", "ATT&CK mapping", "ok", "Every rule is mapped to at least one ATT&CK technique.")
    )
    return checks


def check_structure(nodes, assoc_ids, node_rule_ids, rules):
    items = []
    placed = set(node_rule_ids)
    for rid in sorted(assoc_ids - placed):
        if rid in rules:
            items.append(_item(rules[rid], "Attached to the bundle but not placed in any folder — it is missing from the structure download.",
                                   unplaced=True))
    children = defaultdict(int)
    for n in nodes:
        if n.parent_id:
            children[n.parent_id] += 1
    for n in nodes:
        if n.node_type == "folder" and not children.get(n.id):
            items.append({"rule_id": None, "name": n.name, "detail": "Empty folder.", "meta": {"node_id": n.id, "empty": "folder"}})
        elif n.node_type == "file" and not n.rule_id and not (n.custom_content or "").strip():
            items.append({"rule_id": None, "name": n.name, "detail": "Empty file.", "meta": {"node_id": n.id, "empty": "file"}})
    if not items:
        return _check("structure", "Structure", "ok", "Every rule is placed, no empty folder or file.")
    return _check("structure", "Structure", "info", f"{len(items)} housekeeping item{'s' if len(items) > 1 else ''}: rules not placed in a folder, empty folders or empty files.", items)


# ── Report ────────────────────────────────────────────────────────────────

def bundle_health(bundle_id: int, refresh: bool = False, release=None) -> dict | None:
    """Health of the live bundle, or of a frozen release (release=BundleRelease)."""
    bundle = db.session.get(Bundle, bundle_id)
    if not bundle:
        return None
    if release is not None:
        nodes, assoc_ids, node_rule_ids, rules, tags_by_rule, attack_rules, bundle_tags = _load_snapshot(release)
    else:
        nodes, assoc_ids, node_rule_ids, rules, tags_by_rule, attack_rules, bundle_tags = _load(bundle_id)

    checks = [
        check_syntax(rules, refresh),
        check_collisions(rules),
        check_dependencies(rules),
        check_marking(rules, tags_by_rule, bundle_tags),
        check_duplicates(rules, node_rule_ids, nodes),
        check_quality(rules),
        *check_metadata(rules, attack_rules),
        check_structure(nodes, assoc_ids, node_rule_ids, rules),
    ]
    penalty = sum(LEVEL_PENALTY.get(c["level"], 0) for c in checks)
    score = max(0, 100 - penalty) if rules else None
    counts = {lvl: sum(1 for c in checks if c["level"] == lvl) for lvl in ("error", "warning", "info", "ok")}
    if not rules:
        verdict = "empty"
    elif counts["error"]:
        verdict = "blocking"
    elif counts["warning"]:
        verdict = "review"
    else:
        verdict = "ready"
    import datetime
    return {
        "bundle_id": bundle_id,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "rules": len(rules),
        "score": score,
        "verdict": verdict,
        "counts": counts,
        "checks": checks,
    }
