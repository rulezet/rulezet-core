"""
connector_sync_api.py — Sync endpoints exposed BY this instance TO remote connectors.

These endpoints are what other Rulezet instances call when they pull from us.
Authentication uses the standard X-API-KEY header (same as private API).
"""

import json
import os
import datetime

from flask import request
from flask_restx import Namespace, Resource

from app.core.db_class.db import Rule, Bundle, Tag, RuleTagAssociation, BundleTagAssociation, RuleUpdateHistory

sync_ns = Namespace(
    "Sync 🔗",
    description="Federation sync endpoints — used by remote connectors to pull content from this instance."
)

PER_PAGE_MAX = 500


def _since_dt(since_str: str | None) -> datetime.datetime:
    if not since_str:
        return datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    try:
        return datetime.datetime.fromisoformat(since_str.replace('Z', '+00:00'))
    except ValueError:
        return datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def _rule_to_sync_json(rule: Rule) -> dict:
    tags = [a.tag.name for a in
            RuleTagAssociation.query.filter_by(rule_id=rule.id).all()
            if a.tag]
    history = [
        {
            'old_content':   h.old_content,
            'new_content':   h.new_content,
            'message':       h.message,
            'success':       h.success,
            'analyzed_at':   h.analyzed_at.isoformat() if h.analyzed_at else None,
            'manuel_submit': h.manuel_submit or False,
        }
        for h in (rule.rule_update_history
                  .order_by(RuleUpdateHistory.analyzed_at.asc())
                  .all())
    ]
    # cve_id is stored as a JSON-encoded list or plain string
    try:
        cve_ids = json.loads(rule.cve_id) if rule.cve_id else []
    except (TypeError, ValueError):
        cve_ids = [rule.cve_id] if rule.cve_id else []

    return {
        # canonical identity: keep the origin uuid when this rule was itself
        # pulled from another instance, so identity stays stable across hops
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
            'since':    'ISO-8601 datetime — only rules modified after this date are returned',
            'page':     'Page number (default 1)',
            'per_page': f'Items per page (default 50, max {PER_PAGE_MAX})',
        }
    )
    def get(self):
        since    = _since_dt(request.args.get('since'))
        page     = max(1, request.args.get('page', 1, type=int))
        per_page = min(PER_PAGE_MAX, max(1, request.args.get('per_page', 50, type=int)))

        # Only expose non-deleted, non-connector-imported rules
        query = (Rule.query
                 .filter(
                     Rule.is_deleted == False,
                     Rule.last_modif >= since.replace(tzinfo=None),
                 )
                 .order_by(Rule.last_modif.asc()))

        total    = query.count()
        rules    = query.offset((page - 1) * per_page).limit(per_page).all()
        has_more = (page * per_page) < total

        return {
            'since':    since.isoformat(),
            'page':     page,
            'per_page': per_page,
            'total':    total,
            'has_more': has_more,
            'rules':    [_rule_to_sync_json(r) for r in rules],
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

        query = (Bundle.query
                 .filter(
                     Bundle.access == True,
                     Bundle.updated_at >= since.replace(tzinfo=None),
                 )
                 .order_by(Bundle.updated_at.asc()))

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
