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


# Jobs that clone into, or read from, the clone cache — clearing it under them
# would break them mid-run.
GIT_JOB_TYPES = ('github_import', 'github_repo_resync', 'github_repo_branch_backfill',
                 'github_proposal_bulk_import', 'github_sync_schedule_run', 'delete_github_rules',
                 'git_cache_pull')


@git_settings_blueprint.route('/rule/github/settings/cache', methods=['GET'])
def repo_cache():
    from app.features.rule.rule_format.utils_format.utils_import_update import repo_cache_stats
    return jsonify(repo_cache_stats())


@git_settings_blueprint.route('/rule/github/settings/cache/clear', methods=['POST'])
def clear_repo_cache():
    """Delete the local clones kept after imports / updates (re-cloned when needed)."""
    from app.core.db_class.job import BackgroundJob
    from app.features.rule.rule_format.utils_format.utils_import_update import clear_repo_cache as clear
    busy = BackgroundJob.query.filter(BackgroundJob.job_type.in_(GIT_JOB_TYPES),
                                      BackgroundJob.status.in_(('pending', 'running', 'paused'))).count()
    if busy:
        return jsonify({'success': False,
                        'message': f'{busy} Git job(s) running, waiting or paused — try again once they are done.'}), 409
    removed = clear()
    if removed is None:
        return jsonify({'success': False,
                        'message': 'A Git import or update is using the cache right now — try again once it is done.'}), 409
    log_activity('github.cache_cleared', f"Cleared the git clone cache ({removed['repos']} clones)",
                 extra=removed, is_public=False, icon='fa-solid fa-broom')
    return jsonify({'success': True, 'removed': removed,
                    'message': f"Cache cleared — {removed['repos']} clone(s) removed."})


@git_settings_blueprint.route('/rule/github/settings/cache/pull', methods=['POST'])
def pull_repo_cache():
    """`git pull` every cached clone, as a background job (progress on its job page)."""
    from app.core.db_class.job import BackgroundJob
    from app.features.jobs import jobs_core
    running = BackgroundJob.query.filter(BackgroundJob.job_type == 'git_cache_pull',
                                         BackgroundJob.status.in_(('pending', 'running'))).first()
    if running:
        return jsonify({'success': True, 'job_uuid': running.uuid, 'message': 'A pull is already running.'})
    job = jobs_core.create_job('git_cache_pull', {}, 'Git pull — every cached clone', current_user.id)
    if job is None:
        return jsonify({'success': False, 'message': 'Could not start the pull.'}), 500
    log_activity('github.cache_pull', 'Started a git pull of every cached clone',
                 extra={'job_uuid': job.uuid}, is_public=False, icon='fa-solid fa-code-pull-request')
    return jsonify({'success': True, 'job_uuid': job.uuid, 'message': 'Pull started — follow it on the job page.'})
