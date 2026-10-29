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
    "elastic":  "[rule] references, risk_score, severity, type, note (investigation guide, Markdown, kept whole), setup and the [metadata] table",
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
    long_keys = {k.lower() for k in conf.get("long_text_keys") or []}
    long_limit = int(conf.get("long_text_max_length") or 20000)
    struct_keys = {k.lower() for k in conf.get("structured_keys") or []}
    struct_limit = int(conf.get("structured_max_length") or 20000)
    hint_keys = {k.lower() for k in conf.get("platform_hint_keys") or []}
    hints = []

    references, extra, struct_found = [], {}, set()
    pairs = list(pairs)
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
        if key in hint_keys:                          # tags (os:linux, "OS: Windows"): platforms only
            hints += [h for h in _flatten(value, limit) if h not in hints][:50]
        if key in skip_keys:
            continue
        if key in long_keys:
            text = _long_text(value)
            if text:
                extra[key] = [text[:long_limit]]            # Markdown kept whole, line breaks included
            continue
        if isinstance(value, dict) and value and key not in struct_keys and _flat_object(value):
            # a simple object ({actions: [alert, snapshot], severity: high}): one field per entry,
            # "response_actions" with its values as a list — no "[…]" text. Entries read on their
            # own through extract_paths (long texts, JSON blocks) are not repeated.
            for k, v in value.items():
                child = _key(f"{key}_{k}")
                if _key(k) not in long_keys and _key(k) not in struct_keys and child not in extra:
                    pairs.append((child, v))
            continue
        if (key in struct_keys or _nested(value)) and isinstance(value, (dict, list)) and value:
            # structured data (listed in the setting, or any object / list holding objects or lists):
            # one indented JSON block, never flattened into "key: {…}" lines
            extra[key] = [json.dumps(value, ensure_ascii=False, indent=2, default=str)[:struct_limit]]
            struct_found.add(key)
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
    if struct_found - struct_keys:
        extra["_structured"] = sorted(struct_found - struct_keys)    # found on their own: shown as JSON too
    if hints:
        extra["_platform_hints"] = hints[:50]                       # read for the platforms, never shown
    return {"references": references, "extra": extra}


def _flat_object(value: dict) -> bool:
    """Every entry a value or a list of values (no object inside): split into fields."""
    return all(not isinstance(v, dict) and not (isinstance(v, list) and any(isinstance(x, (dict, list)) for x in v))
               for v in value.values())


def _nested(value) -> bool:
    """An object or a list that holds objects or lists: structured data, not a list of values."""
    if isinstance(value, dict):
        return any(isinstance(v, (dict, list)) for v in value.values())   # {product: windows} stays readable
    if isinstance(value, list):
        return any(isinstance(v, (dict, list)) for v in value)
    return False


