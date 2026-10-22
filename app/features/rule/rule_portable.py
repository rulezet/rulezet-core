"""Portable JSON of a rule — what the "JSON" download writes and what the
"From JSON" tab of the create page (and the bundle JSON import) reads back.

One shape both ways: the flat `Rule.to_json()` fields plus `tags` (names —
ids differ between instances) and `attacks` (ATT&CK technique ids). The
importer also accepts the nested `to_json_detail()` shape (the detail page's
"Json" tab) and the older flat exports without tags/attacks.

Only the rule's own fields are read: id, user_id, votes, status… are ignored,
the new rule always belongs to the user importing it.
"""
import json

from app.core.db_class.rule import Rule
from app.core.db_class.tag import Tag

# The fields read from a pasted rule, in the order the preview shows them.
IMPORT_FIELDS = (
    ("title", "Title"),
    ("format", "Format"),
    ("version", "Version"),
    ("license", "License"),
    ("author", "Author"),
    ("source", "Source"),
    ("description", "Description"),
    ("original_uuid", "Original UUID"),
    ("cve_id", "Vulnerabilities"),
    ("to_string", "Content"),
)


def rule_to_portable(rule: Rule) -> dict:
    """Flat to_json() + tag names + ATT&CK technique ids."""
    data = rule.to_json()
    data["tags"] = sorted({a.tag.name for a in rule.rule_tags_assocs if a.tag})
    data["attacks"] = sorted({a.technique_id for a in rule.attack_assocs})
    return data


def _clean_str(value) -> str:
    return str(value).strip() if isinstance(value, (str, int, float)) and not isinstance(value, bool) else ""


def _vuln_list(value) -> list:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            value = [v for v in value.replace(";", ",").replace(" ", ",").split(",")]
    if not isinstance(value, list):
        return []
    out = []
    for v in value:
        v = _clean_str(v)
        if v and v not in out:
            out.append(v)
    return out


def _name_list(value, *keys) -> list:
    """Names out of a list of strings or of objects (first of `keys` set)."""
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        name = _clean_str(item) if not isinstance(item, dict) else next(
            (_clean_str(item.get(k)) for k in keys if _clean_str(item.get(k))), "")
        if name and name not in out:
            out.append(name)
    return out


def flatten_rule_json(parsed: dict) -> dict:
    """The nested to_json_detail() shape → the flat shape; flat input is
    returned as is."""
    if not isinstance(parsed.get("identity"), dict) and not isinstance(parsed.get("content"), dict):
        return parsed
    identity = parsed.get("identity") or {}
    content = parsed.get("content") or {}
    authorship = parsed.get("authorship") or {}
    relations = parsed.get("relations") or {}
    vulnerability = parsed.get("vulnerability") or {}
    flat = {
        "uuid": identity.get("uuid"),
        "original_uuid": identity.get("original_uuid"),
        "title": identity.get("title"),
        "version": identity.get("version"),
        "format": identity.get("format"),
        "to_string": content.get("to_string"),
        "description": content.get("description"),
        "source": content.get("source"),
        "author": authorship.get("author"),
        "license": authorship.get("license"),
        "tags": relations.get("tags") or [],
        "attacks": relations.get("attacks") or parsed.get("attacks") or [],
        "cve_id": vulnerability.get("cve_ids") or [],
    }
    return flat


def normalize_rule_json(parsed) -> tuple[dict | None, str | None]:
    """A pasted rule (flat or nested) → (rule_dict, None) or (None, error).

    rule_dict has the add_rule_core() keys plus `tag_names` and `attacks`."""
    if not isinstance(parsed, dict):
        return None, "The JSON must be a single rule object."
    flat = flatten_rule_json(parsed)
    rule_dict = {
        "format": _clean_str(flat.get("format")).lower(),
        "title": _clean_str(flat.get("title")),
        "to_string": str(flat.get("to_string") or ""),
        "license": _clean_str(flat.get("license")),
        "description": _clean_str(flat.get("description")),
        "source": _clean_str(flat.get("source")),
        "author": _clean_str(flat.get("author")),
        "version": _clean_str(flat.get("version")),
        # The source instance's own uuid identifies the rule here — an
        # already imported copy is then found as a duplicate.
        "original_uuid": _clean_str(flat.get("uuid") or flat.get("original_uuid")),
        "cve_id": _vuln_list(flat.get("cve_id") or flat.get("vulnerabilities")),
        "tag_names": _name_list(flat.get("tags"), "name", "tag_name"),
        "attacks": [a.upper() for a in _name_list(flat.get("attacks"), "technique_id", "id")],
    }
    if not rule_dict["title"] or not rule_dict["format"] or not rule_dict["to_string"].strip():
        return None, 'The JSON must include at least "title", "format" and "to_string".'
    return rule_dict, None


