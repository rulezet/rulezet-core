"""Background jobs — layer 2: a job's life in the database.

created (pending) → running → done / failed / cancelled, with pause / resume
in between; progress, log lines and the error kept on the row. The worker
step is run directly (`run_next_job`) — no thread, no sleep. The bulk jobs
that change rules must only touch active rules (never the trash).
"""
import datetime
import uuid

import pytest

from app import db
from app.core.db_class.db import ActivityLog, BackgroundJob, BackgroundJobLog, RuleTagAssociation
from tests_new.helpers.db import count, reload
from tests_new.helpers.jobs import (
    ADMIN_JOB_TYPE, FAKE_JOB_TYPE, add_log, fake_handler, make_job, run_next_job, with_special_roles,
)
from tests_new.helpers.rules import make_rule
from tests_new.helpers.tags import default_tag, make_tag

HOURS_AGO = lambda h: datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=h)  # noqa: E731


def _trash(rule):
    rule.is_deleted = True
    rule.deleted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return rule


def _log_events(job):
    db.session.expire_all()
    return [log.event for log in BackgroundJobLog.query.filter_by(job_id=job.id).order_by(BackgroundJobLog.id)]


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_job_stores_a_pending_job_owned_by_the_creator(clients, users):
    response = clients["admin"].post("/jobs/create", json={
        "job_type": ADMIN_JOB_TYPE, "label": "Rescore everything", "payload": {"filters": {}}})

    assert response.status_code == 200
    job = BackgroundJob.query.one()
    assert response.get_json()["job"]["uuid"] == job.uuid
    assert (job.status, job.label, job.created_by) == ("pending", "Rescore everything", users.admin.id)
    assert job.payload == {"filters": {}, "user_id": users.admin.id}
    assert _log_events(job) == ["queued"]
    assert count(ActivityLog, action="job.create") == 1


def test_create_job_without_a_label_is_labelled_with_its_type(clients):
    clients["admin"].post("/jobs/create", json={"job_type": ADMIN_JOB_TYPE})

    assert BackgroundJob.query.one().label == ADMIN_JOB_TYPE


def test_create_job_without_a_type_stores_nothing(clients):
    response = clients["admin"].post("/jobs/create", json={"payload": {}})

    assert response.status_code == 400
    assert count(BackgroundJob) == 0


def test_create_job_of_an_unknown_type_stores_nothing(clients):
    response = clients["admin"].post("/jobs/create", json={"job_type": "no_such_job"})

    assert response.status_code == 400
    assert count(BackgroundJob) == 0


# ── Read ──────────────────────────────────────────────────────────────────────

def test_job_detail_returns_progress_and_log(clients, users):
    job = make_job(users.owner, status="running", total=4, done=1)
    add_log(job, "batch 1 done", event="progress")

    data = clients["owner"].get(f"/jobs/api/{job.uuid}").get_json()

    assert (data["status"], data["total"], data["done"], data["progress"]) == ("running", 4, 1, 25)
    assert [log["msg"] for log in data["logs"]] == ["batch 1 done"]
    assert data["author"]["id"] == users.owner.id


def test_job_log_since_id_returns_only_newer_lines(clients, users):
    job = make_job(users.owner)
    first = add_log(job, "first")
    add_log(job, "second")

    data = clients["owner"].get(f"/jobs/logs/{job.uuid}?since_id={first.id}").get_json()

    assert [log["message"] for log in data] == ["second"]


def test_finished_job_without_items_is_complete(users):
    job = make_job(users.owner, status="done")

    assert job.progress_pct == 100


@pytest.mark.parametrize("status", ["pending", "running", "paused"])
def test_my_active_jobs_lists_unfinished_jobs(status, clients, users):
    job = make_job(users.owner, status=status)

    data = clients["owner"].get("/jobs/my_active").get_json()

    assert [j["uuid"] for j in data] == [job.uuid]


def test_my_active_jobs_drops_jobs_finished_long_ago(clients, users):
    make_job(users.owner, status="done", finished_at=HOURS_AGO(1))
    make_job(users.owner, status="failed")

    assert clients["owner"].get("/jobs/my_active").get_json() == []


def test_list_filters_by_status_and_search(clients, users):
    make_job(users.owner, status="done", label="alpha")
    wanted = make_job(users.owner, status="failed", label="alpha beta")
    make_job(users.owner, status="failed", label="gamma")

    data = clients["owner"].get("/jobs/api/list?status=failed&search=alpha").get_json()

    assert [j["uuid"] for j in data["items"]] == [wanted.uuid]
    assert data["total"] == 1


