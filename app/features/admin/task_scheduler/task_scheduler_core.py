"""
task_scheduler_core.py — CRUD + validation for AdminTaskSchedule (the
generalized Admin Task Scheduler). Modeled directly on
sync_schedule_core.py: keeps the live APScheduler trigger in lockstep with
the DB row on every mutation so a restart is never needed to pick up a
change. See docs/design/admin_task_scheduler.md for the full design.
"""
import datetime
import re
import uuid as _uuid_mod

from flask import current_app

from app import db
from app.core.db_class.task_scheduler import AdminTaskSchedule, AdminWorkflow
from app.features.admin.task_scheduler.task_types import TASK_TYPES
from app.features.admin.task_scheduler.scheduler_engine import _creates_cycle

VALID_TRIGGER_MODES = ('once', 'daily', 'weekly', 'monthly', 'cron', 'after_task')

_EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def _clean_notify_emails(raw):
    """Defense-in-depth: drop anything that isn't a plausible single email
    address before it ever reaches Message(recipients=...) — Flask-Mail
    already rejects CRLF in a header value, but this feature shouldn't rely
    on that alone."""
    if not raw:
        return []
    # 254: the longest valid address (RFC 5321) — also bounds the regex's work
    return [e.strip() for e in raw if isinstance(e, str) and len(e.strip()) <= 254 and _EMAIL_RE.match(e.strip())]


# ─── Workflows — the container an admin creates first, then assigns tasks into ──

def get_workflow_list_page(page=1, per_page=20, search='', sort='created_at', direction='desc'):
    per_page = max(1, min(per_page or 20, 100))
    query = AdminWorkflow.query
    if search:
        query = query.filter(AdminWorkflow.title.ilike(f"%{search}%"))
    sort_col = {
        'title': AdminWorkflow.title,
        'created_at': AdminWorkflow.created_at,
        'updated_at': AdminWorkflow.updated_at,
    }.get(sort, AdminWorkflow.created_at)
    query = query.order_by(sort_col.asc() if direction == 'asc' else sort_col.desc())
    return query.paginate(page=page, per_page=per_page, max_per_page=100)


def get_workflow_by_uuid(workflow_uuid):
    return AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()


def create_workflow(data, editor):
    title = (data.get('title') or '').strip()
    if not title:
        return None, "Title is required."

    workflow = AdminWorkflow(
        uuid=str(_uuid_mod.uuid4()),
        title=title,
        description=data.get('description'),
        editor_id=editor.id,
        is_active=bool(data.get('is_active', True)),
        notify_on_failure=bool(data.get('notify_on_failure', True)),
        notify_on_success=bool(data.get('notify_on_success', False)),
        notify_emails=_clean_notify_emails(data.get('notify_emails')),
    )
    db.session.add(workflow)
    db.session.commit()
    return workflow, None


def update_workflow(workflow_uuid, data):
    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return None, "Workflow not found."

    title = (data.get('title') or '').strip()
    if not title:
        return None, "Title is required."

    workflow.title = title
    workflow.description = data.get('description')
    workflow.is_active = bool(data.get('is_active', workflow.is_active))
    workflow.notify_on_failure = bool(data.get('notify_on_failure', workflow.notify_on_failure))
    workflow.notify_on_success = bool(data.get('notify_on_success', workflow.notify_on_success))
    if 'notify_emails' in data:
        workflow.notify_emails = _clean_notify_emails(data.get('notify_emails'))

    if data.get('launch'):
        err = _set_workflow_launch(workflow, data['launch'])
        if err:
            db.session.rollback()
            return None, err

    db.session.commit()
    return workflow, None


def _set_workflow_launch(workflow, launch):
    """'Launch date' from the Edit Workflow modal: the workflow starts when
    its first task does, so this rewrites that task's time trigger (and
    re-activates it — giving it a launch date means it should run)."""
    from app.features.admin.task_scheduler.scheduler_engine import workflow_first_task
    task = workflow_first_task(workflow)
    if not task:
        return "Add a task to this workflow first — the launch date is the date of its first task."
    if launch.get('trigger_mode') not in ('once', 'daily', 'weekly', 'monthly', 'cron'):
        return "The launch date must be a date or a recurrence."
    ok, err = _validate_trigger(launch, schedule_id=task.id, workflow_id=workflow.id)
    if not ok:
        return err
    _apply_trigger_fields(task, launch)
    task.is_active = True
    _register_live(task)
    return None


def delete_workflow(workflow_uuid):
    from app.features.admin.task_scheduler.scheduler_engine import unregister_schedule
    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return False
    for task in workflow.tasks:
        unregister_schedule(task.uuid)
    db.session.delete(workflow)  # cascades to its tasks (AdminWorkflow.tasks relationship)
    db.session.commit()
    return True


# ─── Tasks — always scoped to a workflow ───────────────────────────────────────

def _validate_trigger(data, schedule_id=None, workflow_id=None):
    mode = data.get('trigger_mode')
    if mode not in VALID_TRIGGER_MODES:
        return False, f"Invalid trigger_mode: {mode!r}"

    if mode == 'once':
        if not data.get('run_once_at'):
            return False, "run_once_at is required when trigger_mode is 'once'."
        try:
            datetime.datetime.fromisoformat(data['run_once_at'])
        except ValueError:
            return False, "run_once_at must be an ISO datetime string."
        return True, None

    if mode == 'after_task':
        depends_on_id = data.get('depends_on_schedule_id')
        if not depends_on_id:
            return False, "depends_on_schedule_id is required when trigger_mode is 'after_task'."
        parent = AdminTaskSchedule.query.get(depends_on_id)
        if not parent:
            return False, "The parent task to depend on was not found."
        if workflow_id is not None and parent.workflow_id != workflow_id:
            return False, "A task can only depend on another task within the same workflow."
        if depends_on_id == schedule_id:
            return False, "A task cannot depend on itself."
        if _creates_cycle(schedule_id, depends_on_id) or (schedule_id and _reaches(depends_on_id, schedule_id)):
            return False, "This dependency would create a cycle between tasks."
        if data.get('depends_on_condition') not in ('success', 'failure', 'always'):
            return False, "depends_on_condition must be 'success', 'failure', or 'always'."
        return True, None

    if mode == 'weekly':
        dow = data.get('days_of_week') or []
        if not isinstance(dow, list) or not dow or not all(isinstance(d, int) and 0 <= d <= 6 for d in dow):
            return False, "days_of_week must be a non-empty list of integers 0-6 (0 = Monday)."

    if mode == 'monthly':
        dom = data.get('day_of_month')
        if dom is None or not (dom == -1 or 1 <= dom <= 31):
            return False, "day_of_month must be 1-31, or -1 for the last day of the month."

    if mode == 'cron':
        cron_expr = data.get('cron_expr')
        if not cron_expr:
            return False, "cron_expr is required when trigger_mode is 'cron'."
        try:
            from apscheduler.triggers.cron import CronTrigger
            CronTrigger.from_crontab(cron_expr, timezone=data.get('timezone') or 'UTC')
        except Exception as e:
            return False, f"Invalid cron expression: {e}"

    hour = data.get('hour', 3)
    minute = data.get('minute', 0)
    if not isinstance(hour, int) or not (0 <= hour <= 23):
        return False, "hour must be an integer 0-23."
    if not isinstance(minute, int) or not (0 <= minute <= 59):
        return False, "minute must be an integer 0-59."

    return True, None


