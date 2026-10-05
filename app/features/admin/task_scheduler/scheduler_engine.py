"""
scheduler_engine.py — the "when" half of the generalized Admin Task
Scheduler (see docs/design/admin_task_scheduler.md).

`AdminTaskSchedule.next_run_at` in Postgres is the single source of truth
for "when does this fire next": the CRUD routes (gunicorn web process)
only ever compute and store it, and the worker process (worker.py — the
only process started with start_worker=True in prod) polls the table every
TICK_SECONDS and fires whatever is due. No trigger lives in memory any
more: the previous design registered APScheduler jobs from the CRUD
routes, i.e. inside the gunicorn process — which never loaded them at
boot, gets recycled every ~1000 requests (--max-requests) and so silently
dropped every task created/edited since the last worker restart, while the
worker kept firing the stale pre-edit triggers.

A workflow is launched by its *first task(s)* — the roots, i.e. every task
not triggered by another task (see workflow_root_tasks()). When a root's
time comes, the whole workflow is launched exactly like the "Run Workflow"
button (one AdminWorkflowRun, the chain follows via on_job_finished()).
APScheduler is still used, but only as a pure "next fire time" calculator
for the cron/daily/weekly/monthly expressions.
"""
import datetime
import threading
import time
import uuid as _uuid_mod

from apscheduler.triggers.cron import CronTrigger

TICK_SECONDS = 20
# Same tolerance the old APScheduler misfire_grace_time gave: a fire missed
# by more than this (worker down for hours) is skipped, not run late.
MISFIRE_GRACE_SECONDS = 3600

_ticker_started = False


def build_trigger(schedule):
    """schedule: an AdminTaskSchedule row. Returns an APScheduler trigger for
    a recurring mode, or None for 'once'/'after_task' (handled directly by
    compute_next_run_at)."""
    tz = schedule.timezone or "UTC"
    mode = schedule.trigger_mode
    if mode in ('once', 'after_task'):
        return None
    if mode == 'daily':
        return CronTrigger(hour=schedule.hour, minute=schedule.minute, timezone=tz)
    if mode == 'weekly':
        dow = schedule.days_of_week_list() or [0]
        return CronTrigger(day_of_week=','.join(str(d) for d in dow),
                            hour=schedule.hour, minute=schedule.minute, timezone=tz)
    if mode == 'monthly':
        day = schedule.day_of_month or 1
        return CronTrigger(day=('last' if day == -1 else day),
                            hour=schedule.hour, minute=schedule.minute, timezone=tz)
    if mode == 'cron':
        return CronTrigger.from_crontab(schedule.cron_expr, timezone=tz)
    raise ValueError(f"Unknown trigger_mode: {mode}")


def _once_run_at_utc(schedule):
    """run_once_at is stored naive, in the task's own timezone."""
    if not schedule.run_once_at:
        return None
    from zoneinfo import ZoneInfo
    aware = schedule.run_once_at
    if aware.tzinfo is None:
        aware = aware.replace(tzinfo=ZoneInfo(schedule.timezone or "UTC"))
    return aware.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def compute_next_run_at(schedule, after=None):
    """Next time this task fires on its own (naive UTC), or None if it never
    will: paused, 'after_task' (fired by its parent), or a 'once' task that
    already ran."""
    if not schedule.is_active or schedule.trigger_mode == 'after_task':
        return None
    if schedule.trigger_mode == 'once':
        run_at = _once_run_at_utc(schedule)
        if run_at is None:
            return None
        if schedule.last_run_at and schedule.last_run_at >= run_at:
            return None  # already fired
        return run_at
    now = (after or datetime.datetime.utcnow()).replace(tzinfo=datetime.timezone.utc)
    nxt = build_trigger(schedule).get_next_fire_time(None, now)
    return nxt.astimezone(datetime.timezone.utc).replace(tzinfo=None) if nxt else None


def workflow_root_tasks(workflow):
    """The workflow's first task(s): every task that isn't chained after
    another one. An 'after_task' whose parent was deleted (depends_on
    cleared by delete_schedule) has become a first task too — just one
    with no launch date of its own."""
    return [t for t in workflow.tasks
            if t.trigger_mode != 'after_task' or t.depends_on_schedule_id is None]


def workflow_first_task(workflow):
    """The single task whose trigger the workflow's 'Launch date' (Edit
    Workflow modal) reads and writes: the oldest first task."""
    roots = workflow_root_tasks(workflow)
    return roots[0] if roots else None


