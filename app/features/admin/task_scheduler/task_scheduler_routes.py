"""
task_scheduler_routes.py — admin-only Blueprint for the generalized Admin
Task Scheduler (CRUD + registry + pickers + manual run). Tasks always live
inside a Workflow (create the workflow first, then assign tasks into it —
modeled on a GitHub Actions workflow file containing several jobs). All
DB/business logic lives in task_scheduler_core.py; execution happens
through the existing generic BackgroundJob pipeline (job_worker.py), exactly
like every other admin bulk action. See docs/design/admin_task_scheduler.md.
"""
from flask import Blueprint, Response, abort, current_app, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app.core.db_class.connector import Connector
from app.core.db_class.rule import Rule
from app.core.utils.activity_log import log_activity
from app.features.admin.task_scheduler import task_scheduler_core as TaskSchedulerModel
from app.features.admin.task_scheduler.task_types import serialize_task_types
from app.features.admin.task_scheduler import workflow_spec as WorkflowSpec
from app.features.admin.task_scheduler import workflow_notes as WorkflowNotes
from app.features.rule.rule_core import _active

task_scheduler_blueprint = Blueprint(
    'task_scheduler',
    __name__,
    template_folder='templates',
)


@task_scheduler_blueprint.before_request
def _require_admin():
    if not current_user.is_authenticated:
        return redirect(url_for('account.login'))
    if not current_user.is_admin():
        abort(403)


def _workflow_or_none(workflow_uuid):
    return TaskSchedulerModel.get_workflow_by_uuid(workflow_uuid) if workflow_uuid else None


@task_scheduler_blueprint.route('/', methods=['GET'])
def admin_panel():
    # Legacy '?workflow=<uuid>' links redirect to the canonical path-based
    # URL below, which is the one that actually 404s for a bad/deleted uuid.
    workflow_uuid = request.args.get('workflow')
    if workflow_uuid:
        return redirect(url_for('task_scheduler.admin_panel_workflow', workflow_uuid=workflow_uuid))
    return render_template('admin/task_scheduler.html', initial_workflow=None)


@task_scheduler_blueprint.route('/<workflow_uuid>', methods=['GET'])
def admin_panel_workflow(workflow_uuid):
    workflow = _workflow_or_none(workflow_uuid)
    if not workflow:
        abort(404)
    return render_template('admin/task_scheduler.html', initial_workflow=workflow.to_json())


@task_scheduler_blueprint.route('/types', methods=['GET'])
def task_types():
    return jsonify(serialize_task_types()), 200


@task_scheduler_blueprint.route('/formats', methods=['GET'])
def formats():
    """Distinct rule formats — feeds the 'format_filter_only' target picker."""
    rows = _active().with_entities(Rule.format).distinct().all()
    values = sorted({r[0] for r in rows if r[0]})
    return jsonify({"formats": values}), 200


@task_scheduler_blueprint.route('/connectors', methods=['GET'])
def connectors():
    """Feeds the 'connector_select' target picker — badges is_system so an
    admin can tell an official-instance connector from a custom one."""
    rows = Connector.query.order_by(Connector.name.asc()).all()
    return jsonify({
        "connectors": [
            {"id": c.id, "name": c.name, "is_system": c.is_system, "is_active": c.is_active,
             "instance_url": c.instance_url}
            for c in rows
        ]
    }), 200


@task_scheduler_blueprint.route('/field_configs', methods=['GET'])
def field_configs():
    """Saved Field Parser / Platform Tags configs (from the Bulk Parse
    Fields page) — feeds the 'saved_config' option of those task types."""
    from app.features.rule.field_parser_core import get_all_configs
    config_type = request.args.get('type', 'field_parser', type=str)
    if config_type not in ('field_parser', 'platform_tags'):
        return jsonify({"message": "Unknown config type.", "toast_class": "danger-subtle"}), 400
    return jsonify({
        "configs": [{"id": c.id, "name": c.name} for c in get_all_configs(config_type=config_type)]
    }), 200


@task_scheduler_blueprint.route('/config', methods=['GET'])
def config():
    """Feeds the workflow modal's notification section — disable those
    checkboxes outright when this instance has no mail server configured,
    rather than letting an admin turn on a setting that can never fire."""
    return jsonify({"mail_configured": bool(current_app.config.get('MAIL_SERVER'))}), 200


# ─── Workflows (JSON API used by the Vue app) ─────────────────────────────────

@task_scheduler_blueprint.route('/workflows', methods=['GET'])
def list_workflows():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '', type=str).strip()
    sort = request.args.get('sort', 'created_at', type=str)
    direction = request.args.get('dir', 'desc', type=str)

    pagination = TaskSchedulerModel.get_workflow_list_page(page, per_page, search, sort, direction)
    return jsonify({
        "workflows": [w.to_json() for w in pagination.items],
        "total": pagination.total,
        "total_pages": pagination.pages,
    }), 200


