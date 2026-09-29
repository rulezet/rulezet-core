"""
alert_core.py — "tell me when..." alerts: validation, CRUD, the matching
engine, the periodic sweeper and the alert emails.

How it works
------------
An Alert is a saved set of criteria (CVEs, tags, ATT&CK techniques,
keywords, formats, users, GitHub repos). Nothing is evaluated when a rule
is created — rules come from ~20 code paths (manual, GitHub import,
connector pull, bundle import...) and their tags/CVEs/ATT&CK links are
often attached afterwards. Instead run_sweep() runs every few minutes
(app/__init__.py::_start_alert_sweeper), looks at what was created or
updated since its last pass (AlertSweepState watermark), evaluates every
active alert against that window in SQL, and records AlertMatch rows —
unique per (alert, object, event, version), so a pass is idempotent.

Each alert with new matches then gets ONE grouped notification per pass
("12 new rules match 'NetScaler 0-day'"), never one per rule, so a 3 000
rule GitHub import can't flood anyone. Emails follow the alert's
email_mode (instant = grouped per pass, daily / weekly digests) and only
ever go out when app/core/utils/mail_status.py says email is available.

Visibility: rules are public unless soft-deleted; bundles only when
Bundle.access is true. A user is never alerted about their own content.
"""

import datetime
import re
import uuid as uuid_mod

from flask import current_app
from sqlalchemy import and_, func, or_

from app import db
from app.core.db_class.db import (
    Alert, AlertMatch, AlertSweepState, Bundle, BundleTagAssociation, Notification,
    Rule, RuleAttackAssociation, RuleTagAssociation, Tag, User,
)

# ─── Limits ──────────────────────────────────────────────────────────────────

MAX_ALERTS_PER_USER   = 50
MAX_VALUES_PER_FIELD  = 20
KEYWORD_MIN_LEN       = 3
KEYWORD_MAX_LEN       = 60
NAME_MAX_LEN          = 120
SWEEP_WINDOW          = 5000   # objects looked at per pass and per kind; the rest waits for the next pass
# creation_date and last_modif come from two separate now() calls, so a
# never-edited rule still has last_modif a hair after creation_date.
EDIT_GRACE            = datetime.timedelta(seconds=2)
INSTANT_EMAIL_COOLDOWN = datetime.timedelta(minutes=15)
DIGEST_PERIODS = {'daily': datetime.timedelta(days=1), 'weekly': datetime.timedelta(days=7)}

CRITERIA_LIST_FIELDS = ('cves', 'tags', 'attacks', 'keywords', 'formats', 'users', 'github_repos')
# "Any ..." switches: any vulnerability id / non-marking tag / ATT&CK technique
# at all, or any GitHub import. Each one supersedes its specific list.
CRITERIA_ANY_FLAGS   = ('cve_any', 'tag_any', 'attack_any', 'github_any')

# Any vulnerability id VulnerabilityInput accepts: CVE-, GHSA-, RHSA-2024:1234, MSRC_CVE-...
_MARKING_TAG_PREFIXES = ('tlp:', 'pap:')   # default markings, never "content" tags

_CVE_RE    = re.compile(r'^[A-Z][A-Z0-9_]*-[A-Z0-9][A-Z0-9:_.-]*$')
_ATTACK_RE = re.compile(r'^T\d{4}(\.\d{3})?$')


class AlertError(ValueError):
    """Validation / permission problem to show to the user as-is."""


# ─── Criteria normalisation ──────────────────────────────────────────────────

def _clean_list(values, transform, validate=None):
    if isinstance(values, str):
        values = values.split(',')
    out = []
    for raw in values or []:
        value = transform(str(raw).strip())
        if not value or value in out:
            continue
        if validate and not validate(value):
            raise AlertError(f'Invalid value: "{raw}".')
        out.append(value)
    if len(out) > MAX_VALUES_PER_FIELD:
        raise AlertError(f'At most {MAX_VALUES_PER_FIELD} values per criterion.')
    return out


def _clean_keyword(value):
    value = value.lower()
    if value and not (KEYWORD_MIN_LEN <= len(value) <= KEYWORD_MAX_LEN):
        raise AlertError(f'Keywords must be {KEYWORD_MIN_LEN}–{KEYWORD_MAX_LEN} characters: "{value}".')
    return value


def _clean_repo(value):
    """Accepts owner/repo or a full GitHub URL; stored as lowercase owner/repo."""
    value = value.lower().rstrip('/')
    value = re.sub(r'^(https?://)?(www\.)?github\.com/', '', value)
    value = re.sub(r'\.git$', '', value)
    return value