def _apply_trigger_fields(schedule, data):
    mode = data.get('trigger_mode')
    schedule.trigger_mode = mode

    schedule.run_once_at = None
    schedule.days_of_week = None
    schedule.day_of_month = None
    schedule.cron_expr = None
    schedule.depends_on_schedule_id = None
    schedule.depends_on_condition = 'success'

    if mode == 'once':
        run_at = datetime.datetime.fromisoformat(data['run_once_at'])
        if run_at.tzinfo is not None:
            # The picker sends an absolute instant (toISOString → 'Z') —
            # store it as naive UTC, run_once_at being read in self.timezone.
            schedule.run_once_at = run_at.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            schedule.timezone = 'UTC'
        else:
            schedule.run_once_at = run_at
            schedule.timezone = data.get('timezone') or schedule.timezone or 'UTC'
        return
    if mode == 'after_task':
        schedule.depends_on_schedule_id = data.get('depends_on_schedule_id')
        schedule.depends_on_condition = data.get('depends_on_condition', 'success')
        return

    if mode == 'weekly':
        schedule.days_of_week = ','.join(str(d) for d in data.get('days_of_week', []))
    elif mode == 'monthly':
        schedule.day_of_month = data.get('day_of_month')
    elif mode == 'cron':
        schedule.cron_expr = data.get('cron_expr')

    schedule.hour = data.get('hour', 3)
    schedule.minute = data.get('minute', 0)
    schedule.timezone = data.get('timezone') or 'UTC'


def _apply_extras(schedule, data):
    """The task window's extra settings: more parents (all / any), retries, time limit, auto-pause,
    catch-up. Only keys present in data are changed. Returns an error string or None."""
    from app.core.db_class.task_scheduler import AdminTaskDependency

    def _int(key, lo, hi, allow_none=False):
        if key not in data:
            return getattr(schedule, key), None
        v = data.get(key)
        if v in (None, '') and allow_none:
            return None, None
        try:
            v = int(v)
        except (TypeError, ValueError):
            return None, f"{key} must be a number."
        if not lo <= v <= hi:
            return None, f"{key} must be between {lo} and {hi}."
        return v, None

    for key, lo, hi, none_ok in (('max_retries', 0, 5, False), ('retry_delay_minutes', 1, 1440, False),
                                 ('timeout_minutes', 1, 10080, True), ('max_consecutive_failures', 0, 50, False)):
        v, err = _int(key, lo, hi, none_ok)
        if err:
            return err
        setattr(schedule, key, v)
    if 'catch_up' in data:
        schedule.catch_up = bool(data.get('catch_up'))
    if 'depends_on_mode' in data:
        if data['depends_on_mode'] not in ('all', 'any'):
            return "depends_on_mode must be 'all' or 'any'."
        schedule.depends_on_mode = data['depends_on_mode']
    if schedule.is_active and schedule.auto_disabled_at:      # switched back on by an admin
        schedule.auto_disabled_at = None
        schedule.consecutive_failures = 0

    if 'extra_parents' in data:
        extra = data.get('extra_parents') or []
        if not isinstance(extra, list) or len(extra) > 20:
            return "extra_parents must be a list (20 at most)."
        wanted = {}
        for item in extra:
            pid, cond = (item or {}).get('id'), (item or {}).get('condition', 'success')
            if cond not in ('success', 'failure', 'always'):
                return "A parent's condition must be success, failure or always."
            parent = AdminTaskSchedule.query.get(pid) if isinstance(pid, int) else None
            if not parent or parent.workflow_id != schedule.workflow_id:
                return "A task can only wait for tasks of the same workflow."
            if parent.id == schedule.id or (schedule.id and _reaches(parent.id, schedule.id)):
                return f'Waiting for "{parent.title}" would create a cycle between tasks.'
            if parent.id != schedule.depends_on_schedule_id:
                wanted[parent.id] = cond
        if wanted and schedule.trigger_mode != 'after_task':
            return "Extra parents need the trigger \"After another task\"."
        for dep in list(schedule.extra_dependencies):
            if dep.parent_id not in wanted:
                db.session.delete(dep)
            else:
                dep.condition = wanted.pop(dep.parent_id)
        for pid, cond in wanted.items():
            schedule.extra_dependencies.append(AdminTaskDependency(parent_id=pid, condition=cond))
    elif schedule.trigger_mode != 'after_task':
        for dep in list(schedule.extra_dependencies):
            db.session.delete(dep)
    return None


def _reaches(start_id, target_id):
    """Whether target_id is upstream of start_id through any parent (first or extra) — a link from
    target to start would then be a cycle."""
    from app.core.db_class.task_scheduler import AdminTaskDependency
    seen, stack = set(), [start_id]
    while stack:
        cur = stack.pop()
        if cur == target_id:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        task = AdminTaskSchedule.query.get(cur)
        if task and task.depends_on_schedule_id:
            stack.append(task.depends_on_schedule_id)
        stack += [d.parent_id for d in AdminTaskDependency.query.filter_by(schedule_id=cur).all()]
    return False


