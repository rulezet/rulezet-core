"""Background jobs — layer 4: inputs meant to break Rulezet.

Expected every time: a clean answer (< 500), nothing stored when the input
is refused, and hostile text (a label, a log line, an error) kept as plain
text — escaped when a page shows it, never interpreted.
"""
import pytest

from app.core.db_class.db import BackgroundJob
from tests_new.helpers.db import count, reload
from tests_new.helpers.inputs import BAD_IDS, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests_new.helpers.jobs import ADMIN_JOB_TYPE, add_log, make_job, with_special_roles

NOT_AN_OBJECT = ["[1, 2]", '"text"', "42", "null", "{broken", ""]
ODD_PARAMS = ["abc", "-1", "0", "1.5", str(2**70), pytest.param(TOO_LONG[:5000], id="too-long")]


@pytest.fixture
def every(clients, client_as):
    return with_special_roles(clients, client_as)


# ── /jobs/create ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role", ["admin", "tagger", "ai_user"])
@pytest.mark.parametrize("body", NOT_AN_OBJECT)
def test_create_with_a_body_that_isnt_an_object_stores_nothing(body, role, every):
    response = every[role].post("/jobs/create", data=body, content_type="application/json")

    assert 400 <= response.status_code < 500
    assert count(BackgroundJob) == 0


@pytest.mark.parametrize("role, job_type", [("admin", ADMIN_JOB_TYPE), ("tagger", "bulk_add_tag_to_rules"),
                                            ("ai_user", "ai_generate")])
@pytest.mark.parametrize("payload", [p for p in WRONG_TYPES if not isinstance(p, dict)])
def test_create_with_a_payload_that_isnt_an_object_stores_nothing(payload, role, job_type, every):
    response = every[role].post("/jobs/create", json={"job_type": job_type, "payload": payload})

    assert 400 <= response.status_code < 500
    assert count(BackgroundJob) == 0


@pytest.mark.parametrize("job_type", [t for t in WRONG_TYPES if t is not None]
                         + [pytest.param(TOO_LONG, id="too-long"), *INJECTIONS])
def test_create_with_a_bad_job_type_stores_nothing(job_type, clients):
    response = clients["admin"].post("/jobs/create", json={"job_type": job_type})

    assert response.status_code == 400
    assert count(BackgroundJob) == 0


@pytest.mark.parametrize("label", [12345, ["a"], {"x": 1}, True, pytest.param("A" * 256, id="too-long")])
def test_create_with_a_bad_label_stores_nothing(label, clients):
    response = clients["admin"].post("/jobs/create", json={"job_type": ADMIN_JOB_TYPE, "label": label})

    assert response.status_code == 400
    assert count(BackgroundJob) == 0


@pytest.mark.parametrize("label", [*INJECTIONS, *ODD_CHARACTERS])
def test_create_with_a_hostile_label_stores_it_as_text(label, clients):
    response = clients["admin"].post("/jobs/create", json={"job_type": ADMIN_JOB_TYPE, "label": label})

    assert response.status_code == 200
    assert BackgroundJob.query.one().label == label


def test_create_with_a_huge_payload_never_errors(clients):
    payload = {"filters": {"rule_ids": list(range(1, 50_000))}, "note": TOO_LONG}

    response = clients["admin"].post("/jobs/create", json={"job_type": ADMIN_JOB_TYPE, "payload": payload})

    assert response.status_code < 500


# ── Hostile text shown back ───────────────────────────────────────────────────

@pytest.mark.parametrize("text", INJECTIONS)
def test_hostile_label_log_and_error_come_back_verbatim_in_json(text, clients, users):
    job = make_job(users.owner, status="failed", label=text, error=text)
    add_log(job, text, level="error")

    data = clients["owner"].get(f"/jobs/api/{job.uuid}").get_json()

    assert (data["title"], data["error"], data["logs"][0]["msg"]) == (text, text, text)


def test_hostile_label_is_escaped_on_the_detail_page(clients, users):
    job = make_job(users.owner, label="<script>alert(1)</script>{{7*7}}")

    page = clients["owner"].get(f"/jobs/detail/{job.uuid}").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


# ── Ids and query parameters ──────────────────────────────────────────────────

@pytest.mark.parametrize("ref", [str(b) for b in BAD_IDS] + [pytest.param(TOO_LONG[:3000], id="too-long"), "%00", "<script>"])
@pytest.mark.parametrize("url", ["/jobs/api/{ref}", "/jobs/status/{ref}", "/jobs/logs/{ref}", "/jobs/detail/{ref}"])
def test_read_an_unknown_job_is_not_found(url, ref, clients):
    response = clients["admin"].get(url.format(ref=ref))

    assert response.status_code == 404


