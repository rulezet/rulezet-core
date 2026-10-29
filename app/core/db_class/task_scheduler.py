"""Admin task scheduler: workflows, tasks and their runs.
"""
from app import db
import datetime


class AdminWorkflow(db.Model):
    """A named container of AdminTaskSchedule rows (see
    docs/design/admin_task_scheduler.md) — the unit an admin creates first,
    then assigns tasks into, modeled on a GitHub Actions workflow file
    containing several jobs. A task's 'after another task' dependency is
    always scoped to tasks within the same workflow."""
    __tablename__ = "admin_workflow"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), index=True, unique=True)
    title       = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    editor_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_active   = db.Column(db.Boolean, default=True, index=True)
    share_key   = db.Column(db.String(64), nullable=True, unique=True)   # read-only link (workflow_notes.py)

    # Email alerts — configured per workflow (not per task): the admin who
    # created the workflow always receives it, plus any notify_emails.
    notify_on_failure = db.Column(db.Boolean, nullable=False, default=True)
    notify_on_success = db.Column(db.Boolean, nullable=False, default=False)
    notify_emails     = db.Column(db.JSON, nullable=True)  # extra recipients on top of editor.email

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    editor = db.relationship("User")
    tasks  = db.relationship("AdminTaskSchedule", backref="workflow", cascade="all, delete-orphan", lazy=True,
                              order_by="AdminTaskSchedule.created_at")

    def to_json(self):
        task_count = len(self.tasks)
        active_task_count = sum(1 for t in self.tasks if t.is_active)
        from app.features.admin.task_scheduler.scheduler_engine import workflow_launch_status, workflow_first_task
        first = workflow_first_task(self)
        return {
            "launch_status": workflow_launch_status(self),
            # Feeds the Edit Workflow modal's "Launch date" picker.
            "first_task": {
                "uuid": first.uuid, "title": first.title, "is_active": first.is_active,
                "trigger_mode": first.trigger_mode, "run_once_at": first.to_json()["run_once_at"],
                "days_of_week": first.days_of_week_list(), "day_of_month": first.day_of_month,
                "hour": first.hour, "minute": first.minute, "cron_expr": first.cron_expr,
                "timezone": first.timezone,
            } if first else None,
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "editor": {
                "id": self.editor.id,
                "name": f"{self.editor.first_name} {self.editor.last_name}".strip(),
                "avatar": self.editor.get_avatar_url(),
            } if self.editor else None,
            "is_active": self.is_active,
            "notify_on_failure": self.notify_on_failure,
            "notify_on_success": self.notify_on_success,
            "notify_emails": self.notify_emails or [],
            "shared": bool(self.share_key),
            "notes_count": len(self.notes),
            "files_count": len(self.files),
            "task_count": task_count,
            "active_task_count": active_task_count,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
        }