@task_scheduler_blueprint.route('/workflows/<uuid>', methods=['GET'])
def get_workflow(uuid):
    workflow = _workflow_or_none(uuid)
    if not workflow:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404
    return jsonify({"workflow": workflow.to_json()}), 200


@task_scheduler_blueprint.route('/workflows/create', methods=['POST'])
def create_workflow():
    data = request.get_json(silent=True) or {}
    workflow, err = TaskSchedulerModel.create_workflow(data, current_user)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400

    log_activity("admin.workflow_created",
                 f"Created workflow '{workflow.title}'",
                 target_type="admin_workflow",
                 target_uuid=workflow.uuid,
                 icon="fa-solid fa-diagram-project")
    return jsonify({
        "message": "Workflow created.",
        "toast_class": "success-subtle",
        "workflow": workflow.to_json(),
    }), 201


@task_scheduler_blueprint.route('/workflows/<uuid>/update', methods=['POST'])
def update_workflow(uuid):
    data = request.get_json(silent=True) or {}
    workflow, err = TaskSchedulerModel.update_workflow(uuid, data)
    if err:
        status = 404 if err == "Workflow not found." else 400
        return jsonify({"message": err, "toast_class": "danger-subtle"}), status

    log_activity("admin.workflow_updated",
                 f"Updated workflow '{workflow.title}'",
                 target_type="admin_workflow",
                 target_uuid=workflow.uuid,
                 icon="fa-solid fa-diagram-project")
    return jsonify({
        "message": "Workflow updated.",
        "toast_class": "success-subtle",
        "workflow": workflow.to_json(),
    }), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/delete', methods=['POST'])
