"""
workflow_notes.py — what an admin keeps next to a workflow: markdown notes (why it exists, what to
do when it fails, what happened on a given launch) and attached files (runbook, exported config,
screenshot), plus the workflow's own activity feed. Admin-only through the blueprint's before_request.
"""
import datetime
import os
import shutil
import uuid as _uuid

from flask import current_app

from app import db
from app.core.db_class.activity_log import ActivityLog
from app.core.db_class.task_scheduler import AdminWorkflowFile, AdminWorkflowNote, AdminWorkflowRun

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES = 30
MAX_NOTES = 100
MAX_NOTE_CHARS = 50_000


def files_dir(workflow):
    root = os.path.join(os.path.dirname(current_app.root_path), 'data', 'workflow_files')
    return os.path.join(root, workflow.uuid)


def list_notes(workflow):
    notes = AdminWorkflowNote.query.filter_by(workflow_id=workflow.id).order_by(
        AdminWorkflowNote.pinned.desc(), AdminWorkflowNote.updated_at.desc()).all()
    return [n.to_json() for n in notes]


def _run(workflow, run_uuid):
    if not run_uuid:
        return None, None
    run = AdminWorkflowRun.query.filter_by(uuid=run_uuid, workflow_id=workflow.id).first()
    return (run, None) if run else (None, 'That launch is not in this workflow.')


def save_note(workflow, data, user, note_uuid=None):
    title = (data.get('title') or '').strip()[:200]
    content = data.get('content') or ''
    if not title.lstrip('#').strip():   # markdown title: "# Runbook" — a bare "#" is empty
        return None, 'Give the note a title.'
    if len(content) > MAX_NOTE_CHARS:
        return None, f'A note is at most {MAX_NOTE_CHARS} characters.'
    run, err = _run(workflow, data.get('run_uuid'))
    if err:
        return None, err
    if note_uuid:
        note = AdminWorkflowNote.query.filter_by(uuid=note_uuid, workflow_id=workflow.id).first()
        if not note:
            return None, 'Note not found.'
    else:
        if AdminWorkflowNote.query.filter_by(workflow_id=workflow.id).count() >= MAX_NOTES:
            return None, f'At most {MAX_NOTES} notes per workflow.'
        note = AdminWorkflowNote(uuid=str(_uuid.uuid4()), workflow_id=workflow.id, author_id=user.id)
        db.session.add(note)
    note.title, note.content, note.pinned = title, content, bool(data.get('pinned'))
    note.workflow_run_id = run.id if run else None
    note.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    return note, None


def delete_note(workflow, note_uuid):
    note = AdminWorkflowNote.query.filter_by(uuid=note_uuid, workflow_id=workflow.id).first()
    if not note:
        return None
    title = note.title
    db.session.delete(note)
    db.session.commit()
    return title


def list_files(workflow):
    files = AdminWorkflowFile.query.filter_by(workflow_id=workflow.id).order_by(AdminWorkflowFile.created_at.desc()).all()
    return [f.to_json() for f in files]


def add_file(workflow, storage, user):
    name = os.path.basename((storage.filename or '').replace('\\', '/')).strip()[:255]
    if not name:
        return None, 'No file.'
    if AdminWorkflowFile.query.filter_by(workflow_id=workflow.id).count() >= MAX_FILES:
        return None, f'At most {MAX_FILES} files per workflow.'
    data = storage.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        return None, 'A file is at most 10 MB.'
    stored = _uuid.uuid4().hex   # never the user's name on disk
    folder = files_dir(workflow)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, stored), 'wb') as fh:
        fh.write(data)
    f = AdminWorkflowFile(uuid=str(_uuid.uuid4()), workflow_id=workflow.id, uploader_id=user.id,
                          filename=name, stored_name=stored, size=len(data))
    db.session.add(f)
    db.session.commit()
    return f, None


def get_file(workflow, file_uuid):
    f = AdminWorkflowFile.query.filter_by(uuid=file_uuid, workflow_id=workflow.id).first()
    if not f:
        return None, None
    path = os.path.join(files_dir(workflow), f.stored_name)
    return f, (path if os.path.isfile(path) else None)