class AdminTaskSchedule(db.Model):
    """Generalized admin task scheduler (see docs/design/admin_task_scheduler.md).
    Belongs to an AdminWorkflow. Phase 1: a single optional parent
    dependency (depends_on_schedule_id / depends_on_condition), always
    within the same workflow — multi-parent AND/OR is a Phase 3 addition
    (AdminTaskDependency) once a linear chain proves too limiting."""
    __tablename__ = "admin_task_schedule"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), index=True, unique=True)
    title       = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    editor_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    workflow_id = db.Column(db.Integer, db.ForeignKey("admin_workflow.id", ondelete="CASCADE"), nullable=False, index=True)

    # Key into the TASK_TYPES registry (task_scheduler/task_types.py) — e.g. 'quality_score'.
    task_type = db.Column(db.String(50), nullable=False, index=True)

    # Payload passed as-is to create_job() — already in the shape the
    # corresponding job_type's handler expects (e.g. {"filters": {...}}).
    target_payload = db.Column(db.JSON, nullable=False, default=dict)

    is_active = db.Column(db.Boolean, default=True, index=True)

    # ── Triggering: either time-based, or "after another task" — never both. ──
    trigger_mode = db.Column(db.String(20), nullable=False, default='cron')
    # 'once' | 'daily' | 'weekly' | 'monthly' | 'cron' | 'after_task'

    run_once_at  = db.Column(db.DateTime, nullable=True)      # trigger_mode == 'once'
    days_of_week = db.Column(db.String(20), nullable=True)    # 'weekly' only
    day_of_month = db.Column(db.Integer, nullable=True)       # 'monthly' only
    hour         = db.Column(db.Integer, nullable=False, default=3)
    minute       = db.Column(db.Integer, nullable=False, default=0)
    cron_expr    = db.Column(db.String(120), nullable=True)   # 'cron' only
    timezone     = db.Column(db.String(60), nullable=False, default="UTC")

    # Chaining — 'after_task' only.
    depends_on_schedule_id = db.Column(db.Integer,
        db.ForeignKey("admin_task_schedule.id", ondelete="SET NULL"), nullable=True)
    depends_on_condition   = db.Column(db.String(20), nullable=False, default='success')

    # Free-form position on the workflow's Canvas view — null until the admin
    # drags the node for the first time, at which point the canvas switches
    # from its auto-layout fallback to this saved position.
    # Several parents (AdminTaskDependency rows, on top of depends_on_schedule_id above, the first
    # parent): 'all' = runs once every parent has finished as its condition says, 'any' = as soon as one has
    depends_on_mode = db.Column(db.String(10), nullable=False, default='all', server_default='all')

    # Robustness (scheduler_engine.on_job_finished / tick):
    max_retries              = db.Column(db.Integer, nullable=False, default=0, server_default='0')    # retries after a failure
    retry_delay_minutes      = db.Column(db.Integer, nullable=False, default=10, server_default='10')
    timeout_minutes          = db.Column(db.Integer, nullable=True)       # job cancelled when it runs longer
    max_consecutive_failures = db.Column(db.Integer, nullable=False, default=0, server_default='0')    # 0 = never auto-pause
    consecutive_failures     = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    auto_disabled_at         = db.Column(db.DateTime, nullable=True)      # paused by the circuit breaker
    catch_up                 = db.Column(db.Boolean, nullable=False, default=False, server_default='false')  # run a missed launch late
    retry_at                 = db.Column(db.DateTime, nullable=True)      # next retry of a failed run

    position_x = db.Column(db.Float, nullable=True)
    position_y = db.Column(db.Float, nullable=True)
    # 'success' | 'failure' | 'always'

    next_run_at = db.Column(db.DateTime, index=True, nullable=True)
    last_run_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    editor      = db.relationship("User")
    depends_on  = db.relationship("AdminTaskSchedule", remote_side=[id])
    runs        = db.relationship("AdminTaskRun", backref="schedule", cascade="all, delete-orphan", lazy=True,
                                   order_by="desc(AdminTaskRun.started_at)")

    def _run_once_at_utc_iso(self):
        from app.features.admin.task_scheduler.scheduler_engine import _once_run_at_utc
        utc = _once_run_at_utc(self)
        return utc.strftime('%Y-%m-%dT%H:%M:%SZ') if utc else None

    def run_stats(self):
        """Its last runs: how many, success rate, average / last duration (seconds) — the task window
        and the graph show it, the launch preview uses it to estimate how long a run takes."""
        finished = [r for r in self.runs[:20] if r.finished_at and r.started_at]
        if not finished:
            return {"runs": len(self.runs), "success_rate": None, "avg_seconds": None, "last_seconds": None}
        durations = [(r.finished_at - r.started_at).total_seconds() for r in finished]
        ok = sum(1 for r in finished if r.status == 'done')
        return {"runs": len(self.runs), "success_rate": round(100 * ok / len(finished)),
                "avg_seconds": round(sum(durations) / len(durations)), "last_seconds": round(durations[0])}

    def days_of_week_list(self):
        if not self.days_of_week:
            return []
        return [int(d) for d in self.days_of_week.split(',') if d != '']

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "editor": {
                "id": self.editor.id,
                "name": f"{self.editor.first_name} {self.editor.last_name}".strip(),
                "avatar": self.editor.get_avatar_url(),
            } if self.editor else None,
            "workflow_id": self.workflow_id,
            "workflow_uuid": self.workflow.uuid if self.workflow else None,
            "task_type": self.task_type,
            "target_payload": self.target_payload,
            "is_active": self.is_active,
            "trigger_mode": self.trigger_mode,
            # Absolute UTC instant ('Z') — run_once_at itself is naive, in self.timezone.
            "run_once_at": self._run_once_at_utc_iso(),
            "days_of_week": self.days_of_week_list(),
            "day_of_month": self.day_of_month,
            "hour": self.hour,
            "minute": self.minute,
            "cron_expr": self.cron_expr,
            "timezone": self.timezone,
            "depends_on_schedule_id": self.depends_on_schedule_id,
            "depends_on_schedule_uuid": self.depends_on.uuid if self.depends_on else None,
            "depends_on_schedule_title": self.depends_on.title if self.depends_on else None,
            "depends_on_condition": self.depends_on_condition,
            "depends_on_mode": self.depends_on_mode or 'all',
            "extra_parents": [{"id": d.parent_id, "uuid": d.parent.uuid if d.parent else None,
                               "title": d.parent.title if d.parent else None, "condition": d.condition}
                              for d in self.extra_dependencies],
            "max_retries": self.max_retries or 0,
            "retry_delay_minutes": self.retry_delay_minutes or 10,
            "timeout_minutes": self.timeout_minutes,
            "max_consecutive_failures": self.max_consecutive_failures or 0,
            "consecutive_failures": self.consecutive_failures or 0,
            "auto_disabled_at": self.auto_disabled_at.strftime('%Y-%m-%d %H:%M') if self.auto_disabled_at else None,
            "catch_up": bool(self.catch_up),
            "retry_at": self.retry_at.strftime('%Y-%m-%d %H:%M') if self.retry_at else None,
            "stats": self.run_stats(),
            "position_x": self.position_x,
            "position_y": self.position_y,
            "next_run_at": self.next_run_at.strftime('%Y-%m-%d %H:%M') if self.next_run_at else None,
            "last_run_at": self.last_run_at.strftime('%Y-%m-%d %H:%M') if self.last_run_at else None,
            "last_run_status": self.runs[0].status if self.runs else None,
            "last_run_job_uuid": self.runs[0].job_uuid if self.runs else None,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }


class AdminTaskDependency(db.Model):
    """One more parent of a task (the first one stays in AdminTaskSchedule.depends_on_schedule_id):
    a task waiting for several tasks — all of them or any one, its depends_on_mode."""
    __tablename__ = "admin_task_dependency"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("admin_task_schedule.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id   = db.Column(db.Integer, db.ForeignKey("admin_task_schedule.id", ondelete="CASCADE"), nullable=False, index=True)
    condition   = db.Column(db.String(20), nullable=False, default='success')   # success | failure | always

    schedule = db.relationship("AdminTaskSchedule", foreign_keys=[schedule_id], backref=db.backref(
        "extra_dependencies", cascade="all, delete-orphan", lazy=True))
    parent   = db.relationship("AdminTaskSchedule", foreign_keys=[parent_id])

    __table_args__ = (db.UniqueConstraint('schedule_id', 'parent_id', name='uq_admin_task_dependency'),)


class AdminWorkflowRun(db.Model):
    """One 'Run Workflow' launch — groups every AdminTaskRun it directly
    fired plus every one chained afterwards (on_job_finished propagates
    workflow_run_id down the chain as each dependent task fires) into a
    single launch-history entry. Feeds the workflow detail page's history
    table; deliberately NOT created for a single task's manual 'Run now'
    (that's a task-level action, not a workflow launch)."""
    __tablename__ = "admin_workflow_run"

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid            = db.Column(db.String(36), index=True, unique=True)
    workflow_id     = db.Column(db.Integer, db.ForeignKey("admin_workflow.id", ondelete="CASCADE"), nullable=False)
    triggered_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    started_at      = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    workflow     = db.relationship("AdminWorkflow", backref=db.backref(
        "launch_runs", cascade="all, delete-orphan", lazy=True, order_by="desc(AdminWorkflowRun.started_at)"))
    triggered_by = db.relationship("User")


class AdminTaskRun(db.Model):
    """One firing of an AdminTaskSchedule. Thin wrapper around the real
    BackgroundJob — no duplication of progress/log data."""
    __tablename__ = "admin_task_run"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), index=True, unique=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("admin_task_schedule.id", ondelete="CASCADE"), nullable=False)
    job_uuid    = db.Column(db.String(36), nullable=True)   # -> BackgroundJob.uuid

    # Set only when this run is part of a whole-workflow launch (see
    # AdminWorkflowRun) — null for a standalone task 'Run now'.
    workflow_run_id = db.Column(db.Integer, db.ForeignKey("admin_workflow_run.id", ondelete="SET NULL"), nullable=True)

    status      = db.Column(db.String(20), default="pending")  # pending | done | failed
    attempt     = db.Column(db.Integer, nullable=False, default=1, server_default='1')  # 2+ = an automatic retry
    started_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "schedule_id": self.schedule_id,
            "job_uuid": self.job_uuid,
            "status": self.status,
            "started_at": self.started_at.strftime('%Y-%m-%d %H:%M') if self.started_at else None,
            "finished_at": self.finished_at.strftime('%Y-%m-%d %H:%M') if self.finished_at else None,
        }


