"""
attack_core.py — Business logic for MITRE ATT&CK technique management.

Key functions:
  - get_techniques_for_rule(rule_id) -> list[dict]
  - add_technique_to_rule(rule_id, technique_id, user_id, source) -> RuleAttackAssociation | None
  - remove_technique_from_rule(rule_id, technique_id) -> bool
  - search_techniques(q, limit) -> list[dict]
  - upsert_attack_data(stix_objects) -> (created, updated)  — called by the update job
  - get_stats() -> dict
"""
import datetime
import uuid as uuid_mod
import json
from pathlib import Path

from ... import db
from ...core.db_class.db import AttackTechnique, RuleAttackAssociation, Rule

# ── Read ──────────────────────────────────────────────────────────────────────

def get_techniques_for_rule(rule_id: int) -> list:
    assocs = (
        RuleAttackAssociation.query
        .filter_by(rule_id=rule_id)
        .join(AttackTechnique, RuleAttackAssociation.technique_id == AttackTechnique.technique_id)
        .order_by(AttackTechnique.technique_id)
        .all()
    )
    return [a.to_json() for a in assocs]


def search_techniques(q: str, limit: int = 20) -> list:
    q = q.strip()
    if not q:
        return []
    like = f"%{q}%"
    rows = (
        AttackTechnique.query
        .filter(
            ~AttackTechnique.deprecated,
            db.or_(
                AttackTechnique.technique_id.ilike(like),
                AttackTechnique.name.ilike(like),
            )
        )
        .order_by(AttackTechnique.technique_id)
        .limit(limit)
        .all()
    )
    return [t.to_json() for t in rows]


def get_all_techniques(tactic: str = None) -> list:
    q = AttackTechnique.query.filter(~AttackTechnique.deprecated)
    if tactic:
        q = q.filter(AttackTechnique.tactic_keys.contains([tactic]))
    return [t.to_json() for t in q.order_by(AttackTechnique.technique_id).all()]


def get_stats() -> dict:
    total      = AttackTechnique.query.count()
    deprecated = AttackTechnique.query.filter_by(deprecated=True).count()
    assocs     = RuleAttackAssociation.query.count()
    rules_covered = db.session.query(RuleAttackAssociation.rule_id).distinct().count()
    last_update = (
        db.session.query(db.func.max(AttackTechnique.updated_at)).scalar()
    )
    return {
        'total_techniques': total,
        'deprecated':       deprecated,
        'total_assocs':     assocs,
        'rules_covered':    rules_covered,
        'last_update':      last_update.isoformat() if last_update else None,
    }


# ── Write ─────────────────────────────────────────────────────────────────────

def add_technique_to_rule(rule_id: int, technique_id: str, user_id: int | None = None, source: str = 'manual'):
    technique_id = technique_id.upper().strip()
    tech = AttackTechnique.query.filter_by(technique_id=technique_id).first()
    if not tech:
        return None, 'technique_not_found'

    existing = RuleAttackAssociation.query.filter_by(rule_id=rule_id, technique_id=technique_id).first()
    if existing:
        return existing, 'already_exists'

    assoc = RuleAttackAssociation(
        uuid=str(uuid_mod.uuid4()),
        rule_id=rule_id,
        technique_id=technique_id,
        user_id=user_id,
        source=source,
        added_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(assoc)
    db.session.commit()
    return assoc, 'created'


def remove_technique_from_rule(rule_id: int, technique_id: str) -> bool:
    assoc = RuleAttackAssociation.query.filter_by(
        rule_id=rule_id, technique_id=technique_id.upper()
    ).first()
    if not assoc:
        return False
    db.session.delete(assoc)
    db.session.commit()
    return True


# ── MITRE data import ─────────────────────────────────────────────────────────

_TACTIC_ORDER = [
    'reconnaissance', 'resource-development', 'initial-access', 'execution',
    'persistence', 'privilege-escalation', 'defense-evasion', 'credential-access',
    'discovery', 'lateral-movement', 'collection', 'command-and-control',
    'exfiltration', 'impact',
]

ATTACK_STIX_URL = (
    'https://raw.githubusercontent.com/mitre/cti/master/'
    'enterprise-attack/enterprise-attack.json'
)

# Local path set by the cti git submodule (app/modules/cti)
_LOCAL_CTI_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / 'modules' / 'cti' / 'enterprise-attack' / 'enterprise-attack.json'
)


