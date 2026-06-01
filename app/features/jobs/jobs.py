"""
jobs.py — Blueprint for background job management.
Routes only. All DB logic in jobs_core.py.
"""

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

import app.features.jobs.jobs_core as JobsModel
from app.core.utils.activity_log import log_activity

jobs_blueprint = Blueprint(
    'jobs',
    __name__,
    template_folder='templates',
)


def _get_job_or_403(job_uuid):
    job = JobsModel.get_job_by_uuid(job_uuid)
    if not job:
        return None, (jsonify({"error": "Job not found."}), 404)
    if job.created_by != current_user.id and not current_user.is_admin():
        return None, (jsonify({"error": "Forbidden."}), 403)
    return job, None


@jobs_blueprint.route('/list', methods=['GET'])
@login_required
def list_jobs():
    return render_template('jobs/list.html')


@jobs_blueprint.route('/get_jobs', methods=['GET'])
@login_required
def get_jobs():
    items, total, page, per_page = JobsModel.get_jobs_for_user(current_user.id, request.args)
    return jsonify({
        "jobs":       [j.to_json() for j in items],
        "total":      total,
        "page":       page,
        "per_page":   per_page,
        "total_pages": max(1, -(-total // per_page)),  # ceil division
    }), 200


@jobs_blueprint.route('/zombies', methods=['GET'])
@login_required
def get_zombies():
    if not current_user.is_admin():
        return jsonify({"error": "Forbidden."}), 403
    zombies = JobsModel.get_zombie_jobs()
    return jsonify([j.to_json() for j in zombies]), 200


@jobs_blueprint.route('/kill_zombies', methods=['POST'])
@login_required
def kill_zombies():
    if not current_user.is_admin():
        return jsonify({"error": "Forbidden."}), 403
    ok, count, msg = JobsModel.kill_all_zombies()
    return jsonify({"message": msg, "killed": count}), 200 if ok else 500


@jobs_blueprint.route('/status/<string:job_uuid>', methods=['GET'])
@login_required
def job_status(job_uuid):
    job, err = _get_job_or_403(job_uuid)
    if err: return err
    return jsonify(job.to_json()), 200


@jobs_blueprint.route('/logs/<string:job_uuid>', methods=['GET'])
@login_required
def job_logs(job_uuid):
    """Return log lines for a job. Pass ?since_id=N to get only new lines."""
    job, err = _get_job_or_403(job_uuid)
    if err: return err
    since_id = request.args.get('since_id', 0, type=int)
    logs = JobsModel.get_job_logs(job_uuid, since_id=since_id)
    return jsonify([l.to_json() for l in logs]), 200


@jobs_blueprint.route('/create', methods=['POST'])
@login_required
def create_job():
    data     = request.json or {}
    job_type = data.get('job_type')
    payload  = data.get('payload', {})
    label    = data.get('label', job_type)

    if not job_type:
        return jsonify({"error": "job_type is required."}), 400

    payload['user_id'] = current_user.id

    job = JobsModel.create_job(
        job_type=job_type,
        payload=payload,
        label=label,
        created_by=current_user.id,
    )
    if not job:
        return jsonify({"error": "Failed to create job."}), 500

    log_activity("job.create", f"Created job '{label}' (type={job_type})",
                 target_type="job", target_id=job.id, target_uuid=job.uuid)
    return jsonify({"job": job.to_json(), "message": "Job queued."}), 200


@jobs_blueprint.route('/cancel/<string:job_uuid>', methods=['POST'])
@login_required
def cancel_job(job_uuid):
    job, err = _get_job_or_403(job_uuid)
    if err: return err
    ok, msg = JobsModel.cancel_job(job)
    if ok:
        log_activity("job.cancel", f"Cancelled job '{job.label}' (uuid={job_uuid})",
                     target_type="job", target_id=job.id, target_uuid=job_uuid)
    return jsonify({"message": msg}), 200 if ok else 400


@jobs_blueprint.route('/pause/<string:job_uuid>', methods=['POST'])
@login_required
def pause_job(job_uuid):
    job, err = _get_job_or_403(job_uuid)
    if err: return err
    ok, msg = JobsModel.pause_job(job)
    if ok:
        log_activity("job.pause", f"Paused job '{job.label}' (uuid={job_uuid})",
                     target_type="job", target_id=job.id, target_uuid=job_uuid)
    return jsonify({"message": msg}), 200 if ok else 400


@jobs_blueprint.route('/resume/<string:job_uuid>', methods=['POST'])
@login_required
def resume_job(job_uuid):
    job, err = _get_job_or_403(job_uuid)
    if err: return err
    ok, msg = JobsModel.resume_job(job)
    if ok:
        log_activity("job.resume", f"Resumed job '{job.label}' (uuid={job_uuid})",
                     target_type="job", target_id=job.id, target_uuid=job_uuid)
    return jsonify({"message": msg}), 200 if ok else 400


@jobs_blueprint.route('/delete/<string:job_uuid>', methods=['POST'])
@login_required
def delete_job(job_uuid):
    job, err = _get_job_or_403(job_uuid)
    if err: return err
    job_label = job.label
    ok, msg = JobsModel.delete_job(job)
    if ok:
        log_activity("job.delete", f"Deleted job '{job_label}' (uuid={job_uuid})",
                     extra={"job_uuid": job_uuid})
    return jsonify({"message": msg}), 200 if ok else 400