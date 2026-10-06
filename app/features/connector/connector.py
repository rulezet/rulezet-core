"""
connector.py — Blueprint for the Connector feature (UI routes).
All DB logic lives in connector_core.py.
Access is restricted to admin users only.
"""

from urllib.parse import urlparse

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import app.features.connector.connector_core as ConnectorModel
from app.core.utils.utils import json_object

connector_blueprint = Blueprint(
    'connector',
    __name__,
    template_folder='templates',
)


@connector_blueprint.before_request
def _require_admin():
    if not current_user.is_authenticated:
        return redirect(url_for('account.login'))
    if not current_user.is_admin():
        abort(403)


# ─── List ─────────────────────────────────────────────────────────────────────

@connector_blueprint.route('/list', methods=['GET'])
def connector_list():
    return render_template('connector/connector_list.html')


@connector_blueprint.route('/how-it-works', methods=['GET'])
def connector_how_it_works():
    return render_template('connector/connector_how_it_works.html')


# ─── CRUD (JSON API used by the Vue app) ──────────────────────────────────────

def _is_self(instance_url: str) -> bool:
    """Return True if instance_url resolves to this very instance (same host AND port)."""
    try:
        remote_netloc = urlparse(instance_url).netloc.lower()
        local_netloc  = request.host.lower()
        return remote_netloc == local_netloc
    except Exception:
        return False


@connector_blueprint.route('/get', methods=['GET'])
def get_connectors():
    connectors = ConnectorModel.get_connectors(current_user.id)
    result = []
    for c in connectors:
        d = c.to_json()
        d['is_self'] = _is_self(c.instance_url)
        result.append(d)
    return jsonify(result), 200


# Text fields of a connector and their column sizes (None = unbounded).
_TEXT_FIELDS = {'name': 255, 'instance_url': 512, 'api_key_outbound': 512, 'icon': 64, 'description': None}
_FLAGS = ('sync_rules', 'sync_bundles', 'is_active')
_OWNER_MODES = ('shadow', 'self')
_CONNECTOR_TYPES = ('rulezet',)


def _valid_remote_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname)
    except ValueError:
        return False


def _connector_fields(data: dict, creating: bool):
    """(fields, error) — the connector fields of a create / update body,
    checked: text that fits its column (NUL characters dropped), real
    booleans, a known owner mode, a non-empty name and an http(s) URL.
    Only the keys present in `data` are returned."""
    fields = {}
    for key, limit in _TEXT_FIELDS.items():
        if key not in data:
            continue
        value = data[key]
        if value is None:
            value = ''
        if not isinstance(value, str):
            return None, f'{key} must be text.'
        value = value.replace('\x00', '').strip()
        if limit and len(value) > limit:
            return None, f'{key} is too long (max {limit} characters).'
        fields[key] = value or None

    for key in ('name', 'instance_url'):
        if (creating or key in data) and not fields.get(key):
            return None, 'Name and URL are required.'
    if fields.get('instance_url') and not _valid_remote_url(fields['instance_url']):
        return None, 'URL must start with http:// or https://'

    for key in _FLAGS:
        if key in data:
            if not isinstance(data[key], bool):
                return None, f'{key} must be true or false.'
            fields[key] = data[key]
    if 'owner_mode' in data:
        if data['owner_mode'] not in _OWNER_MODES:
            return None, f"owner_mode must be one of: {', '.join(_OWNER_MODES)}."
        fields['owner_mode'] = data['owner_mode']
    if creating and 'connector_type' in data:
        if data['connector_type'] not in _CONNECTOR_TYPES:
            return None, f"connector_type must be one of: {', '.join(_CONNECTOR_TYPES)}."
        fields['connector_type'] = data['connector_type']
    return fields, None