def normalize_criteria(raw) -> dict:
    """Validates and canonicalises a criteria dict (see Alert's docstring)."""
    raw = raw if isinstance(raw, dict) else {}
    criteria = {
        'cves':         _clean_list(raw.get('cves'), str.upper, _CVE_RE.match),
        'tags':         _clean_list(raw.get('tags'), str.lower),
        'attacks':      _clean_list(raw.get('attacks'), str.upper, _ATTACK_RE.match),
        'keywords':     _clean_list(raw.get('keywords'), _clean_keyword),
        'formats':      _clean_list(raw.get('formats'), str.lower),
        'users':        [],
        'github_repos': _clean_list(raw.get('github_repos'), _clean_repo,
                                    lambda v: re.match(r'^[a-z0-9_.-]+/[a-z0-9_.-]+$', v)),
    }
    for flag in CRITERIA_ANY_FLAGS:
        criteria[flag] = bool(raw.get(flag))
    # An "any" switch makes its specific list redundant — drop it so what's
    # stored is exactly what gets matched.
    for flag, field in (('cve_any', 'cves'), ('tag_any', 'tags'), ('attack_any', 'attacks'),
                        ('github_any', 'github_repos')):
        if criteria[flag]:
            criteria[field] = []
    user_ids = _clean_list(raw.get('users'), lambda v: v if v.isdigit() else v, lambda v: v.isdigit())
    if user_ids:
        ids = [int(u) for u in user_ids]
        existing = {u.id for u in User.query.filter(User.id.in_(ids)).all()}
        missing = [u for u in ids if u not in existing]
        if missing:
            raise AlertError(f'Unknown user id(s): {", ".join(map(str, missing))}.')
        criteria['users'] = ids
    return criteria


def has_any_criterion(criteria) -> bool:
    return any(criteria.get(f) for f in CRITERIA_LIST_FIELDS + CRITERIA_ANY_FLAGS)


def validate_alert_payload(data: dict, email_available: bool, current_email_mode=None) -> dict:
    """Turns a create/update request body into clean Alert fields.
    Raises AlertError with a user-facing message.

    While email is unavailable the form doesn't show the email section, so
    an edit keeps the alert's stored email_mode (current_email_mode) instead
    of silently resetting it — it simply stays dormant until email is back."""
    name = (data.get('name') or '').strip()
    if not name:
        raise AlertError('Give this alert a name.')
    if len(name) > NAME_MAX_LEN:
        raise AlertError(f'Name is limited to {NAME_MAX_LEN} characters.')

    targets = [t for t in (data.get('targets') or []) if t in Alert.TARGETS]
    if not targets:
        raise AlertError('Pick at least one target: rules and/or bundles.')

    events = [e for e in (data.get('events') or []) if e in Alert.EVENTS]
    if not events:
        raise AlertError('Pick at least one event: new and/or updated.')

    match_mode = data.get('match_mode') if data.get('match_mode') in ('any', 'all') else 'any'

    criteria = normalize_criteria(data.get('criteria'))
    if not has_any_criterion(criteria):
        raise AlertError('Add at least one criterion (CVE, tag, technique, keyword, user...).')

    if email_available:
        email_mode = data.get('email_mode') or 'off'
        if email_mode not in Alert.EMAIL_MODES:
            raise AlertError('Unknown email mode.')
    else:
        email_mode = current_email_mode or 'off'

    notify_in_app = bool(data.get('notify_in_app', True))
    if not notify_in_app and (email_mode == 'off' or not email_available):
        raise AlertError('This alert would never tell you anything — enable in-app notifications'
                         + (' or email.' if email_available else '.'))

    return {
        'name': name, 'targets': targets, 'events': events, 'match_mode': match_mode,
        'criteria': criteria, 'email_mode': email_mode, 'notify_in_app': notify_in_app,
    }


# ─── CRUD ────────────────────────────────────────────────────────────────────

def get_alert_by_uuid(alert_uuid):
    return Alert.query.filter_by(uuid=alert_uuid).first()


def get_user_alerts(user_id):
    return Alert.query.filter_by(user_id=user_id).order_by(Alert.created_at.desc()).all()


def unseen_counts(user_id) -> dict:
    """{alert_id: unseen match count} for every alert of this user."""
    rows = (
        db.session.query(AlertMatch.alert_id, func.count(AlertMatch.id))
        .join(Alert, Alert.id == AlertMatch.alert_id)
        .filter(Alert.user_id == user_id, AlertMatch.seen_at.is_(None))
        .group_by(AlertMatch.alert_id)
        .all()
    )
    return dict(rows)


