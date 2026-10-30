"""
workflow_spec.py — a workflow as plain JSON: its tasks, their options, triggers and links.

One format for three features of the Workflows page:
  - templates: ready-made workflows (TEMPLATES below) created in one click;
  - export / import: a workflow downloaded as a .json file and created again here or on another
    Rulezet instance;
  - duplicate: export + import in one go.

    {"rulezet_workflow": 1, "title": "...", "description": "...",
     "notify_on_failure": true, "notify_on_success": false,
     "tasks": [
        {"ref": "pull", "title": "...", "task_type": "git_cache_pull", "target_payload": {},
         "is_active": true, "trigger": {"trigger_mode": "weekly", "days_of_week": [6], "hour": 2, "minute": 0,
                                        "timezone": "UTC"},
         "position": [80, 120]},
        {"ref": "relink", ..., "trigger": {"after": "pull", "condition": "success"}}
     ]}

A task's "after" names the "ref" of an EARLIER task of the list (parents first). Tasks are created
through task_scheduler_core.create_schedule, so every check of the task window applies (task type,
options, trigger, no cycle).
"""
import re

from app import db
from app.core.db_class.task_scheduler import AdminTaskSchedule, AdminWorkflow

SPEC_VERSION = 1
MAX_TASKS = 50

_RELIABILITY_KEYS = ('max_retries', 'retry_delay_minutes', 'timeout_minutes', 'max_consecutive_failures', 'catch_up')
_TRIGGER_KEYS = ('trigger_mode', 'run_once_at', 'days_of_week', 'day_of_month', 'hour', 'minute',
                 'cron_expr', 'timezone')


def _weekly(day, hour, minute=0):
    return {'trigger_mode': 'weekly', 'days_of_week': [day], 'hour': hour, 'minute': minute, 'timezone': 'UTC'}


def _after(ref, condition='always'):
    return {'after': ref, 'condition': condition}


# Ready-made workflows: the setting workflows.templates (app/config/workflows.templates.json, editable
# on Admin → Configuration; "Save as template" adds to it). Their first task is created paused: nothing
# runs before an admin has looked at it and switched it on (Edit task → Active, or Run now).
TEMPLATES_SETTING = 'workflows.templates'


def templates():
    from app.core.utils.app_settings import get_setting
    value = get_setting(TEMPLATES_SETTING)
    return value if isinstance(value, dict) else {}


def serialize_templates():
    """Templates for the "New workflow" gallery: their card and the tasks they create."""
    from app.features.admin.task_scheduler.task_types import TASK_TYPES
    out = []
    for key, t in templates().items():
        if not isinstance(t, dict) or not isinstance(t.get('spec'), dict):
            continue
        out.append({
            'key': key, 'label': t.get('label') or key, 'icon': t.get('icon') or 'fa-solid fa-diagram-project',
            'description': t.get('description') or '', 'custom': bool(t.get('custom')),
            'tasks': [{'title': task.get('title') or '', 'icon': TASK_TYPES.get(task.get('task_type'), {}).get('icon', 'fa-solid fa-gear')}
                      for task in t['spec'].get('tasks') or [] if isinstance(task, dict)],
        })
    return out


def _ordered_tasks(workflow):
    """The workflow's tasks, every parent (first or extra) before its children — a topological order,
    so an export / a template always names earlier tasks only."""
    tasks = AdminTaskSchedule.query.filter_by(workflow_id=workflow.id).order_by(AdminTaskSchedule.id).all()
    ids = {t.id for t in tasks}
    parents = {t.id: {p for p in ([t.depends_on_schedule_id] if t.trigger_mode == 'after_task' else [])
                      + [d.parent_id for d in t.extra_dependencies] if p in ids} for t in tasks}
    ordered, placed = [], set()
    while len(ordered) < len(tasks):
        ready = [t for t in tasks if t.id not in placed and parents[t.id] <= placed]
        if not ready:                                   # a cycle (refused on save, but never loop forever)
            ready = [t for t in tasks if t.id not in placed]
        for t in ready:
            ordered.append(t)
            placed.add(t.id)
    return ordered


def export_workflow(workflow, include_files=True) -> dict:
    """A workflow as a spec (no ids, no owner): download it, import it elsewhere, duplicate it.
    Every instance reference is made portable (workflow_portable.py); what may not exist on the
    other side is listed in "warnings"."""
    from app.features.admin.task_scheduler import workflow_portable as portable
    warnings = []
    tasks = _ordered_tasks(workflow)
    refs = {t.id: f't{i + 1}' for i, t in enumerate(tasks)}
    out_tasks = []
    for t in tasks:
        if t.trigger_mode == 'after_task' and t.depends_on_schedule_id in refs:
            trigger = {'after': refs[t.depends_on_schedule_id], 'condition': t.depends_on_condition or 'success'}
            also = [{'ref': refs[d.parent_id], 'condition': d.condition} for d in t.extra_dependencies if d.parent_id in refs]
            if also:
                trigger['also_after'] = also
                trigger['mode'] = t.depends_on_mode or 'all'
        else:
            trigger = {'trigger_mode': t.trigger_mode, 'hour': t.hour, 'minute': t.minute,
                       'timezone': t.timezone or 'UTC'}
            if t.trigger_mode == 'once' and t.run_once_at:
                trigger['run_once_at'] = t.run_once_at.isoformat()
            if t.trigger_mode == 'weekly' and t.days_of_week:
                trigger['days_of_week'] = [int(d) for d in t.days_of_week.split(',') if d.strip().isdigit()]
            if t.trigger_mode == 'monthly':
                trigger['day_of_month'] = t.day_of_month
            if t.trigger_mode == 'cron':
                trigger['cron_expr'] = t.cron_expr
        task = {'ref': refs[t.id], 'title': t.title, 'description': t.description, 'task_type': t.task_type,
                'target_payload': portable.export_payload(t, warnings), 'is_active': bool(t.is_active), 'trigger': trigger,
                'reliability': {k: getattr(t, k) for k in _RELIABILITY_KEYS}}
        if t.position_x is not None and t.position_y is not None:
            task['position'] = [t.position_x, t.position_y]
        out_tasks.append(task)
    notes, files = portable.export_attachments(workflow, include_files, warnings)
    return {'rulezet_workflow': SPEC_VERSION, 'title': workflow.title, 'description': workflow.description,
            'notify_on_failure': bool(workflow.notify_on_failure), 'notify_on_success': bool(workflow.notify_on_success),
            'notify_emails': list(workflow.notify_emails or []),
            'color': workflow.color, 'icon': workflow.icon,
            'warnings': warnings, 'tasks': out_tasks, 'notes': notes, 'files': files}


def create_from_spec(spec, editor, title=None, root_paused=False, report=None):
    """Create a workflow and its tasks from a spec. Returns (workflow, error). `report`, a list,
    gets what could not be carried over from another instance (also pinned as a note). All or nothing:
    a task the task window would refuse (unknown type, missing option, bad trigger) removes the
    workflow again and its error is returned."""
    from app.features.admin.task_scheduler import task_scheduler_core as core
    if not isinstance(spec, dict) or not isinstance(spec.get('tasks'), list):
        return None, 'Not a Rulezet workflow file (no "tasks" list).'
    if len(spec['tasks']) > MAX_TASKS:
        return None, f'A workflow holds {MAX_TASKS} tasks at most.'

    workflow, err = core.create_workflow({
        'title': (title or spec.get('title') or 'Imported workflow')[:150],
        'description': spec.get('description'),
        'notify_on_failure': spec.get('notify_on_failure', True),
        'notify_on_success': spec.get('notify_on_success', False),
        'notify_emails': [e for e in (spec.get('notify_emails') or []) if isinstance(e, str)][:20],
        'color': spec.get('color') if isinstance(spec.get('color'), str) else None,
        'icon': spec.get('icon') if isinstance(spec.get('icon'), str) else None,
    }, editor)
    if err:
        return None, err

    from app.features.admin.task_scheduler import workflow_portable as portable
    warnings = []
    ids = {}
    try:
        for n, task in enumerate(spec['tasks'], start=1):
            if not isinstance(task, dict):
                raise ValueError(f'Task {n} is not an object.')
            trigger = task.get('trigger') or {}
            data = {'workflow_uuid': workflow.uuid, 'title': (task.get('title') or task.get('task_type') or f'Task {n}')[:150],
                    'description': task.get('description'), 'task_type': task.get('task_type'),
                    'is_active': bool(task.get('is_active', True))}
            data['target_payload'] = portable.import_payload(data['title'], task.get('target_payload'), editor, warnings)
            if 'after' in trigger:
                parent = ids.get(trigger.get('after'))
                if not parent:
                    raise ValueError(f'Task "{data["title"]}" runs after "{trigger.get("after")}", which is not an earlier task.')
                data.update(trigger_mode='after_task', depends_on_schedule_id=parent,
                            depends_on_condition=trigger.get('condition') or 'success')
                also = trigger.get('also_after') or []
                if also:
                    if any(not isinstance(a, dict) or a.get('ref') not in ids for a in also):
                        raise ValueError(f'Task "{data["title"]}" waits for a task that is not an earlier one.')
                    data['extra_parents'] = [{'id': ids[a['ref']], 'condition': a.get('condition') or 'success'} for a in also]
                    data['depends_on_mode'] = trigger.get('mode') or 'all'
            else:
                data.update({k: trigger[k] for k in _TRIGGER_KEYS if k in trigger})
                if root_paused:
                    data['is_active'] = False
            rel = task.get('reliability') or {}
            if isinstance(rel, dict):
                data.update({k: rel[k] for k in _RELIABILITY_KEYS if k in rel})
            schedule, err = core.create_schedule(data, editor)
            if err:
                raise ValueError(f'Task "{data["title"]}": {err}')
            pos = task.get('position')
            if isinstance(pos, (list, tuple)) and len(pos) == 2 and all(isinstance(v, (int, float)) for v in pos):
                schedule.position_x, schedule.position_y = float(pos[0]), float(pos[1])
            ids[task.get('ref') or f't{n}'] = schedule.id
        portable.import_attachments(workflow, spec, editor, warnings)
        if warnings:
            portable.report_note(workflow, editor, warnings)
        db.session.commit()
        if report is not None:
            report.extend(warnings)
    except ValueError as e:
        db.session.rollback()
        core.delete_workflow(workflow.uuid)
        return None, str(e)
    return workflow, None