@connector_blueprint.route('/create', methods=['POST'])
def create_connector():
    fields, error = _connector_fields(json_object(), creating=True)
    if error:
        return jsonify({'success': False, 'error': error}), 400

    connector = ConnectorModel.create_connector(
        owner_id=current_user.id,
        name=fields['name'],
        instance_url=fields['instance_url'],
        connector_type=fields.get('connector_type', 'rulezet'),
        api_key_outbound=fields.get('api_key_outbound'),
        description=fields.get('description'),
        icon=fields.get('icon'),
        sync_rules=fields.get('sync_rules', True),
        sync_bundles=fields.get('sync_bundles', False),
        owner_mode=fields.get('owner_mode', 'shadow'),
    )
    if not connector:
        return jsonify({'success': False, 'error': 'Could not create connector.'}), 500

    return jsonify({'success': True, 'connector': connector.to_json()}), 200


@connector_blueprint.route('/update/<string:connector_uuid>', methods=['POST'])
def update_connector(connector_uuid):
    connector = ConnectorModel.get_connector_by_uuid(connector_uuid)
    if not connector:
        return jsonify({'success': False, 'error': 'Not found.'}), 404
    if connector.is_system:
        return jsonify({'success': False, 'error': 'System connectors cannot be modified.'}), 403

    fields, error = _connector_fields(json_object(), creating=False)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    ok = ConnectorModel.update_connector(connector, fields)
    return jsonify({'success': ok}), 200 if ok else 500


@connector_blueprint.route('/delete/<string:connector_uuid>', methods=['POST'])
def delete_connector(connector_uuid):
    connector = ConnectorModel.get_connector_by_uuid(connector_uuid)
    if not connector:
        return jsonify({'success': False, 'error': 'Not found.'}), 404
    if connector.is_system:
        return jsonify({'success': False, 'error': 'System connectors cannot be deleted.'}), 403

    ok = ConnectorModel.delete_connector(connector)
    return jsonify({'success': ok}), 200 if ok else 500


# ─── Actions ──────────────────────────────────────────────────────────────────

@connector_blueprint.route('/test/<string:connector_uuid>', methods=['POST'])
def test_connector(connector_uuid):
    connector = ConnectorModel.get_connector_by_uuid(connector_uuid)
    if not connector:
        return jsonify({'success': False, 'error': 'Not found.'}), 404

    ok, msg, stats = ConnectorModel.test_connector(connector)
    return jsonify({'success': ok, 'message': msg, 'stats': stats}), 200


@connector_blueprint.route('/history/<string:connector_uuid>', methods=['GET'])
def connector_history(connector_uuid):
    connector = ConnectorModel.get_connector_by_uuid(connector_uuid)
    if not connector:
        return jsonify({'success': False, 'error': 'Not found.'}), 404
    return jsonify(ConnectorModel.get_connector_history(connector)), 200


@connector_blueprint.route('/import_tag_families', methods=['POST'])
def import_tag_families():
    """Import one or more tag families from the MISP taxonomy/galaxy submodules.

    Body: { "families": ["tlp", "pap", "misp-galaxy:threat-actor", ...] }
    """
    families = json_object().get('families')
    if not families or not isinstance(families, list) or not all(isinstance(f, str) for f in families):
        return jsonify({'success': False, 'error': 'families must be a non-empty list of names.'}), 400

    results = ConnectorModel.import_tag_families(families, current_user)
    all_ok  = all(r['ok'] for r in results)
    return jsonify({'success': True, 'results': results, 'all_ok': all_ok}), 200


@connector_blueprint.route('/preview/<string:connector_uuid>', methods=['GET'])
def preview_connector(connector_uuid):
    """Fetch the count of rules matching a CVE filter on the remote without importing."""
    import requests as http_requests

    connector = ConnectorModel.get_connector_by_uuid(connector_uuid)
    if not connector:
        return jsonify({'success': False, 'error': 'Not found.'}), 404

    cve = request.args.get('cve', '').strip()
    if not cve:
        return jsonify({'success': False, 'error': 'No CVE specified.'}), 400

    headers = {'Accept': 'application/json'}
    if connector.api_key_outbound:
        headers['X-API-KEY'] = connector.api_key_outbound
    try:
        resp = http_requests.get(
            f"{connector.instance_url}/api/sync/rules?cve={cve}&count_only=true",
            headers=headers, timeout=10,
        )
        if resp.status_code == 200:
            data  = resp.json()
            count = data.get('count', data.get('total', 0))
            return jsonify({'success': True, 'count': count, 'cve': cve}), 200
        return jsonify({'success': False, 'error': f'Remote returned HTTP {resp.status_code}'}), 502
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