def workflow_launch_status(workflow):
    """Whether this workflow will ever start on its own, for the workflow
    list's warning. Returns {"will_run", "warning", "next_run_at"}."""
    if not workflow.tasks:
        return {"will_run": False, "next_run_at": None,
                "warning": "This workflow has no task — it will never run."}

    roots = workflow_root_tasks(workflow)
    scheduled = [t for t in roots if t.is_active and t.trigger_mode != 'after_task' and t.next_run_at]
    if scheduled:
        nxt = min(t.next_run_at for t in scheduled)
        return {"will_run": True, "warning": None, "next_run_at": nxt.strftime('%Y-%m-%dT%H:%M:%SZ')}

    titles = ', '.join(f'"{t.title}"' for t in roots[:3]) or '—'
    if any(t.trigger_mode == 'after_task' for t in roots):
        reason = f"its first task ({titles}) has no launch date — set one (Edit → time trigger)"
    elif any(not t.is_active for t in roots):
        reason = f"its first task ({titles}) is paused"
    else:
        reason = f"its first task ({titles}) has no upcoming run"
    return {"will_run": False, "next_run_at": None,
            "warning": f"This workflow will never run automatically: {reason}."}


def _creates_cycle(schedule_id, depends_on_schedule_id):
    """Walk the depends_on chain starting at depends_on_schedule_id — if we
    ever reach schedule_id, adding this edge would create a cycle. schedule_id
    may be None for a brand-new schedule (nothing to walk into yet)."""
    from app.core.db_class.db import AdminTaskSchedule

    seen = set()
    current_id = depends_on_schedule_id
    while current_id is not None:
        if current_id == schedule_id:
            return True
        if current_id in seen:
            return False  # pre-existing cycle elsewhere — not this call's problem
        seen.add(current_id)
        parent = AdminTaskSchedule.query.get(current_id)
        if not parent:
            return False
        current_id = parent.depends_on_schedule_id
    return False


def _fire_schedule(app, schedule_uuid, workflow_run_id=None, ignore_paused=False):
    """Runs in the APScheduler thread (or synchronously for a manual
    run_now/chained fire). Only ever creates an AdminTaskRun + BackgroundJob
    row — the real work happens later on job_worker's thread.

    workflow_run_id: set when this firing is part of a whole-workflow launch
    (see AdminWorkflowRun) — passed in directly for a root task by
    run_workflow_now(), and propagated automatically to each chained child
    by on_job_finished() below, so a launch-history entry covers the entire
    cascade, not just the root task(s) that were fired directly.

    ignore_paused: set by on_job_finished() when chaining inside a manual
    workflow launch, so a paused mid-chain task still runs as part of that
    explicit launch (pausing only opts a task out of firing on its own
    schedule/automatically)."""
    from app import db
    from app.core.db_class.db import AdminTaskSchedule, AdminTaskRun
    from app.features.jobs.jobs_core import create_job
    from app.features.admin.task_scheduler.task_types import TASK_TYPES

    with app.app_context():
        try:
            query = AdminTaskSchedule.query.filter_by(uuid=schedule_uuid)
            if not ignore_paused:
                query = query.filter_by(is_active=True)
            schedule = query.first()
            if not schedule:
                return

            task_def = TASK_TYPES.get(schedule.task_type)
            if not task_def:
                print(f"[task_scheduler] Unknown task_type '{schedule.task_type}' for schedule {schedule_uuid} — skipping.")
                return

            run = AdminTaskRun(uuid=str(_uuid_mod.uuid4()), schedule_id=schedule.id, status='pending',
                                workflow_run_id=workflow_run_id)
            db.session.add(run)
            db.session.flush()

            job = create_job(
                job_type=task_def['job_type'],
                payload=schedule.target_payload or {},
                label=f"{schedule.title} — {task_def['label']}",
                created_by=schedule.editor_id,
            )
            if job is None:
                db.session.rollback()
                return

            run.job_uuid = job.uuid
            schedule.last_run_at = datetime.datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[task_scheduler] _fire_schedule error for {schedule_uuid}: {e}")


def register_schedule(app, schedule):
    """Recompute and store this task's next_run_at — the worker's ticker
    picks it up from the DB, whichever process this runs in. Kept under its
    old name/signature (app unused) so every CRUD call site stays as is."""
    schedule.next_run_at = compute_next_run_at(schedule)


def unregister_schedule(schedule_uuid):
    """Nothing to do: no trigger lives in memory any more — deleting or
    pausing the row (next_run_at = None) is enough."""


def _fire_due_root(app, schedule):
    """A first task's time has come: launch its workflow (history entry,
    chain, notifications — same as the Run Workflow button), unless the
    whole workflow is paused. Advances next_run_at first, in its own
    commit, so a crash mid-launch can never make it fire twice."""
    from app import db
    schedule.next_run_at = compute_next_run_at(schedule)
    if schedule.trigger_mode == 'once':
        schedule.next_run_at = None
    db.session.commit()

    workflow = schedule.workflow
    if workflow is None or not workflow.is_active:
        return
    from app.features.admin.task_scheduler.task_scheduler_core import launch_workflow
    launch_workflow(workflow, [schedule], triggered_by=None)


