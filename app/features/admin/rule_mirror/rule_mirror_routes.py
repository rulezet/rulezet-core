"""
rule_mirror_routes.py — admin-only settings for Rulesets / Rule Git Mirror
(see docs/design/rule_git_mirror.md). An instance can configure several
mirror targets (RuleMirrorConfig rows); each one's "Run now" reuses the
existing BackgroundJob pipeline directly (register_handler('rule_git_mirror_sync')
in job_handlers.py) — the same job type is also schedulable recurring
through the generic Admin Task Scheduler (task_types.py), which syncs every
currently-enabled config when it isn't targeting one in particular.
"""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.features.admin.rule_mirror import rule_mirror_core as RuleMirrorModel
from app.features.jobs.jobs_core import create_job
from app.core.utils.activity_log import log_activity

rule_mirror_blueprint = Blueprint(
    'rule_mirror',
    __name__,
    template_folder='templates',
)


@rule_mirror_blueprint.before_request
def _require_admin():
    if not current_user.is_authenticated:
        return redirect(url_for('account.login'))
    if not current_user.is_admin():
        abort(403)


@rule_mirror_blueprint.route('/admin/rule_mirror', methods=['GET'])
def settings_page():
    return render_template('admin/rule_mirror.html')


@rule_mirror_blueprint.route('/admin/rule_mirror/how-it-works', methods=['GET'])
def how_it_works():
    return render_template('admin/rule_mirror_how_it_works.html')


# ─── CRUD (JSON API used by the Vue app) ──────────────────────────────────────

@rule_mirror_blueprint.route('/admin/rule_mirror/list', methods=['GET'])
def list_configs():
    configs = RuleMirrorModel.list_configs()
    return jsonify([c.to_json() for c in configs]), 200


@rule_mirror_blueprint.route('/admin/rule_mirror/create', methods=['POST'])
def create_config():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    repo_url = (data.get('repo_url') or '').strip()
    github_token = (data.get('github_token') or '').strip()

    if not name or not repo_url or not github_token:
        return jsonify({'success': False, 'message': 'Name, repository URL and token are all required.'}), 400

    config = RuleMirrorModel.create_config(
        user_id=current_user.id,
        name=name,
        enabled=bool(data.get('enabled')),
        repo_url=repo_url,
        github_token=github_token,
        branch=data.get('branch'),
    )
    return jsonify({'success': True, 'config': config.to_json()}), 201


@rule_mirror_blueprint.route('/admin/rule_mirror/update/<string:config_uuid>', methods=['POST'])
def update_config(config_uuid):
    config = RuleMirrorModel.get_config_by_uuid(config_uuid)
    if not config:
        return jsonify({'success': False, 'message': 'Not found.'}), 404

    data = request.get_json(silent=True) or {}
    config = RuleMirrorModel.update_config(
        config,
        user_id=current_user.id,
        name=data.get('name'),
        enabled=bool(data.get('enabled')) if 'enabled' in data else None,
        repo_url=data.get('repo_url'),
        github_token=data.get('github_token'),
        branch=data.get('branch'),
    )
    return jsonify({'success': True, 'config': config.to_json()}), 200


@rule_mirror_blueprint.route('/admin/rule_mirror/delete/<string:config_uuid>', methods=['POST'])
def delete_config(config_uuid):
    config = RuleMirrorModel.get_config_by_uuid(config_uuid)
    if not config:
        return jsonify({'success': False, 'message': 'Not found.'}), 404

    RuleMirrorModel.delete_config(config)
    return jsonify({'success': True}), 200


@rule_mirror_blueprint.route('/admin/rule_mirror/history/<string:config_uuid>', methods=['GET'])
def config_history(config_uuid):
    config = RuleMirrorModel.get_config_by_uuid(config_uuid)
    if not config:
        return jsonify({'success': False, 'message': 'Not found.'}), 404
    return jsonify(RuleMirrorModel.get_config_history(config)), 200


@rule_mirror_blueprint.route('/admin/rule_mirror/test/<string:config_uuid>', methods=['POST'])
def test_config(config_uuid):
    config = RuleMirrorModel.get_config_by_uuid(config_uuid)
    if not config:
        return jsonify({'success': False, 'message': 'Not found.'}), 404

    ok, message = RuleMirrorModel.test_config(config)
    return jsonify({'success': ok, 'message': message, 'config': config.to_json()}), 200


@rule_mirror_blueprint.route('/admin/rule_mirror/run_now/<string:config_uuid>', methods=['POST'])
def run_now(config_uuid):
    config = RuleMirrorModel.get_config_by_uuid(config_uuid)
    if not config:
        return jsonify({'success': False, 'message': 'Not found.'}), 404
    if not config.enabled:
        return jsonify({'success': False, 'message': f"Enable '{config.name}' first."}), 400
    if not config.repo_url or not config.github_token:
        return jsonify({'success': False, 'message': f"Set a repository URL and token for '{config.name}' first."}), 400

    # Mandatory pre-flight: always re-test the connection right before
    # launching a sync, rather than trusting a possibly-stale earlier
    # result (e.g. the token could have been revoked on GitHub since).
    # "Run now" can never skip this — there's no path to create_job below
    # without a test having just passed.
    ok, message = RuleMirrorModel.test_config(config)
    if not ok:
        return jsonify({'success': False, 'message': f"Connection test failed: {message}", 'config': config.to_json()}), 400

    # A run is already a BackgroundJob like everything else — reuse the
    # same handler the Task Scheduler would call on a recurring schedule.
    job = create_job(
        job_type='rule_git_mirror_sync',
        payload={'config_id': config.id},
        label=f"Rulesets — sync ({config.name})",
        created_by=current_user.id,
    )
    log_activity(
        'admin.rule_mirror_run_triggered',
        f"Rulesets sync manually triggered for '{config.name}'",
        target_type='rule_mirror_config', target_id=config.id,
        extra={'job_uuid': job.uuid}, is_public=False,
    )
    return jsonify({'success': True, 'job_uuid': job.uuid, 'config': config.to_json()}), 201