def _build_target_payload(task_type, target_payload):
    """Merge in any registry-level fixed_payload (e.g. activity_log_purge
    always forces delete_all=True) — client-supplied keys never override
    these, since they express a deliberate scheduling-safety choice, not a
    per-run preference."""
    task_def = TASK_TYPES[task_type]
    payload = dict(target_payload) if isinstance(target_payload, dict) else {}
    payload.update(task_def.get('fixed_payload', {}))
    return payload


def _validate_target_payload(task_type, payload):
    """Per-type sanity checks on what a task will hand its job — catches a
    blank repo URL or an empty format list at save time instead of as a
    failed run in the middle of the night. Returns an error string or None."""
    task_def = TASK_TYPES[task_type]
    labels = {o['key']: o['label'] for o in task_def.get('extra_options', [])}
    for key in task_def.get('required_options', []):
        value = payload.get(key)
        if value in (None, '', [], {}):
            return f"\"{labels.get(key, key)}\" is required."

    if task_type == 'github_import':
        from app.features.rule.rule_format.utils_format.utils_import_update import valider_repo_github
        url = payload.get('url')
        if not isinstance(url, str) or not valider_repo_github(url.strip(), is_generic_source=True):
            return "Enter a valid git repository URL (https://host/owner/repo — GitHub, GitLab, Gitea, …)."
        for key in ('branch', 'license'):
            if payload.get(key) is not None and not isinstance(payload.get(key), str):
                return f"{key} must be text."

    if task_type == 'native_tags_import':
        from app.features.tags.imported_tags_core import FORMAT_TAG_SOURCES
        formats = payload.get('formats')
        if not isinstance(formats, list) or any(f not in FORMAT_TAG_SOURCES for f in formats):
            return "Unsupported rule format in the list."

    if task_type in ('field_parser', 'platform_tagging'):
        from app.features.rule.field_parser_core import get_config, ALL_PLATFORM_CONFIGS
        config_id = payload.get('config_id')
        if not (task_type == 'platform_tagging' and config_id == ALL_PLATFORM_CONFIGS):
            config_type = 'field_parser' if task_type == 'field_parser' else 'platform_tags'
            try:
                config_id = int(config_id)
            except (TypeError, ValueError):
                return "Choose a saved config."
            if not get_config(config_id, config_type=config_type):
                return "The chosen config no longer exists."
            payload['config_id'] = config_id

    for key in ('limit', 'batch_size', 'max_seconds'):
        if key in payload and payload[key] not in (None, ''):
            try:
                if int(payload[key]) <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return f"\"{labels.get(key, key)}\" must be a positive number."
    return None


def run_task_type_now(task_type, target_payload, title, editor):
    """The task form's "Now" trigger: one job of this task type, right now,
    with no schedule saved — same job_type / fixed_payload / validation as
    a scheduled firing."""
    from app.features.jobs.jobs_core import create_job
    if task_type not in TASK_TYPES:
        return None, f"Unknown task_type: {task_type!r}"
    if target_payload is not None and not isinstance(target_payload, dict):
        return None, "target_payload must be an object."
    payload = _build_target_payload(task_type, target_payload)
    err = _validate_target_payload(task_type, payload)
    if err:
        return None, err
    task_def = TASK_TYPES[task_type]
    title = (title or '').strip() if isinstance(title, str) else ''
    label = f"{title} — {task_def['label']}" if title else task_def['label']
    job = create_job(job_type=task_def['job_type'], payload=payload, label=label[:255], created_by=editor.id)
    if job is None:
        return None, "Could not queue the job."
    return job, None


def _register_live(schedule):
    from app.features.admin.task_scheduler.scheduler_engine import register_schedule
    register_schedule(current_app._get_current_object(), schedule)
    db.session.commit()


def get_schedule_list_page(workflow_id, page=1, per_page=20, search='', sort='created_at', direction='desc', task_type=None):
    per_page = max(1, min(per_page or 20, 100))
    query = AdminTaskSchedule.query.filter_by(workflow_id=workflow_id)
    if search:
        query = query.filter(AdminTaskSchedule.title.ilike(f"%{search}%"))
    if task_type:
        query = query.filter(AdminTaskSchedule.task_type == task_type)
    sort_col = {
        'title': AdminTaskSchedule.title,
        'next_run_at': AdminTaskSchedule.next_run_at,
        'last_run_at': AdminTaskSchedule.last_run_at,
        'created_at': AdminTaskSchedule.created_at,
    }.get(sort, AdminTaskSchedule.created_at)
    query = query.order_by(sort_col.asc() if direction == 'asc' else sort_col.desc())
    return query.paginate(page=page, per_page=per_page, max_per_page=100)


def create_schedule(data, editor):
    workflow = AdminWorkflow.query.filter_by(uuid=data.get('workflow_uuid')).first()
    if not workflow:
        return None, "Workflow not found."

    task_type = data.get('task_type')
    if task_type not in TASK_TYPES:
        return None, f"Unknown task_type: {task_type!r}"

    ok, err = _validate_trigger(data, workflow_id=workflow.id)
    if not ok:
        return None, err

    title = (data.get('title') or '').strip()
    if not title:
        return None, "Title is required."

    target_payload = _build_target_payload(task_type, data.get('target_payload'))
    err = _validate_target_payload(task_type, target_payload)
    if err:
        return None, err

    schedule = AdminTaskSchedule(
        uuid=str(_uuid_mod.uuid4()),
        title=title,
        description=data.get('description'),
        editor_id=editor.id,
        workflow_id=workflow.id,
        task_type=task_type,
        target_payload=target_payload,
        is_active=bool(data.get('is_active', True)),
    )
    _apply_trigger_fields(schedule, data)
    db.session.add(schedule)
    db.session.flush()
    err = _apply_extras(schedule, data)
    if err:
        db.session.rollback()
        return None, err
    db.session.commit()

    _register_live(schedule)
    return schedule, None