def delete_file(workflow, file_uuid):
    f, path = get_file(workflow, file_uuid)
    if not f:
        return None
    name = f.filename
    if path:
        os.remove(path)
    db.session.delete(f)
    db.session.commit()
    return name


def remove_all_files(workflow):
    """On workflow deletion (the rows go with the cascade)."""
    shutil.rmtree(files_dir(workflow), ignore_errors=True)


def activity(workflow, limit=40):
    """What happened to this workflow: edits, launches, notes, files, action-task lines."""
    logs = ActivityLog.query.filter_by(target_uuid=workflow.uuid).order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return [{
        'action': l.action, 'title': l.title, 'description': l.description, 'icon': l.icon,
        'user': l.user.get_username() if getattr(l, 'user', None) else None,
        'created_at': l.created_at.strftime('%Y-%m-%d %H:%M') if l.created_at else None,
    } for l in logs]


# ─── Read-only share link ─────────────────────────────────────────────────────

def set_share(workflow, action):
    """'regenerate' → a new key (any old link stops working); 'disable' → no link."""
    import secrets
    workflow.share_key = secrets.token_urlsafe(32) if action == 'regenerate' else None
    db.session.commit()
    return workflow.share_key


def workflow_by_share_key(key):
    from app.core.db_class.task_scheduler import AdminWorkflow
    if not key or len(key) < 32:
        return None
    return AdminWorkflow.query.filter_by(share_key=key).first()


def share_url(workflow):
    from flask import url_for
    return url_for('workflow_share.shared_page', key=workflow.share_key, _external=True) if workflow.share_key else None


# ─── Health board of every workflow (workflows list) ──────────────────────────

def _launch_status(run):
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.task_scheduler import AdminTaskRun
    statuses = []
    for tr in AdminTaskRun.query.filter_by(workflow_run_id=run.id).all():
        job = BackgroundJob.query.filter_by(uuid=tr.job_uuid).first() if tr.job_uuid else None
        statuses.append(job.status if job else tr.status)
    if any(s in ('pending', 'running') for s in statuses):
        return 'running'
    if 'failed' in statuses:
        return 'failed'
    if 'cancelled' in statuses:
        return 'cancelled'
    return 'done' if statuses else 'pending'


def health_board(recent=10):
    """Per workflow: its last launches (oldest → newest) and success rate; plus what needs a look
    across the instance — workflows whose last launch failed, running ones, auto-paused tasks."""
    from app.core.db_class.task_scheduler import AdminTaskSchedule, AdminWorkflow
    per, failing, running = {}, [], []
    for wf in AdminWorkflow.query.all():
        runs = AdminWorkflowRun.query.filter_by(workflow_id=wf.id).order_by(AdminWorkflowRun.started_at.desc()).limit(recent).all()
        dots = [{'status': _launch_status(r), 'at': r.started_at.strftime('%Y-%m-%d %H:%M') if r.started_at else None} for r in runs][::-1]
        finished = [d for d in dots if d['status'] in ('done', 'failed', 'cancelled')]
        rate = round(100 * sum(d['status'] == 'done' for d in finished) / len(finished)) if finished else None
        per[wf.uuid] = {'dots': dots, 'rate': rate, 'notes': len(wf.notes), 'files': len(wf.files)}
        if dots and dots[-1]['status'] == 'failed':
            failing.append({'uuid': wf.uuid, 'title': wf.title, 'at': dots[-1]['at']})
        if dots and dots[-1]['status'] == 'running':
            running.append({'uuid': wf.uuid, 'title': wf.title})
    auto_paused = [{'workflow_uuid': t.workflow.uuid, 'workflow': t.workflow.title, 'task': t.title}
                   for t in AdminTaskSchedule.query.filter(AdminTaskSchedule.auto_disabled_at.isnot(None),
                                                           AdminTaskSchedule.is_active == False).all() if t.workflow]
    return {
        'per_workflow': per,
        'failing': failing, 'running': running, 'auto_paused': auto_paused,
        'total': len(per), 'paused': AdminWorkflow.query.filter_by(is_active=False).count(),
    }