def total_unseen(user_id) -> int:
    return (
        db.session.query(func.count(AlertMatch.id))
        .join(Alert, Alert.id == AlertMatch.alert_id)
        .filter(Alert.user_id == user_id, AlertMatch.seen_at.is_(None))
        .scalar()
    ) or 0


def matches_since(user_id, days=7) -> int:
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    return (
        db.session.query(func.count(AlertMatch.id))
        .join(Alert, Alert.id == AlertMatch.alert_id)
        .filter(Alert.user_id == user_id, AlertMatch.created_at >= since)
        .scalar()
    ) or 0


def create_alert(user_id, fields: dict) -> Alert:
    if Alert.query.filter_by(user_id=user_id).count() >= MAX_ALERTS_PER_USER:
        raise AlertError(f'You can have at most {MAX_ALERTS_PER_USER} alerts.')
    alert = Alert(uuid=str(uuid_mod.uuid4()), user_id=user_id, **fields)
    db.session.add(alert)
    db.session.commit()
    return alert


def update_alert(alert: Alert, fields: dict) -> Alert:
    for key, value in fields.items():
        setattr(alert, key, value)
    db.session.commit()
    return alert


def set_alert_active(alert: Alert, active: bool) -> Alert:
    alert.is_active = bool(active)
    db.session.commit()
    return alert


def delete_alert(alert: Alert):
    db.session.delete(alert)
    db.session.commit()


def mark_matches_seen(alert: Alert):
    now = datetime.datetime.utcnow()
    AlertMatch.query.filter_by(alert_id=alert.id, seen_at=None).update({'seen_at': now})
    db.session.commit()


def disable_alert_emails(alert: Alert):
    alert.email_mode = 'off'
    if not alert.notify_in_app:
        alert.notify_in_app = True  # never leave an alert that can't tell anyone anything
    db.session.commit()


# ─── Matching engine ─────────────────────────────────────────────────────────

def _attack_condition(techniques):
    # Watching T1059 also covers its sub-techniques (T1059.001, ...).
    conds = []
    for t in techniques:
        conds.append(RuleAttackAssociation.technique_id == t)
        if '.' not in t:
            conds.append(RuleAttackAssociation.technique_id.like(f'{t}.%'))
    return or_(*conds)


def _rule_conditions(criteria) -> list:
    """One SQL condition per non-empty criterion, for the Rule table."""
    from app.features.rule.rule_core import presence_conditions

    conds = []
    if criteria.get('cve_any'):
        conds += presence_conditions(has_cve=True)
    elif criteria.get('cves'):
        conds.append(or_(*[Rule.cve_id.ilike(f'%"{c}"%') for c in criteria['cves']]))
    if criteria.get('tag_any'):
        conds += presence_conditions(has_tags=True)
    elif criteria.get('tags'):
        tagged = (db.session.query(RuleTagAssociation.rule_id)
                  .join(Tag, Tag.id == RuleTagAssociation.tag_id)
                  .filter(func.lower(Tag.name).in_(criteria['tags'])))
        conds.append(Rule.id.in_(tagged))
    if criteria.get('attack_any'):
        conds += presence_conditions(has_attack=True)
    elif criteria.get('attacks'):
        mapped = db.session.query(RuleAttackAssociation.rule_id).filter(_attack_condition(criteria['attacks']))
        conds.append(Rule.id.in_(mapped))
    if criteria.get('keywords'):
        conds.append(or_(*[
            or_(Rule.title.ilike(f'%{k}%'), Rule.description.ilike(f'%{k}%'), Rule.to_string.ilike(f'%{k}%'))
            for k in criteria['keywords']
        ]))
    if criteria.get('formats'):
        conds.append(func.lower(Rule.format).in_(criteria['formats']))
    if criteria.get('users'):
        conds.append(Rule.user_id.in_(criteria['users']))
    if criteria.get('github_repos'):
        conds.append(or_(*[Rule.source.ilike(f'%{r}%') for r in criteria['github_repos']]))
    if criteria.get('github_any'):
        conds.append(or_(Rule.github_path.isnot(None), Rule.source.ilike('%github.com/%')))
    return conds