def update_schedule(schedule_uuid, data):
    schedule = AdminTaskSchedule.query.filter_by(uuid=schedule_uuid).first()
    if not schedule:
        return None, "Schedule not found."

    task_type = data.get('task_type', schedule.task_type)
    if task_type not in TASK_TYPES:
        return None, f"Unknown task_type: {task_type!r}"

    # A task's workflow is fixed at creation — Phase 1 does not support
    # moving a task between workflows (a cross-workflow depends_on would
    # need to be untangled first).
    ok, err = _validate_trigger(data, schedule_id=schedule.id, workflow_id=schedule.workflow_id)
    if not ok:
        return None, err

    title = (data.get('title') or '').strip()
    if not title:
        return None, "Title is required."

    if 'target_payload' in data:
        target_payload = _build_target_payload(task_type, data.get('target_payload'))
        err = _validate_target_payload(task_type, target_payload)
        if err:
            return None, err

    schedule.title = title
    schedule.description = data.get('description')
    schedule.is_active = bool(data.get('is_active', schedule.is_active))
    schedule.task_type = task_type
    if 'target_payload' in data:
        schedule.target_payload = target_payload
    _apply_trigger_fields(schedule, data)
    err = _apply_extras(schedule, data)
    if err:
        db.session.rollback()
        return None, err

    db.session.commit()
    _register_live(schedule)
    return schedule, None


def delete_schedule(schedule_uuid):
    from app.features.admin.task_scheduler.scheduler_engine import unregister_schedule
    schedule = AdminTaskSchedule.query.filter_by(uuid=schedule_uuid).first()
    if not schedule:
        return False
    unregister_schedule(schedule.uuid)
    # Any child schedule depending on this one loses its parent — surface
    # that in the UI (depends_on_schedule_title becomes null) rather than
    # silently leaving a dangling reference.
    AdminTaskSchedule.query.filter_by(depends_on_schedule_id=schedule.id).update(
        {"depends_on_schedule_id": None, "is_active": False}
    )
    # it is no longer an extra parent of anything either (all / any waits)
    from app.core.db_class.task_scheduler import AdminTaskDependency
    AdminTaskDependency.query.filter_by(parent_id=schedule.id).delete()
    db.session.delete(schedule)
    db.session.commit()
    return True


def _resolve_bulk_targets(workflow_id, mode, filters, selected_uuids, excluded_uuids):
    filters = filters or {}
    query = AdminTaskSchedule.query.filter_by(workflow_id=workflow_id)
    if filters.get('search'):
        query = query.filter(AdminTaskSchedule.title.ilike(f"%{filters['search']}%"))

    if mode == 'all':
        excluded = set(excluded_uuids or [])
        return [s for s in query.all() if s.uuid not in excluded]
    return query.filter(AdminTaskSchedule.uuid.in_(selected_uuids or [])).all()


def bulk_delete_schedules(workflow_id, mode, filters, selected_uuids, excluded_uuids):
    from app.features.admin.task_scheduler.scheduler_engine import unregister_schedule
    targets = _resolve_bulk_targets(workflow_id, mode, filters, selected_uuids, excluded_uuids)

    count = 0
    for schedule in targets:
        unregister_schedule(schedule.uuid)
        AdminTaskSchedule.query.filter_by(depends_on_schedule_id=schedule.id).update(
            {"depends_on_schedule_id": None, "is_active": False}
        )
        db.session.delete(schedule)
        count += 1
    db.session.commit()
    return count


def bulk_set_active_schedules(workflow_id, mode, filters, selected_uuids, excluded_uuids, is_active):
    targets = _resolve_bulk_targets(workflow_id, mode, filters, selected_uuids, excluded_uuids)

    count = 0
    for schedule in targets:
        schedule.is_active = is_active
        _register_live(schedule)
        count += 1
    db.session.commit()
    return count


def run_schedule_now(schedule_uuid):
    """Manually trigger one run immediately, outside its normal cadence —
    reuses the exact same _fire_schedule the scheduler/chaining itself
    calls, so a manual run creates an identical AdminTaskRun + BackgroundJob.
    Returns the new run's job_uuid (still truthy, like the old `True`) so the
    caller can jump straight to that job's detail instead of waiting for the
    next live-status poll to discover it."""
    from app.core.db_class.task_scheduler import AdminTaskRun
    from app.features.admin.task_scheduler.scheduler_engine import _fire_schedule
    schedule = AdminTaskSchedule.query.filter_by(uuid=schedule_uuid).first()
    if not schedule:
        return False, "Schedule not found."
    if not schedule.is_active:
        return False, "Task is paused — activate it before running it manually."
    _fire_schedule(current_app._get_current_object(), schedule.uuid)
    run = AdminTaskRun.query.filter_by(schedule_id=schedule.id).order_by(AdminTaskRun.started_at.desc()).first()
    return (run.job_uuid if run else True), None


def run_workflow_now(workflow_uuid, triggered_by=None):
    """Fire every active first task of the workflow (see
    workflow_root_tasks) right now — the rest of the chain follows on its
    own via on_job_finished() as each root's job completes. Lets an admin
    launch the whole pipeline with one click instead of running its first
    task."""
    from app.features.admin.task_scheduler.scheduler_engine import workflow_root_tasks
    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return False, "Workflow not found."

    roots = [t for t in workflow_root_tasks(workflow) if t.is_active]
    if not roots:
        return False, "This workflow has no independently-triggered (non-paused) task to start from."

    return launch_workflow(workflow, roots, triggered_by=triggered_by), None


def launch_workflow(workflow, roots, triggered_by=None):
    """Shared by the Run Workflow button and the scheduler (a first task's
    time came — scheduler_engine.tick): records one AdminWorkflowRun for the
    launch-history table and fires the given root tasks under it; the
    chain's workflow_run_id is propagated to every task it triggers through
    on_job_finished(). triggered_by is None for a scheduled launch."""
    from app.core.db_class.task_scheduler import AdminWorkflowRun
    from app.features.admin.task_scheduler.scheduler_engine import _fire_schedule

    workflow_run = AdminWorkflowRun(
        uuid=str(_uuid_mod.uuid4()), workflow_id=workflow.id,
        triggered_by_id=triggered_by.id if triggered_by else None,
    )
    db.session.add(workflow_run)
    db.session.commit()

    app = current_app._get_current_object()
    for task in roots:
        _fire_schedule(app, task.uuid, workflow_run_id=workflow_run.id)

    try:
        from app.features.notification.notification_core import notify_admins_workflow_run_started
        notify_admins_workflow_run_started(workflow_run)
    except Exception as e:
        current_app.logger.warning(f"notify_admins_workflow_run_started failed: {e}")

    try:
        from app.features.admin.task_scheduler.notifications import maybe_send_workflow_run_alert
        maybe_send_workflow_run_alert(workflow, 'started')
    except Exception as e:
        current_app.logger.warning(f"maybe_send_workflow_run_alert(started) failed: {e}")

    return workflow_run


