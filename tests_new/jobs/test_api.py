"""Background jobs — layer 3: the JSON endpoints.

Jobs have no Flask-RESTX namespace: the job pages talk to the JSON routes of
the jobs blueprint (/jobs/api/…, /jobs/status, /jobs/logs, /jobs/get_jobs…),
which work with a logged-in session only — an X-API-KEY alone never opens
them. Jobs are also queued by other features' REST endpoints (e.g. the tags
API's bulk_add); such a job belongs to the key's owner like any other.
"""
import pytest

from app.core.db_class.db import BackgroundJob, RuleTagAssociation
from tests_new.helpers.access import LOGIN, assert_outcome
from tests_new.helpers.jobs import ADMIN_JOB_TYPE, add_log, make_job, run_next_job
from tests_new.helpers.rules import make_rule
from tests_new.helpers.tags import make_tag
from tests_new.helpers.users import api_headers, make_user_with_permission

READ_ROUTES = ["/jobs/api/list", "/jobs/get_jobs", "/jobs/api/alerts", "/jobs/my_active", "/jobs/errors",
               "/jobs/zombies", "/jobs/api/{uuid}", "/jobs/status/{uuid}", "/jobs/logs/{uuid}"]
WRITE_ROUTES = ["/jobs/cancel/{uuid}", "/jobs/pause/{uuid}", "/jobs/api/{uuid}/cancel", "/jobs/delete/{uuid}",
                "/jobs/kill_zombies", "/jobs/api/bulk", "/jobs/create"]


# ── An API key is not a session ───────────────────────────────────────────────

@pytest.mark.parametrize("url", READ_ROUTES)
def test_read_with_only_an_admin_api_key_needs_a_login(url, app, users):
    job = make_job(users.owner, label="owner's job")

    response = app.test_client().get(url.format(uuid=job.uuid), headers=api_headers(users.admin))

    assert_outcome(response, LOGIN)
    assert b"owner's job" not in response.data


@pytest.mark.parametrize("url", WRITE_ROUTES)
def test_write_with_only_an_admin_api_key_needs_a_login(url, app, users):
    job = make_job(users.owner, status="running")

    response = app.test_client().post(url.format(uuid=job.uuid), headers=api_headers(users.admin),
                                      json={"job_type": ADMIN_JOB_TYPE, "action": "cancel", "uuids": [job.uuid]})

    assert_outcome(response, LOGIN)
    assert BackgroundJob.query.one().status == "running"


# ── Jobs queued through another feature's REST API ────────────────────────────

def test_job_queued_by_the_tags_api_belongs_to_the_key_owner_and_runs(app, users, client_as):
    tagger = make_user_with_permission("rule.tag_any", "tagger")
    rule, tag = make_rule(users.owner), make_tag(users.admin)

    response = app.test_client().post("/api/tags/private/bulk_add", headers=api_headers(tagger),
                                      json={"rule_ids": [rule.id], "tag_ids": [tag.id], "confirm": True})
    job_uuid = response.get_json()["job_uuid"]
    run_next_job(app)

    assert client_as(tagger).get(f"/jobs/api/{job_uuid}").get_json()["status"] == "done"
    assert client_as(users.user).get(f"/jobs/api/{job_uuid}").status_code == 403
    assert RuleTagAssociation.query.filter_by(rule_id=rule.id, tag_id=tag.id).count() == 1


# ── Response shapes ───────────────────────────────────────────────────────────

def test_create_returns_the_queued_job(clients):
    data = clients["admin"].post("/jobs/create", json={"job_type": ADMIN_JOB_TYPE}).get_json()

    assert data["job"]["status"] == "pending"
    assert {"uuid", "job_type", "label", "progress_pct", "created_by"} <= data["job"].keys()


def test_list_shape(clients, users):
    make_job(users.owner)

    data = clients["owner"].get("/jobs/api/list").get_json()

    assert data.keys() == {"items", "total", "total_pages"}
    assert {"id", "uuid", "title", "type", "status", "progress", "duration", "error",
            "created_at", "started_at", "finished_at"} <= data["items"][0].keys()


def test_get_jobs_shape(clients, users):
    make_job(users.owner)

    data = clients["owner"].get("/jobs/get_jobs").get_json()

    assert data.keys() == {"jobs", "total", "page", "per_page", "total_pages"}
    assert "owner" not in data["jobs"][0]


def test_get_jobs_shows_the_owner_to_an_admin(clients, users):
    make_job(users.owner)

    job = clients["admin"].get("/jobs/get_jobs").get_json()["jobs"][0]

    assert job["author"]["id"] == users.owner.id
    assert job["owner"]


def test_detail_shape(clients, users):
    job = make_job(users.owner, status="running")
    add_log(job, "hello", level="success", event="progress")

    data = clients["owner"].get(f"/jobs/api/{job.uuid}").get_json()

    assert {"uuid", "title", "type", "status", "progress", "total", "done", "duration", "error", "meta",
            "logs", "author", "created_at", "started_at", "finished_at"} <= data.keys()
    assert data["logs"][0] == {"ts": data["logs"][0]["ts"], "level": "success", "msg": "hello"}


def test_logs_shape(clients, users):
    job = make_job(users.owner)
    add_log(job, "hello", level="warning", event="paused")

    data = clients["owner"].get(f"/jobs/logs/{job.uuid}").get_json()

    assert {k: data[0][k] for k in ("level", "event", "message")} == {
        "level": "warning", "event": "paused", "message": "hello"}


def test_errors_shape(clients, users):
    job = make_job(users.owner, status="failed")
    add_log(job, "it broke", level="error", event="failed")

    data = clients["admin"].get("/jobs/errors").get_json()

    assert {k: data[0][k] for k in ("message", "job_uuid", "job_status")} == {
        "message": "it broke", "job_uuid": job.uuid, "job_status": "failed"}


def test_unknown_job_answers_404(clients):
    for url in ("/jobs/api/no-such-job", "/jobs/status/no-such-job", "/jobs/logs/no-such-job"):
        assert clients["admin"].get(url).status_code == 404
    assert clients["admin"].post("/jobs/cancel/no-such-job").status_code == 404
    assert clients["admin"].delete("/jobs/api/no-such-job").status_code == 404