def _parse_stix_technique(obj: dict) -> dict | None:
    """Extract our fields from a STIX attack-pattern object."""
    tech_id = None
    url = None
    for ref in obj.get('external_references', []):
        if ref.get('source_name') == 'mitre-attack':
            tech_id = ref.get('external_id')
            url = ref.get('url')
    if not tech_id:
        return None

    tactics = [
        p['phase_name']
        for p in obj.get('kill_chain_phases', [])
        if p.get('kill_chain_name') == 'mitre-attack'
    ]
    is_sub = obj.get('x_mitre_is_subtechnique', False)
    deprecated = obj.get('x_mitre_deprecated', False) or obj.get('revoked', False)
    parent = tech_id.split('.')[0] if is_sub and '.' in tech_id else None

    desc = obj.get('description', '')
    if desc and len(desc) > 2000:
        desc = desc[:2000] + '…'

    return {
        'technique_id':        tech_id,
        'name':                obj.get('name', ''),
        'tactic_keys':         tactics,
        'description':         desc or None,
        'url':                 url,
        'is_subtechnique':     is_sub,
        'parent_technique_id': parent,
        'deprecated':          deprecated,
        'updated_at':          datetime.datetime.utcnow(),
    }


def fetch_and_update_attack_data() -> tuple[int, int]:
    """
    Load the MITRE ATT&CK STIX bundle and upsert into AttackTechnique.
    Prefers the local cti submodule (app/modules/cti); falls back to HTTP.
    Returns (created_count, updated_count).
    """
    import urllib.request

    if _LOCAL_CTI_PATH.exists():
        bundle = json.loads(_LOCAL_CTI_PATH.read_text(encoding='utf-8'))
    else:
        with urllib.request.urlopen(ATTACK_STIX_URL, timeout=120) as resp:
            bundle = json.loads(resp.read())

    created = updated = 0
    now = datetime.datetime.utcnow()

    for obj in bundle.get('objects', []):
        if obj.get('type') != 'attack-pattern':
            continue
        parsed = _parse_stix_technique(obj)
        if not parsed:
            continue

        existing = AttackTechnique.query.filter_by(
            technique_id=parsed['technique_id']
        ).first()
        if existing:
            for k, v in parsed.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.session.add(AttackTechnique(**parsed))
            created += 1

    db.session.commit()
    return created, updated


# ── Auto-parse rules ──────────────────────────────────────────────────────────

import re as _re

# Sigma / generic  attack.<TID> — block list, inline list, quoted
_SIGMA_INLINE_RE = _re.compile(r'attack\.(t\d{4}(?:[._]\d{3})?)', _re.IGNORECASE)

# Generic bare TID — word-bounded, sub-tech via . / _ separator
_GENERIC_ID_RE = _re.compile(r'\b(t\d{4})(?:[./_](\d{3}))?\b', _re.IGNORECASE)

# URL:  /techniques/T1059/001  or  /techniques/T1059
_URL_ID_RE = _re.compile(r'/techniques/(T\d{4})(?:/(\d{3}))?', _re.IGNORECASE)

# XML tags (Wazuh):  <id>T1059.001</id>  <technique>T1059</technique>
_XML_ID_RE = _re.compile(
    r'<(?:id|technique|mitre[_-]?id|attack[_-]?id|technique[_-]?id)>\s*(T\d{4}(?:[._]\d{3})?)\s*</',
    _re.IGNORECASE,
)

# Named key=value field (YAML/JSON/YARA meta)
# attack = "T1059", technique_id: T1059, mitre.attack.id: "T1059.001", etc.
_FIELD_RE = _re.compile(
    r'(?:attack|att[_&]ck'
    r'|mitre[_.-]?attack(?:[_.-](?:id|technique(?:[_.-]?id)?)?)?'
    r'|technique[_.-]?id|attack[_.-]?id'
    r'|cve[_.-]?attack|attck)'
    r'\s*[=:]\s*["\']?\s*([^\n"\']+)',
    _re.IGNORECASE,
)

# Elastic ECS: threat.technique.id / threat.tactic.id (JSON/YAML)
_ELASTIC_TECH_RE = _re.compile(
    r'threat[._]technique[._](?:sub)?(?:technique[._])?id\s*[=:]\s*["\']?\s*(T\d{4}(?:[._]\d{3})?)',
    _re.IGNORECASE,
)
_ELASTIC_ID_RE = _re.compile(
    r'"id"\s*:\s*"(T\d{4}(?:[._]\d{3})?)"',
    _re.IGNORECASE,
)