class AdminWorkflowNote(db.Model):
    """A markdown note on a workflow (why it exists, how to fix it when it fails…),
    optionally about one launch. Pinned notes show first."""
    __tablename__ = "admin_workflow_note"

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid            = db.Column(db.String(36), index=True, unique=True)
    workflow_id     = db.Column(db.Integer, db.ForeignKey("admin_workflow.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_run_id = db.Column(db.Integer, db.ForeignKey("admin_workflow_run.id", ondelete="SET NULL"), nullable=True)
    author_id       = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    title           = db.Column(db.String(200), nullable=False)
    content         = db.Column(db.Text, nullable=False, default='')
    pinned          = db.Column(db.Boolean, nullable=False, default=False)
    created_at      = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    workflow     = db.relationship("AdminWorkflow", backref=db.backref("notes", cascade="all, delete-orphan", lazy=True))
    workflow_run = db.relationship("AdminWorkflowRun")
    author       = db.relationship("User")

    def to_json(self):
        return {
            'uuid': self.uuid, 'title': self.title, 'content': self.content, 'pinned': self.pinned,
            'run_uuid': self.workflow_run.uuid if self.workflow_run else None,
            'run_started_at': self.workflow_run.started_at.strftime('%Y-%m-%d %H:%M') if self.workflow_run and self.workflow_run.started_at else None,
            'author': self.author.get_username() if self.author else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
        }


class AdminWorkflowFile(db.Model):
    """A file attached to a workflow (runbook, exported config, screenshot…). The bytes live in
    data/workflow_files/<workflow uuid>/<stored_name>; the original name is only displayed."""
    __tablename__ = "admin_workflow_file"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), index=True, unique=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey("admin_workflow.id", ondelete="CASCADE"), nullable=False, index=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    filename    = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(64), nullable=False)
    size        = db.Column(db.Integer, nullable=False, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    workflow = db.relationship("AdminWorkflow", backref=db.backref("files", cascade="all, delete-orphan", lazy=True))
    uploader = db.relationship("User")

    def to_json(self):
        return {
            'uuid': self.uuid, 'filename': self.filename, 'size': self.size,
            'uploader': self.uploader.get_username() if self.uploader else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }
