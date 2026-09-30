"""
imported_tags_core.py — Rule authors' own tags ("imported tags").

Many rule formats carry free-form tags written by the rule's author (YARA
`rule X : apt ransomware`, Sigma `tags:`, Kunai `meta.tags`, CRS `tag:'…'`…).
Rulezet's own tag space is MISP taxonomies/galaxies (standardized) plus
Manual tags; the author's tags are kept apart as tags with
source = "Imported" — public, attached to the rule, and filterable in the
rule search — so it always stays clear which tags come from the platform
and which from the rule itself (GitHub issue #70).

Two entry points:
  - attach_imported_tags(rule, user_id) — on every new rule (add_rule_core)
  - the `import_native_tags` background job — re-parses existing rules,
    launched by an admin from /account/admin/bulk_parse_fields.
"""

from __future__ import annotations

import datetime
import re
import uuid as uuid_mod

from sqlalchemy import func

from app import db
from app.core.db_class.db import Rule, RuleTagAssociation, Tag

IMPORTED_SOURCE = "Imported"
IMPORTED_TAG_ICON = "fa-user-tag"
IMPORTED_TAG_COLOR = "#fd7e14"   # orange — Taxonomy blue, Galaxy purple, Manual green
MAX_TAG_LENGTH = 100
MAX_TAGS_PER_RULE = 25          # an author's tag list, not a way to mint tags in bulk
MISP_TAXONOMIES_DIR = "app/modules/misp-taxonomies"

# Where each format keeps its author tags — also shown on the admin page.
FORMAT_TAG_SOURCES: dict[str, str] = {
    "yara":     "Rule tags (rule Name : tag1 tag2) and meta tags / tag",
    "nova":     "meta tags / tag",
    "sigma":    "tags: list",
    "kunai":    "meta.tags list",
    "elastic":  "[rule] tags array",
    "splunk":   "tags.analytic_story (or top-level analytic_story)",
    "atr":      "tags.category and tags.subcategory",
    "crs":      "tag:'…' actions",
    "suricata": "metadata: tag <value> entries",
    "sagan":    "metadata: tag <value> entries",
    "nse":      "categories = {…}",
    "wazuh":    "<group> names",
    "kql":      "// tags: header comment",
}


# ── Normalization ────────────────────────────────────────────────────────────

_WS_RE = re.compile(r"\s+")
_COLON_RE = re.compile(r"\s*:\s*")
# Placeholder values some rule sets write where there is no tag (Sagan's
# "metadata: tag none"…) — never a real tag.
_PLACEHOLDERS = {"none", "null", "nil", "n/a", "na", "tbd", "todo", "-"}


def normalize_tag_name(value) -> str | None:
    """Lower-case, trimmed, single-spaced — so 'Ransomware' and 'ransomware'
    end up as one tag. None when the value isn't a usable tag."""
    if value is None or isinstance(value, (dict, list, bool)):
        return None
    name = _WS_RE.sub(" ", str(value)).strip().strip("\"'`,;").strip().lower()
    # "exploit: cve-2017-11882" / "exploit :cve-…" → "exploit:cve-2017-11882",
    # the namespace:value form of the rest of the tag space (tlp:clear…).
    name = _COLON_RE.sub(":", name)
    if not name or len(name) > MAX_TAG_LENGTH or not any(c.isalnum() for c in name):
        return None
    if name.startswith(":") or name.endswith(":"):
        return None
    if name in _PLACEHOLDERS:
        return None
    return name


def _dedup(values) -> list[str]:
    seen, out = set(), []
    for v in values:
        name = normalize_tag_name(v)
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _split(text: str) -> list[str]:
    """Split a free-form tag string: "apt malware", "a, b; c", "a|b".
    Commas / semicolons / pipes always separate; spaces separate too, except
    around a colon — "exploit: cve-2017-11882" is ONE namespaced tag, not
    "exploit:" + "cve-2017-11882"."""
    out = []
    for part in re.split(r"[,;|]+", text or ""):
        part = _COLON_RE.sub(":", part.strip())
        out += [t for t in part.split() if t]
    return out


def _as_str_list(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, (str, int, float)) and not isinstance(v, bool)]
    return []


# ── Per-format extractors ────────────────────────────────────────────────────

# Strings kept as-is, /* */ and // comments blanked — so a commented-out
# `rule X : a b` or `tags = "…"` is never picked up.
_C_TOKENS_RE = re.compile(r'"(?:\\.|[^"\\\n])*"|/\*.*?\*/|//[^\n]*', re.S)
_YARA_HEADER_RE = re.compile(
    r"(?:^|[\s}])(?:(?:private|global)\s+)*rule\s+[A-Za-z_]\w*\s*(?::\s*([A-Za-z_][\w \t\r\n]*?))?\s*\{")
_YARA_META_RE = re.compile(r"\bmeta\s*:(.*?)(?=\b(?:strings|condition|keywords|semantics|llm)\s*:|\Z)", re.S)
_META_TAG_RE = re.compile(r"\btags?\s*=\s*\"((?:\\.|[^\"\\])*)\"", re.I)