def _bundle_conditions(criteria):
    """Same for bundles. Returns None when the alert can't match a bundle:
    ATT&CK / format / GitHub criteria only exist on rules, so in 'all' mode
    any of them rules bundles out; in 'any' mode they're just skipped."""
    rule_only = any(criteria.get(f) for f in ('attacks', 'formats', 'github_repos', 'attack_any', 'github_any'))
    conds = []
    if criteria.get('cve_any'):
        conds.append(and_(Bundle.vulnerability_identifiers.isnot(None),
                          ~Bundle.vulnerability_identifiers.in_(['', '[]', 'null', '[""]'])))
    elif criteria.get('cves'):
        conds.append(or_(*[Bundle.vulnerability_identifiers.ilike(f'%"{c}"%') for c in criteria['cves']]))
    if criteria.get('tag_any') or criteria.get('tags'):
        tag_filter = (and_(*[~func.lower(Tag.name).like(f'{p}%') for p in _MARKING_TAG_PREFIXES])
                      if criteria.get('tag_any') else func.lower(Tag.name).in_(criteria['tags']))
        tagged = (db.session.query(BundleTagAssociation.bundle_id)
                  .join(Tag, Tag.id == BundleTagAssociation.tag_id)
                  .filter(tag_filter))
        conds.append(Bundle.id.in_(tagged))
    if criteria.get('keywords'):
        conds.append(or_(*[
            or_(Bundle.name.ilike(f'%{k}%'), Bundle.description.ilike(f'%{k}%'))
            for k in criteria['keywords']
        ]))
    if criteria.get('users'):
        conds.append(Bundle.user_id.in_(criteria['users']))
    return conds, rule_only


def _combine(conds, match_mode):
    return and_(*conds) if match_mode == 'all' else or_(*conds)


def rule_match_query(criteria, match_mode, base_query=None):
    """Rules matching the criteria (active only), or None if nothing to match on."""
    conds = _rule_conditions(criteria)
    if not conds:
        return None
    query = base_query if base_query is not None else Rule.query
    return query.filter(Rule.is_deleted == False, _combine(conds, match_mode))


def bundle_match_query(criteria, match_mode, base_query=None):
    """Public bundles matching the criteria, or None if the alert can't match bundles."""
    conds, rule_only = _bundle_conditions(criteria)
    if not conds or (match_mode == 'all' and rule_only):
        return None
    query = base_query if base_query is not None else Bundle.query
    return query.filter(Bundle.access == True, _combine(conds, match_mode))


def _json_ids(raw) -> list:
    """Vulnerability ids stored as a JSON list string ('["CVE-..."]')."""
    import json
    try:
        values = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []
    return [str(v) for v in values if v] if isinstance(values, list) else []


def _is_marking_tag(name):
    return (name or '').lower().startswith(_MARKING_TAG_PREFIXES)


# At most this many values per "any ..." reason, so a rule with 40 CVEs
# doesn't turn one match into a wall of chips.
_ANY_REASON_LIMIT = 3


def _matched_on_rules(criteria, rule_ids) -> dict:
    """{rule_id: ["cve:...", "tag:...", ...]} — why each rule matched, for display."""
    if not rule_ids:
        return {}
    reasons = {rid: [] for rid in rule_ids}
    rows = Rule.query.filter(Rule.id.in_(rule_ids)).with_entities(
        Rule.id, Rule.cve_id, Rule.title, Rule.description, Rule.format, Rule.user_id,
        Rule.source, Rule.github_path).all()

    tags_by_rule = {}
    if criteria.get('tag_any') or criteria.get('tags'):
        wanted = set(criteria.get('tags') or [])
        for rid, name in (db.session.query(RuleTagAssociation.rule_id, Tag.name)
                          .join(Tag, Tag.id == RuleTagAssociation.tag_id)
                          .filter(RuleTagAssociation.rule_id.in_(rule_ids)).all()):
            name = (name or '').lower()
            if (criteria.get('tag_any') and name and not _is_marking_tag(name)) or name in wanted:
                tags_by_rule.setdefault(rid, set()).add(name)

    attacks_by_rule = {}
    if criteria.get('attack_any') or criteria.get('attacks'):
        q = db.session.query(RuleAttackAssociation.rule_id, RuleAttackAssociation.technique_id) \
            .filter(RuleAttackAssociation.rule_id.in_(rule_ids))
        if not criteria.get('attack_any'):
            q = q.filter(_attack_condition(criteria['attacks']))
        for rid, tid in q.all():
            attacks_by_rule.setdefault(rid, set()).add(tid)

    for rid, cve_raw, title, description, fmt, owner, source, github_path in rows:
        r = reasons[rid]
        if criteria.get('cve_any'):
            r += [f'cve:{c}' for c in _json_ids(cve_raw)[:_ANY_REASON_LIMIT]]
        else:
            r += [f'cve:{c}' for c in criteria.get('cves') or [] if f'"{c}"'.lower() in (cve_raw or '').lower()]
        limit = _ANY_REASON_LIMIT if criteria.get('tag_any') else None
        r += [f'tag:{t}' for t in sorted(tags_by_rule.get(rid, set()))[:limit]]
        limit = _ANY_REASON_LIMIT if criteria.get('attack_any') else None
        r += [f'attack:{t}' for t in sorted(attacks_by_rule.get(rid, set()))[:limit]]
        haystack = f'{title or ""} {description or ""}'.lower()
        r += [f'keyword:{k}' for k in criteria.get('keywords') or [] if k in haystack]
        if fmt and fmt.lower() in (criteria.get('formats') or []):
            r.append(f'format:{fmt.lower()}')
        if owner in (criteria.get('users') or []):
            r.append(f'user:{owner}')
        r += [f'repo:{repo}' for repo in criteria.get('github_repos') or [] if repo in (source or '').lower()]
        if criteria.get('github_any') and (github_path or 'github.com/' in (source or '').lower()):
            r.append('github')
    return reasons