def create_from_template(key, editor, title=None):
    template = templates().get(key)
    if not isinstance(template, dict) or not isinstance(template.get('spec'), dict):
        return None, 'Unknown template.'
    return create_from_spec(template['spec'], editor, title=title, root_paused=True)


def save_as_template(workflow, editor, label=None, description=None):
    """Add a workflow to the templates (setting workflows.templates, history kept on Admin →
    Configuration). Returns (key, error)."""
    from app.core.utils.app_settings import set_setting
    label = (label or workflow.title or '').strip()[:80]
    if not label:
        return None, 'A template needs a name.'
    current = dict(templates())
    key = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')[:50] or 'template'
    base, n = key, 2
    while key in current:
        key, n = f'{base}_{n}', n + 1
    current[key] = {'label': label, 'icon': 'fa-solid fa-diagram-project', 'custom': True,
                    'description': (description or workflow.description or f'Saved from the workflow "{workflow.title}".')[:300],
                    'spec': {k: v for k, v in export_workflow(workflow, include_files=False).items()
                             if k not in ('notes', 'files', 'warnings', 'notify_emails')}}
    set_setting(TEMPLATES_SETTING, current, user_id=editor.id, action='saved')
    return key, None


def delete_template(key, editor):
    """Remove a template saved from a workflow (shipped templates are removed on Admin → Configuration)."""
    from app.core.utils.app_settings import set_setting
    current = dict(templates())
    t = current.get(key)
    if not t:
        return 'Unknown template.'
    if not t.get('custom'):
        return 'Built-in templates are changed on Admin → Configuration (Workflow templates).'
    del current[key]
    set_setting(TEMPLATES_SETTING, current, user_id=editor.id, action='saved')
    return None


def duplicate_workflow(workflow, editor):
    spec = export_workflow(workflow, include_files=False)
    return create_from_spec(spec, editor, title=f'{workflow.title} (copy)'[:150], root_paused=True)


def duplicate_task(schedule, editor):
    """A copy of one task in the same workflow, paused, next to the original on the graph."""
    from app.features.admin.task_scheduler import task_scheduler_core as core
    data = {'workflow_uuid': schedule.workflow.uuid if getattr(schedule, 'workflow', None) else
            AdminWorkflow.query.get(schedule.workflow_id).uuid,
            'title': f'{schedule.title} (copy)'[:150], 'description': schedule.description,
            'task_type': schedule.task_type, 'target_payload': dict(schedule.target_payload or {}),
            'is_active': False, 'trigger_mode': schedule.trigger_mode}
    data.update({k: getattr(schedule, k) for k in _RELIABILITY_KEYS})
    if schedule.trigger_mode == 'after_task':
        data.update(depends_on_schedule_id=schedule.depends_on_schedule_id,
                    depends_on_condition=schedule.depends_on_condition or 'success',
                    depends_on_mode=schedule.depends_on_mode or 'all',
                    extra_parents=[{'id': d.parent_id, 'condition': d.condition} for d in schedule.extra_dependencies])
    else:
        data.update(hour=schedule.hour, minute=schedule.minute, timezone=schedule.timezone or 'UTC',
                    cron_expr=schedule.cron_expr, day_of_month=schedule.day_of_month,
                    run_once_at=schedule.run_once_at.isoformat() if schedule.run_once_at else None,
                    days_of_week=[int(d) for d in (schedule.days_of_week or '').split(',') if d.strip().isdigit()])
    copy, err = core.create_schedule(data, editor)
    if err:
        return None, err
    if schedule.position_x is not None:
        copy.position_x, copy.position_y = schedule.position_x + 40, (schedule.position_y or 0) + 40
        db.session.commit()
    return copy, None
