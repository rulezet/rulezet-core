"""
connector.py — Blueprint for the Connector feature (UI routes).
All DB logic lives in connector_core.py.
Access is restricted to admin users only.
"""

from urllib.parse import urlparse

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import app.features.connector.connector_core as ConnectorModel
from app.core.utils.activity_log import log_activity

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


@connector_blueprint.route('/create', methods=['POST'])
def create_connector():
    data = request.get_json() or {}
    name         = (data.get('name') or '').strip()
    instance_url = (data.get('instance_url') or '').strip()
    if not name or not instance_url:
        return jsonify({'success': False, 'error': 'Name and URL are required.'}), 400

    connector = ConnectorModel.create_connector(
        owner_id=current_user.id,
        name=name,
        instance_url=instance_url,
        connector_type=data.get('connector_type', 'rulezet'),
        api_key_outbound=data.get('api_key_outbound') or None,
        description=data.get('description') or None,
        icon=data.get('icon') or None,
        sync_rules=data.get('sync_rules', True),
        sync_bundles=data.get('sync_bundles', False),
        owner_mode=data.get('owner_mode', 'shadow'),
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

    data = request.get_json() or {}
    ok = ConnectorModel.update_connector(connector, data)
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
    data     = request.get_json(silent=True) or {}
    families = data.get('families', [])
    if not families or not isinstance(families, list):
        return jsonify({'success': False, 'error': 'families must be a non-empty list.'}), 400

    results = ConnectorModel.import_tag_families(families, current_user)
    all_ok  = all(r['ok'] for r in results)
    return jsonify({'success': True, 'results': results, 'all_ok': all_ok}), 200


@connector_blueprint.route('/pull/<string:connector_uuid>', methods=['POST'])
def pull_connector(connector_uuid):
    connector = ConnectorModel.get_connector_by_uuid(connector_uuid)
    if not connector:
        return jsonify({'success': False, 'error': 'Not found.'}), 404

    if _is_self(connector.instance_url):
        return jsonify({'success': False, 'error': 'Cannot pull from this instance — that would sync with yourself.'}), 400

    if not connector.is_active:
        return jsonify({'success': False, 'error': 'Connector is disabled.'}), 400

    job = ConnectorModel.trigger_pull(connector, triggered_by=current_user.id)
    if not job:
        return jsonify({'success': False, 'error': 'Could not queue pull job.'}), 500

    return jsonify({
        'success': True,
        'message': 'Pull queued as background job.',
        'job_uuid': job.uuid,
    }), 200
