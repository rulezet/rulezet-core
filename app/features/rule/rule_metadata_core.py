"""
rule_metadata_core.py — References and other metadata written in a rule's own text.

A rule often carries more than Rulezet's fields (title, description, author, licence, version):
references (YARA `reference = "…"`, Sigma `references:`, Suricata `reference:url,…;`), dates,
hashes of the samples it was written from, a status, a level, a TLP… This module reads them,
per format, into two JSON columns of the rule:

    rule_references   ["https://…", "CVE-2021-44228", …]           — in order, deduplicated
    extra_metadata    {"date": "2024-01-02", "hash": ["…", "…"], …} — a key -> a value or a list

Both are derived from the rule's text only: Rule's `to_string` / `format` set events keep them in
sync (every way a rule is created or changed goes through them), and the `reparse_rule_metadata`
job (Admin → Bulk parse fields → References & metadata) catches up existing rules. Which keys are
references and which are skipped: setting `rule.metadata_extraction`.
"""

from __future__ import annotations

import json
import re

from app.core.utils.app_settings import cached_setting

# Where each format keeps them — also shown on the admin page.
FORMAT_METADATA_SOURCES: dict[str, str] = {
    "yara":     "meta: section (reference = \"…\", hash = \"…\", date = \"…\"…)",
    "nova":     "meta: section",
    "sigma":    "references: list and the other top-level keys (date, status, level, falsepositives, logsource…)",
    "plum":     "references: list and the other top-level keys",
    "atr":      "references and the other top-level keys",
    "splunk":   "references: list and the other top-level keys",
    "kunai":    "meta: keys",
    "elastic":  "[rule] references, risk_score, severity, type and the [metadata] table",
    "suricata": "reference:type,value; options, metadata: entries, sid, rev, classtype, priority",
    "sagan":    "reference:type,value; options, metadata: entries, sid, rev, classtype, priority",
    "wazuh":    "<info type=\"link\"> (references), level",
    "kql":      "// key: value header comments",
    "crs":      "severity and ver actions",
}

MAX_EXTRACT_CHARS = 1_000_000     # runs on every change of a rule: bound the work
_GENERIC_HEADER_LINES = 60


def _conf() -> dict:
    """The extraction setting, never read from the database here: this runs inside SQLAlchemy
    attribute events (see app_settings.cached_setting)."""
    try:
        return cached_setting("rule.metadata_extraction") or {}
    except Exception:
        return {}


# ── Normalization ────────────────────────────────────────────────────────────

_WS_RE = re.compile(r"\s+")


def _key(raw) -> str:
    return _WS_RE.sub("_", str(raw or "").strip().lower()).strip("_-.")[:60]


def _text(value, limit) -> str | None:
    """One value as display text: single-spaced, quotes trimmed, bounded."""
    if value is None:
        return None
    text = _WS_RE.sub(" ", str(value)).strip().strip("\"'`").strip()
    return text[:limit] if text else None


