"""git_settings_routes.py — Git tokens & hosts (/rule/github/settings): the four
.env settings the Git features need (GITHUB_TOKEN, GITHUB_HOST, GIT_HOSTS,
GIT_HOST_TOKENS), editable by admins and Git Managers (github.manage) without
giving them the whole Admin → Settings page. Tokens are never sent back to the
browser — only whether one is set and for which hosts."""
import os

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for, current_app
from flask_login import current_user

from app.core.utils.activity_log import log_activity

git_settings_blueprint = Blueprint('git_settings', __name__)

GIT_KEYS = ('GITHUB_TOKEN', 'GITHUB_HOST', 'GIT_HOSTS', 'GIT_HOST_TOKENS')
SECRET_KEYS = ('GITHUB_TOKEN', 'GIT_HOST_TOKENS')


@git_settings_blueprint.before_request
def _require_git_manager():
    if not current_user.is_authenticated:
        return redirect(url_for('account.login'))
    if not (current_user.is_admin() or current_user.has_permission('github.manage')):
        abort(403)


@git_settings_blueprint.route('/rule/github/settings', methods=['GET'])
def git_settings_page():
    return render_template('rule/url_github/git_settings.html')


@git_settings_blueprint.route('/rule/github/settings/data', methods=['GET'])
def git_settings_data():
    from app.features.rule.rule_format.utils_format.git_provider import (
        _parse_host_map, configured_hosts, detect_provider,
    )
    return jsonify({
        'github_token_set': bool(os.environ.get('GITHUB_TOKEN')),
        'github_host': os.environ.get('GITHUB_HOST') or 'github.com',
        'git_hosts': os.environ.get('GIT_HOSTS') or '',
        # Hosts only — never the tokens themselves.
        'git_token_hosts': sorted(_parse_host_map(os.environ.get('GIT_HOST_TOKENS'))),
        'hosts_detected': [{'host': h, 'provider': detect_provider(h)} for h in sorted(configured_hosts())],
    })


@git_settings_blueprint.route('/rule/github/settings/save', methods=['POST'])
def git_settings_save():
    from app.features.admin import admin_core as AdminModel
    data = request.get_json(silent=True) or {}
    key = str(data.get('key', '')).strip()
    value = str(data.get('value', '')).strip()
    if key not in GIT_KEYS:
        return jsonify({'success': False, 'message': 'Only the Git settings can be changed here.'}), 400
    if len(value) > 4000 or '\n' in value or '\r' in value:
        return jsonify({'success': False, 'message': 'Invalid value.'}), 400
    if not AdminModel.write_env_value(key, value):
        return jsonify({'success': False, 'message': 'Could not write the setting.'}), 500
    os.environ[key] = value               # applied at once, read straight from os.environ
    current_app.config[key] = value
    log_activity('github.settings_changed', f"Updated {key} (Git tokens & hosts)",
                 extra={'key': key, 'secret': key in SECRET_KEYS}, is_public=False, icon='fa-solid fa-key')
    return jsonify({'success': True, 'message': 'Saved and applied.'})


@git_settings_blueprint.route('/rule/github/settings/test_github_token', methods=['POST'])
def test_github_token():
    """Is the GitHub token accepted, and how much API quota is left?"""
    from app.features.rule.rule_format.utils_format.utils_import_update import get_github_rate_limit_status
    return jsonify(get_github_rate_limit_status())