def stop_workflow_jobs(workflow_uuid):
    """Cancel every currently pending/running job among this workflow's
    tasks — the 'Stop Workflow' button. Cooperative like every other cancel
    in the app: a handler only actually halts at its next _is_cancelled()
    checkpoint (see job_worker.py), it isn't a hard kill. Cancelling a job
    directly (not via job_worker's own completion path) does NOT trigger
    on_job_finished(), so the chain simply stops — no child task fires from
    a cancelled run, which is exactly the intent of stopping a workflow."""
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.task_scheduler import AdminTaskRun
    from app.features.jobs.jobs_core import cancel_job

    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return None, "Workflow not found."

    stopped = 0
    touched_run_ids = set()
    for task in workflow.tasks:
        run = (AdminTaskRun.query.filter_by(schedule_id=task.id)
               .order_by(AdminTaskRun.started_at.desc()).first())
        if not run or not run.job_uuid:
            continue
        job = BackgroundJob.query.filter_by(uuid=run.job_uuid).first()
        if job and job.status in ('pending', 'running', 'paused'):
            ok, _ = cancel_job(job)
            if ok:
                stopped += 1
                touched_run_ids.add(run.workflow_run_id)

    for run_id in touched_run_ids:
        _finalize_workflow_run_if_done(run_id)

    return stopped, None


def _finalize_workflow_run_if_done(workflow_run_id):
    """Fire the one 'workflow run finished' notification for a launch once
    every task run tied to it has reached a terminal state — called after
    each settling task (see on_job_finished in scheduler_engine.py) and
    after Stop Workflow, since a cancelled job never goes through
    on_job_finished on its own. Idempotent: skips if already notified."""
    if not workflow_run_id:
        return
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.notification import Notification
    from app.core.db_class.task_scheduler import AdminTaskRun, AdminWorkflowRun

    workflow_run = AdminWorkflowRun.query.get(workflow_run_id)
    if not workflow_run:
        return

    task_runs = AdminTaskRun.query.filter_by(workflow_run_id=workflow_run_id).all()
    if not task_runs:
        return

    statuses = []
    for tr in task_runs:
        job = BackgroundJob.query.filter_by(uuid=tr.job_uuid).first() if tr.job_uuid else None
        statuses.append(job.status if job else tr.status)

    if any(s in ('pending', 'running', 'paused') for s in statuses):
        return  # still in flight — a chained child may still fire

    already_notified = Notification.query.filter_by(
        job_uuid=workflow_run.uuid, notif_type='workflow_run_finished').first()
    if already_notified:
        return

    done_count = sum(1 for s in statuses if s == 'done')
    failed_count = sum(1 for s in statuses if s == 'failed')
    cancelled_count = sum(1 for s in statuses if s == 'cancelled')

    try:
        from app.features.notification.notification_core import notify_admins_workflow_run_finished
        notify_admins_workflow_run_finished(
            workflow_run, done_count=done_count, failed_count=failed_count,
            cancelled_count=cancelled_count, task_count=len(statuses),
        )
    except Exception as e:
        current_app.logger.warning(f"notify_admins_workflow_run_finished failed: {e}")

    # One email for the whole launch, not one per task — cancelled-with-no-
    # failures was a deliberate Stop Workflow, not an outcome worth emailing.
    if failed_count or (done_count and not cancelled_count):
        try:
            from app.features.admin.task_scheduler.notifications import maybe_send_workflow_run_alert
            summary = f"{done_count}/{len(statuses)} task(s) done" + (f", {failed_count} failed" if failed_count else "")
            maybe_send_workflow_run_alert(workflow_run.workflow, 'failure' if failed_count else 'success', summary)
        except Exception as e:
            current_app.logger.warning(f"maybe_send_workflow_run_alert(finished) failed: {e}")


def get_workflow_runs_page(workflow_uuid, page=1, per_page=10):
    """Launch history — one row per 'Run Workflow' click, each summarizing
    every task run it directly fired or chained afterwards."""
    from app.core.db_class.task_scheduler import AdminWorkflowRun
    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return None
    return (AdminWorkflowRun.query.filter_by(workflow_id=workflow.id)
            .order_by(AdminWorkflowRun.started_at.desc())
            .paginate(page=page, per_page=min(per_page or 10, 50), max_per_page=50))


def bulk_delete_workflow_runs(workflow_uuid, run_uuids):
    """Delete one or more launch-history entries. Only removes the
    bookkeeping row — the AdminTaskRun rows it grouped keep existing (their
    workflow_run_id is set to NULL by the FK's ON DELETE SET NULL), so a
    task's own last_run_status/logs are unaffected."""
    from app.core.db_class.task_scheduler import AdminWorkflowRun
    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return None, "Workflow not found."

    targets = AdminWorkflowRun.query.filter(
        AdminWorkflowRun.workflow_id == workflow.id,
        AdminWorkflowRun.uuid.in_(run_uuids or []),
    ).all()
    count = len(targets)
    for run in targets:
        db.session.delete(run)
    db.session.commit()
    return count, None


def serialize_workflow_run(run):
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.task_scheduler import AdminTaskRun

    db.session.expire_all()
    task_runs = AdminTaskRun.query.filter_by(workflow_run_id=run.id).order_by(AdminTaskRun.started_at.asc()).all()
    tasks = []
    last_finish = None
    for tr in task_runs:
        job = BackgroundJob.query.filter_by(uuid=tr.job_uuid).first() if tr.job_uuid else None
        job_status = job.status if job else tr.status
        finished = (job.finished_at if job else None) or tr.finished_at
        if finished is not None:
            if finished.tzinfo is not None:
                finished = finished.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            last_finish = max(last_finish, finished) if last_finish else finished
        tasks.append({
            "task_uuid": tr.schedule.uuid,
            "task_title": tr.schedule.title,
            "task_type": tr.schedule.task_type,
            "job_uuid": tr.job_uuid,
            "status": job_status,
            "duration_seconds": _seconds_between(job.started_at, job.finished_at) if job else None,
        })

    statuses = [t["status"] for t in tasks]
    if any(s in ('pending', 'running') for s in statuses):
        overall = 'running'
    elif any(s == 'failed' for s in statuses):
        overall = 'failed'
    elif any(s == 'cancelled' for s in statuses):
        overall = 'cancelled'
    elif statuses:
        overall = 'done'
    else:
        overall = 'pending'

    return {
        "uuid": run.uuid,
        "started_at": run.started_at.strftime('%Y-%m-%d %H:%M') if run.started_at else None,
        "triggered_by": {
            "id": run.triggered_by.id,
            "name": f"{run.triggered_by.first_name} {run.triggered_by.last_name}".strip(),
            "avatar": run.triggered_by.get_avatar_url(),
        } if run.triggered_by else None,
        "status": overall,
        "duration_seconds": _seconds_between(run.started_at, last_finish) if overall not in ('running', 'pending') else None,
        "task_count": len(tasks),
        "done_count": sum(1 for s in statuses if s == 'done'),
        "failed_count": sum(1 for s in statuses if s == 'failed'),
        "tasks": tasks,
    }