def find_existing_rule(rule_dict: dict):
    """The rule add_rule_core() would refuse this one for, without creating
    anything: ("uuid" | "content" | "trash", rule) or (None, None)."""
    from sqlalchemy import or_
    from app.features.rule.rule_core import (
        _active, get_rule_by_content, _find_in_trash_by_content,
        EMPTY_UUID_VALUES, _LOCALLY_SCOPED_ORIGINAL_UUID_FORMATS,
    )
    ouuid = (rule_dict.get("original_uuid") or "").strip()
    if (ouuid and ouuid.lower() not in EMPTY_UUID_VALUES
            and (rule_dict.get("format") or "").lower() not in _LOCALLY_SCOPED_ORIGINAL_UUID_FORMATS):
        existing = _active().filter(or_(Rule.uuid == ouuid, Rule.original_uuid == ouuid)).first()
        if existing is not None:
            return "uuid", existing
    content = (rule_dict.get("to_string") or "").strip()
    existing = get_rule_by_content(content)
    if existing is not None:
        return "content", existing
    trashed = _find_in_trash_by_content(content)
    if trashed is not None:
        return "trash", trashed
    return None, None


def _known_tags(names) -> dict:
    if not names:
        return {}
    return {t.name.lower(): t for t in Tag.query.filter(Tag.name.in_(names)).all()}


def _known_attacks(ids) -> set:
    if not ids:
        return set()
    from app.core.db_class.attack import AttackTechnique
    return {t.technique_id for t in AttackTechnique.query.filter(AttackTechnique.technique_id.in_(ids)).all()}


def preview_rule(rule_dict: dict) -> dict:
    """Everything the import would do with this rule, nothing written:
    the fields, syntax check, duplicate, tags / techniques found or not."""
    from app.features.rule.rule_format.main_format import verify_syntax_rule_by_format

    try:
        valid, error = verify_syntax_rule_by_format(dict(rule_dict))
    except Exception as e:  # a parser crash is a refused rule, not a 500
        valid, error = False, f"Validation failed: {e}"
    kind, existing = find_existing_rule(rule_dict)
    tags = _known_tags(rule_dict["tag_names"])
    attacks = _known_attacks(rule_dict["attacks"])
    return {
        "fields": [{"key": k, "label": label, "value": rule_dict.get(k)} for k, label in IMPORT_FIELDS],
        "valid": bool(valid),
        "error": None if valid else (error or "Invalid rule."),
        "existing": None if not existing else {
            "kind": kind, "id": existing.id, "uuid": existing.uuid, "title": existing.title,
        },
        "tags": [{"name": n, "found": n.lower() in tags} for n in rule_dict["tag_names"]],
        "attacks": [{"id": a, "found": a in attacks} for a in rule_dict["attacks"]],
    }


def create_rule_from_portable(rule_dict: dict, user, record_activity: bool = True):
    """Create the rule (syntax already checked by the caller) with its tags
    and techniques — same result as add_rule_core(): (rule, msg) / (False, msg)."""
    from app.features.rule import rule_core as RuleModel
    from app.features.rule.rule_format.utils_format.utils_import_update import fill_all_void_field

    data = dict(rule_dict)
    tags = _known_tags(data.pop("tag_names", []))
    attacks = data.pop("attacks", [])
    data["tags"] = [{"id": t.id} for t in tags.values()]
    data = fill_all_void_field(data)
    new_rule, message = RuleModel.add_rule_core(data, user, record_activity=record_activity)
    if new_rule:
        from app.features.attack.attack_core import add_technique_to_rule
        for tid in _known_attacks(attacks):
            try:
                add_technique_to_rule(new_rule.id, tid, user.id, source="manual")
            except Exception:
                pass
    return new_rule, message
