"""app_settings_routes.py — the admin Configuration page (/admin/configuration):
every value written in the code, and the ones an admin can change
(see app/core/utils/app_settings.py and hardcoded_inventory.py). Admin only."""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.core.utils import app_settings, hardcoded_inventory
from app.core.utils.activity_log import log_activity

app_settings_blueprint = Blueprint('app_settings', __name__)


@app_settings_blueprint.before_request
def _require_admin():
    if not current_user.is_authenticated:
        return redirect(url_for('account.login'))
    if not current_user.is_admin():
        abort(403)


@app_settings_blueprint.route('/admin/configuration', methods=['GET'])
def configuration_page():
    return render_template('admin/app_settings.html')


@app_settings_blueprint.route('/admin/configuration/data', methods=['GET'])
def configuration_data():
    return jsonify({
        'settings': app_settings.list_settings(),
        'constants': hardcoded_inventory.list_constants(),
        'data_files': hardcoded_inventory.list_data_files(),
    })


@app_settings_blueprint.route('/admin/configuration/<path:key>', methods=['POST'])
def save_setting(key):
    if key not in {s['key'] for s in app_settings.list_settings()}:
        return jsonify({'success': False, 'message': f"Unknown setting '{key}'."}), 404
    data = request.get_json(silent=True) or {}
    if 'value' not in data:
        return jsonify({'success': False, 'message': "Missing 'value'."}), 400
    error = app_settings.validate(key, data['value'])
    if error:
        return jsonify({'success': False, 'message': error}), 400
    app_settings.set_setting(key, data['value'], user_id=current_user.id)
    log_activity('admin.setting_changed', f"Changed setting '{key}'",
                 extra={'key': key}, is_public=False, icon='fa-solid fa-sliders')
    return jsonify({'success': True, 'message': 'Saved.'})


@app_settings_blueprint.route('/admin/configuration/<path:key>/reset', methods=['POST'])
def reset_setting(key):
    if key not in {s['key'] for s in app_settings.list_settings()}:
        return jsonify({'success': False, 'message': f"Unknown setting '{key}'."}), 404
    app_settings.reset_setting(key, user_id=current_user.id)
    log_activity('admin.setting_reset', f"Reset setting '{key}' to its default",
                 extra={'key': key}, is_public=False, icon='fa-solid fa-rotate-left')
    return jsonify({'success': True, 'message': 'Back to the default value.'})


@app_settings_blueprint.route('/admin/configuration/<path:key>/history', methods=['GET'])
def setting_history(key):
    if key not in {s['key'] for s in app_settings.list_settings()}:
        return jsonify({'success': False, 'message': f"Unknown setting '{key}'."}), 404
    return jsonify({'success': True, 'history': app_settings.setting_history(key)})


@app_settings_blueprint.route('/admin/configuration/<path:key>/restore/<int:history_id>', methods=['POST'])
def restore_setting_version(key, history_id):
    if not app_settings.restore_version(key, history_id, user_id=current_user.id):
        return jsonify({'success': False, 'message': 'Unknown version.'}), 404
    log_activity('admin.setting_restored', f"Restored an earlier version of setting '{key}'",
                 extra={'key': key, 'history_id': history_id}, is_public=False, icon='fa-solid fa-clock-rotate-left')
    return jsonify({'success': True, 'message': 'Version restored.'})


@app_settings_blueprint.route('/admin/configuration/<path:key>/accept_merge', methods=['POST'])
def accept_setting_merge(key):
    if key not in {s['key'] for s in app_settings.list_settings()}:
        return jsonify({'success': False, 'message': f"Unknown setting '{key}'."}), 404
    app_settings.accept_merge(key, user_id=current_user.id)
    log_activity('admin.setting_merged', f"Accepted the merge of setting '{key}' with its updated file",
                 extra={'key': key}, is_public=False, icon='fa-solid fa-code-merge')
    return jsonify({'success': True, 'message': 'Merge accepted.'})


@app_settings_blueprint.route('/admin/configuration/data_file', methods=['GET'])
def read_data_file():
    """Content of one data file — only a file the inventory lists, never an
    arbitrary path."""
    import os
    rel = request.args.get('file', '')
    if rel not in {f['file'] for f in hardcoded_inventory.list_data_files()}:
        return jsonify({'success': False, 'message': 'Unknown data file.'}), 404
    path = os.path.join(hardcoded_inventory.REPO_DIR, rel)
    with open(path, encoding='utf-8', errors='replace') as f:
        content = f.read(500_000)
    return jsonify({'success': True, 'file': rel, 'content': content})
