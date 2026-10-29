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
from app import db
from app.core.db_class.task_scheduler import AdminTaskSchedule, AdminWorkflow

SPEC_VERSION = 1
MAX_TASKS = 50

_TRIGGER_KEYS = ('trigger_mode', 'run_once_at', 'days_of_week', 'day_of_month', 'hour', 'minute',
                 'cron_expr', 'timezone')


def _weekly(day, hour, minute=0):
    return {'trigger_mode': 'weekly', 'days_of_week': [day], 'hour': hour, 'minute': minute, 'timezone': 'UTC'}


def _after(ref, condition='always'):
    return {'after': ref, 'condition': condition}


# Ready-made workflows. Their first task is created paused: nothing runs before an admin has
# looked at it and switched it on (Edit task → Active, or Run now).
TEMPLATES = {
    'weekly_maintenance': {
        'label': 'Weekly maintenance',
        'icon': 'fa-solid fa-screwdriver-wrench',
        'description': 'Every Sunday night: pull the git clones, resync Git Sources, look again for links between '
                       'rules, try the bad rules again, re-read references & metadata, recompute the leaderboard, '
                       'clear the caches.',
        'spec': {
            'title': 'Weekly maintenance',
            'description': 'Keeps rules, links, metadata and figures fresh — every Sunday at 02:00 UTC.',
            'tasks': [
                {'ref': 'pull', 'title': 'Pull the git clones', 'task_type': 'git_cache_pull', 'trigger': _weekly(6, 2)},
                {'ref': 'resync', 'title': 'Resync Git Sources', 'task_type': 'github_repo_resync', 'trigger': _after('pull')},
                {'ref': 'relink', 'title': 'Links between rules', 'task_type': 'relink_rules',
                 'target_payload': {'formats': ['wazuh', 'kunai']}, 'trigger': _after('resync')},
                {'ref': 'bad', 'title': 'Bad rules — retry & link', 'task_type': 'bad_rules_retry',
                 'target_payload': {'formats': ['yara'], 'link_dependencies': True}, 'trigger': _after('relink')},
                {'ref': 'meta', 'title': 'References & metadata', 'task_type': 'reparse_rule_metadata',
                 'target_payload': {'formats': ''}, 'trigger': _after('bad')},
                {'ref': 'points', 'title': 'Recompute the leaderboard', 'task_type': 'gamification_recompute',
                 'trigger': _after('meta')},
                {'ref': 'cache', 'title': 'Clear the caches', 'task_type': 'clear_caches', 'trigger': _after('points')},
            ],
        },
    },
    'bad_rules_cleanup': {
        'label': 'Bad rules clean-up',
        'icon': 'fa-solid fa-broom',
        'description': 'Every day: try every bad rule again (YARA rules naming another rule are imported linked to '
                       'it), look again for links, clear the caches.',
        'spec': {
            'title': 'Bad rules clean-up',
            'description': 'Imports the bad rules that became valid — every day at 04:00 UTC.',
            'tasks': [
                {'ref': 'bad', 'title': 'Bad rules — retry & link', 'task_type': 'bad_rules_retry',
                 'target_payload': {'formats': [], 'link_dependencies': True},
                 'trigger': {'trigger_mode': 'daily', 'hour': 4, 'minute': 0, 'timezone': 'UTC'}},
                {'ref': 'relink', 'title': 'Links between rules', 'task_type': 'relink_rules',
                 'target_payload': {'formats': ['wazuh', 'kunai', 'yara']}, 'trigger': _after('bad', 'success')},
                {'ref': 'cache', 'title': 'Clear the caches', 'task_type': 'clear_caches', 'trigger': _after('relink')},
            ],
        },
    },
    'threat_intel_refresh': {
        'label': 'Threat intel refresh',
        'icon': 'fa-solid fa-satellite-dish',
        'description': 'Every Monday: update the MISP taxonomies & galaxies and the MITRE ATT&CK data, then clear '
                       'the caches.',
        'spec': {
            'title': 'Threat intel refresh',
            'description': 'MISP and MITRE ATT&CK data up to date — every Monday at 03:00 UTC.',
            'tasks': [
                {'ref': 'misp', 'title': 'Update MISP taxonomies & galaxies', 'task_type': 'misp_update_data',
                 'trigger': _weekly(0, 3)},
                {'ref': 'attack', 'title': 'Update MITRE ATT&CK data', 'task_type': 'attack_update_data',
                 'trigger': _after('misp')},
                {'ref': 'cache', 'title': 'Clear the caches', 'task_type': 'clear_caches', 'trigger': _after('attack')},
            ],
        },
    },
    'nightly_backup': {
        'label': 'Nightly backup',
        'icon': 'fa-solid fa-database',
        'description': 'Every night at 01:00 UTC: a backup of the database.',
        'spec': {
            'title': 'Nightly backup',
            'description': 'A database backup every night at 01:00 UTC.',
            'tasks': [
                {'ref': 'backup', 'title': 'Database backup', 'task_type': 'db_backup',
                 'trigger': {'trigger_mode': 'daily', 'hour': 1, 'minute': 0, 'timezone': 'UTC'}},
            ],
        },
    },
}


