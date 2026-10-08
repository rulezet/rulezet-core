"""Background jobs — layer 1: who can do what.

Roles: "owner" created the job (`created_by`), "tagger" is a non-admin holding
`rule.tag_any`, "ai_user" a non-admin holding `ai.use`.

Permission model: every jobs route needs an account. A job, its progress and
its log are seen only by the user who created it and by admins — another
user gets a 403 (a 404 on the detail page, which doesn't reveal it exists).
The same goes for pausing, resuming, cancelling and deleting it. Lists show a
user their own jobs only; admins see every job. The error log panel, zombie
detection / killing and the admin job list are for admins. Through
/jobs/create, admins queue any job type; a tagger may queue the two bulk tag
jobs, an ai_user a Rule Analysis run — nothing else.
"""
import pytest

from app.core.db_class.db import BackgroundJob
from tests_new.helpers.access import FORBIDDEN, LOGIN, NOT_FOUND, OK, assert_outcome, matrix
from tests_new.helpers.db import count, reload
from tests_new.helpers.jobs import ADMIN_JOB_TYPE, TAG_JOB_TYPES, add_log, make_job, with_special_roles
from tests_new.helpers.tags import default_tag

LOGGED_IN = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK}
CREATOR_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
CREATOR_OR_ADMIN_PAGE = {"anonymous": LOGIN, "user": NOT_FOUND, "owner": OK, "admin": OK}
ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}

CREATE_ADMIN_JOB = {"anonymous": LOGIN, "user": FORBIDDEN, "admin": OK, "tagger": FORBIDDEN, "ai_user": FORBIDDEN}
CREATE_TAG_JOB = {"anonymous": LOGIN, "user": FORBIDDEN, "admin": OK, "tagger": OK, "ai_user": FORBIDDEN}
CREATE_RULE_ANALYSIS = {"anonymous": LOGIN, "user": FORBIDDEN, "admin": OK, "tagger": FORBIDDEN, "ai_user": OK}


@pytest.fixture
def every(clients, client_as):
    return with_special_roles(clients, client_as)


# ── Pages ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_open_my_jobs_page(role, expected, clients):
    response = clients[role].get("/jobs/list")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_open_admin_jobs_page(role, expected, clients):
    response = clients[role].get("/admin/jobs/list")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN_PAGE))
def test_open_job_detail_page(role, expected, clients, users):
    job = make_job(users.owner)

    response = clients[role].get(f"/jobs/detail/{job.uuid}")

    assert_outcome(response, expected)


# ── Reading one job ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", ["/jobs/api/{uuid}", "/jobs/status/{uuid}"])
@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_read_job(role, expected, url, clients, users):
    job = make_job(users.owner, label="owner's secret job")

    response = clients[role].get(url.format(uuid=job.uuid))

    assert_outcome(response, expected)
    assert (b"owner's secret job" in response.data) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_read_job_log(role, expected, clients, users):
    job = make_job(users.owner)
    add_log(job, "secret log line")

    response = clients[role].get(f"/jobs/logs/{job.uuid}")

    assert_outcome(response, expected)
    assert (b"secret log line" in response.data) is (expected is OK)


# ── Lists ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url, key", [
    ("/jobs/api/list?per_page=100", "items"),
    ("/jobs/get_jobs?per_page=100", "jobs"),
])
@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_list_jobs(role, expected, url, key, clients, users):
    owners_job = make_job(users.owner)

    response = clients[role].get(url)

    assert_outcome(response, expected)
    if expected is OK:
        listed = {j["uuid"] for j in response.get_json()[key]}
        assert (owners_job.uuid in listed) is (role in ("owner", "admin"))


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_list_job_alerts(role, expected, clients, users):
    failed = make_job(users.owner, status="failed", error="boom")

    response = clients[role].get("/jobs/api/alerts")

    assert_outcome(response, expected)
    if expected is OK:
        listed = {j["uuid"] for j in response.get_json()["errors"]}
        assert (failed.uuid in listed) is (role in ("owner", "admin"))


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_list_my_active_jobs(role, expected, clients, users):
    running = make_job(users.owner, status="running")

    response = clients[role].get("/jobs/my_active")

    assert_outcome(response, expected)
    if expected is OK:
        assert (running.uuid in {j["uuid"] for j in response.get_json()}) is (role == "owner")


def test_admin_list_view_shows_each_jobs_author(clients, users):
    make_job(users.owner)

    rows = clients["admin"].get("/jobs/api/list?admin=true").get_json()["items"]

    assert rows[0]["author"]["id"] == users.owner.id


def test_user_list_view_never_shows_an_author_column(clients, users):
    make_job(users.owner)

    rows = clients["owner"].get("/jobs/api/list?admin=true").get_json()["items"]

    assert "author" not in rows[0]


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_read_error_log_of_every_job(role, expected, clients, users):
    job = make_job(users.owner, status="failed")
    add_log(job, "an error line", level="error")

    response = clients[role].get("/jobs/errors")

    assert_outcome(response, expected)
    assert (b"an error line" in response.data) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_list_zombie_jobs(role, expected, clients):
    response = clients[role].get("/jobs/zombies")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_kill_zombie_jobs(role, expected, clients, users):
    import datetime
    long_ago = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=3)
    stuck = make_job(users.owner, status="running", started_at=long_ago)

    response = clients[role].post("/jobs/kill_zombies")

    assert_outcome(response, expected)
    assert reload(stuck).status == ("failed" if expected is OK else "running")


