"""
workflow_portable.py — what makes an exported workflow work on ANOTHER Rulezet instance.

Database ids mean nothing elsewhere, so the export turns every reference a task holds into
something the other instance can find again, and the import turns it back:
    filters.rule_ids  → rule_uuids      (rules imported from the same source share their UUID)
    connector_id      → connector name
    config_id         → the saved config itself (Bulk Parse Fields), re-created if missing
    schedule_uuid     → the Git sync schedule's title
What cannot be found on the other side is dropped from the task and reported: the export file
lists its warnings, the import puts them in a pinned note of the new workflow (and in the toast).
Notes (markdown) and attached files travel with the workflow (files up to MAX_FILES_BYTES in all).
"""
import base64
import os
import uuid as _uuid

from app import db

MAX_FILES_BYTES = 8 * 1024 * 1024
_PORT = '_portable'


# ─── Export ───────────────────────────────────────────────────────────────────

def export_payload(task, warnings):
    """The task's target_payload with its instance ids replaced by portable references."""
    payload = dict(task.target_payload or {})
    port = {}
    filters = payload.get('filters')
    if isinstance(filters, dict) and filters.get('rule_ids'):
        from app.core.db_class.rule import Rule
        ids = [i for i in filters['rule_ids'] if isinstance(i, int)]
        uuids = [u for (u,) in db.session.query(Rule.uuid).filter(Rule.id.in_(ids)).all() if u]
        payload['filters'] = {k: v for k, v in filters.items() if k != 'rule_ids'}
        port['rule_uuids'] = uuids
        warnings.append(f'"{task.title}" targets {len(uuids)} hand-picked rule(s): on another instance only '
                        f'the ones with the same UUID (imported from the same source) are kept.')
    if payload.get('connector_id'):
        from app.core.db_class.connector import Connector
        c = db.session.get(Connector, int(payload['connector_id'])) if str(payload['connector_id']).isdigit() else None
        payload.pop('connector_id')
        if c:
            port['connector'] = c.name
            warnings.append(f'"{task.title}" uses the connector "{c.name}": the other instance needs a connector with that name.')
    if payload.get('config_id'):
        from app.core.db_class.rule import FieldParserConfig
        cfg = db.session.get(FieldParserConfig, int(payload['config_id'])) if str(payload['config_id']).isdigit() else None
        payload.pop('config_id')
        if cfg:
            port['config'] = {'name': cfg.name, 'config_type': cfg.config_type, 'config': cfg.config}
    if payload.get('schedule_uuid'):
        from app.core.db_class.git import GithubSyncSchedule
        s = GithubSyncSchedule.query.filter_by(uuid=payload['schedule_uuid']).first()
        payload.pop('schedule_uuid')
        if s:
            port['git_schedule'] = s.title
            warnings.append(f'"{task.title}" runs the Git sync schedule "{s.title}": the other instance needs one with that title.')
    if port:
        payload[_PORT] = port
    return payload


def export_attachments(workflow, include_files, warnings):
    notes = [{'title': n.title, 'content': n.content, 'pinned': bool(n.pinned)} for n in workflow.notes]
    files, total = [], 0
    if include_files:
        from app.features.admin.task_scheduler.workflow_notes import files_dir
        for f in workflow.files:
            path = os.path.join(files_dir(workflow), f.stored_name)
            if not os.path.isfile(path):
                continue
            if total + f.size > MAX_FILES_BYTES:
                warnings.append(f'File "{f.filename}" left out: the files of an export are {MAX_FILES_BYTES // 1048576} MB at most.')
                continue
            with open(path, 'rb') as fh:
                files.append({'filename': f.filename, 'data': base64.b64encode(fh.read()).decode()})
            total += f.size
    return notes, files


# ─── Import ───────────────────────────────────────────────────────────────────

def import_payload(title, payload, editor, warnings):
    """Back from portable references to this instance's ids (what is missing is dropped + reported)."""
    payload = dict(payload or {})
    port = payload.pop(_PORT, None) or {}
    if not isinstance(port, dict):
        return payload
    if 'rule_uuids' in port:
        from app.features.rule.rule_core import _active
        from app.core.db_class.rule import Rule
        wanted = [u for u in port.get('rule_uuids') or [] if isinstance(u, str)][:50000]
        ids = [i for (i,) in _active().with_entities(Rule.id).filter(Rule.uuid.in_(wanted)).all()] if wanted else []
        filters = dict(payload.get('filters') or {})
        filters['rule_ids'] = ids
        payload['filters'] = filters
        if len(ids) < len(wanted):
            warnings.append(f'"{title}": {len(wanted) - len(ids)} of its {len(wanted)} hand-picked rule(s) are not on this instance — '
                            f'{len(ids)} kept. Edit the task to pick them again.')
    if port.get('connector'):
        from app.core.db_class.connector import Connector
        c = Connector.query.filter_by(name=port['connector']).first()
        if c:
            payload['connector_id'] = c.id
        else:
            warnings.append(f'"{title}": no connector named "{port["connector"]}" here — choose one in the task.')
    cfg = port.get('config')
    if isinstance(cfg, dict) and cfg.get('name'):
        from app.core.db_class.rule import FieldParserConfig
        ctype = cfg.get('config_type') or 'field_parser'
        found = FieldParserConfig.query.filter_by(name=cfg['name'], config_type=ctype).first()
        if not found and isinstance(cfg.get('config'), (dict, list)):
            found = FieldParserConfig(name=str(cfg['name'])[:100], config_type=ctype, config=cfg['config'], user_id=editor.id)
            db.session.add(found)
            db.session.flush()
            warnings.append(f'"{title}": its saved config "{found.name}" was created on this instance.')
        if found:
            payload['config_id'] = found.id
    if port.get('git_schedule'):
        from app.core.db_class.git import GithubSyncSchedule
        s = GithubSyncSchedule.query.filter_by(title=port['git_schedule']).first()
        if s:
            payload['schedule_uuid'] = s.uuid
        else:
            warnings.append(f'"{title}": no Git sync schedule titled "{port["git_schedule"]}" here — create it on Git Sources, then pick it in the task.')
    return payload


def import_attachments(workflow, spec, editor, warnings):
    from app.core.db_class.task_scheduler import AdminWorkflowFile, AdminWorkflowNote
    from app.features.admin.task_scheduler.workflow_notes import MAX_FILE_BYTES, MAX_FILES, MAX_NOTES, files_dir
    for n in (spec.get('notes') or [])[:MAX_NOTES]:
        if isinstance(n, dict) and (n.get('title') or '').strip():
            db.session.add(AdminWorkflowNote(uuid=str(_uuid.uuid4()), workflow_id=workflow.id, author_id=editor.id,
                                             title=str(n['title'])[:200], content=str(n.get('content') or '')[:50000],
                                             pinned=bool(n.get('pinned'))))
    for f in (spec.get('files') or [])[:MAX_FILES]:
        if not isinstance(f, dict):
            continue
        name = os.path.basename(str(f.get('filename') or '').replace('\\', '/')).strip()[:255]
        try:
            data = base64.b64decode(f.get('data') or '', validate=True)
        except Exception:
            data = None
        if not name or data is None or len(data) > MAX_FILE_BYTES:
            warnings.append(f'File "{name or "?"}" not imported (unreadable or over 10 MB).')
            continue
        stored = _uuid.uuid4().hex
        os.makedirs(files_dir(workflow), exist_ok=True)
        with open(os.path.join(files_dir(workflow), stored), 'wb') as fh:
            fh.write(data)
        db.session.add(AdminWorkflowFile(uuid=str(_uuid.uuid4()), workflow_id=workflow.id, uploader_id=editor.id,
                                         filename=name, stored_name=stored, size=len(data)))


def report_note(workflow, editor, warnings):
    """What to check after an import, pinned on top of the new workflow."""
    from app.core.db_class.task_scheduler import AdminWorkflowNote
    body = 'Imported from another Rulezet instance. Some references could not be carried over:\n\n' + \
           '\n'.join(f'- {w}' for w in warnings) + '\n\nFix the tasks above, then delete this note.'
    db.session.add(AdminWorkflowNote(uuid=str(_uuid.uuid4()), workflow_id=workflow.id, author_id=editor.id,
                                     title='# To check after the import', content=body, pinned=True))