# Suricata metadata keyword:  metadata: mitre_attack_id T1059;
_SURICATA_META_RE = _re.compile(
    r'(?:mitre[_.-]attack[_.-]?(?:id|technique(?:[_.-]?id)?)?|attack[._](?:target|id|technique))'
    r'[,\s]+"?(t\d{4}(?:[._]\d{3})?)"?',
    _re.IGNORECASE,
)

# Comment-line TIDs:  # T1059  |  // T1059  |  -- T1059  |  /* T1059 */
_COMMENT_TID_RE = _re.compile(
    r'(?:#|//|--|/\*)\s*(?:.*?)\b(T\d{4})(?:[./_](\d{3}))?\b',
    _re.IGNORECASE,
)

# Tactic names — these look like `attack.execution` but are NOT technique IDs.
# Also includes post-replace('_','.') dot-variants so the check fires regardless.
_TACTIC_NAMES = frozenset({
    # dash variants
    'reconnaissance', 'resource-development', 'initial-access', 'execution',
    'persistence', 'privilege-escalation', 'defense-evasion', 'credential-access',
    'discovery', 'lateral-movement', 'collection', 'command-and-control',
    'exfiltration', 'impact', 'pre-attack',
    # underscore variants
    'resource_development', 'initial_access', 'privilege_escalation',
    'defense_evasion', 'credential_access', 'lateral_movement',
    'command_and_control', 'pre_attack',
    # dot variants (after replace('_','.') on underscore forms)
    'resource.development', 'initial.access', 'privilege.escalation',
    'defense.evasion', 'credential.access', 'lateral.movement',
    'command.and.control', 'pre.attack',
    # Sigma extra keywords
    'threat-hunting', 'threat_hunting', 'threat.hunting',
    'car', 'car2', 'detection', 'hunting',
})


def _norm_tid(main: str, sub: str | None = None) -> str:
    tid = main.upper()
    return f"{tid}.{sub}" if sub else tid


def _tids_from_generic(text: str) -> list[str]:
    """Extract all T-IDs from arbitrary text using the generic regex."""
    out = []
    for m in _GENERIC_ID_RE.finditer(text):
        out.append(_norm_tid(m.group(1), m.group(2)))
    return out


def _tids_from_field_value(value: str) -> list[str]:
    """Extract T-IDs from a field value that may be comma/space/semi separated."""
    out = []
    for part in _re.split(r'[,;|\s]+', value):
        for m in _GENERIC_ID_RE.finditer(part):
            out.append(_norm_tid(m.group(1), m.group(2)))
    return out


def _dedup(ids: list[str]) -> list[str]:
    seen: set = set()
    out: list = []
    for tid in ids:
        if tid not in seen:
            seen.add(tid)
            out.append(tid)
    return out


def _extract_technique_ids(rule_format: str, content: str) -> list[str]:
    """
    Return deduplicated uppercase technique IDs from rule content.
    Priority: explicit labelled fields → URLs → XML → inline patterns → bare IDs.
    """
    ids: list[str] = []
    fmt = (rule_format or '').lower()

    def _add(tid: str) -> None:
        if tid and tid not in ids:
            ids.append(tid)

    def _add_all(lst: list) -> None:
        for t in lst:
            _add(t)

    # ── Sigma ──────────────────────────────────────────────────────────────────
    if fmt == 'sigma':
        # 1. attack.<TID> (block list `-` or inline `[]` or quoted)
        for m in _SIGMA_INLINE_RE.finditer(content):
            raw = m.group(1).lower().replace('_', '.')
            if raw in _TACTIC_NAMES:
                continue
            parts = raw.split('.', 1)
            _add(_norm_tid(parts[0], parts[1] if len(parts) > 1 else None))
        # 2. Named fields (some sigma rules have attack: T1234 in custom fields)
        for m in _FIELD_RE.finditer(content):
            _add_all(_tids_from_field_value(m.group(1)))
        # 3. URLs embedded in description/reference
        for m in _URL_ID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2)))
        # 4. Bare TIDs anywhere (catches non-standard sigma layouts)
        _add_all(_tids_from_generic(content))

    # ── YARA ───────────────────────────────────────────────────────────────────
    elif fmt == 'yara':
        # 1. Named meta fields
        for m in _FIELD_RE.finditer(content):
            _add_all(_tids_from_field_value(m.group(1)))
        # 2. URLs anywhere
        for m in _URL_ID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2)))
        # 3. Meta section + comments (avoid false positives in string literals)
        meta = _re.search(r'\bmeta\s*:(.*?)(?:strings|condition)\s*:', content, _re.DOTALL | _re.IGNORECASE)
        comments = _re.findall(r'//[^\n]*|/\*.*?\*/', content, _re.DOTALL)
        safe_zone = (meta.group(1) if meta else '') + '\n'.join(comments)
        _add_all(_tids_from_generic(safe_zone))
        # 4. Comment-line patterns
        for m in _COMMENT_TID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2) if m.lastindex >= 2 else None))
        # 5. Full-content fallback
        _add_all(_tids_from_generic(content))

    # ── Suricata ───────────────────────────────────────────────────────────────
    elif fmt == 'suricata':
        for m in _SURICATA_META_RE.finditer(content):
            _add_all(_tids_from_field_value(m.group(1)))
        for m in _FIELD_RE.finditer(content):
            _add_all(_tids_from_field_value(m.group(1)))
        for m in _URL_ID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2)))
        for m in _COMMENT_TID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2) if m.lastindex >= 2 else None))
        _add_all(_tids_from_generic(content))

    # ── Wazuh (XML) ────────────────────────────────────────────────────────────
    elif fmt == 'wazuh':
        for m in _XML_ID_RE.finditer(content):
            _add_all(_tids_from_generic(m.group(1)))
        for m in _FIELD_RE.finditer(content):
            _add_all(_tids_from_field_value(m.group(1)))
        for m in _URL_ID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2)))
        _add_all(_tids_from_generic(content))

    # ── Elastic (ECS JSON/YAML) ────────────────────────────────────────────────
    elif fmt == 'elastic':
        # threat.technique.id / threat.technique.subtechnique.id
        for m in _ELASTIC_TECH_RE.finditer(content):
            _add(_norm_tid(m.group(1).split('.')[0], m.group(1).split('.')[1] if '.' in m.group(1) else None))
        # "id": "T1059" anywhere in JSON threat block
        for m in _ELASTIC_ID_RE.finditer(content):
            _add(_norm_tid(m.group(1).split('.')[0], m.group(1).split('.')[1] if '.' in m.group(1) else None))
        for m in _FIELD_RE.finditer(content):
            _add_all(_tids_from_field_value(m.group(1)))
        for m in _URL_ID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2)))
        _add_all(_tids_from_generic(content))

    # ── Zeek / NSE / CRS / Nova / unknown ─────────────────────────────────────
    else:
        for m in _FIELD_RE.finditer(content):
            _add_all(_tids_from_field_value(m.group(1)))
        for m in _XML_ID_RE.finditer(content):
            _add_all(_tids_from_generic(m.group(1)))
        for m in _URL_ID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2)))
        for m in _ELASTIC_ID_RE.finditer(content):
            _add(_norm_tid(m.group(1).split('.')[0], m.group(1).split('.')[1] if '.' in m.group(1) else None))
        for m in _COMMENT_TID_RE.finditer(content):
            _add(_norm_tid(m.group(1), m.group(2) if m.lastindex >= 2 else None))
        _add_all(_tids_from_generic(content))

    return _dedup(ids)


def auto_parse_rule(rule_id: int, user_id: int | None = None) -> list[str]:
    """
    Parse ATT&CK technique IDs from a single rule and create associations.
    Returns list of technique_ids that were added (new only).
    """
    rule = Rule.query.get(rule_id)
    if not rule or rule.is_deleted:
        return []

    ids = _extract_technique_ids(rule.format or '', rule.to_string or '')
    ids = list(dict.fromkeys(ids))   # dedup, preserve order

    # Only keep IDs that exist in AttackTechnique table
    known = {
        t.technique_id
        for t in AttackTechnique.query.filter(AttackTechnique.technique_id.in_(ids)).all()
    }

    added = []
    for tid in ids:
        if tid not in known:
            continue
        existing = RuleAttackAssociation.query.filter_by(
            rule_id=rule_id, technique_id=tid
        ).first()
        if existing:
            continue
        db.session.add(RuleAttackAssociation(
            uuid=str(uuid_mod.uuid4()),
            rule_id=rule_id,
            technique_id=tid,
            user_id=user_id,
            source='auto',
            added_at=datetime.datetime.now(tz=datetime.timezone.utc),
        ))
        added.append(tid)

    if added:
        db.session.commit()
    return added
