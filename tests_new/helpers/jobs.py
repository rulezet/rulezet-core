"""Background-job factories and a fake handler for the worker.

A job is a `BackgroundJob` row; its owner is `created_by`. The worker step
under test is `run_next_job(app)` (app/features/jobs/job_worker.py) — the
polling thread is never started, nothing sleeps.
"""
import datetime
import itertools
import uuid

from app import db
from app.core.db_class.db import BackgroundJob, BackgroundJobLog

_counter = itertools.count(1)

# A job type every role can be asked about: admin-only through /jobs/create,
# harmless to create (nothing runs until a worker picks it up).
ADMIN_JOB_TYPE = "compute_rule_quality_score"
TAG_JOB_TYPES = ("bulk_add_tag_to_rules", "bulk_remove_tag_from_rules")
FAKE_JOB_TYPE = "tests_fake_job"


def make_job(creator, *, status="pending", job_type=FAKE_JOB_TYPE, payload=None, label=None,
             created_at=None, **overrides):
    """A job created by `creator`, `status` as given (pending by default).
    Jobs made later are queued later (the worker runs the oldest first)."""
    n = next(_counter)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    fields = dict(
        uuid=str(uuid.uuid4()),
        job_type=job_type,
        status=status,
        payload=payload if payload is not None else {},
        label=label or f"Test job {n}",
        created_by=creator.id,
        total=0,
        done=0,
        created_at=created_at or now - datetime.timedelta(hours=1) + datetime.timedelta(milliseconds=n),
    )
    if status in ("running", "done", "failed", "cancelled", "paused"):
        fields["started_at"] = now
    if status in ("done", "failed", "cancelled"):
        fields["finished_at"] = now
    fields.update(overrides)
    job = BackgroundJob(**fields)
    db.session.add(job)
    db.session.commit()
    return job


def add_log(job, message, level="info", event=None):
    entry = BackgroundJobLog(job_id=job.id, level=level, event=event, message=message,
                             created_at=datetime.datetime.now(tz=datetime.timezone.utc))
    db.session.add(entry)
    db.session.commit()
    return entry


def fake_handler(monkeypatch, job_type=FAKE_JOB_TYPE, run=None):
    """Register a handler for `job_type` for this test only. `run(job, app)`
    is what it does (nothing by default); returns the list of jobs it ran."""
    from app.features.jobs import job_worker
    ran = []

    def handler(job, app):
        ran.append(job.uuid)
        if run is not None:
            run(job, app)

    monkeypatch.setitem(job_worker._HANDLERS, job_type, handler)
    return ran


def run_next_job(app):
    """One step of the default-lane worker: the next pending job, run to its end."""
    from app.features.jobs.job_worker import run_next_job as _run
    return _run(app, lane="default")


def with_special_roles(clients, client_as):
    """The role clients plus "tagger" (rule.tag_any) and "ai_user" (ai.use) —
    the two permissions /jobs/create knows about."""
    from tests_new.helpers.users import make_user_with_permission
    return {
        **clients,
        "tagger": client_as(make_user_with_permission("rule.tag_any", "tagger")),
        "ai_user": client_as(make_user_with_permission("ai.use", "ai-user")),
    }