def _matched_on_bundles(criteria, bundle_ids) -> dict:
    if not bundle_ids:
        return {}
    reasons = {bid: [] for bid in bundle_ids}
    tags_by_bundle = {}
    if criteria.get('tag_any') or criteria.get('tags'):
        wanted = set(criteria.get('tags') or [])
        for bid, name in (db.session.query(BundleTagAssociation.bundle_id, Tag.name)
                          .join(Tag, Tag.id == BundleTagAssociation.tag_id)
                          .filter(BundleTagAssociation.bundle_id.in_(bundle_ids)).all()):
            name = (name or '').lower()
            if (criteria.get('tag_any') and name and not _is_marking_tag(name)) or name in wanted:
                tags_by_bundle.setdefault(bid, set()).add(name)
    for bid, vulns, name, description, owner in (Bundle.query.filter(Bundle.id.in_(bundle_ids))
            .with_entities(Bundle.id, Bundle.vulnerability_identifiers, Bundle.name,
                           Bundle.description, Bundle.user_id).all()):
        r = reasons[bid]
        if criteria.get('cve_any'):
            r += [f'cve:{c}' for c in _json_ids(vulns)[:_ANY_REASON_LIMIT]]
        else:
            r += [f'cve:{c}' for c in criteria.get('cves') or [] if f'"{c}"'.lower() in (vulns or '').lower()]
        limit = _ANY_REASON_LIMIT if criteria.get('tag_any') else None
        r += [f'tag:{t}' for t in sorted(tags_by_bundle.get(bid, set()))[:limit]]
        haystack = f'{name or ""} {description or ""}'.lower()
        r += [f'keyword:{k}' for k in criteria.get('keywords') or [] if k in haystack]
        if owner in (criteria.get('users') or []):
            r.append(f'user:{owner}')
    return reasons


# ─── Preview ("would have matched N in the last 30 days") ───────────────────

def preview(criteria, match_mode, targets, user_id=None, days=30, sample_size=5) -> dict:
    """Same rules as the sweeper, applied to the last `days` days: what this
    alert would have caught. The user's own content is left out, as in run_sweep."""
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    out = {'days': days, 'rules': 0, 'bundles': 0, 'sample': []}
    if 'rule' in targets:
        q = rule_match_query(criteria, match_mode)
        if q is not None:
            q = q.filter(Rule.creation_date >= since)
            if user_id is not None:
                q = q.filter(Rule.user_id != user_id)
            out['rules'] = q.count()
            out['sample'] += [
                {'type': 'rule', 'id': r.id, 'title': r.title, 'format': r.format,
                 'link': f'/rule/detail_rule/{r.id}'}
                for r in q.order_by(Rule.creation_date.desc()).limit(sample_size).all()
            ]
    if 'bundle' in targets:
        q = bundle_match_query(criteria, match_mode)
        if q is not None:
            q = q.filter(Bundle.created_at >= since)
            if user_id is not None:
                q = q.filter(Bundle.user_id != user_id)
            out['bundles'] = q.count()
            out['sample'] += [
                {'type': 'bundle', 'id': b.id, 'title': b.name, 'format': None,
                 'link': f'/bundle/detail/{b.id}'}
                for b in q.order_by(Bundle.created_at.desc()).limit(sample_size).all()
            ]
    return out


# ─── Sweep ───────────────────────────────────────────────────────────────────