def delete_workflow(uuid):
    ok = TaskSchedulerModel.delete_workflow(uuid)
    if not ok:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404

    log_activity("admin.workflow_deleted",
                 "Deleted a workflow (and its tasks)",
                 target_type="admin_workflow",
                 target_uuid=uuid,
                 icon="fa-solid fa-diagram-project")
    return jsonify({"message": "Workflow and its tasks deleted.", "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/run_now', methods=['POST'])
def run_workflow_now(uuid):
    workflow_run, err = TaskSchedulerModel.run_workflow_now(uuid, triggered_by=current_user)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400

    log_activity("admin.workflow_run_now",
                 "Manually launched a workflow",
                 target_type="admin_workflow",
                 target_uuid=uuid,
                 icon="fa-solid fa-diagram-project")
    return jsonify({
        "message": "Workflow launched.",
        "toast_class": "success-subtle",
        "workflow_run_uuid": workflow_run.uuid,
    }), 202


@task_scheduler_blueprint.route('/workflows/<uuid>/stop', methods=['POST'])
def stop_workflow(uuid):
    stopped, err = TaskSchedulerModel.stop_workflow_jobs(uuid)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 404

    log_activity("admin.workflow_stopped",
                 f"Stopped {stopped} running job(s) for a workflow",
                 target_type="admin_workflow",
                 target_uuid=uuid,
                 icon="fa-solid fa-diagram-project")
    return jsonify({
        "message": f"Stopped {stopped} running job(s)." if stopped else "Nothing was running.",
        "toast_class": "success-subtle",
        "stopped": stopped,
    }), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/live', methods=['GET'])
def workflow_live_status(uuid):
    tasks = TaskSchedulerModel.get_workflow_live_status(uuid)
    if tasks is None:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404
    return jsonify({"tasks": tasks}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/runs', methods=['GET'])
def workflow_runs(uuid):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = TaskSchedulerModel.get_workflow_runs_page(uuid, page, per_page)
    if pagination is None:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404
    return jsonify({
        "runs": [TaskSchedulerModel.serialize_workflow_run(r) for r in pagination.items],
        "total": pagination.total,
        "total_pages": pagination.pages,
    }), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/runs/<run_uuid>/trace', methods=['GET'])
def workflow_run_trace(uuid, run_uuid):
    """The execution path of one launch — see get_workflow_run_trace."""
    trace = TaskSchedulerModel.get_workflow_run_trace(uuid, run_uuid)
    if trace is None:
        return jsonify({"message": "Launch not found.", "toast_class": "danger-subtle"}), 404
    return jsonify({"trace": trace}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/runs/bulk_delete', methods=['POST'])
def bulk_delete_workflow_runs(uuid):
    data = request.get_json(silent=True) or {}
    count, err = TaskSchedulerModel.bulk_delete_workflow_runs(uuid, data.get('run_uuids'))
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 404

    log_activity("admin.workflow_run_bulk_deleted",
                 f"Deleted {count} launch history entr{'y' if count == 1 else 'ies'}",
                 target_type="admin_workflow",
                 target_uuid=uuid,
                 icon="fa-solid fa-diagram-project")
    return jsonify({"message": f"{count} history entr{'y' if count == 1 else 'ies'} deleted.", "toast_class": "success-subtle", "count": count}), 200


# ─── Tasks — always scoped to a workflow (JSON API used by the Vue app) ────────

@task_scheduler_blueprint.route('/list', methods=['GET'])
def list_schedules():
    workflow = _workflow_or_none(request.args.get('workflow_uuid'))
    if not workflow:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '', type=str).strip()
    sort = request.args.get('sort', 'created_at', type=str)
    direction = request.args.get('dir', 'desc', type=str)
    task_type = request.args.get('task_type', None, type=str)

    pagination = TaskSchedulerModel.get_schedule_list_page(workflow.id, page, per_page, search, sort, direction, task_type)
    return jsonify({
        "schedules": [s.to_json() for s in pagination.items],
        "total": pagination.total,
        "total_pages": pagination.pages,
    }), 200


@task_scheduler_blueprint.route('/picker', methods=['GET'])
def picker():
    """Lightweight list for the 'after which task' dependency select, scoped
    to one workflow — excludes exclude_uuid (the task being edited) so it
    can't depend on itself in the dropdown (the server still re-validates
    on save)."""
    from app.core.db_class.task_scheduler import AdminTaskSchedule
    workflow = _workflow_or_none(request.args.get('workflow_uuid'))
    if not workflow:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404

    exclude_uuid = request.args.get('exclude_uuid')
    query = AdminTaskSchedule.query.filter_by(workflow_id=workflow.id).order_by(AdminTaskSchedule.title.asc())
    if exclude_uuid:
        query = query.filter(AdminTaskSchedule.uuid != exclude_uuid)
    return jsonify({
        "schedules": [{"id": s.id, "uuid": s.uuid, "title": s.title, "task_type": s.task_type} for s in query.all()]
    }), 200


@task_scheduler_blueprint.route('/create', methods=['POST'])
def create():
    data = request.get_json(silent=True) or {}
    schedule, err = TaskSchedulerModel.create_schedule(data, current_user)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400

    log_activity("admin.task_schedule_created",
                 f"Created scheduled task '{schedule.title}' ({schedule.task_type})",
                 target_type="admin_task_schedule",
                 target_uuid=schedule.uuid,
                 icon="fa-solid fa-list-check")
    return jsonify({
        "message": "Task created.",
        "toast_class": "success-subtle",
        "schedule": schedule.to_json(),
    }), 201


@task_scheduler_blueprint.route('/<uuid>/update', methods=['POST'])
def update(uuid):
    data = request.get_json(silent=True) or {}
    schedule, err = TaskSchedulerModel.update_schedule(uuid, data)
    if err:
        status = 404 if err == "Schedule not found." else 400
        return jsonify({"message": err, "toast_class": "danger-subtle"}), status

    log_activity("admin.task_schedule_updated",
                 f"Updated scheduled task '{schedule.title}'",
                 target_type="admin_task_schedule",
                 target_uuid=schedule.uuid,
                 icon="fa-solid fa-list-check")
    return jsonify({
        "message": "Task updated.",
        "toast_class": "success-subtle",
        "schedule": schedule.to_json(),
    }), 200


@task_scheduler_blueprint.route('/<uuid>/delete', methods=['POST'])
def delete(uuid):
    ok = TaskSchedulerModel.delete_schedule(uuid)
    if not ok:
        return jsonify({"message": "Schedule not found.", "toast_class": "danger-subtle"}), 404

    log_activity("admin.task_schedule_deleted",
                 "Deleted a scheduled task",
                 target_type="admin_task_schedule",
                 target_uuid=uuid,
                 icon="fa-solid fa-list-check")
    return jsonify({"message": "Task deleted.", "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/bulk_delete', methods=['POST'])
def bulk_delete():
    data = request.get_json(silent=True) or {}
    workflow = _workflow_or_none(data.get('workflow_uuid'))
    if not workflow:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404

    mode = data.get('mode', 'partial')
    count = TaskSchedulerModel.bulk_delete_schedules(
        workflow.id, mode, data.get('filters'), data.get('selected_uuids'), data.get('excluded_uuids')
    )

    log_activity("admin.task_schedule_bulk_deleted",
                 f"Bulk-deleted {count} scheduled task(s)",
                 extra={"count": count, "mode": mode},
                 icon="fa-solid fa-list-check")
    return jsonify({"message": f"{count} task(s) deleted.", "toast_class": "success-subtle", "count": count}), 200


@task_scheduler_blueprint.route('/bulk_set_active', methods=['POST'])
def bulk_set_active():
    data = request.get_json(silent=True) or {}
    workflow = _workflow_or_none(data.get('workflow_uuid'))
    if not workflow:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404

    mode = data.get('mode', 'partial')
    is_active = bool(data.get('is_active', True))
    count = TaskSchedulerModel.bulk_set_active_schedules(
        workflow.id, mode, data.get('filters'), data.get('selected_uuids'), data.get('excluded_uuids'), is_active
    )

    verb = 'activated' if is_active else 'paused'
    log_activity("admin.task_schedule_bulk_set_active",
                 f"Bulk-{verb} {count} scheduled task(s)",
                 extra={"count": count, "mode": mode, "is_active": is_active},
                 icon="fa-solid fa-list-check")
    return jsonify({"message": f"{count} task(s) {verb}.", "toast_class": "success-subtle", "count": count}), 200


@task_scheduler_blueprint.route('/run_adhoc', methods=['POST'])
def run_adhoc():
    """The task form's "Now" trigger — queue one job of that task type right
    away without saving a schedule. Built server-side like a scheduled
    firing (registry job_type, fixed_payload, payload validation)."""
    data = request.get_json(silent=True) or {}
    job, err = TaskSchedulerModel.run_task_type_now(
        data.get('task_type'), data.get('target_payload'), data.get('title'), current_user)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400

    log_activity("admin.task_run_adhoc",
                 f"Ran '{job.label}' once, without saving a task",
                 target_type="job",
                 target_uuid=job.uuid,
                 icon="fa-solid fa-list-check")
    return jsonify({"message": "Job queued! Running in background…", "toast_class": "success-subtle",
                    "job_uuid": job.uuid}), 202


@task_scheduler_blueprint.route('/<uuid>/run_now', methods=['POST'])
def run_now(uuid):
    job_uuid, err = TaskSchedulerModel.run_schedule_now(uuid)
    if not job_uuid:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400

    log_activity("admin.task_schedule_run_now",
                 "Manually triggered a scheduled task run",
                 target_type="admin_task_schedule",
                 target_uuid=uuid,
                 icon="fa-solid fa-list-check")
    return jsonify({
        "message": "Run started.",
        "toast_class": "success-subtle",
        "job_uuid": job_uuid if isinstance(job_uuid, str) else None,
    }), 202


@task_scheduler_blueprint.route('/<uuid>/position', methods=['POST'])
def set_position(uuid):
    """Feeds the Canvas view's drag-to-move — fired on node release, not on
    every mousemove frame, so this is not a hot path."""
    data = request.get_json(silent=True) or {}
    schedule, err = TaskSchedulerModel.set_task_position(uuid, data.get('x'), data.get('y'))
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 404
    return jsonify({"message": "Position saved.", "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/<uuid>/set_dependency', methods=['POST'])
def set_dependency(uuid):
    """Feeds the Canvas view's drag-to-connect — sets only the trigger,
    leaving every other field on the task untouched."""
    data = request.get_json(silent=True) or {}
    schedule, err = TaskSchedulerModel.set_task_dependency(
        uuid, data.get('depends_on_schedule_id'), data.get('depends_on_condition', 'success')
    )
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400

    log_activity("admin.task_schedule_updated",
                 f"Connected task '{schedule.title}' on the workflow canvas",
                 target_type="admin_task_schedule",
                 target_uuid=uuid,
                 icon="fa-solid fa-list-check")
    return jsonify({
        "message": "Dependency set.",
        "toast_class": "success-subtle",
        "schedule": schedule.to_json(),
    }), 200


@task_scheduler_blueprint.route('/<uuid>/clear_dependency', methods=['POST'])
def clear_dependency(uuid):
    """Feeds the Canvas view's 'Remove connection' action."""
    schedule, err = TaskSchedulerModel.clear_task_dependency(uuid)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400

    log_activity("admin.task_schedule_updated",
                 f"Removed a connection to task '{schedule.title}' on the workflow canvas",
                 target_type="admin_task_schedule",
                 target_uuid=uuid,
                 icon="fa-solid fa-list-check")
    return jsonify({
        "message": "Connection removed — task paused, set its trigger via Edit.",
        "toast_class": "success-subtle",
        "schedule": schedule.to_json(),
    }), 200


# ── Templates, export / import, duplicate (workflow_spec.py) ────────────────────

def _created(workflow, message, action):
    log_activity(action, f"{message}: '{workflow.title}'", target_type="admin_workflow",
                 target_uuid=workflow.uuid, icon="fa-solid fa-diagram-project")
    return jsonify({"message": f"{message}.", "toast_class": "success-subtle", "workflow": workflow.to_json()}), 201


@task_scheduler_blueprint.route('/templates', methods=['GET'])
def workflow_templates():
    return jsonify(WorkflowSpec.serialize_templates()), 200


@task_scheduler_blueprint.route('/workflows/from_template', methods=['POST'])
def create_workflow_from_template():
    data = request.get_json(silent=True) or {}
    workflow, err = WorkflowSpec.create_from_template(data.get('key'), current_user, title=(data.get('title') or '').strip() or None)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400
    return _created(workflow, "Workflow created from a template", "admin.workflow_created")


@task_scheduler_blueprint.route('/workflows/<uuid>/export', methods=['GET'])
def export_workflow(uuid):
    workflow = _workflow_or_none(uuid)
    if not workflow:
        abort(404)
    import json as _json, re as _re
    name = _re.sub(r'[^A-Za-z0-9._-]+', '-', workflow.title).strip('-')[:60] or 'workflow'
    resp = current_app.response_class(_json.dumps(WorkflowSpec.export_workflow(workflow), indent=2), mimetype='application/json')
    resp.headers['Content-Disposition'] = f'attachment; filename="rulezet-workflow-{name}.json"'
    return resp


@task_scheduler_blueprint.route('/workflows/import', methods=['POST'])
def import_workflow():
    """A workflow file (export of this page): body = the JSON itself, or {"spec": ..., "title": ...}."""
    if request.content_length and request.content_length > 16 * 1024 * 1024:   # attached files ride along (8 MB)
        return jsonify({"message": "File too large.", "toast_class": "danger-subtle"}), 413
    data = request.get_json(silent=True)
    spec = data.get('spec') if isinstance(data, dict) and 'spec' in data else data
    title = (data.get('title') or '').strip() or None if isinstance(data, dict) and 'spec' in data else None
    report = []
    workflow, err = WorkflowSpec.create_from_spec(spec, current_user, title=title, root_paused=True, report=report)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400
    resp, code = _created(workflow, "Workflow imported", "admin.workflow_created")
    if report:
        body = resp.get_json()
        body.update(warnings=report, toast_class='warning-subtle',
                    message=f'Workflow imported — {len(report)} thing(s) to check: see the pinned note.')
        return jsonify(body), code
    return resp, code


@task_scheduler_blueprint.route('/workflows/<uuid>/duplicate', methods=['POST'])
def duplicate_workflow(uuid):
    workflow = _workflow_or_none(uuid)
    if not workflow:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404
    copy, err = WorkflowSpec.duplicate_workflow(workflow, current_user)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400
    return _created(copy, "Workflow duplicated", "admin.workflow_created")


@task_scheduler_blueprint.route('/<uuid>/duplicate', methods=['POST'])
def duplicate_task(uuid):
    from app.core.db_class.task_scheduler import AdminTaskSchedule
    schedule = AdminTaskSchedule.query.filter_by(uuid=uuid).first()
    if not schedule:
        return jsonify({"message": "Task not found.", "toast_class": "danger-subtle"}), 404
    copy, err = WorkflowSpec.duplicate_task(schedule, current_user)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400
    log_activity("admin.task_schedule_created", f"Duplicated task '{schedule.title}'",
                 target_type="admin_task_schedule", target_uuid=copy.uuid, icon="fa-solid fa-list-check")
    return jsonify({"message": "Task duplicated (paused).", "toast_class": "success-subtle",
                    "schedule": copy.to_json()}), 201


@task_scheduler_blueprint.route('/workflows/<uuid>/preview', methods=['GET'])
def preview_workflow(uuid):
    """What "Run workflow" will do: tasks in order, items to go through, usual durations."""
    data = TaskSchedulerModel.preview_workflow(uuid)
    if data is None:
        return jsonify({"message": "Workflow not found."}), 404
    return jsonify(data), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/save_as_template', methods=['POST'])
def save_workflow_as_template(uuid):
    workflow = _workflow_or_none(uuid)
    if not workflow:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404
    data = request.get_json(silent=True) or {}
    key, err = WorkflowSpec.save_as_template(workflow, current_user, label=data.get('label'), description=data.get('description'))
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400
    log_activity("admin.settings_changed", f"Saved the workflow '{workflow.title}' as a template",
                 target_type="admin_workflow", target_uuid=workflow.uuid, icon="fa-solid fa-diagram-project")
    return jsonify({"message": "Saved as a template.", "toast_class": "success-subtle", "key": key}), 201


@task_scheduler_blueprint.route('/templates/<key>/delete', methods=['POST'])
def delete_workflow_template(key):
    err = WorkflowSpec.delete_template(key, current_user)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400
    log_activity("admin.settings_changed", f"Deleted the workflow template '{key}'", icon="fa-solid fa-diagram-project")
    return jsonify({"message": "Template deleted.", "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/dashboard', methods=['GET'])
def workflow_dashboard(uuid):
    data = TaskSchedulerModel.workflow_dashboard(uuid)
    if data is None:
        return jsonify({"message": "Workflow not found."}), 404
    return jsonify(data), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/set_active', methods=['POST'])
def set_workflow_active(uuid):
    """Pause / resume a whole workflow (its tasks keep their own Active switch)."""
    workflow = _workflow_or_none(uuid)
    if not workflow:
        return jsonify({"message": "Workflow not found.", "toast_class": "danger-subtle"}), 404
    from app import db
    workflow.is_active = bool((request.get_json(silent=True) or {}).get('is_active'))
    db.session.commit()
    verb = 'resumed' if workflow.is_active else 'paused'
    log_activity("admin.workflow_updated", f"Workflow '{workflow.title}' {verb}", target_type="admin_workflow",
                 target_uuid=workflow.uuid, icon="fa-solid fa-diagram-project")
    return jsonify({"message": f"Workflow {verb}.", "toast_class": "success-subtle", "is_active": workflow.is_active}), 200


@task_scheduler_blueprint.route('/<uuid>/run_from_here', methods=['POST'])
def run_from_here(uuid):
    run, err = TaskSchedulerModel.run_from_task(uuid, current_user)
    if err:
        return jsonify({"message": err, "toast_class": "danger-subtle"}), 400
    log_activity("admin.workflow_run_now", "Launched a workflow from one of its tasks",
                 target_type="admin_task_schedule", target_uuid=uuid, icon="fa-solid fa-play")
    return jsonify({"message": "Launched from this task.", "toast_class": "success-subtle",
                    "workflow_run_uuid": run.uuid}), 202


# ─── Notes, files, activity and history export of a workflow ──────────────────

def _wf_or_404(uuid):
    workflow = _workflow_or_none(uuid)
    if not workflow:
        abort(404)
    return workflow


def _err(msg, code=400):
    return jsonify({"message": msg, "toast_class": "danger-subtle"}), code


@task_scheduler_blueprint.route('/workflows/<uuid>/notebook', methods=['GET'])
def workflow_notebook(uuid):
    workflow = _wf_or_404(uuid)
    return jsonify({"notes": WorkflowNotes.list_notes(workflow), "files": WorkflowNotes.list_files(workflow),
                    "activity": WorkflowNotes.activity(workflow),
                    "max_file_mb": WorkflowNotes.MAX_FILE_BYTES // (1024 * 1024)}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/notes', methods=['POST'])
@task_scheduler_blueprint.route('/workflows/<uuid>/notes/<note_uuid>', methods=['POST'])
def workflow_note_save(uuid, note_uuid=None):
    workflow = _wf_or_404(uuid)
    note, err = WorkflowNotes.save_note(workflow, request.get_json(silent=True) or {}, current_user, note_uuid)
    if err:
        return _err(err)
    log_activity('admin.workflow_note_edit' if note_uuid else 'admin.workflow_note_add',
                 f'Note "{note.title}" {"edited" if note_uuid else "added"} on workflow "{workflow.title}"',
                 target_type='admin_workflow', target_uuid=workflow.uuid, icon='fa-solid fa-note-sticky', is_public=False)
    return jsonify({"note": note.to_json(), "message": "Note saved.", "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/notes/<note_uuid>', methods=['DELETE'])
def workflow_note_delete(uuid, note_uuid):
    workflow = _wf_or_404(uuid)
    title = WorkflowNotes.delete_note(workflow, note_uuid)
    if title is None:
        return _err('Note not found.', 404)
    log_activity('admin.workflow_note_delete', f'Note "{title}" deleted from workflow "{workflow.title}"',
                 target_type='admin_workflow', target_uuid=workflow.uuid, icon='fa-solid fa-note-sticky', is_public=False)
    return jsonify({"message": "Note deleted.", "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/files', methods=['POST'])
def workflow_file_upload(uuid):
    workflow = _wf_or_404(uuid)
    storage = request.files.get('file')
    if not storage:
        return _err('No file.')
    f, err = WorkflowNotes.add_file(workflow, storage, current_user)
    if err:
        return _err(err)
    log_activity('admin.workflow_file_add', f'File "{f.filename}" attached to workflow "{workflow.title}"',
                 target_type='admin_workflow', target_uuid=workflow.uuid, icon='fa-solid fa-paperclip', is_public=False)
    return jsonify({"file": f.to_json(), "message": "File attached.", "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/files/<file_uuid>', methods=['GET'])
def workflow_file_download(uuid, file_uuid):
    workflow = _wf_or_404(uuid)
    f, path = WorkflowNotes.get_file(workflow, file_uuid)
    if not path:
        abort(404)
    # Always a download, never rendered by the browser (an attached .html / .svg stays inert).
    resp = send_file(path, as_attachment=True, download_name=f.filename, mimetype='application/octet-stream')
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp


@task_scheduler_blueprint.route('/workflows/<uuid>/files/<file_uuid>', methods=['DELETE'])
def workflow_file_delete(uuid, file_uuid):
    workflow = _wf_or_404(uuid)
    name = WorkflowNotes.delete_file(workflow, file_uuid)
    if name is None:
        return _err('File not found.', 404)
    log_activity('admin.workflow_file_delete', f'File "{name}" removed from workflow "{workflow.title}"',
                 target_type='admin_workflow', target_uuid=workflow.uuid, icon='fa-solid fa-paperclip', is_public=False)
    return jsonify({"message": "File removed.", "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/runs/export.csv', methods=['GET'])
def workflow_runs_csv(uuid):
    """The launch history as a CSV: one line per task of each launch (last 500 launches)."""
    import csv
    import io
    workflow = _wf_or_404(uuid)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['launch', 'started_at', 'launch_status', 'triggered_by', 'task', 'task_type', 'task_status', 'duration_seconds', 'notes'])
    for run in workflow.launch_runs[:500]:
        r = TaskSchedulerModel.serialize_workflow_run(run)
        by = (r.get('triggered_by') or {}).get('name') if isinstance(r.get('triggered_by'), dict) else r.get('triggered_by')
        for t in r.get('tasks') or [{}]:
            row = [r['uuid'], r.get('started_at'), r.get('status'), by or 'schedule', t.get('task_title'),
                   t.get('task_type'), t.get('status'), t.get('duration_seconds'), r.get('notes_count')]
            # Spreadsheet formula injection: a cell starting with = + - @ is read as a formula.
            w.writerow(["'" + str(c) if isinstance(c, str) and c[:1] in '=+-@' else c for c in row])
    name = ''.join(ch if ch.isalnum() else '_' for ch in workflow.title)[:60] or 'workflow'
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{name}_history.csv"'})


@task_scheduler_blueprint.route('/workflows/<uuid>/share', methods=['GET'])
def workflow_share_get(uuid):
    return jsonify({"url": WorkflowNotes.share_url(_wf_or_404(uuid))}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/share', methods=['POST'])
def workflow_share_set(uuid):
    workflow = _wf_or_404(uuid)
    action = (request.get_json(silent=True) or {}).get('action')
    if action not in ('regenerate', 'disable'):
        return _err('Unknown action.')
    WorkflowNotes.set_share(workflow, action)
    log_activity('admin.workflow_share', f'Read-only link of workflow "{workflow.title}" '
                 f'{"(re)generated" if action == "regenerate" else "disabled"}',
                 target_type='admin_workflow', target_uuid=workflow.uuid, icon='fa-solid fa-share-nodes', is_public=False)
    return jsonify({"url": WorkflowNotes.share_url(workflow),
                    "message": "New link created — any old one stops working." if action == 'regenerate' else "Sharing stopped.",
                    "toast_class": "success-subtle"}), 200


@task_scheduler_blueprint.route('/workflows/health', methods=['GET'])
def workflows_health():
    """Health board of the workflows list — see workflow_notes.health_board."""
    return jsonify(WorkflowNotes.health_board()), 200


@task_scheduler_blueprint.route('/<uuid>/alert', methods=['POST'])
def set_task_alert(uuid):
    """The email alert of one task — or of the link leading to it ("reached") — from the canvas,
    leaving the rest of the task untouched. Body: {"alert": {"on": [...], "to": "...", "message": "..."}}."""
    from app.core.db_class.task_scheduler import AdminTaskSchedule
    from app.features.admin.task_scheduler.notifications import validate_alert
    from app import db
    schedule = AdminTaskSchedule.query.filter_by(uuid=uuid).first()
    if not schedule:
        return _err('Task not found.', 404)
    data = request.get_json(silent=True) or {}
    current = (schedule.target_payload or {}).get('_alert') or {}
    if 'link' in data:   # a graph link: only its "reached" point, the rest of the alert kept
        link = data.get('link') or {}
        on = [p for p in (current.get('on') or []) if p != 'reached'] + (['reached'] if link.get('reached') else [])
        alert = {'on': on, 'to': link.get('to', current.get('to', '')), 'message': link.get('message', current.get('message', ''))}
    else:
        alert = data.get('alert') or {}
    err = validate_alert(alert)
    if err:
        return _err(err)
    payload = dict(schedule.target_payload or {})
    if alert.get('on'):
        payload['_alert'] = {'on': alert['on'], 'to': (alert.get('to') or '').strip(), 'message': (alert.get('message') or '').strip()}
    else:
        payload.pop('_alert', None)
    schedule.target_payload = payload
    db.session.commit()
    log_activity('admin.task_alert', f"Email alert of task '{schedule.title}' "
                 f"{'set: ' + ', '.join(alert['on']) if alert.get('on') else 'removed'}",
                 target_type='admin_workflow', target_uuid=schedule.workflow.uuid, icon='fa-solid fa-bell', is_public=False)
    if 'link' in data:
        message = 'Alert on this link: on.' if 'reached' in alert['on'] else 'Alert on this link: off.'
    else:
        message = 'Alert saved.' if alert.get('on') else 'Alert removed.'
    return jsonify({"message": message, "toast_class": "success-subtle",
                    "schedule": schedule.to_json()}), 200


@task_scheduler_blueprint.route('/backups', methods=['GET'])
def backups_folder():
    """The backup folder as the "Database backup + rotation" task shows it (admin only)."""
    from app.features.admin.task_scheduler.backup_rotation import list_backups
    return jsonify(list_backups()), 200


def _planned_launches(start, end, exclude_uuid=None):
    """Planned launches of every workflow's time-triggered first tasks between start and end (aware
    datetimes, from now on) — the calendar's events, and what the per-day limit counts."""
    import datetime
    from app.core.db_class.task_scheduler import AdminWorkflow
    from app.features.admin.task_scheduler.scheduler_engine import build_trigger, workflow_root_tasks
    now = datetime.datetime.now(datetime.timezone.utc)
    events = []
    for wf in AdminWorkflow.query.all():
        if exclude_uuid and wf.uuid == exclude_uuid:
            continue
        for root in workflow_root_tasks(wf):
            if root.trigger_mode == 'after_task':
                continue
            base = {'kind': 'planned', 'workflow_uuid': wf.uuid, 'title': wf.title, 'task': root.title,
                    'days_of_week': root.days_of_week_list() if root.trigger_mode == 'weekly' else None,
                    'day_of_month': root.day_of_month if root.trigger_mode == 'monthly' else None,
                    'mode': root.trigger_mode, 'active': bool(wf.is_active and root.is_active)}
            if root.trigger_mode == 'once':
                if root.run_once_at:
                    at = root.run_once_at if root.run_once_at.tzinfo else root.run_once_at.replace(tzinfo=datetime.timezone.utc)
                    if max(start, now) <= at <= end:
                        events.append({**base, 'start': at.isoformat()})
                continue
            try:
                trig, cur = build_trigger(root), max(start, now)
                for _ in range(400):
                    nxt = trig.get_next_fire_time(None, cur)
                    if not nxt or nxt > end:
                        break
                    events.append({**base, 'start': nxt.astimezone(datetime.timezone.utc).isoformat()})
                    cur = nxt + datetime.timedelta(seconds=1)
            except Exception:
                continue
    return events


@task_scheduler_blueprint.route('/calendar', methods=['GET'])
def workflows_calendar():
    """Launches of every workflow between ?start= and ?end= (ISO dates) — for the calendar view.
    Planned: one event per launch of a time-triggered first task (once / daily / weekly / monthly /
    cron), from now on. Past: the launches that happened (with how they ended)."""
    import datetime

    def parse(v, default):
        try:
            d = datetime.datetime.fromisoformat((v or '').replace('Z', '+00:00'))
            return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return default
    now = datetime.datetime.now(datetime.timezone.utc)
    start = parse(request.args.get('start'), now - datetime.timedelta(days=7))
    end = min(parse(request.args.get('end'), now + datetime.timedelta(days=35)), start + datetime.timedelta(days=100))
    events = _planned_launches(start, end)
    # launches that happened in the range
    from app.core.db_class.task_scheduler import AdminWorkflowRun
    from app.features.admin.task_scheduler.workflow_notes import _launch_status
    naive = lambda d: d.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    runs = (AdminWorkflowRun.query.filter(AdminWorkflowRun.started_at >= naive(start),
                                          AdminWorkflowRun.started_at <= naive(min(end, now)))
            .order_by(AdminWorkflowRun.started_at).limit(500).all())
    for run in runs:
        if not run.workflow:
            continue
        events.append({'kind': 'past', 'workflow_uuid': run.workflow.uuid, 'title': run.workflow.title,
                       'status': _launch_status(run), 'run_uuid': run.uuid, 'active': True,
                       'start': run.started_at.replace(tzinfo=datetime.timezone.utc).isoformat()})
    return jsonify({'events': events}), 200


@task_scheduler_blueprint.route('/workflows/<uuid>/launch', methods=['POST'])
def set_workflow_launch(uuid):
    """Only the launch date / recurrence of a workflow (its first task) — the calendar's
    drag and drop, nothing else of the workflow changes. Body: {"launch": {trigger_mode, …}}."""
    from app import db
    workflow = _workflow_or_none(uuid)
    if not workflow:
        return _err('Workflow not found.', 404)
    launch = (request.get_json(silent=True) or {}).get('launch')
    if not isinstance(launch, dict):
        return _err('No launch given.')
    err = TaskSchedulerModel._set_workflow_launch(workflow, launch)
    if err:
        db.session.rollback()
        return _err(err)
    # At most N launches a day (setting workflows.calendar_max_per_day) over the next 5 weeks, this one included
    import datetime
    from collections import Counter
    from app.core.utils.app_settings import get_setting
    try:
        limit = int(get_setting('workflows.calendar_max_per_day') or 5)
    except (KeyError, TypeError, ValueError):
        limit = 5
    db.session.flush()
    now = datetime.datetime.now(datetime.timezone.utc)
    per_day = Counter(e['start'][:10] for e in _planned_launches(now, now + datetime.timedelta(days=35)))
    full = sorted(d for d, n in per_day.items() if n > limit)
    if full:
        db.session.rollback()
        return _err(f'More than {limit} workflow launches on {full[0]}' + (f' (and {len(full) - 1} other day(s))' if len(full) > 1 else '')
                    + ' — pick another day or time. The limit is the setting workflows.calendar_max_per_day.')
    db.session.commit()
    log_activity('admin.workflow_updated', f"Launch of workflow '{workflow.title}' set from the calendar "
                 f"({launch.get('trigger_mode')})", target_type='admin_workflow', target_uuid=workflow.uuid,
                 icon='fa-regular fa-calendar')
    return jsonify({'message': 'Launch saved.', 'toast_class': 'success-subtle', 'workflow': workflow.to_json()}), 200