def _strip_c_comments(text: str) -> str:
    return _C_TOKENS_RE.sub(lambda m: m.group(0) if m.group(0).startswith('"') else " ", text)


def _extract_yara_like(content: str, native: bool = True) -> list[str]:
    text = _strip_c_comments(content)
    tags = []
    if native:
        for m in _YARA_HEADER_RE.finditer(text):
            if m.group(1):
                tags += m.group(1).split()
    for meta in _YARA_META_RE.finditer(text):
        for m in _META_TAG_RE.finditer(meta.group(1)):
            tags += _split(m.group(1))
    return tags


def _yaml_docs(content: str) -> list:
    import yaml
    try:
        return [d for d in yaml.safe_load_all(content) if isinstance(d, dict)]
    except Exception:
        return []


def _extract_sigma(content):
    return [t for d in _yaml_docs(content) for t in _as_str_list(d.get("tags"))]


def _extract_kunai(content):
    return [t for d in _yaml_docs(content) if isinstance(d.get("meta"), dict)
            for t in _as_str_list(d["meta"].get("tags"))]


def _extract_splunk(content):
    out = []
    for d in _yaml_docs(content):
        tags = d.get("tags")
        stories = tags.get("analytic_story") if isinstance(tags, dict) else None
        if stories is None:
            stories = d.get("analytic_story")
        out += _as_str_list(stories)
    return out


def _extract_atr(content):
    out = []
    for d in _yaml_docs(content):
        tags = d.get("tags")
        if isinstance(tags, dict):
            for key in ("category", "subcategory"):
                out += _as_str_list(tags.get(key))
    return out


def _extract_elastic(content):
    try:
        import tomllib
        doc = tomllib.loads(content)
        rule = doc.get("rule") if isinstance(doc.get("rule"), dict) else doc
        return _as_str_list(rule.get("tags"))
    except Exception:
        m = re.search(r"^\s*tags\s*=\s*\[(.*?)\]", content or "", re.S | re.M)
        return re.findall(r'"((?:\\.|[^"\\])*)"', m.group(1)) if m else []


def _extract_crs(content):
    return re.findall(r"\btag\s*:\s*'([^']*)'", content or "") + \
        re.findall(r'\btag\s*:\s*"([^"]*)"', content or "")


def _extract_snort_metadata(content):
    out = []
    for block in re.findall(r"\bmetadata\s*:\s*([^;]*);", content or ""):
        for entry in block.split(","):
            parts = entry.strip().split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "tag":
                out.append(parts[1])
    return out


def _extract_nse(content):
    out = []
    for block in re.findall(r"\bcategories\s*=\s*\{([^}]*)\}", content or ""):
        out += re.findall(r"[\"']([^\"']+)[\"']", block)
    return out


def _extract_wazuh(content):
    out = []
    for block in re.findall(r"<group>([^<]*)</group>", content or ""):
        out += [g for g in block.split(",") if g.strip()]
    return out


def _extract_kql(content):
    out = []
    for m in re.finditer(r"^\s*//\s*tags?\s*[:=]\s*(.+)$", content or "", re.M | re.I):
        out += [t for t in re.split(r"[,;|]", m.group(1)) if t.strip()]
    return out


_EXTRACTORS = {
    "yara":     lambda c: _extract_yara_like(c, native=True),
    "nova":     lambda c: _extract_yara_like(c, native=False),
    "sigma":    _extract_sigma,
    "kunai":    _extract_kunai,
    "elastic":  _extract_elastic,
    "splunk":   _extract_splunk,
    "atr":      _extract_atr,
    "crs":      _extract_crs,
    "suricata": _extract_snort_metadata,
    "sagan":    _extract_snort_metadata,
    "nse":      _extract_nse,
    "wazuh":    _extract_wazuh,
    "kql":      _extract_kql,
}


def extract_native_tags(rule_format: str | None, content: str | None) -> list[str]:
    """The author's tags written in the rule itself, normalized and
    deduplicated in order of appearance. [] for formats without tags."""
    extractor = _EXTRACTORS.get((rule_format or "").strip().lower())
    if not extractor or not content:
        return []
    try:
        return _dedup(extractor(content))
    except Exception:
        return []


# ── Tags in the database ─────────────────────────────────────────────────────

def _now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


_reserved_cache = {"names": None}


def reserved_namespaces() -> set:
    """Namespaces an imported tag may never be *created* in: every MISP
    taxonomy (installed or not — a squatted "tlp:red" would block the
    taxonomy's later import, tag names being unique) and the galaxies."""
    if _reserved_cache["names"] is None:
        import os
        names = {"misp-galaxy"}
        try:
            names |= {d.lower() for d in os.listdir(MISP_TAXONOMIES_DIR)
                      if os.path.isdir(os.path.join(MISP_TAXONOMIES_DIR, d))}
        except OSError:
            pass
        names |= {(ns or "").lower() for (ns,) in db.session.query(Tag.namespace)
                  .filter(Tag.source == "Taxonomy").distinct() if ns}
        _reserved_cache["names"] = names
    return _reserved_cache["names"]