def _get_state() -> AlertSweepState:
    """First pass ever: start from "now" — alerts are about what happens
    next, never a backfill of the whole catalog."""
    state = AlertSweepState.query.first()
    if state is None:
        now = datetime.datetime.utcnow()
        state = AlertSweepState(
            id=1,
            last_rule_id=db.session.query(func.max(Rule.id)).scalar() or 0,
            last_bundle_id=db.session.query(func.max(Bundle.id)).scalar() or 0,
            rules_modified_at=now,
            bundles_updated_at=now,
        )
        db.session.add(state)
        db.session.commit()
    return state


def _window(state):
    """What changed since the last pass.

    Returns (slices, marks): slices is [(object_type, event, rows)] with
    rows = [(id, owner_id, version_timestamp)], and marks the watermark
    values this pass reached — kept separate because the "updated" rule
    scan advances past rows it then discards (touched but never edited)."""
    marks = {}

    new_rules = (Rule.query.filter(Rule.id > state.last_rule_id, Rule.is_deleted == False)
                 .order_by(Rule.id.asc()).limit(SWEEP_WINDOW)
                 .with_entities(Rule.id, Rule.user_id, Rule.last_modif).all())
    if new_rules:
        marks['last_rule_id'] = new_rules[-1][0]

    updated_rules = []
    if state.rules_modified_at:
        touched = (Rule.query.filter(Rule.id <= state.last_rule_id, Rule.is_deleted == False,
                                     Rule.last_modif > state.rules_modified_at)
                   .order_by(Rule.last_modif.asc()).limit(SWEEP_WINDOW)
                   .with_entities(Rule.id, Rule.user_id, Rule.last_modif, Rule.creation_date).all())
        if touched:
            marks['rules_modified_at'] = touched[-1][2]
        updated_rules = [(rid, owner, modif) for rid, owner, modif, created in touched
                         if not created or modif - created > EDIT_GRACE]

    new_bundles = (Bundle.query.filter(Bundle.id > state.last_bundle_id, Bundle.access == True)
                   .order_by(Bundle.id.asc()).limit(SWEEP_WINDOW)
                   .with_entities(Bundle.id, Bundle.user_id, Bundle.updated_at).all())
    if new_bundles:
        marks['last_bundle_id'] = new_bundles[-1][0]

    updated_bundles = []
    if state.bundles_updated_at:
        updated_bundles = (Bundle.query.filter(Bundle.id <= state.last_bundle_id, Bundle.access == True,
                                               Bundle.updated_at > state.bundles_updated_at)
                           .order_by(Bundle.updated_at.asc()).limit(SWEEP_WINDOW)
                           .with_entities(Bundle.id, Bundle.user_id, Bundle.updated_at).all())
        if updated_bundles:
            marks['bundles_updated_at'] = updated_bundles[-1][2]

    slices = [
        ('rule', 'created', new_rules), ('rule', 'updated', updated_rules),
        ('bundle', 'created', new_bundles), ('bundle', 'updated', updated_bundles),
    ]
    return slices, marks


def _version(ts):
    return ts.isoformat() if ts else ''


def _evaluate(alert, object_type, event, rows, now):
    """New AlertMatch rows for one alert over one slice of the window."""
    if object_type not in (alert.targets or []) or event not in (alert.events or []):
        return []
    # Never alert someone about their own content.
    candidates = {oid: (owner, ts) for oid, owner, ts in rows if owner != alert.user_id}
    if not candidates:
        return []

    ids = list(candidates)
    if object_type == 'rule':
        q = rule_match_query(alert.criteria or {}, alert.match_mode)
        if q is None:
            return []
        matched = [r[0] for r in q.filter(Rule.id.in_(ids)).with_entities(Rule.id).all()]
        reasons = _matched_on_rules(alert.criteria or {}, matched)
    else:
        q = bundle_match_query(alert.criteria or {}, alert.match_mode)
        if q is None:
            return []
        matched = [b[0] for b in q.filter(Bundle.id.in_(ids)).with_entities(Bundle.id).all()]
        reasons = _matched_on_bundles(alert.criteria or {}, matched)
    if not matched:
        return []

    versions = {oid: (_version(candidates[oid][1]) if event == 'updated' else '') for oid in matched}
    existing = {
        (m.object_id, m.object_version)
        for m in AlertMatch.query.filter(
            AlertMatch.alert_id == alert.id, AlertMatch.object_type == object_type,
            AlertMatch.event == event, AlertMatch.object_id.in_(matched),
        ).with_entities(AlertMatch.object_id, AlertMatch.object_version).all()
    }
    return [
        AlertMatch(alert_id=alert.id, object_type=object_type, object_id=oid,
                   object_version=versions[oid], event=event,
                   matched_on=reasons.get(oid) or [], created_at=now)
        for oid in matched if (oid, versions[oid]) not in existing
    ]


def run_sweep(now=None) -> dict:
    """One pass: evaluate every active alert against what changed since the
    previous pass, record matches, notify. Returns a small summary."""
    now = now or datetime.datetime.utcnow()
    state = _get_state()
    slices, marks = _window(state)

    new_matches_by_alert = {}
    if any(rows for _, _, rows in slices):
        for alert in Alert.query.filter_by(is_active=True).all():
            found = []
            for object_type, event, rows in slices:
                if rows:
                    found += _evaluate(alert, object_type, event, rows, now)
            if found:
                db.session.add_all(found)
                alert.match_count = (alert.match_count or 0) + len(found)
                alert.last_triggered_at = now
                new_matches_by_alert[alert.id] = (alert, found)
        db.session.flush()

    # Advance the watermark to what this pass actually covered.
    for field, value in marks.items():
        setattr(state, field, value)
    state.last_run_at = now
    db.session.commit()

    for alert, matches in new_matches_by_alert.values():
        _notify_in_app(alert, matches)

    emails_sent = send_due_emails(now)
    return {
        'alerts_triggered': len(new_matches_by_alert),
        'matches': sum(len(m) for _, m in new_matches_by_alert.values()),
        'emails_sent': emails_sent,
    }


# ─── In-app notification ─────────────────────────────────────────────────────

def _object_label(object_type, object_id):
    if object_type == 'rule':
        rule = Rule.query.get(object_id)
        return (rule.title if rule else f'Rule #{object_id}'), f'/rule/detail_rule/{object_id}'
    bundle = Bundle.query.get(object_id)
    return (bundle.name if bundle else f'Bundle #{object_id}'), f'/bundle/detail/{object_id}'


def _count_label(matches):
    rules = sum(1 for m in matches if m.object_type == 'rule')
    bundles = len(matches) - rules
    parts = []
    if rules:
        parts.append(f'{rules} rule{"s" if rules > 1 else ""}')
    if bundles:
        parts.append(f'{bundles} bundle{"s" if bundles > 1 else ""}')
    return ' and '.join(parts)