def test_list_mine_only_hides_other_jobs_from_an_admin(clients, users):
    make_job(users.owner)
    mine = make_job(users.admin)

    data = clients["admin"].get("/jobs/api/list?mine_only=true").get_json()

    assert [j["uuid"] for j in data["items"]] == [mine.uuid]


def test_alerts_list_failed_jobs_and_jobs_cancelled_mid_run(clients, users):
    failed = make_job(users.owner, status="failed", error="boom")
    stopped = make_job(users.owner, status="cancelled")
    make_job(users.owner, status="cancelled", started_at=None)
    make_job(users.owner, status="done")

    data = clients["owner"].get("/jobs/api/alerts").get_json()

    assert [j["uuid"] for j in data["errors"]] == [failed.uuid]
    assert [j["uuid"] for j in data["warnings"]] == [stopped.uuid]


# ── Pause / resume / cancel / delete ──────────────────────────────────────────

@pytest.mark.parametrize("status", ["pending", "running", "paused"])
def test_cancel_unfinished_job(status, clients, users):
    job = make_job(users.owner, status=status)

    response = clients["owner"].post(f"/jobs/cancel/{job.uuid}")

    assert response.status_code == 200
    stored = reload(job)
    assert stored.status == "cancelled"
    assert stored.finished_at is not None
    assert _log_events(job)[-1] == "cancelled"
    assert count(ActivityLog, action="job.cancel") == 1


@pytest.mark.parametrize("status", ["done", "failed", "cancelled"])
def test_cancel_finished_job_is_refused(status, clients, users):
    job = make_job(users.owner, status=status)

    response = clients["owner"].post(f"/jobs/cancel/{job.uuid}")

    assert response.status_code == 400
    assert reload(job).status == status


@pytest.mark.parametrize("status", ["pending", "running"])
def test_pause_job(status, clients, users):
    job = make_job(users.owner, status=status)

    response = clients["owner"].post(f"/jobs/pause/{job.uuid}")

    assert response.status_code == 200
    assert reload(job).status == "paused"


@pytest.mark.parametrize("status", ["paused", "done", "failed", "cancelled"])
def test_pause_job_that_isnt_running_is_refused(status, clients, users):
    job = make_job(users.owner, status=status)

    response = clients["owner"].post(f"/jobs/pause/{job.uuid}")

    assert response.status_code == 400
    assert reload(job).status == status


def test_resume_paused_job_queues_it_again(clients, users):
    job = make_job(users.owner, status="paused", payload={"_resume_offset": 40})

    response = clients["owner"].post(f"/jobs/resume/{job.uuid}")

    assert response.status_code == 200
    stored = reload(job)
    assert (stored.status, stored.started_at) == ("pending", None)
    assert stored.payload["_resume_offset"] == 40


@pytest.mark.parametrize("status", ["pending", "running", "done", "failed", "cancelled"])
def test_resume_job_that_isnt_paused_is_refused(status, clients, users):
    job = make_job(users.owner, status=status)

    response = clients["owner"].post(f"/jobs/resume/{job.uuid}")

    assert response.status_code == 400
    assert reload(job).status == status


@pytest.mark.parametrize("status", ["done", "failed", "cancelled", "paused"])
def test_delete_job_removes_it_and_its_log(status, clients, users):
    job = make_job(users.owner, status=status)
    add_log(job, "a line")

    response = clients["owner"].post(f"/jobs/delete/{job.uuid}")

    assert response.status_code == 200
    assert reload(job) is None
    assert count(BackgroundJobLog) == 0
    assert count(ActivityLog, action="job.delete") == 1


@pytest.mark.parametrize("status", ["pending", "running"])
def test_delete_unfinished_job_is_refused(status, clients, users):
    job = make_job(users.owner, status=status)

    response = clients["owner"].post(f"/jobs/delete/{job.uuid}")

    assert response.status_code == 400
    assert reload(job).status == status


def test_bulk_cancel_counts_each_job(clients, users):
    mine_running = make_job(users.owner, status="running")
    mine_done = make_job(users.owner, status="done")
    someone_elses = make_job(users.user, status="running")

    response = clients["owner"].post("/jobs/api/bulk", json={
        "action": "cancel", "uuids": [mine_running.id, mine_done.uuid, someone_elses.uuid, "no-such-job"]})

    assert (response.get_json()["success"], response.get_json()["failed"]) == (1, 3)
    assert reload(mine_running).status == "cancelled"
    assert reload(mine_done).status == "done"
    assert reload(someone_elses).status == "running"


def test_bulk_delete_by_admin_removes_any_finished_job(clients, users):
    jobs = [make_job(users.owner, status="done"), make_job(users.user, status="failed")]

    response = clients["admin"].post("/jobs/api/bulk", json={"action": "delete", "uuids": [j.uuid for j in jobs]})

    assert response.get_json()["success"] == 2
    assert count(BackgroundJob) == 0


# ── Zombies ───────────────────────────────────────────────────────────────────

def test_zombies_are_jobs_stuck_running_or_pending_too_long(clients, users):
    stuck_running = make_job(users.owner, status="running", started_at=HOURS_AGO(3))
    stuck_pending = make_job(users.owner, created_at=HOURS_AGO(7))
    make_job(users.owner, status="running")
    make_job(users.owner)

    data = clients["admin"].get("/jobs/zombies").get_json()

    assert {j["uuid"] for j in data} == {stuck_running.uuid, stuck_pending.uuid}


def test_kill_zombies_fails_only_the_stuck_jobs(clients, users):
    stuck = make_job(users.owner, status="running", started_at=HOURS_AGO(3))
    healthy = make_job(users.owner, status="running")

    response = clients["admin"].post("/jobs/kill_zombies")

    assert response.get_json()["killed"] == 1
    assert (reload(stuck).status, reload(healthy).status) == ("failed", "running")
    assert "Killed by admin" in reload(stuck).error


# ── The worker ────────────────────────────────────────────────────────────────

def test_worker_with_nothing_pending_does_nothing(app, users):
    make_job(users.owner, status="done")

    assert run_next_job(app) is None


def test_worker_runs_the_oldest_pending_job_to_done(app, users, monkeypatch):
    ran = fake_handler(monkeypatch)
    first = make_job(users.owner)
    second = make_job(users.owner)

    assert run_next_job(app) == first.uuid

    assert ran == [first.uuid]
    stored = reload(first)
    assert stored.status == "done"
    assert stored.started_at is not None and stored.finished_at is not None
    assert _log_events(first) == ["picked_up"]
    assert reload(second).status == "pending"


def test_worker_keeps_the_progress_the_handler_reports(app, users, monkeypatch):
    def work(job, app):
        job.total, job.done = 8, 8
        job.payload = {**job.payload, "_resume_offset": 8, "result": {"changed": 3}}
        db.session.commit()
    fake_handler(monkeypatch, run=work)
    job = make_job(users.owner)

    run_next_job(app)

    stored = reload(job)
    assert (stored.status, stored.progress_pct) == ("done", 100)
    assert stored.payload == {"result": {"changed": 3}}


def test_worker_marks_a_crashing_job_failed_with_its_error(app, users, monkeypatch):
    def crash(job, app):
        raise RuntimeError("disk on fire")
    fake_handler(monkeypatch, run=crash)
    job = make_job(users.owner)

    run_next_job(app)

    stored = reload(job)
    assert (stored.status, stored.error) == ("failed", "disk on fire")
    assert stored.finished_at is not None
    assert _log_events(job)[-1] == "failed"


def test_worker_keeps_running_jobs_after_one_crashed(app, users, monkeypatch):
    def crash_first(job, app):
        if job.label == "first":
            raise RuntimeError("boom")
    fake_handler(monkeypatch, run=crash_first)
    first = make_job(users.owner, label="first")
    second = make_job(users.owner, label="second")

    run_next_job(app)
    run_next_job(app)

    assert (reload(first).status, reload(second).status) == ("failed", "done")


def test_worker_does_not_save_half_of_a_crashing_jobs_changes(app, users, monkeypatch):
    rule = make_rule(users.owner)

    def half_then_crash(job, app):
        rule.title = "half-written"
        raise RuntimeError("boom")
    fake_handler(monkeypatch, run=half_then_crash)
    make_job(users.owner)

    run_next_job(app)

    assert reload(rule).title != "half-written"


@pytest.mark.parametrize("status", ["cancelled", "paused", "failed"])
def test_worker_keeps_the_status_a_handler_stopped_on(status, app, users, monkeypatch):
    def stop(job, app):
        job.status = status
        db.session.commit()
    fake_handler(monkeypatch, run=stop)
    job = make_job(users.owner)

    run_next_job(app)

    assert reload(job).status == status


def test_worker_fails_a_job_of_an_unknown_type_without_blocking_the_queue(app, users, monkeypatch):
    fake_handler(monkeypatch)
    unknown = make_job(users.owner, job_type="no_such_job")
    queued_after = make_job(users.owner)

    run_next_job(app)
    run_next_job(app)

    assert reload(unknown).status == "failed"
    assert "no_such_job" in reload(unknown).error
    assert reload(queued_after).status == "done"


def test_default_worker_leaves_background_lane_jobs_alone(app, users, monkeypatch):
    fake_handler(monkeypatch, "ai_generate")
    ai_job = make_job(users.owner, job_type="ai_generate")

    assert run_next_job(app) is None

    assert reload(ai_job).status == "pending"


def test_worker_restart_queues_interrupted_jobs_again(app, users):
    from app.features.jobs.job_worker import recover_interrupted_jobs
    interrupted = make_job(users.owner, status="running")
    finished = make_job(users.owner, status="done")

    assert recover_interrupted_jobs("default") == 1

    assert (reload(interrupted).status, reload(interrupted).started_at) == ("pending", None)
    assert reload(finished).status == "done"


@pytest.mark.parametrize("status", ["running", "paused", "done", "failed", "cancelled"])
def test_worker_only_picks_up_pending_jobs(status, app, users, monkeypatch):
    ran = fake_handler(monkeypatch)
    make_job(users.owner, status=status)

    assert run_next_job(app) is None

    assert ran == []


# ── Bulk jobs on rules: active rules only ─────────────────────────────────────

@pytest.fixture
def every(clients, client_as):
    return with_special_roles(clients, client_as)


def _queue_and_run(app, client, job_type, payload):
    response = client.post("/jobs/create", json={"job_type": job_type, "payload": payload})
    assert response.status_code == 200
    run_next_job(app)
    return BackgroundJob.query.filter_by(uuid=response.get_json()["job"]["uuid"]).one()


def _tag_ids(rule):
    db.session.expire_all()
    return {a.tag_id for a in RuleTagAssociation.query.filter_by(rule_id=rule.id)}


@pytest.mark.parametrize("filters", [{}, "pick"])
def test_bulk_add_tag_tags_active_rules_only(filters, app, every, users):
    active, trashed = make_rule(users.owner), _trash(make_rule(users.owner))
    tag = make_tag(users.admin)
    if filters == "pick":
        filters = {"rule_ids": [active.id, trashed.id]}

    job = _queue_and_run(app, every["tagger"], "bulk_add_tag_to_rules", {"tag_ids": [tag.id], "filters": filters})

    assert job.status == "done"
    assert tag.id in _tag_ids(active)
    assert tag.id not in _tag_ids(trashed)


def test_bulk_add_tag_ignores_unknown_tag_ids(app, every, users):
    rule = make_rule(users.owner)
    tag = make_tag(users.admin)

    job = _queue_and_run(app, every["tagger"], "bulk_add_tag_to_rules",
                         {"tag_ids": [tag.id, 999_999], "filters": {"rule_ids": [rule.id]}})

    assert job.status == "done"
    assert _tag_ids(rule) == {tag.id}


def test_bulk_add_tag_with_only_unknown_tags_fails_cleanly(app, every, users):
    rule = make_rule(users.owner)

    job = _queue_and_run(app, every["tagger"], "bulk_add_tag_to_rules",
                         {"tag_ids": [999_999], "filters": {"rule_ids": [rule.id]}})

    assert job.status == "failed"
    assert _tag_ids(rule) == set()


def test_bulk_remove_tag_leaves_trashed_rules_untouched(app, every, users):
    tag = default_tag()
    active, trashed = make_rule(users.owner), make_rule(users.owner)
    for rule in (active, trashed):
        db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=rule.id, tag_id=tag.id, user_id=users.admin.id))
    db.session.commit()
    _trash(trashed)

    job = _queue_and_run(app, every["tagger"], "bulk_remove_tag_from_rules", {"tag_ids": [tag.id], "filters": {}})

    assert job.status == "done"
    assert tag.id not in _tag_ids(active)
    assert tag.id in _tag_ids(trashed)


def test_rule_quality_job_scores_active_rules_only(app, every, users):
    active, trashed = make_rule(users.owner), _trash(make_rule(users.owner))

    job = _queue_and_run(app, every["admin"], ADMIN_JOB_TYPE, {"filters": {}})

    assert (job.status, job.total) == ("done", 1)
    assert reload(active).quality_score is not None
    assert reload(trashed).quality_score is None


def test_delete_github_rules_job_trashes_only_active_rules_of_those_sources(app, users):
    url = "https://github.com/acme/rules"
    kept = make_rule(users.owner, source="https://github.com/other/rules")
    target = make_rule(users.owner, source=url)
    already = _trash(make_rule(users.owner, source=url))
    already_batch = already.delete_batch_uuid
    make_job(users.admin, job_type="delete_github_rules", payload={"urls": [url]})

    run_next_job(app)

    assert reload(target).is_deleted is True
    assert reload(kept).is_deleted is False
    assert reload(already).delete_batch_uuid == already_batch