def tick(app, now=None):
    """Fire every due task once. Called by the worker's ticker thread every
    TICK_SECONDS; also callable directly from tests."""
    from app import db
    from app.core.db_class.db import AdminTaskSchedule

    now = now or datetime.datetime.utcnow()
    due = (AdminTaskSchedule.query
           .filter(AdminTaskSchedule.is_active.is_(True),
                   AdminTaskSchedule.trigger_mode != 'after_task',
                   AdminTaskSchedule.next_run_at.isnot(None),
                   AdminTaskSchedule.next_run_at <= now)
           .order_by(AdminTaskSchedule.next_run_at.asc())
           .all())
    for schedule in due:
        try:
            if (now - schedule.next_run_at).total_seconds() > MISFIRE_GRACE_SECONDS:
                print(f"[task_scheduler] {schedule.uuid} missed its run at {schedule.next_run_at} "
                      f"by more than {MISFIRE_GRACE_SECONDS}s — skipped, rescheduling.")
                schedule.next_run_at = None if schedule.trigger_mode == 'once' else compute_next_run_at(schedule, now)
                db.session.commit()
                continue
            _fire_due_root(app, schedule)
        except Exception as e:
            db.session.rollback()
            print(f"[task_scheduler] failed to fire schedule {schedule.uuid}: {e}")


def _ticker_loop(app):
    from app import db
    while True:
        with app.app_context():
            try:
                tick(app)
            except Exception as e:
                print(f"[task_scheduler] tick error: {e}")
            finally:
                db.session.remove()
        time.sleep(TICK_SECONDS)


def start_scheduler(app):
    """Boot-time loader — called from create_app(start_worker=True), i.e. in
    the worker process only. Fills in next_run_at for any active task that
    lacks one (rows from before this engine), then starts the ticker."""
    global _ticker_started
    from app import db
    from app.core.db_class.db import AdminTaskSchedule

    with app.app_context():
        try:
            schedules = AdminTaskSchedule.query.filter_by(is_active=True, next_run_at=None).all()
        except Exception:
            # Table doesn't exist yet — a brand-new install/test DB before
            # `flask db upgrade` / db.create_all() has run.
            return
        for schedule in schedules:
            try:
                register_schedule(app, schedule)
            except Exception as e:
                print(f"[task_scheduler] failed to compute next run for {schedule.uuid}: {e}")
        db.session.commit()

    if not _ticker_started:
        _ticker_started = True
        threading.Thread(target=_ticker_loop, args=(app,), daemon=True, name="task-scheduler-ticker").start()


def on_job_finished(job):
    """Called from job_worker.py right after a job's status is finalized to
    'done' or 'failed'. Phase 1: single-parent chaining only — walks the one
    depends_on_schedule_id/depends_on_condition pair. Multi-parent AND/OR
    (AdminTaskDependency) is a Phase 3 addition, see §4bis of the design doc."""
    from app import db
    from app.core.db_class.db import AdminTaskSchedule, AdminTaskRun

    run = AdminTaskRun.query.filter_by(job_uuid=job.uuid).first()
    if not run:
        return  # this job wasn't launched via an AdminTaskSchedule — nothing to do

    run.status = 'done' if job.status == 'done' else 'failed'
    run.finished_at = datetime.datetime.utcnow()
    db.session.commit()

    try:
        # A task that's part of a "Run Workflow" launch gets exactly one
        # email for the whole launch (see run_workflow_now /
        # _finalize_workflow_run_if_done) instead of one per task here.
        from app.features.admin.task_scheduler.notifications import maybe_send_task_alert
        if run.schedule.workflow and not run.workflow_run_id:
            maybe_send_task_alert(run.schedule.workflow, run.schedule, job)
    except Exception as e:
        print(f"[task_scheduler] failed to send task alert: {e}")

    # A manual "Run Workflow" launch (workflow_run_id set) always runs the
    # full chain top to bottom regardless of a task's paused state — pausing
    # a task means "don't fire it on its own schedule/automatically", not
    # "skip it when the admin explicitly launches the whole pipeline". A
    # lone scheduled/manual single-task run (no workflow_run_id) keeps the
    # old behavior: only an active child continues the chain.
    candidates_query = AdminTaskSchedule.query.filter_by(
        trigger_mode='after_task', depends_on_schedule_id=run.schedule_id,
    )
    if not run.workflow_run_id:
        candidates_query = candidates_query.filter_by(is_active=True)
    candidates = candidates_query.all()
    for candidate in candidates:
        condition = candidate.depends_on_condition
        condition_met = (
            condition == 'always' or
            (condition == 'success' and run.status == 'done') or
            (condition == 'failure' and run.status == 'failed')
        )
        if condition_met:
            from flask import current_app
            _fire_schedule(current_app._get_current_object(), candidate.uuid,
                            workflow_run_id=run.workflow_run_id, ignore_paused=bool(run.workflow_run_id))

    if run.workflow_run_id:
        # Any child this run was going to trigger has already been fired
        # above, so if nothing tied to this launch is pending/running any
        # more, the whole workflow run just finished.
        from app.features.admin.task_scheduler.task_scheduler_core import _finalize_workflow_run_if_done
        _finalize_workflow_run_if_done(run.workflow_run_id)