def _iso_utc(dt):
    """BackgroundJob timestamps are UTC (aware or naive depending on the
    backend) — always hand the browser an explicit 'Z' instant so it can
    show local times and compute durations without guessing."""
    if not dt:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def _seconds_between(start, end):
    if not start or not end:
        return None
    if start.tzinfo is not None:
        start = start.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    if end.tzinfo is not None:
        end = end.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return max(0, int((end - start).total_seconds()))


_CONDITION_WORDS = {'success': 'succeeds', 'failure': 'fails', 'always': 'finishes'}


def _skip_reason(task, parent_step):
    """Why a task of the workflow has no run in this launch — the parent's
    step (or None if the parent never ran here either) is enough to tell
    'branch not taken' apart from 'never reached'."""
    if task.trigger_mode != 'after_task' or not task.depends_on:
        if not task.is_active:
            return 'not_launched', "Not launched — this first task is paused."
        return 'not_launched', "Not part of this launch."
    parent_title = task.depends_on.title
    if not parent_step:
        return 'not_reached', f"Never reached — \"{parent_title}\" did not run in this launch."
    status = parent_step['status']
    if status in ('pending', 'running', 'paused'):
        return 'waiting', f"Waiting for \"{parent_title}\" to finish."
    if status == 'cancelled':
        return 'not_reached', f"Never reached — \"{parent_title}\" was cancelled."
    outcome = 'succeeded' if status == 'done' else 'failed'
    return 'branch_not_taken', (f"Skipped — runs only if \"{parent_title}\" "
                                f"{_CONDITION_WORDS.get(task.depends_on_condition, 'finishes')}, but it {outcome}.")


def get_workflow_run_trace(workflow_uuid, run_uuid):
    """The full execution path of one launch: every task that actually ran,
    in the order it ran, with what triggered it (first task, or 'X
    succeeded → on success'), its timing, its progress and its last log
    line — plus every task of the workflow that did NOT run, with the
    reason (branch not taken, never reached, paused…). Feeds the run trace
    panel and the graph's 'path taken' highlighting. None if not found."""
    from app.core.db_class.job import BackgroundJob, BackgroundJobLog
    from app.core.db_class.task_scheduler import AdminTaskRun, AdminWorkflowRun

    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return None
    run = AdminWorkflowRun.query.filter_by(uuid=run_uuid, workflow_id=workflow.id).first()
    if not run:
        return None

    db.session.expire_all()  # job_worker mutates jobs on another thread
    task_runs = (AdminTaskRun.query.filter_by(workflow_run_id=run.id)
                 .order_by(AdminTaskRun.started_at.asc(), AdminTaskRun.id.asc()).all())

    steps = []
    step_by_schedule = {}
    for tr in task_runs:
        task = tr.schedule
        job = BackgroundJob.query.filter_by(uuid=tr.job_uuid).first() if tr.job_uuid else None
        status = job.status if job else tr.status
        started = (job.started_at if job else None)
        finished = (job.finished_at if job else None) or tr.finished_at
        last_log = None
        if job:
            last = (BackgroundJobLog.query.filter_by(job_id=job.id)
                    .order_by(BackgroundJobLog.id.desc()).first())
            if last:
                last_log = {"level": last.level, "message": (last.message or '')[:300]}

        parent = step_by_schedule.get(task.depends_on_schedule_id) if task.trigger_mode == 'after_task' else None
        if parent:
            trigger = {
                "kind": "after_task",
                "parent_task_uuid": parent['task_uuid'],
                "parent_title": parent['task_title'],
                "parent_status": parent['status'],
                "condition": task.depends_on_condition,
            }
        else:
            trigger = {"kind": "root"}

        step = {
            "step": len(steps) + 1,
            "task_uuid": task.uuid,
            "task_title": task.title,
            "task_type": task.task_type,
            "job_uuid": tr.job_uuid,
            "status": status,
            "queued_at": _iso_utc(tr.started_at),
            "started_at": _iso_utc(started),
            "finished_at": _iso_utc(finished),
            "wait_seconds": _seconds_between(tr.started_at, started),
            "duration_seconds": _seconds_between(started, finished),
            "done": job.done if job else 0,
            "total": job.total if job else 0,
            "error": (job.error or '')[:500] if job and job.error else None,
            "last_log": last_log,
            "trigger": trigger,
        }
        steps.append(step)
        step_by_schedule[task.id] = step

    skipped = []
    for task in workflow.tasks:
        if task.id in step_by_schedule:
            continue
        parent_step = step_by_schedule.get(task.depends_on_schedule_id) if task.depends_on_schedule_id else None
        kind, reason = _skip_reason(task, parent_step)
        skipped.append({
            "task_uuid": task.uuid,
            "task_title": task.title,
            "task_type": task.task_type,
            "kind": kind,
            "reason": reason,
            "parent_task_uuid": task.depends_on.uuid if task.depends_on else None,
        })

    statuses = [s['status'] for s in steps]
    if any(s in ('pending', 'running', 'paused') for s in statuses):
        overall = 'running'
    elif 'failed' in statuses:
        overall = 'failed'
    elif 'cancelled' in statuses:
        overall = 'cancelled'
    elif statuses:
        overall = 'done'
    else:
        overall = 'pending'

    finished_points = [s['finished_at'] for s in steps if s['finished_at']]
    finished_at = max(finished_points) if (finished_points and overall != 'running') else None
    run_started = _iso_utc(run.started_at)
    duration = None
    if finished_at and run.started_at:
        duration = _seconds_between(run.started_at, datetime.datetime.strptime(finished_at, '%Y-%m-%dT%H:%M:%SZ'))

    return {
        "uuid": run.uuid,
        "status": overall,
        "started_at": run_started,
        "finished_at": finished_at,
        "duration_seconds": duration,
        "triggered_by": {
            "id": run.triggered_by.id,
            "name": f"{run.triggered_by.first_name} {run.triggered_by.last_name}".strip(),
            "avatar": run.triggered_by.get_avatar_url(),
        } if run.triggered_by else None,
        "counts": {
            "done": statuses.count('done'),
            "failed": statuses.count('failed'),
            "cancelled": statuses.count('cancelled'),
            "running": sum(1 for s in statuses if s in ('pending', 'running', 'paused')),
            "skipped": len(skipped),
            "total": len(workflow.tasks),
        },
        "steps": steps,
        "skipped": skipped,
    }


def get_workflow_live_status(workflow_uuid):
    """One row per task in the workflow, describing its most recent run's
    live BackgroundJob state — feeds the graph view's running/done/failed
    node highlighting and the 'Live runs' log panel while a workflow is in
    flight. Returns None if the workflow doesn't exist."""
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.task_scheduler import AdminTaskRun

    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return None

    db.session.expire_all()  # avoid stale progress — job_worker mutates jobs on another thread
    result = []
    for task in workflow.tasks:
        run = (AdminTaskRun.query.filter_by(schedule_id=task.id)
               .order_by(AdminTaskRun.started_at.desc()).first())
        job = BackgroundJob.query.filter_by(uuid=run.job_uuid).first() if (run and run.job_uuid) else None
        result.append({
            "task_uuid": task.uuid,
            "job_uuid": job.uuid if job else None,
            "job_status": job.status if job else None,
            "job_label": job.label if job else None,
            "done": job.done if job else 0,
            "total": job.total if job else 0,
        })
    return result


# ─── Canvas view — free-form node positions + drag-to-connect ─────────────────

def set_task_position(schedule_uuid, x, y):
    """Persist where this task's node sits on the workflow's Canvas view.
    No validation beyond existence — position is purely cosmetic, never
    read by the scheduler engine."""
    schedule = AdminTaskSchedule.query.filter_by(uuid=schedule_uuid).first()
    if not schedule:
        return None, "Task not found."
    schedule.position_x = float(x)
    schedule.position_y = float(y)
    db.session.commit()
    return schedule, None


def set_task_dependency(schedule_uuid, depends_on_schedule_id, depends_on_condition):
    """Surgical version of update_schedule() that only ever touches the
    trigger — used by the Canvas view's drag-to-connect: dragging from one
    node to another must not silently reset the target's title, task_type,
    target_payload, etc. the way re-submitting the full edit form would if
    those fields weren't carried along. Reuses the exact same validation
    (cycle guard, same-workflow check) as the modal-based flow."""
    schedule = AdminTaskSchedule.query.filter_by(uuid=schedule_uuid).first()
    if not schedule:
        return None, "Task not found."

    data = {
        'trigger_mode': 'after_task',
        'depends_on_schedule_id': depends_on_schedule_id,
        'depends_on_condition': depends_on_condition,
    }
    ok, err = _validate_trigger(data, schedule_id=schedule.id, workflow_id=schedule.workflow_id)
    if not ok:
        return None, err

    _apply_trigger_fields(schedule, data)
    db.session.commit()
    _register_live(schedule)
    return schedule, None


def clear_task_dependency(schedule_uuid):
    """Remove an existing dependency (Canvas view: click an edge, choose
    'Remove connection'). A task can't be left with no trigger at all, so it
    falls back to a safe, inert default — daily at 03:00, paused — rather
    than guessing a schedule the admin never asked for; they re-enable it
    with a real cadence via Edit once they've decided what it should be."""
    schedule = AdminTaskSchedule.query.filter_by(uuid=schedule_uuid).first()
    if not schedule:
        return None, "Task not found."
    if schedule.trigger_mode != 'after_task':
        return None, "This task has no dependency to remove."

    data = {'trigger_mode': 'daily', 'hour': 3, 'minute': 0, 'timezone': schedule.timezone or 'UTC'}
    _apply_trigger_fields(schedule, data)
    schedule.is_active = False
    db.session.commit()
    _register_live(schedule)
    return schedule, None


# ── Launch preview: what a run of the workflow will do, before it runs ──────────

def _estimate(task):
    """How many items the task will go through, when it can be counted cheaply: (count, unit) or None."""
    from sqlalchemy import func
    from app.core.db_class.rule import Rule, InvalidRuleModel
    from app.features.rule.rule_core import _active
    p = task.target_payload or {}
    try:
        if task.task_type == 'bad_rules_retry':
            q = InvalidRuleModel.query
            if p.get('formats'):
                q = q.filter(func.lower(InvalidRuleModel.rule_type).in_([f.lower() for f in p['formats']]))
            return q.count(), 'bad rules'
        if task.task_type in ('relink_rules',):
            return _active().filter(Rule.format.in_(p.get('formats') or [])).count(), 'rules'
        if task.task_type == 'reparse_rule_metadata':
            f = p.get('formats')
            q = Rule.query
            if isinstance(f, str) and f.strip() and f != 'ALL':
                q = q.filter(func.lower(Rule.format) == f.lower())
            elif isinstance(f, list) and f:
                q = q.filter(func.lower(Rule.format).in_([x.lower() for x in f]))
            return q.count(), 'rules'
        if task.task_type == 'github_sync_schedule_launch':
            from app.core.db_class.git import GithubSyncSchedule
            sched = GithubSyncSchedule.query.filter_by(uuid=p.get('schedule_uuid')).first()
            return (len(sched.repos), 'repositories') if sched else None
        if task.task_type in ('quality_score', 'attack_parser') and p.get('rule_ids'):
            return len(p['rule_ids']), 'rules'
    except Exception:
        return None
    return None


def preview_workflow(workflow_uuid):
    """The launch preview: tasks in run order, what each does, how many items, how long it usually
    takes, what it waits for. {"tasks": [...], "total_seconds": n|None, "warnings": [...]}"""
    from app.features.admin.task_scheduler.workflow_spec import _ordered_tasks
    from app.features.admin.task_scheduler.scheduler_engine import _parents
    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return None
    tasks = _ordered_tasks(workflow)
    titles = {t.id: t.title for t in tasks}
    out, total, unknown, warnings = [], 0, False, []
    for t in tasks:
        tdef = TASK_TYPES.get(t.task_type, {})
        stats = t.run_stats()
        est = _estimate(t)
        if stats['avg_seconds'] is None:
            unknown = True
        else:
            total += stats['avg_seconds']
        parents = [{'title': titles.get(pid, '?'), 'condition': cond} for pid, cond in _parents(t)]
        if t.auto_disabled_at:
            warnings.append(f'"{t.title}" was paused after repeated failures.')
        if not tdef:
            warnings.append(f'"{t.title}" has an unknown task type and will be skipped.')
        out.append({
            'uuid': t.uuid, 'title': t.title, 'icon': tdef.get('icon', 'fa-solid fa-gear'),
            'description': tdef.get('description', ''), 'is_active': bool(t.is_active),
            'parents': parents, 'mode': t.depends_on_mode or 'all',
            'estimate': {'count': est[0], 'unit': est[1]} if est else None,
            'avg_seconds': stats['avg_seconds'], 'success_rate': stats['success_rate'],
            'max_retries': t.max_retries or 0, 'timeout_minutes': t.timeout_minutes,
        })
    if not tasks:
        warnings.append('This workflow has no task.')
    return {'tasks': out, 'total_seconds': None if unknown and not total else total,
            'partial_estimate': unknown, 'warnings': warnings}


# ── Workflow dashboard: figures, insights, upcoming launches ────────────────────

def workflow_dashboard(workflow_uuid):
    """Everything the workflow page's header and History insights show, in one call:
    launches (count, success rate, average duration, the last one, one bar per recent launch),
    the tasks failing or slow the most, and the next launches."""
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.task_scheduler import AdminTaskRun, AdminWorkflowRun
    from app.features.admin.task_scheduler.scheduler_engine import (
        build_trigger, workflow_launch_status, workflow_root_tasks,
    )
    workflow = AdminWorkflow.query.filter_by(uuid=workflow_uuid).first()
    if not workflow:
        return None

    recent = (AdminWorkflowRun.query.filter_by(workflow_id=workflow.id)
              .order_by(AdminWorkflowRun.started_at.desc()).limit(30).all())
    bars = [serialize_workflow_run(r) for r in recent]
    finished = [b for b in bars if b['status'] in ('done', 'failed', 'cancelled')]
    ok = [b for b in finished if b['status'] == 'done']
    durations = [b['duration_seconds'] for b in finished if b['duration_seconds'] is not None]

    # per task, over its last 50 runs
    since = datetime.datetime.utcnow() - datetime.timedelta(days=60)
    per_task = []
    for t in workflow.tasks:
        runs = (AdminTaskRun.query.filter(AdminTaskRun.schedule_id == t.id, AdminTaskRun.started_at >= since)
                .order_by(AdminTaskRun.started_at.desc()).limit(50).all())
        done_runs = [r for r in runs if r.finished_at and r.started_at]
        if not done_runs:
            continue
        fails = sum(1 for r in done_runs if r.status == 'failed')
        avg = sum((r.finished_at - r.started_at).total_seconds() for r in done_runs) / len(done_runs)
        per_task.append({'uuid': t.uuid, 'title': t.title, 'task_type': t.task_type, 'runs': len(done_runs),
                         'failures': fails, 'fail_rate': round(100 * fails / len(done_runs)), 'avg_seconds': round(avg)})

    # next launches of its first tasks
    upcoming = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for root in workflow_root_tasks(workflow):
        if not root.is_active or root.trigger_mode in ('after_task',):
            continue
        if root.trigger_mode == 'once':
            if root.next_run_at:
                upcoming.append({'at': root.next_run_at.strftime('%Y-%m-%dT%H:%M:%SZ'), 'task': root.title})
            continue
        try:
            trig, cur = build_trigger(root), now
            for _ in range(5):
                nxt = trig.get_next_fire_time(None, cur)
                if not nxt:
                    break
                upcoming.append({'at': nxt.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'task': root.title})
                cur = nxt + datetime.timedelta(seconds=1)
        except Exception:
            continue
    upcoming.sort(key=lambda u: u['at'])

    return {
        'workflow': workflow.to_json(),
        'launch_status': workflow_launch_status(workflow),
        'launches': AdminWorkflowRun.query.filter_by(workflow_id=workflow.id).count(),
        'success_rate': round(100 * len(ok) / len(finished)) if finished else None,
        'avg_seconds': round(sum(durations) / len(durations)) if durations else None,
        'last': bars[0] if bars else None,
        'bars': [{'uuid': b['uuid'], 'status': b['status'], 'started_at': b['started_at'],
                  'duration_seconds': b['duration_seconds'], 'done': b['done_count'], 'failed': b['failed_count'],
                  'tasks': b['task_count']} for b in reversed(bars)],
        'failing': sorted([p for p in per_task if p['failures']], key=lambda p: (-p['fail_rate'], -p['failures']))[:5],
        'slowest': sorted(per_task, key=lambda p: -p['avg_seconds'])[:5],
        'upcoming': upcoming[:6],
        'task_count': len(workflow.tasks),
        'active_task_count': sum(1 for t in workflow.tasks if t.is_active),
        'auto_paused': [t.title for t in workflow.tasks if t.auto_disabled_at],
    }


def run_from_task(schedule_uuid, triggered_by):
    """Launch the workflow from one task: it and everything after it (a new launch in the history),
    e.g. to finish a chain after fixing what made a task fail. Returns (workflow_run, error)."""
    schedule = AdminTaskSchedule.query.filter_by(uuid=schedule_uuid).first()
    if not schedule or not schedule.workflow:
        return None, "Task not found."
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.task_scheduler import AdminTaskRun
    busy = (AdminTaskRun.query.join(AdminTaskSchedule, AdminTaskSchedule.id == AdminTaskRun.schedule_id)
            .filter(AdminTaskSchedule.workflow_id == schedule.workflow_id, AdminTaskRun.status == 'pending').all())
    for r in busy:
        job = BackgroundJob.query.filter_by(uuid=r.job_uuid).first() if r.job_uuid else None
        if job and job.status in ('pending', 'running', 'paused'):
            return None, "This workflow is already running — wait for it or stop it first."
    return launch_workflow(schedule.workflow, [schedule], triggered_by=triggered_by), None