# ── Acting on one job ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", ["/jobs/cancel/{uuid}", "/jobs/api/{uuid}/cancel"])
@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_cancel_job(role, expected, url, clients, users):
    job = make_job(users.owner, status="running")

    response = clients[role].post(url.format(uuid=job.uuid))

    assert_outcome(response, expected)
    assert reload(job).status == ("cancelled" if expected is OK else "running")


@pytest.mark.parametrize("url", ["/jobs/pause/{uuid}", "/jobs/api/{uuid}/pause"])
@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_pause_job(role, expected, url, clients, users):
    job = make_job(users.owner, status="running")

    response = clients[role].post(url.format(uuid=job.uuid))

    assert_outcome(response, expected)
    assert reload(job).status == ("paused" if expected is OK else "running")


@pytest.mark.parametrize("url", ["/jobs/resume/{uuid}", "/jobs/api/{uuid}/resume"])
@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_resume_job(role, expected, url, clients, users):
    job = make_job(users.owner, status="paused")

    response = clients[role].post(url.format(uuid=job.uuid))

    assert_outcome(response, expected)
    assert reload(job).status == ("pending" if expected is OK else "paused")


@pytest.mark.parametrize("method, url", [("post", "/jobs/delete/{uuid}"), ("delete", "/jobs/api/{uuid}")])
@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_delete_job(role, expected, method, url, clients, users):
    job = make_job(users.owner, status="done")

    response = getattr(clients[role], method)(url.format(uuid=job.uuid))

    assert_outcome(response, expected)
    assert (reload(job) is None) is (expected is OK)


@pytest.mark.parametrize("action, status_after", [("cancel", "cancelled"), ("delete", None)])
@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_bulk_action_on_jobs(role, expected, action, status_after, clients, users):
    job = make_job(users.owner, status="running" if action == "cancel" else "done")
    status_before = job.status

    response = clients[role].post("/jobs/api/bulk", json={"action": action, "uuids": [job.uuid]})

    if expected is LOGIN:
        assert_outcome(response, LOGIN)
    else:
        assert response.status_code == 200
        assert response.get_json()["success"] == (1 if expected is OK else 0)
    stored = reload(job)
    if expected is OK:
        assert (stored is None) if status_after is None else (stored.status == status_after)
    else:
        assert stored.status == status_before


# ── Creating a job ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(CREATE_ADMIN_JOB))
def test_create_admin_job(role, expected, every):
    response = every[role].post("/jobs/create", json={"job_type": ADMIN_JOB_TYPE, "payload": {"filters": {}}})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type=ADMIN_JOB_TYPE) == (1 if expected is OK else 0)


@pytest.mark.parametrize("job_type", TAG_JOB_TYPES)
@pytest.mark.parametrize("role, expected", matrix(CREATE_TAG_JOB))
def test_create_bulk_tag_job(role, expected, job_type, every):
    payload = {"tag_ids": [default_tag().id], "filters": {"rule_ids": [1]}}

    response = every[role].post("/jobs/create", json={"job_type": job_type, "payload": payload})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type=job_type) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(CREATE_RULE_ANALYSIS))
def test_create_rule_analysis_job(role, expected, every):
    payload = {"agent_key": "rule_analysis", "filters": {}}

    response = every[role].post("/jobs/create", json={"job_type": "ai_generate", "payload": payload})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="ai_generate") == (1 if expected is OK else 0)


def test_create_other_ai_job_as_ai_user_is_forbidden(every):
    payload = {"agent_key": "rule_generator"}

    response = every["ai_user"].post("/jobs/create", json={"job_type": "ai_generate", "payload": payload})

    assert response.status_code == 403
    assert count(BackgroundJob) == 0


def test_create_rule_analysis_as_ai_user_drops_the_run_limits(every):
    """Lifting the batch / time caps is an AI admin decision (ai.manage)."""
    payload = {"agent_key": "rule_analysis", "unlimited_batch": True, "unlimited_time": True,
               "batch_size": 10**6, "max_seconds": 10**9}

    every["ai_user"].post("/jobs/create", json={"job_type": "ai_generate", "payload": payload})

    stored = BackgroundJob.query.one().payload
    assert not {"unlimited_batch", "unlimited_time", "batch_size", "max_seconds"} & stored.keys()


def test_create_job_records_the_creator_not_a_user_id_from_the_payload(clients, users):
    response = clients["admin"].post("/jobs/create", json={
        "job_type": ADMIN_JOB_TYPE, "payload": {"filters": {}, "user_id": users.owner.id}})

    assert response.status_code == 200
    job = BackgroundJob.query.one()
    assert job.created_by == users.admin.id
    assert job.payload["user_id"] == users.admin.id
