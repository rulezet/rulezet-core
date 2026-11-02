"""A job that finds what it needs busy (the Git cache) goes back in the queue: tried again every 10 min, failed
for good after 4 h (job_handlers.retry_later, job_worker.run_next_job skips it until then)."""
import contextlib
import datetime

from app import db
from app.core.db_class.job import BackgroundJob
from app.features.jobs import job_handlers as H
from app.features.jobs.job_worker import run_next_job


@contextlib.contextmanager
def _busy():
    yield False


def _job(users):
    job = BackgroundJob(uuid="pull-1", job_type="git_cache_pull", status="pending", total=0, done=0,
                        created_by=users.admin.id, payload={})
    db.session.add(job)
    db.session.commit()
    return job


def test_busy_cache_retries_then_gives_up(app, users, monkeypatch):
    import app.features.rule.rule_format.utils_format.utils_import_update as U
    monkeypatch.setattr(U, "repo_cache_exclusive", _busy)
    job = _job(users)
    assert run_next_job(app) == "pull-1"
    db.session.expire_all()
    job = BackgroundJob.query.filter_by(uuid="pull-1").one()
    assert job.status == "pending" and job.payload["_retry_count"] == 1           # back in the queue, not failed
    assert run_next_job(app) is None                                               # not before its time
    # 10 min later it runs again — still busy: attempt 2
    job.payload = {**job.payload, "_retry_at": "2000-01-01T00:00:00+00:00"}
    db.session.commit()
    assert run_next_job(app) == "pull-1"
    db.session.expire_all()
    job = BackgroundJob.query.filter_by(uuid="pull-1").one()
    assert job.status == "pending" and job.payload["_retry_count"] == 2
    # after 4 h of trying: failed for good, with the reason
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)).isoformat()
    job.payload = {**job.payload, "_retry_at": "2000-01-01T00:00:00+00:00", "_retry_since": old}
    db.session.commit()
    run_next_job(app)
    db.session.expire_all()
    job = BackgroundJob.query.filter_by(uuid="pull-1").one()
    assert job.status == "failed" and "giving up" in job.error and "_retry_at" not in job.payload


def test_waiting_job_does_not_block_the_queue(app, users, monkeypatch):
    import app.features.rule.rule_format.utils_format.utils_import_update as U
    monkeypatch.setattr(U, "repo_cache_exclusive", _busy)
    _job(users)
    run_next_job(app)                                                              # now waiting
    other = BackgroundJob(uuid="other-1", job_type="no_such_type", status="pending", total=0, done=0,
                          created_by=users.admin.id, payload={})
    db.session.add(other)
    db.session.commit()
    assert run_next_job(app) == "other-1"                                          # the next job runs meanwhile