def _long_text(value) -> str | None:
    """A long field as Markdown text: a string as is, a list as a bullet list (one item each)."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (list, tuple)):
        items = [str(v).strip() for v in value if v is not None and str(v).strip()]
        return "\n".join(f"- {_WS_RE.sub(' ', i)}" for i in items) or None
    return None


def _path_value(doc, path):
    for part in path.split("."):
        if not isinstance(doc, dict) or part not in doc:
            return None
        doc = doc[part]
    return doc


def _path_pairs(fmt, content, conf) -> list:
    """Nested values the setting asks for (extract_paths: {format: {"dotted.path": "key"}})."""
    paths = (conf.get("extract_paths") or {}).get(fmt) or {}
    if not paths:
        return []
    try:
        if fmt == "elastic":
            import tomllib
            doc = tomllib.loads(content)
        else:
            docs = _yaml_docs(content)
            doc = docs[0] if docs else {}
    except Exception:
        return []
    out = []
    for path, key in paths.items():
        value = _path_value(doc, path)
        if value not in (None, "", [], {}):
            out.append((key, value))
    return out


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


_ELASTIC_RULE_KEYS = ("references", "risk_score", "severity", "type", "language", "note", "setup")


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
    conf = _conf()
    try:
        return _collect(extractor(content) + _path_pairs(fmt, content, conf), conf)
    except Exception:
        return empty


def apply_rule_metadata(rule) -> None:
    """Sets the rule's rule_references / extra_metadata / platforms from its format and text (None
    when there is nothing, so untouched rules stay NULL)."""
    found = extract_rule_metadata(rule.format, rule.to_string)
    rule.rule_references = found["references"] or None
    rule.extra_metadata = found["extra"] or None
    rule.platforms = encode_platforms(detect_platforms(found["extra"]))


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


_LIST_SEP = re.compile(r"\s*,\s*")
_SENTENCE = re.compile(r"[.;:!?]\s")


def split_list_value(text: str) -> list[str]:
    """"mirai,gafgyt,tsunami" or "Cobalt Strike, Mimikatz" → one item each. Only a real list is
    split: short items (≤ 60 characters, ≤ 5 words, no sentence punctuation) — a description that
    happens to contain commas stays whole."""
    parts = [p for p in _LIST_SEP.split(text.strip()) if p]
    if len(parts) < 2 or any(len(p) > 60 or len(p.split()) > 5 or _SENTENCE.search(p) for p in parts):
        return [text]
    return parts


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
    split = conf.get("split_comma_lists", True)
    platforms = _platform_patterns(conf.get("platforms") or [])
    try:
        extraction = cached_setting("rule.metadata_extraction") or {}
    except Exception:
        extraction = {}
    long_keys = {k.lower() for k in extraction.get("long_text_keys") or []}
    struct_keys = {k.lower() for k in extraction.get("structured_keys") or []}
    out = []
    auto_struct = set(extra.get("_structured") or [])
    for key, value in extra.items():
        if key.startswith("_"):                         # internal: _structured, _platform_hints
            continue
        known = fields.get(key) or {}
        values = value if isinstance(value, list) else [value]
        if key in long_keys or key in struct_keys or key in auto_struct:      # Markdown / JSON block (rule page: collapsible)
            out.append({"key": key, "label": known.get("label") or key.replace("_", " ").capitalize(),
                        "icon": known.get("icon") or "fa-file-lines", "long": True, "text": str(values[0]),
                        "kind": "json" if (key in struct_keys or key in auto_struct) else "markdown",
                        "values": [], "styled": [], "style": None, "is_hash": False})
            continue
        is_hash = bool(prefixes) and key.startswith(prefixes)
        shown = _shown_values(values, split and not is_hash)
        out.append({
            "key": key,
            "label": known.get("label") or key.replace("_", " ").capitalize(),
            "icon": known.get("icon") or "fa-tag",
            "style": known.get("style") if known.get("style") in ("badge", "scale", "meter", "tlp") else None,
            # one entry per value: its colour (badge / scale) and, for a number, its gauge (0-100)
            "styled": [{**_with_platform(_styled_value(val, known, conf.get("scales") or {}), platforms),
                        "date": _iso_date(val), "hash_type": _hash_type(val) if is_hash else None} for val in shown],
            "values": shown,
            "is_hash": is_hash,
        })
    return out


_TONES = ("red", "orange", "gold", "green", "teal", "blue", "purple", "gray")
_TLP_TONES = {"red", "amber", "green", "clear"}


def _styled_value(value: str, field: dict, scales: dict) -> dict:
    """{text, tone, percent}: the colour of a value (field style badge / scale) and, for a number
    (meter, or a scale given as 0-100 / 0-10), how full its gauge is."""
    style = field.get("style")
    tone, percent = None, None
    if style == "tlp":
        # TLP / PAP label: "TLP:AMBER+STRICT", "pap:green", "Clear" → its TLP 2.0 colour
        level = re.sub(r"^(tlp|pap)\s*:\s*", "", value.strip().lower())
        tone = (scales.get(field.get("scale") or "tlp") or {}).get(level)
        return {"text": value, "tone": tone if tone in _TLP_TONES else None, "percent": None}
    if style == "badge":
        tone = field.get("tone") if field.get("tone") in _TONES else "blue"
    elif style in ("scale", "meter"):
        number = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(%|/\s*(10|100))?\s*", value)
        if number and (style == "meter" or float(number.group(1)) > 5):
            n = float(number.group(1))
            top = 10 if (number.group(3) == "10" or (n <= 10 and number.group(2) is None and style == "meter")) else 100
            percent = max(0, min(100, round(n * 100 / top)))
            tone = "green" if percent >= 75 else "gold" if percent >= 40 else "gray"
            if field.get("scale") == "severity":
                tone = "red" if percent >= 75 else "orange" if percent >= 50 else "gold" if percent >= 25 else "blue"
        elif style == "scale":
            tone = (scales.get(field.get("scale")) or {}).get(value.strip().lower())
    return {"text": value, "tone": tone if tone in _TONES else None, "percent": percent}


_DATE_RE = re.compile(r"\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T]\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?\s*")
_HASH_TYPES = ((re.compile(r"[0-9a-fA-F]{128}"), "SHA-512"), (re.compile(r"[0-9a-fA-F]{64}"), "SHA-256"),
               (re.compile(r"[0-9a-fA-F]{40}"), "SHA-1"), (re.compile(r"[0-9a-fA-F]{32}"), "MD5"),
               (re.compile(r"T1[0-9A-F]{70}"), "TLSH"), (re.compile(r"\d+:[A-Za-z0-9+/]+:[A-Za-z0-9+/]+"), "ssdeep"))


def _iso_date(value: str) -> str | None:
    """"2024/12/02", "2024-12-2", "2024-12-02T10:00:00Z" → "2024-12-02" (for "5 days ago" on the page); else None."""
    import datetime
    m = _DATE_RE.fullmatch(value)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


def _hash_type(value: str) -> str | None:
    """MD5 / SHA-1 / SHA-256 / SHA-512 / TLSH / ssdeep, from the value's shape (imphash looks like MD5)."""
    text = value.strip()
    return next((name for pattern, name in _HASH_TYPES if pattern.fullmatch(text)), None)