def _notify_in_app(alert, matches):
    """One grouped notification per alert per pass."""
    from app.features.notification.notification_core import _get_pref

    if not alert.notify_in_app or not _get_pref(alert.user_id).pref_alerts:
        return
    try:
        if len(matches) == 1:
            m = matches[0]
            label, link = _object_label(m.object_type, m.object_id)
            verb = 'updated' if m.event == 'updated' else 'new'
            title = f'{alert.name}: {verb} {m.object_type} match'
            body = label
        else:
            title = f'{alert.name}: {_count_label(matches)} match'
            body = 'Open the alert to see everything that matched.'
            link = f'/alert/{alert.uuid}'
        db.session.add(Notification(
            user_id=alert.user_id, notif_type='alert_match', title=title[:255], body=(body or '')[:500],
            link=link, icon='fa-solid fa-bell', is_read=False, created_at=datetime.datetime.utcnow(),
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'[alert_core] in-app notification failed for alert {alert.id}: {e}')


# ─── Emails ──────────────────────────────────────────────────────────────────

def _unsubscribe_serializer():
    from itsdangerous import URLSafeSerializer
    return URLSafeSerializer(current_app.config['SECRET_KEY'], salt='alert-email-unsubscribe')


def make_unsubscribe_token(alert):
    return _unsubscribe_serializer().dumps(alert.uuid)


def read_unsubscribe_token(token):
    from itsdangerous import BadSignature
    try:
        return _unsubscribe_serializer().loads(token)
    except BadSignature:
        return None


def _public_base_url():
    from app.core.db_class.db import InstanceConfig
    cfg = InstanceConfig.query.first()
    base = (current_app.config.get('INSTANCE_PUBLIC_URL') or (cfg.public_url if cfg else None)
            or f"http://{current_app.config.get('FLASK_URL', '127.0.0.1')}:{current_app.config.get('FLASK_PORT', 7009)}")
    return base.rstrip('/')


def _email_is_due(alert, now, last_user_email):
    if alert.email_mode == 'instant':
        return last_user_email is None or now - last_user_email >= INSTANT_EMAIL_COOLDOWN
    period = DIGEST_PERIODS.get(alert.email_mode)
    if not period:
        return False
    return alert.last_emailed_at is None or now - alert.last_emailed_at >= period


def send_due_emails(now=None) -> int:
    """Sends every due alert email, grouped into one message per user.
    Returns the number of emails sent. No-op when email isn't available."""
    from app.core.utils.mail_status import is_email_available

    if not is_email_available():
        return 0
    now = now or datetime.datetime.utcnow()

    pending = (db.session.query(Alert, func.count(AlertMatch.id))
               .join(AlertMatch, AlertMatch.alert_id == Alert.id)
               .filter(Alert.is_active == True, Alert.email_mode != 'off', AlertMatch.emailed_at.is_(None))
               .group_by(Alert.id).all())
    by_user = {}
    for alert, _count in pending:
        by_user.setdefault(alert.user_id, []).append(alert)

    sent = 0
    for user_id, alerts in by_user.items():
        last_user_email = max((a.last_emailed_at for a in get_user_alerts(user_id) if a.last_emailed_at),
                              default=None)
        due = [a for a in alerts if _email_is_due(a, now, last_user_email)]
        if not due:
            continue
        user = User.query.get(user_id)
        if not user or not user.email:
            continue
        if _send_alert_email(user, due, now):
            sent += 1
    return sent


def _send_alert_email(user, alerts, now) -> bool:
    from flask_mail import Message
    from app import mail

    base = _public_base_url()
    sections = []
    match_ids = []
    for alert in alerts:
        matches = (AlertMatch.query.filter_by(alert_id=alert.id, emailed_at=None)
                   .order_by(AlertMatch.created_at.desc()).all())
        if not matches:
            continue
        items = []
        for m in matches[:25]:
            label, link = _object_label(m.object_type, m.object_id)
            items.append({'type': m.object_type, 'event': m.event, 'label': label,
                          'url': base + link, 'matched_on': m.matched_on or []})
        sections.append({
            'alert': alert, 'items': items, 'total': len(matches),
            'alert_url': f'{base}/alert/{alert.uuid}',
            'unsubscribe_url': f'{base}/alert/unsubscribe/{make_unsubscribe_token(alert)}',
        })
        match_ids += [m.id for m in matches]
    if not sections:
        return False

    total = sum(s['total'] for s in sections)
    subject = (f'Rulezet — {sections[0]["alert"].name}: {total} new match{"es" if total > 1 else ""}'
               if len(sections) == 1 else f'Rulezet — {total} new matches across {len(sections)} alerts')
    ctx = dict(user=user, sections=sections, total=total, base_url=base,
               manage_url=f'{base}/alert/', year=now.year)
    try:
        msg = Message(subject=subject, recipients=[user.email])
        # Rendered straight from the Jinja env: this runs in the sweeper
        # thread, outside any request, where the app's context processors
        # (current_user, themes...) have nothing to work with.
        env = current_app.jinja_env
        msg.body = env.get_template('alert/email/alert_email.txt').render(**ctx)
        msg.html = env.get_template('alert/email/alert_email.html').render(**ctx)
        mail.send(msg)
    except Exception as e:
        print(f'[alert_core] alert email to user {user.id} failed: {e}')
        return False

    AlertMatch.query.filter(AlertMatch.id.in_(match_ids)).update({'emailed_at': now}, synchronize_session=False)
    for section in sections:
        section['alert'].last_emailed_at = now
    db.session.commit()
    return True


# ─── Detail page data ────────────────────────────────────────────────────────

def get_alert_matches(alert, page=1, per_page=20):
    pagination = (AlertMatch.query.filter_by(alert_id=alert.id)
                  .order_by(AlertMatch.created_at.desc())
                  .paginate(page=page, per_page=per_page, error_out=False))
    items = []
    for m in pagination.items:
        label, link = _object_label(m.object_type, m.object_id)
        items.append({
            'id': m.id, 'object_type': m.object_type, 'object_id': m.object_id, 'event': m.event,
            'label': label, 'link': link, 'matched_on': m.matched_on or [],
            'created_at': m.created_at.isoformat() if m.created_at else None,
            'seen': m.seen_at is not None,
        })
    return {'items': items, 'total': pagination.total, 'total_pages': pagination.pages}


def get_alert_activity(alert, days=30):
    """Matches per day over the last `days` days, ChartViewer-shaped."""
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=days - 1)).date()
    rows = (db.session.query(func.date(AlertMatch.created_at), func.count(AlertMatch.id))
            .filter(AlertMatch.alert_id == alert.id, AlertMatch.created_at >= since)
            .group_by(func.date(AlertMatch.created_at)).all())
    per_day = {str(d): n for d, n in rows}
    categories = [str(since + datetime.timedelta(days=i)) for i in range(days)]
    return {'categories': categories,
            'series': [{'name': 'Matches', 'values': [per_day.get(c, 0) for c in categories]}]}