# Pull filters, in the shape the connector_pull job reads them
# (app/static/js/connector/connectorPullFilter.js builds them).
_TEXT_LIST_FILTERS = ('formats', 'authors', 'attacks')
_GROUP_FILTERS     = ('cves', 'licenses', 'tags')     # [{names: [...], mode, exclude}]
_DATE_FILTERS      = ('date_from', 'date_to')


def _is_text_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _pull_filters(filters):
    """(filters, error) — the filters of a pull request, checked; unknown
    keys are dropped, an empty / missing value means "no filter"."""
    if filters is None:
        return {}, None
    if not isinstance(filters, dict):
        return None, 'filters must be an object.'
    clean = {}
    for key in _TEXT_LIST_FILTERS:
        value = filters.get(key)
        if value is None:
            continue
        if not _is_text_list(value):
            return None, f'filters.{key} must be a list of text values.'
        clean[key] = value
    for key in _GROUP_FILTERS:
        groups = filters.get(key)
        if groups is None:
            continue
        if not isinstance(groups, list):
            return None, f'filters.{key} must be a list.'
        for group in groups:
            if (not isinstance(group, dict) or not _is_text_list(group.get('names'))
                    or not isinstance(group.get('mode', 'OR'), str)
                    or not isinstance(group.get('exclude', False), bool)):
                return None, f'filters.{key} must be a list of {{names, mode, exclude}} groups.'
        clean[key] = groups
    for key in _DATE_FILTERS:
        value = filters.get(key)
        if value is None or value == '':
            continue
        if not isinstance(value, str):
            return None, f'filters.{key} must be a date.'
        clean[key] = value
    return clean, None


@connector_blueprint.route('/pull/<string:connector_uuid>', methods=['POST'])
def pull_connector(connector_uuid):
    connector = ConnectorModel.get_connector_by_uuid(connector_uuid)
    if not connector:
        return jsonify({'success': False, 'error': 'Not found.'}), 404

    if _is_self(connector.instance_url):
        return jsonify({'success': False, 'error': 'Cannot pull from this instance — that would sync with yourself.'}), 400

    if not connector.is_active:
        return jsonify({'success': False, 'error': 'Connector is disabled.'}), 400

    data         = json_object()
    sync_rules   = data.get('sync_rules',   connector.sync_rules)
    sync_bundles = data.get('sync_bundles', connector.sync_bundles)
    if not isinstance(sync_rules, bool) or not isinstance(sync_bundles, bool):
        return jsonify({'success': False, 'error': 'sync_rules and sync_bundles must be true or false.'}), 400
    filters, error = _pull_filters(data.get('filters'))
    if error:
        return jsonify({'success': False, 'error': error}), 400

    if not sync_rules and not sync_bundles:
        return jsonify({'success': False, 'error': 'Nothing to pull — select rules and/or bundles.'}), 400

    job = ConnectorModel.trigger_pull(connector, triggered_by=current_user.id,
                                      sync_rules=sync_rules, sync_bundles=sync_bundles,
                                      filters=filters if filters else None)
    if not job:
        return jsonify({'success': False, 'error': 'Could not queue pull job.'}), 500

    what = ' + '.join(filter(None, ['rules' if sync_rules else '', 'bundles' if sync_bundles else '']))
    return jsonify({
        'success': True,
        'message': f'Pull queued ({what}) as background job.',
        'job_uuid': job.uuid,
    }), 200