_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}")
_ICON = re.compile(r"[a-z0-9 -]{1,60}")


def _platform_patterns(platforms) -> list:
    """[(compiled whole-word pattern, {label, icon, color})] from the setting's platforms."""
    out = []
    for p in platforms:
        words = [re.escape(str(w).lower()) for w in (p.get("match") or []) if str(w).strip()]
        icon, color = str(p.get("icon") or ""), str(p.get("color") or "")
        if not words or not _ICON.fullmatch(icon) or not _HEX_COLOR.fullmatch(color):
            continue                                   # a broken entry is ignored (the colour goes into a style)
        out.append((re.compile(r"(?<![a-z0-9])(?:" + "|".join(words) + r")(?![a-z0-9])", re.I),
                    {"label": str(p.get("label") or ""), "icon": icon, "color": color}))
    return out


def _with_platform(styled: dict, platforms) -> dict:
    """A value naming a platform (Windows, AWS…) gets its logo and colour — not a gauge nor a long text
    (a TLP / PAP field keeps its own style: the page checks the field's style)."""
    if styled.get("percent") is not None or len(styled["text"]) > 80:
        return {**styled, "platform": None}
    found = next((info for pattern, info in platforms if pattern.search(styled["text"])), None)
    return {**styled, "platform": found}


def _shown_values(values, split: bool) -> list[str]:
    out = []
    for v in values:
        for item in (split_list_value(str(v)) if split else [str(v)]):
            if item not in out:
                out.append(item)
    return out


# ── Platforms of a rule (rules list: Platform filter, column, card) ───────────

_PLATFORM_CACHE = {"key": None, "patterns": []}


def _platform_defs() -> list:
    """[(pattern, platform dict)] from the setting (cached until the setting changes)."""
    try:
        conf = cached_setting("rule.metadata_display") or {}
    except Exception:
        conf = {}
    platforms = conf.get("platforms") or []
    key = json.dumps(platforms, sort_keys=True, default=str)
    if _PLATFORM_CACHE["key"] != key:
        out = []
        for p in platforms:
            words = sorted({str(w).lower() for w in (p.get("match") or []) if str(w).strip()}, key=len, reverse=True)
            if words and _ICON.fullmatch(str(p.get("icon") or "")) and _HEX_COLOR.fullmatch(str(p.get("color") or "")):
                pattern = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(w) for w in words) + r")(?![a-z0-9])", re.I)
                out.append((pattern, p))
        _PLATFORM_CACHE.update(key=key, patterns=out)
    return _PLATFORM_CACHE["patterns"]


def detect_platforms(extra: dict | None) -> list[str]:
    """Platforms named in a rule's metadata: ["Windows", "Windows:Sysmon", "AWS", …] — the platform and,
    when the keyword found is one of its details, "Platform:Detail". Long texts and JSON blocks are not read."""
    if not extra:
        return []
    found = []
    for key, value in extra.items():
        for v in (value if isinstance(value, list) else [value]):
            text = str(v)
            if len(text) > 200 or "\n" in text:          # a guide, a JSON block: not a platform name
                continue
            for pattern, p in _platform_defs():
                for m in pattern.finditer(text):
                    label = p.get("label") or ""
                    if label and label not in found:
                        found.append(label)
                    detail = (p.get("details") or {}).get(m.group(1).lower())
                    token = f"{label}:{detail}" if detail else None
                    if token and token not in found:
                        found.append(token)
    return found[:20]


def encode_platforms(tokens: list[str]) -> str | None:
    """The Rule.platforms column: "|Windows|Windows:Sysmon|" (LIKE '%|Windows|%' finds it), None when empty."""
    return ("|" + "|".join(t.replace("|", " ") for t in tokens) + "|")[:500] if tokens else None


def platform_badges(column: str | None) -> list[dict]:
    """[{label, icon, color, details: [...]}] for the rules list, from the stored column."""
    tokens = [t for t in (column or "").split("|") if t]
    info = {p.get("label"): p for _, p in _platform_defs()}
    out = {}
    for t in tokens:
        label, _, detail = t.partition(":")
        p = info.get(label)
        if not p:
            continue
        badge = out.setdefault(label, {"label": label, "icon": p["icon"], "color": p["color"], "details": []})
        if detail and detail not in badge["details"]:
            badge["details"].append(detail)
    return list(out.values())


def format_rule_counts() -> dict[str, int]:
    """Active rules per (lower-case) format, for the admin page."""
    from sqlalchemy import func
    from app import db
    from app.core.db_class.rule import Rule
    rows = (db.session.query(func.lower(Rule.format), func.count(Rule.id))
            .filter(Rule.is_deleted == False).group_by(func.lower(Rule.format)).all())  # noqa: E712
    return {fmt: n for fmt, n in rows if fmt}