def serialize_templates():
    """Templates for the "New workflow" gallery: their card and the tasks they create."""
    from app.features.admin.task_scheduler.task_types import TASK_TYPES
    out = []
    for key, t in TEMPLATES.items():
        out.append({
            'key': key, 'label': t['label'], 'icon': t['icon'], 'description': t['description'],
            'tasks': [{'title': task['title'], 'icon': TASK_TYPES.get(task['task_type'], {}).get('icon', 'fa-solid fa-gear')}
                      for task in t['spec']['tasks']],
        })
    return out


def _ordered_tasks(workflow):
    """The workflow's tasks, parents before their children (roots first, then down each chain)."""
    tasks = AdminTaskSchedule.query.filter_by(workflow_id=workflow.id).order_by(AdminTaskSchedule.id).all()
    by_parent = {}
    for t in tasks:
        by_parent.setdefault(t.depends_on_schedule_id, []).append(t)
    ordered, seen = [], set()
    stack = list(reversed(by_parent.get(None, [])))
    while stack:
        t = stack.pop()
        if t.id in seen:
            continue
        seen.add(t.id)
        ordered.append(t)
        stack.extend(reversed(by_parent.get(t.id, [])))
    ordered += [t for t in tasks if t.id not in seen]      # orphans (parent outside the workflow)
    return ordered


def export_workflow(workflow) -> dict:
    """A workflow as a spec (no ids, no owner): download it, import it elsewhere, duplicate it."""
    tasks = _ordered_tasks(workflow)
    refs = {t.id: f't{i + 1}' for i, t in enumerate(tasks)}
    out_tasks = []
    for t in tasks:
        if t.trigger_mode == 'after_task' and t.depends_on_schedule_id in refs:
            trigger = {'after': refs[t.depends_on_schedule_id], 'condition': t.depends_on_condition or 'success'}
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
                'target_payload': t.target_payload or {}, 'is_active': bool(t.is_active), 'trigger': trigger}
        if t.position_x is not None and t.position_y is not None:
            task['position'] = [t.position_x, t.position_y]
        out_tasks.append(task)
    return {'rulezet_workflow': SPEC_VERSION, 'title': workflow.title, 'description': workflow.description,
            'notify_on_failure': bool(workflow.notify_on_failure), 'notify_on_success': bool(workflow.notify_on_success),
            'tasks': out_tasks}


def create_from_spec(spec, editor, title=None, root_paused=False):
    """Create a workflow and its tasks from a spec. Returns (workflow, error). All or nothing:
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
    }, editor)
    if err:
        return None, err

    ids = {}
    try:
        for n, task in enumerate(spec['tasks'], start=1):
            if not isinstance(task, dict):
                raise ValueError(f'Task {n} is not an object.')
            trigger = task.get('trigger') or {}
            data = {'workflow_uuid': workflow.uuid, 'title': (task.get('title') or task.get('task_type') or f'Task {n}')[:150],
                    'description': task.get('description'), 'task_type': task.get('task_type'),
                    'target_payload': task.get('target_payload') or {},
                    'is_active': bool(task.get('is_active', True))}
            if 'after' in trigger:
                parent = ids.get(trigger.get('after'))
                if not parent:
                    raise ValueError(f'Task "{data["title"]}" runs after "{trigger.get("after")}", which is not an earlier task.')
                data.update(trigger_mode='after_task', depends_on_schedule_id=parent,
                            depends_on_condition=trigger.get('condition') or 'success')
            else:
                data.update({k: trigger[k] for k in _TRIGGER_KEYS if k in trigger})
                if root_paused:
                    data['is_active'] = False
            schedule, err = core.create_schedule(data, editor)
            if err:
                raise ValueError(f'Task "{data["title"]}": {err}')
            pos = task.get('position')
            if isinstance(pos, (list, tuple)) and len(pos) == 2 and all(isinstance(v, (int, float)) for v in pos):
                schedule.position_x, schedule.position_y = float(pos[0]), float(pos[1])
            ids[task.get('ref') or f't{n}'] = schedule.id
        db.session.commit()
    except ValueError as e:
        db.session.rollback()
        core.delete_workflow(workflow.uuid)
        return None, str(e)
    return workflow, None


def create_from_template(key, editor, title=None):
    template = TEMPLATES.get(key)
    if not template:
        return None, 'Unknown template.'
    return create_from_spec(template['spec'], editor, title=title, root_paused=True)


def duplicate_workflow(workflow, editor):
    spec = export_workflow(workflow)
    return create_from_spec(spec, editor, title=f'{workflow.title} (copy)'[:150], root_paused=True)


def duplicate_task(schedule, editor):
    """A copy of one task in the same workflow, paused, next to the original on the graph."""
    from app.features.admin.task_scheduler import task_scheduler_core as core
    data = {'workflow_uuid': schedule.workflow.uuid if getattr(schedule, 'workflow', None) else
            AdminWorkflow.query.get(schedule.workflow_id).uuid,
            'title': f'{schedule.title} (copy)'[:150], 'description': schedule.description,
            'task_type': schedule.task_type, 'target_payload': dict(schedule.target_payload or {}),
            'is_active': False, 'trigger_mode': schedule.trigger_mode}
    if schedule.trigger_mode == 'after_task':
        data.update(depends_on_schedule_id=schedule.depends_on_schedule_id,
                    depends_on_condition=schedule.depends_on_condition or 'success')
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