def _is_admin(user_id) -> bool:
    from app.core.db_class.db import User
    user = db.session.get(User, user_id) if user_id else None
    return bool(user and user.is_admin())


def get_or_create_imported_tag(name: str, user_id: int | None, cache: dict | None = None):
    """The tag to attach for an imported name: an existing public, active tag
    with that name (any source — no duplicate 'malware' next to a Manual
    'malware'), else a new public Imported tag owned by `user_id`.
    None when the name belongs to a private/inactive tag (never attach that
    to a public rule) or when there's nobody to own a new tag."""
    if cache is not None and name in cache:
        return cache[name]
    tag = Tag.query.filter(func.lower(Tag.name) == name).first()
    if tag is not None:
        usable = bool(tag.is_active) and (tag.visibility or "").lower() == "public"
        result = tag if usable else None
    elif user_id and name.split(":", 1)[0] in reserved_namespaces() and ":" in name:
        result = None                     # never mint a tag in a taxonomy / galaxy namespace
    elif user_id:
        now = _now()
        tag = Tag(
            uuid=str(uuid_mod.uuid4()),
            name=name,
            description="Imported from the rule author's own tags.",
            created_at=now,
            updated_at=now,
            is_active=True,
            visibility="public",
            icon=IMPORTED_TAG_ICON,
            color=IMPORTED_TAG_COLOR,
            source=IMPORTED_SOURCE,
            created_by=user_id,
            is_approved_by_admin=_is_admin(user_id),
        )
        db.session.add(tag)
        db.session.flush()
        result = tag
    else:
        result = None
    if cache is not None:
        cache[name] = result
    return result


def attach_imported_tags(rule: Rule, user_id: int | None, cache: dict | None = None,
                         existing_tag_ids: set | None = None, prune: bool = False) -> dict:
    """Extract the rule's native tags and attach them. Idempotent: a tag the
    rule already has is skipped. No commit.

    prune=True (the re-parse job) also detaches the rule's Imported tags
    that its content no longer yields — a tag the author removed, or one
    produced by an older version of these parsers — so re-running the job
    repairs past imports. Only source="Imported" tags are ever detached,
    never a taxonomy/galaxy/Manual tag.
    Returns {'found': n, 'added': n, 'removed': n, 'skipped': [names refused]}."""
    names = extract_native_tags(rule.format, rule.to_string)[:MAX_TAGS_PER_RULE]
    stats = {"found": len(names), "added": 0, "removed": 0, "skipped": []}
    if prune:
        stale = (RuleTagAssociation.query.join(Tag, Tag.id == RuleTagAssociation.tag_id)
                 .filter(RuleTagAssociation.rule_id == rule.id, Tag.source == IMPORTED_SOURCE,
                         Tag.name.notin_(names or [""]))
                 .all())
        for assoc in stale:
            if existing_tag_ids is not None:
                existing_tag_ids.discard(assoc.tag_id)
            db.session.delete(assoc)
        stats["removed"] = len(stale)
    if not names:
        return stats
    if existing_tag_ids is None:
        existing_tag_ids = {tid for (tid,) in db.session.query(RuleTagAssociation.tag_id)
                            .filter(RuleTagAssociation.rule_id == rule.id)}
    for name in names:
        tag = get_or_create_imported_tag(name, user_id, cache)
        if tag is None:
            stats["skipped"].append(name)
            continue
        if tag.id in existing_tag_ids:
            continue
        db.session.add(RuleTagAssociation(
            uuid=str(uuid_mod.uuid4()), rule_id=rule.id, tag_id=tag.id,
            user_id=user_id, added_at=_now(),
        ))
        existing_tag_ids.add(tag.id)
        stats["added"] += 1
    return stats


def delete_orphan_imported_tags() -> int:
    """Delete Imported tags nothing uses any more (no rule, bundle, bundle
    note, workspace or blog post) — leftovers of a prune. No commit."""
    from app.core.db_class.db import (BundleTagAssociation, BundleNoteTag, WorkspaceTagAssociation,
                                      BlogPostTagAssociation)
    used = db.session.query(RuleTagAssociation.tag_id)
    for model in (BundleTagAssociation, BundleNoteTag, WorkspaceTagAssociation, BlogPostTagAssociation):
        used = used.union(db.session.query(model.tag_id))
    orphans = Tag.query.filter(Tag.source == IMPORTED_SOURCE, Tag.id.notin_(used)).all()
    for tag in orphans:
        db.session.delete(tag)
    return len(orphans)


def format_rule_counts() -> dict[str, int]:
    """{format: active rule count} for the formats that carry tags."""
    rows = (db.session.query(func.lower(Rule.format), func.count(Rule.id))
            .filter(Rule.is_deleted == False, func.lower(Rule.format).in_(list(FORMAT_TAG_SOURCES)))
            .group_by(func.lower(Rule.format)).all())
    return {fmt: count for fmt, count in rows}