@pytest.mark.parametrize("url", ["/jobs/cancel/{ref}", "/jobs/pause/{ref}", "/jobs/resume/{ref}",
                                 "/jobs/delete/{ref}", "/jobs/api/{ref}/cancel"])
@pytest.mark.parametrize("ref", ["0", "-1", str(2**63), "abc"])
def test_act_on_an_unknown_job_is_not_found(url, ref, clients):
    response = clients["admin"].post(url.format(ref=ref))

    assert response.status_code == 404


@pytest.mark.parametrize("value", ODD_PARAMS)
@pytest.mark.parametrize("param", ["page", "per_page", "sort", "dir", "status", "search", "mine_only", "admin"])
@pytest.mark.parametrize("url", ["/jobs/api/list", "/jobs/get_jobs"])
def test_list_with_odd_parameters_never_errors(url, param, value, clients, users):
    make_job(users.owner)

    response = clients["admin"].get(url, query_string={param: value})

    assert response.status_code == 200


@pytest.mark.parametrize("param", ["page", "per_page"])
@pytest.mark.parametrize("url", ["/jobs/api/list", "/jobs/get_jobs"])
def test_list_with_a_huge_page_size_is_capped(url, param, clients, users):
    for _ in range(3):
        make_job(users.owner)

    response = clients["owner"].get(url, query_string={"per_page": 10**9, "page": 1})

    assert response.status_code == 200
    assert response.get_json()["total"] == 3


@pytest.mark.parametrize("value", ODD_PARAMS)
def test_error_log_with_an_odd_limit_never_errors(value, clients, users):
    job = make_job(users.owner, status="failed")
    add_log(job, "boom", level="error")

    response = clients["admin"].get("/jobs/errors", query_string={"limit": value})

    assert response.status_code == 200


@pytest.mark.parametrize("value", ODD_PARAMS)
def test_job_log_with_an_odd_since_id_never_errors(value, clients, users):
    job = make_job(users.owner)
    add_log(job, "line")

    response = clients["owner"].get(f"/jobs/logs/{job.uuid}", query_string={"since_id": value})

    assert response.status_code == 200


# ── /jobs/api/bulk ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", NOT_AN_OBJECT)
def test_bulk_with_a_body_that_isnt_an_object_changes_nothing(body, clients, users):
    job = make_job(users.owner, status="running")

    response = clients["owner"].post("/jobs/api/bulk", data=body, content_type="application/json")

    assert 400 <= response.status_code < 500
    assert reload(job).status == "running"


@pytest.mark.parametrize("uuids", ["1", "12", 1, {"1": 1}, True])
def test_bulk_with_uuids_that_arent_a_list_changes_nothing(uuids, clients, users):
    job = make_job(users.owner, status="running")

    response = clients["owner"].post("/jobs/api/bulk", json={"action": "cancel", "uuids": uuids})

    assert response.status_code == 400
    assert reload(job).status == "running"


@pytest.mark.parametrize("ref", [*BAD_IDS, None, 1.5, True, [], {}, pytest.param(TOO_LONG, id="too-long")])
def test_bulk_with_bad_job_references_counts_them_failed(ref, clients, users):
    job = make_job(users.owner, status="running")

    response = clients["owner"].post("/jobs/api/bulk", json={"action": "cancel", "uuids": [ref]})

    assert response.status_code == 200
    assert response.get_json()["success"] == 0
    assert reload(job).status == "running"


@pytest.mark.parametrize("action", [None, 1, ["cancel"], {"a": 1}, "pause", "DELETE", pytest.param(TOO_LONG, id="too-long")])
def test_bulk_with_an_unknown_action_changes_nothing(action, clients, users):
    job = make_job(users.owner, status="done")

    response = clients["owner"].post("/jobs/api/bulk", json={"action": action, "uuids": [job.uuid]})

    assert response.status_code == 400
    assert reload(job) is not None


# ── Bulk rule jobs with a broken payload fail cleanly ─────────────────────────

@pytest.mark.parametrize("payload", [
    {"tag_ids": "1", "filters": {}},
    {"tag_ids": [1], "filters": "all"},
    {"tag_ids": [1], "filters": {"rule_ids": "1,2"}},
    {"tag_ids": [1], "filters": {"user_id": "abc"}},
    {"tag_ids": [1], "filters": {"search": 12}},
    {"tag_ids": [{"id": 1}], "filters": {}},
])
def test_bulk_tag_job_with_a_broken_payload_fails_without_crashing_the_worker(payload, app, users, monkeypatch):
    from tests_new.helpers.jobs import fake_handler, run_next_job
    broken = make_job(users.admin, job_type="bulk_add_tag_to_rules", payload=payload)
    ran = fake_handler(monkeypatch)
    after = make_job(users.admin)

    run_next_job(app)
    run_next_job(app)

    assert reload(broken).status in ("failed", "done")
    assert reload(after).status == "done"
    assert ran == [after.uuid]
