"""
workflow_share_routes.py — the read-only page of a workflow shared by link (/workflow/shared/<key>):
its launch history, notes, files and activity. No login; the key is the only access, an admin
regenerates it (workflow page → Share) to cut old links. Nothing here writes.
"""
from flask import Blueprint, abort, jsonify, render_template, send_file

from app.features.admin.task_scheduler import workflow_notes as WorkflowNotes

workflow_share_blueprint = Blueprint('workflow_share', __name__)


def _workflow(key):
    workflow = WorkflowNotes.workflow_by_share_key(key)
    if not workflow:
        abort(404)
    return workflow


@workflow_share_blueprint.route('/<key>', methods=['GET'])
def shared_page(key):
    workflow = _workflow(key)
    return render_template('admin/workflow_shared.html', workflow=workflow, key=key)


@workflow_share_blueprint.route('/<key>/data', methods=['GET'])
def shared_data(key):
    from app.features.admin.task_scheduler.task_scheduler_core import serialize_workflow_run
    workflow = _workflow(key)
    runs = [serialize_workflow_run(r) for r in workflow.launch_runs[:30]]
    for r in runs:
        r.pop('triggered_by', None)   # no account details on a public page
        for t in r.get('tasks', []):
            t.pop('job_uuid', None)
    return jsonify({'title': workflow.title, 'description': workflow.description, 'runs': runs,
                    'task_count': len(workflow.tasks)}), 200


@workflow_share_blueprint.route('/<key>/notebook', methods=['GET'])
def shared_notebook(key):
    workflow = _workflow(key)
    return jsonify({"notes": WorkflowNotes.list_notes(workflow), "files": WorkflowNotes.list_files(workflow),
                    "activity": WorkflowNotes.activity(workflow), "max_file_mb": 0}), 200


@workflow_share_blueprint.route('/<key>/files/<file_uuid>', methods=['GET'])
def shared_file(key, file_uuid):
    workflow = _workflow(key)
    f, path = WorkflowNotes.get_file(workflow, file_uuid)
    if not path:
        abort(404)
    resp = send_file(path, as_attachment=True, download_name=f.filename, mimetype='application/octet-stream')
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp
