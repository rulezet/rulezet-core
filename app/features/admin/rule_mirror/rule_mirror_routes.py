"""
rule_mirror_routes.py — admin-only settings page for the Rule Git Mirror
(see docs/design/rule_git_mirror.md). Manual "run now" reuses the existing
BackgroundJob pipeline directly (register_handler('rule_git_mirror_sync') in
job_handlers.py) — the same job type is also schedulable recurring through
the generic Admin Task Scheduler (task_types.py), this page is just for the
feature's own enable/repo/token settings, which the Task Scheduler has no
notion of.
"""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.features.admin.rule_mirror import rule_mirror_core as RuleMirrorModel
from app.features.jobs.jobs_core import create_job

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
    config = RuleMirrorModel.get_config()
    return render_template('admin/rule_mirror.html', config=config)


@rule_mirror_blueprint.route('/admin/rule_mirror/how-it-works', methods=['GET'])
def how_it_works():
    return render_template('admin/rule_mirror_how_it_works.html')


@rule_mirror_blueprint.route('/admin/rule_mirror/update', methods=['POST'])
def update_settings():
    data = request.get_json(silent=True) or {}
    config = RuleMirrorModel.update_config(
        user_id=current_user.id,
        enabled=bool(data.get('enabled')) if 'enabled' in data else None,
        repo_url=data.get('repo_url'),
        github_token=data.get('github_token'),
        branch=data.get('branch'),
    )
    return jsonify({'success': True, 'config': config.to_json()})


@rule_mirror_blueprint.route('/admin/rule_mirror/run_now', methods=['POST'])
def run_now():
    config = RuleMirrorModel.get_config()
    if not config.enabled:
        return jsonify({'success': False, 'message': 'Enable the Rule Git Mirror first.'}), 400
    if not config.repo_url or not config.github_token:
        return jsonify({'success': False, 'message': 'Set a repository URL and token first.'}), 400

    # A run is already a BackgroundJob like everything else — reuse the
    # same handler the Task Scheduler would call on a recurring schedule.
    job = create_job(
        job_type='rule_git_mirror_sync',
        payload={},
        label='Rule Git Mirror — manual sync',
        created_by=current_user.id,
    )
    return jsonify({'success': True, 'job_uuid': job.uuid}), 201