def _flatten(value, limit) -> list[str]:
    """A value of any shape as a list of display strings: lists item by item, mappings as
    `key: value` (one level; deeper levels as compact JSON)."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        out = []
        for v in value:
            out += _flatten(v, limit)
        return out
    if isinstance(value, dict):
        out = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False, default=str)
            t = _text(v, limit)
            if t:
                out.append(f"{k}: {t}"[:limit])
        return out
    if isinstance(value, bool):
        return ["true" if value else "false"]
    t = _text(value, limit)
    return [t] if t else []


def _normalize_reference(text: str) -> str:
    """Suricata-style `type,value` references: url,example.com/x -> http://example.com/x,
    cve,2021-44228 -> CVE-2021-44228; anything else as written."""
    kind, sep, rest = text.partition(",")
    kind = kind.strip().lower()
    rest = rest.strip()
    if not sep or not rest or " " in kind:
        return text
    if kind == "url":
        return rest if re.match(r"^[a-z][a-z0-9+.-]*://", rest, re.I) else "http://" + rest
    if kind == "cve":
        return rest.upper() if rest.upper().startswith("CVE-") else "CVE-" + rest
    return f"{kind}: {rest}"


def _collect(pairs, conf) -> dict:
    """(key, value) pairs from a format's extractor -> {references, extra}, with the setting's
    reference / skip keys and limits."""
    limit = int(conf.get("max_value_length") or 300)
    ref_keys = {k.lower() for k in conf.get("reference_keys") or []}
    skip_keys = {k.lower() for k in conf.get("skip_keys") or []}
    max_refs = int(conf.get("max_references") or 50)
    max_fields = int(conf.get("max_fields") or 40)
    max_values = int(conf.get("max_values_per_field") or 20)

    references, extra = [], {}
    for raw_key, value in pairs:
        typed = raw_key == "__reference__"          # Suricata-style `type,value` reference
        key = _key(raw_key)
        if not key:
            continue
        if key in ref_keys or typed:
            for v in _flatten(value, limit):
                ref = _normalize_reference(v) if typed else v
                if ref not in references and len(references) < max_refs:
                    references.append(ref)
            continue
        if key in skip_keys:
            continue
        values = _flatten(value, limit)
        if not values:
            continue
        if key not in extra and len(extra) >= max_fields:
            continue
        bucket = extra.setdefault(key, [])
        for v in values:
            if v not in bucket and len(bucket) < max_values:
                bucket.append(v)
    extra = {k: (v[0] if len(v) == 1 else v) for k, v in extra.items() if v}
    return {"references": references, "extra": extra}


# ── Per-format extractors: each one returns [(key, value)] ───────────────────

_C_TOKENS_RE = re.compile(r'"(?:\\.|[^"\\\n])*"|/\*.*?\*/|//[^\n]*', re.S)
_YARA_META_RE = re.compile(r"\bmeta\s*:(.*?)(?=\b(?:strings|condition|keywords|semantics|llm)\s*:|\Z)", re.S)
_YARA_PAIR_RE = re.compile(r'\b([A-Za-z_]\w*)\s*=\s*("(?:\\.|[^"\\\n])*"|-?\d+(?:\.\d+)?|true|false)')


def _unescape(text: str) -> str:
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
        return re.sub(r'\\(["\\])', r"\1", text)
    return text


def _extract_yara(content):
    text = _C_TOKENS_RE.sub(lambda m: m.group(0) if m.group(0).startswith('"') else " ", content)
    pairs = []
    for meta in _YARA_META_RE.finditer(text):
        for m in _YARA_PAIR_RE.finditer(meta.group(1)):
            pairs.append((m.group(1), _unescape(m.group(2))))
    return pairs


def _yaml_docs(content):
    import yaml
    try:
        return [d for d in yaml.safe_load_all(content) if isinstance(d, dict)]
    except Exception:
        return []


def _extract_yaml_top(content):
    docs = _yaml_docs(content)
    return list(docs[0].items()) if docs else []


def _extract_kunai(content):
    docs = _yaml_docs(content)
    meta = docs[0].get("meta") if docs else None
    return list(meta.items()) if isinstance(meta, dict) else []


_ELASTIC_RULE_KEYS = ("references", "risk_score", "severity", "type", "language")


def _extract_elastic(content):
    try:
        import tomllib
        doc = tomllib.loads(content)
    except Exception:
        return []
    pairs = []
    if isinstance(doc.get("metadata"), dict):
        pairs += list(doc["metadata"].items())
    rule = doc.get("rule") if isinstance(doc.get("rule"), dict) else {}
    pairs += [(k, rule[k]) for k in _ELASTIC_RULE_KEYS if k in rule]
    return pairs


def _snort_options(content):
    """The `key:value;` options of Suricata / Snort / Sagan rules (quoted values kept whole)."""
    body = content[content.find("(") + 1:content.rfind(")")] if "(" in content else ""
    options, current, quoted, escaped = [], [], False, False
    for ch in body:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            current.append(ch)
            escaped = True
        elif ch == '"':
            current.append(ch)
            quoted = not quoted
        elif ch == ";" and not quoted:
            options.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    out = []
    for opt in options:
        key, sep, value = opt.partition(":")
        if sep:
            out.append((key.strip().lower(), value.strip()))
    return out


def _extract_snort(content):
    pairs = []
    for key, value in _snort_options(content):
        if key == "reference":
            pairs.append(("__reference__", value))
        elif key == "metadata":
            for entry in value.split(","):
                k, _, v = entry.strip().partition(" ")
                if k and v.strip() and k.lower() != "tag":
                    pairs.append((k, v.strip()))
        elif key in ("sid", "rev", "gid", "classtype", "priority"):
            pairs.append((key, value))
    return pairs


def _extract_wazuh(content):
    pairs = [("reference", m) for m in re.findall(r'<info\s+type\s*=\s*"link"\s*>\s*([^<]+?)\s*</info>', content, re.I)]
    level = re.search(r'<rule\b[^>]*\blevel\s*=\s*"(\d+)"', content)
    if level:
        pairs.append(("level", level.group(1)))
    return pairs


_COMMENT_PAIR_RE = re.compile(r"^\s*(?:#|//|--|;)+\s*([A-Za-z][\w .-]{0,30}?)\s*[:=]\s*(.+?)\s*$")


def _extract_comment_header(content, known_only):
    """`// key: value` / `# key: value` lines at the top of a rule. With known_only, only keys
    that are references or listed for display (dates, hashes, status…): free comments elsewhere
    are not metadata."""
    known, prefixes = None, ()
    if known_only:
        conf = _conf()
        display = {}
        try:
            display = cached_setting("rule.metadata_display") or {}
        except Exception:
            pass
        known = {k.lower() for k in conf.get("reference_keys") or []} | set((display.get("fields") or {}).keys())
        prefixes = tuple(display.get("hash_prefixes") or ())
    pairs = []
    for line in content.splitlines()[:_GENERIC_HEADER_LINES]:
        m = _COMMENT_PAIR_RE.match(line)
        if not m:
            continue
        key = _key(m.group(1))
        if known is not None and key not in known and not (prefixes and key.startswith(prefixes)):
            continue
        pairs.append((key, m.group(2)))
    return pairs


def _extract_crs(content):
    pairs = []
    for key in ("severity", "ver"):
        for m in re.finditer(rf"\b{key}\s*:\s*'([^']*)'", content):
            pairs.append((key, m.group(1)))
    return pairs


_EXTRACTORS = {
    "yara":     _extract_yara,
    "nova":     _extract_yara,
    "sigma":    _extract_yaml_top,
    "plum":     _extract_yaml_top,
    "atr":      _extract_yaml_top,
    "splunk":   _extract_yaml_top,
    "kunai":    _extract_kunai,
    "elastic":  _extract_elastic,
    "suricata": _extract_snort,
    "sagan":    _extract_snort,
    "wazuh":    _extract_wazuh,
    "kql":      lambda c: _extract_comment_header(c, known_only=False),
    "crs":      _extract_crs,
}


def extract_rule_metadata(rule_format: str | None, content: str | None) -> dict:
    """{references: [...], extra: {...}} read from the rule's text. Formats without their own
    extractor: only well-known keys of `# key: value` header comments. Never raises."""
    empty = {"references": [], "extra": {}}
    if not content:
        return empty
    content = content[:MAX_EXTRACT_CHARS]
    fmt = (rule_format or "").strip().lower()
    extractor = _EXTRACTORS.get(fmt) or (lambda c: _extract_comment_header(c, known_only=True))
    try:
        return _collect(extractor(content), _conf())
    except Exception:
        return empty


def apply_rule_metadata(rule) -> None:
    """Sets the rule's rule_references / extra_metadata from its format and text (None when
    there is nothing, so untouched rules stay NULL)."""
    found = extract_rule_metadata(rule.format, rule.to_string)
    rule.rule_references = found["references"] or None
    rule.extra_metadata = found["extra"] or None


def clean_references(value) -> list[str]:
    """References typed in a form (one per line) or sent as a list: trimmed, deduplicated,
    bounded like the ones read from the text."""
    conf = _conf()
    limit = int(conf.get("max_value_length") or 300)
    items = value.splitlines() if isinstance(value, str) else (value if isinstance(value, list) else [])
    out = []
    for item in items:
        text = _text(item, limit) if isinstance(item, (str, int, float)) else None
        if text and text not in out and len(out) < int(conf.get("max_references") or 50):
            out.append(text)
    return out


def set_manual_references(rule, value) -> None:
    """The references added by hand (create / edit form): those the rule's text already gives
    are not kept twice. None when there are none left."""
    from_text = set(rule.rule_references or [])
    rule.manual_references = [r for r in clean_references(value) if r not in from_text] or None


def display_metadata(extra: dict | None) -> list[dict]:
    """The rule page's "Other metadata": one entry per key, with its label, icon, values and
    whether they are hashes (setting `rule.metadata_display`)."""
    if not extra:
        return []
    try:
        conf = cached_setting("rule.metadata_display") or {}
    except Exception:
        conf = {}
    fields = conf.get("fields") or {}
    prefixes = tuple(conf.get("hash_prefixes") or ())
    out = []
    for key, value in extra.items():
        known = fields.get(key) or {}
        values = value if isinstance(value, list) else [value]
        out.append({
            "key": key,
            "label": known.get("label") or key.replace("_", " ").capitalize(),
            "icon": known.get("icon") or "fa-tag",
            "values": [str(v) for v in values],
            "is_hash": bool(prefixes) and key.startswith(prefixes),
        })
    return out


def format_rule_counts() -> dict[str, int]:
    """Active rules per (lower-case) format, for the admin page."""
    from sqlalchemy import func
    from app import db
    from app.core.db_class.rule import Rule
    rows = (db.session.query(func.lower(Rule.format), func.count(Rule.id))
            .filter(Rule.is_deleted == False).group_by(func.lower(Rule.format)).all())  # noqa: E712
    return {fmt: n for fmt, n in rows if fmt}
