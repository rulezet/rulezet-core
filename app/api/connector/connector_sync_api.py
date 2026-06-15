"""
connector_sync_api.py — Sync endpoints exposed BY this instance TO remote connectors.

These endpoints are what other Rulezet instances call when they pull from us.
Authentication uses the standard X-API-KEY header (same as private API).
"""

import json
import os
import datetime
import logging
from collections import defaultdict

from flask import request
from flask_restx import Namespace, Resource
from sqlalchemy import or_, func

from app.core.db_class.db import Rule, Bundle, Tag, RuleTagAssociation, BundleTagAssociation, RuleUpdateHistory

logger = logging.getLogger(__name__)


def _log_pull_event(rules_total: int) -> None:
    """Record one row in remote_pull_log. Never raises — sync must not fail because of logging."""
    try:
        from app import db
        from app.core.db_class.db import RemotePullLog
        ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or '').split(',')[0].strip()
        entry = RemotePullLog(
            instance_uuid=request.headers.get('X-Rulezet-Instance-UUID') or None,
            instance_url=request.headers.get('X-Rulezet-Instance-URL') or None,
            ip_address=ip or None,
            rules_total=rules_total,
            created_at=datetime.datetime.utcnow(),
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as exc:
        logger.debug("_log_pull_event failed (non-fatal): %s", exc)

sync_ns = Namespace(
    "Sync 🔗",
    description="Federation sync endpoints — used by remote connectors to pull content from this instance."
)

PER_PAGE_MAX = 2000


def _since_dt(since_str: str | None) -> datetime.datetime:
    if not since_str:
        return datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    try:
        return datetime.datetime.fromisoformat(since_str.replace('Z', '+00:00'))
    except ValueError:
        return datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def _batch_load_tags(rule_ids: list) -> dict:
    """Return {rule_id: [tag_name, ...]} for all given rule IDs in a single query."""
    if not rule_ids:
        return {}
    from app import db
    rows = (db.session.query(RuleTagAssociation.rule_id, Tag.name)
            .join(Tag, RuleTagAssociation.tag_id == Tag.id)
            .filter(RuleTagAssociation.rule_id.in_(rule_ids))
            .all())
    result = defaultdict(list)
    for rule_id, name in rows:
        result[rule_id].append(name)
    return dict(result)


def _batch_load_history(rule_ids: list) -> dict:
    """Return {rule_id: [RuleUpdateHistory, ...]} for all given rule IDs in a single query."""
    if not rule_ids:
        return {}
    rows = (RuleUpdateHistory.query
            .filter(RuleUpdateHistory.rule_id.in_(rule_ids))
            .order_by(RuleUpdateHistory.rule_id, RuleUpdateHistory.analyzed_at.asc())
            .all())
    result = defaultdict(list)
    for h in rows:
        result[h.rule_id].append(h)
    return dict(result)


def _rule_to_sync_json(rule: Rule,
                       preloaded_tags: list = None,
                       preloaded_history: list = None) -> dict:
    # Use preloaded data when available — eliminates N+1 queries on large pages.
    if preloaded_tags is not None:
        tags = preloaded_tags
    else:
        tags = [a.tag.name for a in
                RuleTagAssociation.query.filter_by(rule_id=rule.id).all()
                if a.tag]

    if preloaded_history is not None:
        hist_rows = preloaded_history
    else:
        hist_rows = (rule.rule_update_history
                     .order_by(RuleUpdateHistory.analyzed_at.asc())
                     .all())

    history = [
        {
            'old_content':   h.old_content,
            'new_content':   h.new_content,
            'message':       h.message,
            'success':       h.success,
            'analyzed_at':   h.analyzed_at.isoformat() if h.analyzed_at else None,
            'manuel_submit': h.manuel_submit or False,
        }
        for h in hist_rows
    ]
    try:
        cve_ids = json.loads(rule.cve_id) if rule.cve_id else []
    except (TypeError, ValueError):
        cve_ids = [rule.cve_id] if rule.cve_id else []

    return {
        'uuid':           rule.remote_rule_uuid or rule.uuid,
        'format':         rule.format,
        'title':          rule.title,
        'description':    rule.description,
        'to_string':      rule.to_string,
        'author':         rule.author,
        'version':        rule.version,
        'license':        rule.license,
        'source':         rule.source,
        'tags':           tags,
        'cve_ids':        cve_ids,
        'last_modif':     rule.last_modif.isoformat() if rule.last_modif else None,
        'created_at':     rule.creation_date.isoformat() if rule.creation_date else None,
        'update_history': history,
    }


def _bundle_to_sync_json(bundle: Bundle) -> dict:
    rule_uuids = [
        (a.rule.remote_rule_uuid or a.rule.uuid)
        for a in bundle.rules_assoc.all()
        if a.rule and not a.rule.is_deleted
    ]
    tags = [a.tag.name for a in
            BundleTagAssociation.query.filter_by(bundle_id=bundle.id).all()
            if a.tag]
    try:
        vuln_ids = json.loads(bundle.vulnerability_identifiers) if bundle.vulnerability_identifiers else []
    except (TypeError, ValueError):
        vuln_ids = []
    return {
        'uuid':                    bundle.uuid,
        'name':                    bundle.name,
        'description':             bundle.description,
        'rules':                   rule_uuids,
        'tags':                    tags,
        'vulnerability_identifiers': vuln_ids,
        'updated_at':              bundle.updated_at.isoformat() if bundle.updated_at else None,
        'created_at':              bundle.created_at.isoformat() if bundle.created_at else None,
    }


def _apply_rule_filters(query, params: dict):
    """Apply all supported filter parameters to a Rule query.

    params keys (all optional):
        since_dt   — datetime (already stripped of tzinfo), applied with NULL-safe OR
        date_from  — ISO date string (strict lower bound — NULLs excluded)
        date_to    — ISO date string (strict upper bound)
        formats    — comma-separated format names (OR match)
        author     — comma-separated author substrings (OR match)
        license    — comma-separated license substrings (OR match)
        tags       — comma-separated tag names
        tag_mode   — 'OR' (any of) | 'AND' (all of)
        tag_exclude— 'true' / 'false' — flip the tag condition
        cve        — comma-separated CVE IDs (OR match in JSON field)
    """
    since_dt    = params.get('since_dt')
    date_from   = params.get('date_from', '').strip()
    date_to     = params.get('date_to', '').strip()
    formats     = params.get('formats', '').strip()
    author      = params.get('author', '').strip()
    license_p   = params.get('license', '').strip()
    tags_p      = params.get('tags', '').strip()
    tag_mode    = (params.get('tag_mode', 'OR') or 'OR').upper()
    tag_exclude = (params.get('tag_exclude', 'false') or 'false').lower() == 'true'
    cve_p       = params.get('cve', '').strip()

    # ── Date range ────────────────────────────────────────────────────────────
    # date_from is a strict lower bound (excludes NULLs).
    # When only since_dt is set, NULLs are included (backward-compat default).
    if date_from:
        try:
            df = datetime.datetime.fromisoformat(date_from).replace(tzinfo=None)
            # Take the stricter of since_dt and date_from
            lower = df if (since_dt is None or df > since_dt) else since_dt
            query = query.filter(Rule.last_modif >= lower)
        except ValueError:
            if since_dt is not None:
                query = query.filter(or_(Rule.last_modif.is_(None), Rule.last_modif >= since_dt))
    elif since_dt is not None:
        query = query.filter(or_(Rule.last_modif.is_(None), Rule.last_modif >= since_dt))

    if date_to:
        try:
            dt = datetime.datetime.fromisoformat(date_to).replace(tzinfo=None)
            query = query.filter(Rule.last_modif <= dt)
        except ValueError:
            pass

    # ── Format ───────────────────────────────────────────────────────────────
    if formats:
        fmt_list = [f.strip() for f in formats.split(',') if f.strip()]
        if fmt_list:
            query = query.filter(or_(*[Rule.format.ilike(f) for f in fmt_list]))

    # ── Author ───────────────────────────────────────────────────────────────
    if author:
        auth_list = [a.strip() for a in author.split(',') if a.strip()]
        if auth_list:
            query = query.filter(or_(*[Rule.author.ilike(f'%{a}%') for a in auth_list]))

    # ── License ──────────────────────────────────────────────────────────────
    if license_p:
        lic_list = [l.strip() for l in license_p.split(',') if l.strip()]
        if lic_list:
            query = query.filter(or_(*[Rule.license.ilike(f'%{l}%') for l in lic_list]))

    # ── Tags ─────────────────────────────────────────────────────────────────
    if tags_p:
        tag_names = [t.strip().lower() for t in tags_p.split(',') if t.strip()]
        if tag_names:
            matched = Tag.query.filter(func.lower(Tag.name).in_(tag_names)).all()
            tag_ids = [t.id for t in matched]

            if tag_ids:
                if tag_mode == 'AND':
                    # Rule must have ALL specified tags
                    for tid in tag_ids:
                        sub = (RuleTagAssociation.query
                               .filter_by(tag_id=tid)
                               .with_entities(RuleTagAssociation.rule_id)
                               .subquery())
                        if tag_exclude:
                            query = query.filter(Rule.id.notin_(sub))
                        else:
                            query = query.filter(Rule.id.in_(sub))
                else:  # OR
                    sub = (RuleTagAssociation.query
                           .filter(RuleTagAssociation.tag_id.in_(tag_ids))
                           .with_entities(RuleTagAssociation.rule_id)
                           .distinct()
                           .subquery())
                    if tag_exclude:
                        query = query.filter(Rule.id.notin_(sub))
                    else:
                        query = query.filter(Rule.id.in_(sub))
            elif not tag_exclude:
                # Tags requested but none exist locally → no rules can match
                query = query.filter(Rule.id == -1)
            # tag_exclude + no matching tags → nothing to exclude, keep query as-is

    # ── CVE / Vulnerabilities ─────────────────────────────────────────────────
    if cve_p:
        cve_list = [c.strip() for c in cve_p.split(',') if c.strip()]
        if cve_list:
            query = query.filter(or_(*[Rule.cve_id.ilike(f'%"{c}"%') for c in cve_list]))

    return query


# ─── Manifest ─────────────────────────────────────────────────────────────────

@sync_ns.route('/manifest')
class SyncManifest(Resource):
    @sync_ns.doc(description="Returns this instance's identity and capabilities. No auth required.")
    def get(self):
        version_file = os.path.join(os.getcwd(), 'version')
        try:
            with open(version_file) as f:
                ver = f.read().strip()
        except OSError:
            ver = 'unknown'

        return {
            'instance': {
                'name':    os.environ.get('RULEZET_INSTANCE_NAME', 'Rulezet Instance'),
                'version': ver,
                'url':     os.environ.get('FLASK_URL', ''),
            },
            'capabilities': {
                'sync_rules':   True,
                'sync_bundles': True,
            },
        }, 200


# ─── Stats ────────────────────────────────────────────────────────────────────

@sync_ns.route('/stats')
class SyncStats(Resource):
    @sync_ns.doc(description="Returns public rule and bundle counts for this instance. No auth required.")
    def get(self):
        rules_count   = Rule.query.filter(Rule.is_deleted == False).count()
        bundles_count = Bundle.query.filter(Bundle.access == True).count()
        return {
            'rules':   rules_count,
            'bundles': bundles_count,
        }, 200


# ─── Rules ────────────────────────────────────────────────────────────────────

@sync_ns.route('/rules')
class SyncRules(Resource):
    @sync_ns.doc(
        description="Return rules updated since a given timestamp. No authentication required.",
        params={
            'since':       'ISO-8601 datetime — only rules modified after this date are returned',
            'page':        'Page number (default 1)',
            'per_page':    f'Items per page (default 50, max {PER_PAGE_MAX})',
            'uuids':       'Comma-separated rule UUIDs — returns only those specific rules (ignores other params)',
            'count_only':  'Set to "true" to return just the count without rule data (fast preview)',
            'cve':         'Comma-separated CVE IDs — include only rules matching ANY of these CVEs',
            'formats':     'Comma-separated format names — e.g. yara,sigma',
            'author':      'Comma-separated author substrings (OR match)',
            'license':     'Comma-separated license substrings (OR match)',
            'tags':        'Comma-separated tag names (see tag_mode / tag_exclude)',
            'tag_mode':    'OR (default) | AND — how to combine multiple tags',
            'tag_exclude': 'true | false (default) — exclude rules that have the specified tags',
            'date_from':   'ISO date — include only rules modified on or after this date (excludes NULLs)',
            'date_to':     'ISO date — include only rules modified on or before this date',
        }
    )
    def get(self):
        count_only  = request.args.get('count_only', '').lower() in ('1', 'true')

        # ── UUID-targeted fetch (bundle-only pull path) ───────────────────────
        uuids_param = request.args.get('uuids', '').strip()
        if uuids_param:
            uuid_list = [u.strip() for u in uuids_param.split(',') if u.strip()]
            rules = Rule.query.filter(
                Rule.is_deleted == False,
                or_(Rule.uuid.in_(uuid_list), Rule.remote_rule_uuid.in_(uuid_list)),
            ).all()
            rule_ids    = [r.id for r in rules]
            tags_map    = _batch_load_tags(rule_ids)
            history_map = _batch_load_history(rule_ids)
            return {
                'since':    None,
                'page':     1,
                'per_page': len(rules),
                'total':    len(rules),
                'has_more': False,
                'rules':    [_rule_to_sync_json(r, tags_map.get(r.id, []), history_map.get(r.id, [])) for r in rules],
            }, 200

        # ── Standard paginated fetch ──────────────────────────────────────────
        since    = _since_dt(request.args.get('since'))
        page     = max(1, request.args.get('page', 1, type=int))
        per_page = min(PER_PAGE_MAX, max(1, request.args.get('per_page', 50, type=int)))

        filter_params = {
            'since_dt':   since.replace(tzinfo=None),
            'date_from':  request.args.get('date_from', ''),
            'date_to':    request.args.get('date_to', ''),
            'formats':    request.args.get('formats', ''),
            'author':     request.args.get('author', ''),
            'license':    request.args.get('license', ''),
            'tags':       request.args.get('tags', ''),
            'tag_mode':   request.args.get('tag_mode', 'OR'),
            'tag_exclude':request.args.get('tag_exclude', 'false'),
            'cve':        request.args.get('cve', ''),
        }

        query = Rule.query.filter(Rule.is_deleted == False)
        query = _apply_rule_filters(query, filter_params)
        query = query.order_by(Rule.last_modif.asc().nullsfirst())

        total = query.count()

        # count_only — fast preview without fetching rule data
        if count_only:
            return {
                'count': total,
                'cve':   filter_params['cve'],
            }, 200

        rules    = query.offset((page - 1) * per_page).limit(per_page).all()
        has_more = (page * per_page) < total

        # Log pull sessions (page 1 only)
        if page == 1:
            _log_pull_event(total)

        # Batch-load tags and history — eliminates N*2 queries per page
        rule_ids    = [r.id for r in rules]
        tags_map    = _batch_load_tags(rule_ids)
        history_map = _batch_load_history(rule_ids)

        return {
            'since':    since.isoformat(),
            'page':     page,
            'per_page': per_page,
            'total':    total,
            'has_more': has_more,
            'rules':    [_rule_to_sync_json(r, tags_map.get(r.id, []), history_map.get(r.id, [])) for r in rules],
        }, 200


# ─── Bundles ──────────────────────────────────────────────────────────────────

@sync_ns.route('/bundles')
class SyncBundles(Resource):
    @sync_ns.doc(
        description="Return public bundles updated since a given timestamp. No authentication required.",
        params={
            'since':    'ISO-8601 datetime',
            'page':     'Page number (default 1)',
            'per_page': f'Items per page (default 50, max {PER_PAGE_MAX})',
        }
    )
    def get(self):
        since    = _since_dt(request.args.get('since'))
        page     = max(1, request.args.get('page', 1, type=int))
        per_page = min(PER_PAGE_MAX, max(1, request.args.get('per_page', 50, type=int)))

        since_dt = since.replace(tzinfo=None)
        query = (Bundle.query
                 .filter(
                     Bundle.access == True,
                     or_(Bundle.updated_at.is_(None), Bundle.updated_at >= since_dt),
                 )
                 .order_by(Bundle.updated_at.asc().nullsfirst()))

        total   = query.count()
        bundles = query.offset((page - 1) * per_page).limit(per_page).all()
        has_more = (page * per_page) < total

        return {
            'since':    since.isoformat(),
            'page':     page,
            'per_page': per_page,
            'total':    total,
            'has_more': has_more,
            'bundles':  [_bundle_to_sync_json(b) for b in bundles],
        }, 200
