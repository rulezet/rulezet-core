"""AI analysis requests — a user who can't launch an analysis asks for one
from a rule's / bundle's AI Analysis section; the AI managers accept (the
analysis job is queued) or reject it on the admin pages.

Roles: "user" can't launch anything (requests), "admin" can launch and
reviews the requests.
"""
from app.core.db_class.db import AIAnalysisRequest, BackgroundJob, Notification
from tests_new.helpers.bundles import make_bundle
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule


def _request_rule(client, rule, script="standard", message="no description"):
    return client.post(f"/rule/detail_rule/{rule.id}/ai_analysis/request",
                       json={"script": script, "message": message})


def test_a_user_who_cant_launch_may_request_and_admins_are_notified(clients, users):
    rule = make_rule(users.owner)

    state = clients["user"].get(f"/rule/detail_rule/{rule.id}/ai_analysis/request").get_json()
    assert (state["can_launch"], state["can_request"]) == (False, True)

    response = _request_rule(clients["user"], rule, script="deep")

    assert response.status_code == 201
    req = AIAnalysisRequest.query.one()
    assert (req.target_type, req.rule_id, req.script, req.status) == ("rule", rule.id, "deep", "pending")
    assert count(Notification, user_id=users.admin.id, notif_type="ai_analysis_requested") == 1


def test_the_same_request_is_never_duplicated(clients, users):
    rule = make_rule(users.owner)
    _request_rule(clients["user"], rule)

    again = _request_rule(clients["owner"], rule)

    assert again.status_code == 200 and again.get_json()["created"] is False
    assert count(AIAnalysisRequest) == 1


def test_anonymous_and_launchers_cannot_request(clients, users):
    rule = make_rule(users.owner)

    assert _request_rule(clients["anonymous"], rule).status_code in (302, 401)
    assert _request_rule(clients["admin"], rule).status_code == 400
    assert clients["admin"].get(f"/rule/detail_rule/{rule.id}/ai_analysis/request").get_json()["can_launch"] is True
    assert count(AIAnalysisRequest) == 0


def test_bad_script_and_message_are_refused(clients, users):
    rule = make_rule(users.owner)

    assert _request_rule(clients["user"], rule, script="full").status_code == 400
    assert _request_rule(clients["user"], rule, message="x" * 1001).status_code == 400
    assert count(AIAnalysisRequest) == 0


def test_accepting_queues_one_job_per_script_and_notifies(clients, users):
    rules = [make_rule(users.owner) for _ in range(3)]
    _request_rule(clients["user"], rules[0])
    _request_rule(clients["user"], rules[1])
    _request_rule(clients["user"], rules[2], script="deep")

    response = clients["admin"].post("/ai/admin/requests/rule/decide",
                                     json={"action": "accept", "all": True, "note": "on it"})

    assert response.status_code == 200 and response.get_json()["count"] == 3
    jobs = BackgroundJob.query.filter_by(job_type="ai_generate").all()
    assert sorted((j.payload["script"], sorted(j.payload["rule_ids"])) for j in jobs) == [
        ("deep", [rules[2].id]), ("standard", sorted([rules[0].id, rules[1].id]))]
    assert {r.status for r in AIAnalysisRequest.query.all()} == {"accepted"}
    assert count(Notification, user_id=users.user.id, notif_type="ai_analysis_accepted") == 3


def test_rejecting_selected_requests(clients, users):
    rule = make_rule(users.owner)
    _request_rule(clients["user"], rule)
    req = AIAnalysisRequest.query.one()

    response = clients["admin"].post("/ai/admin/requests/rule/decide",
                                     json={"action": "reject", "ids": [req.id], "note": "already documented"})

    assert response.status_code == 200
    assert (reload(req).status, reload(req).decision_note) == ("rejected", "already documented")
    assert count(BackgroundJob, job_type="ai_generate") == 0


def test_only_ai_managers_review_requests(clients, users):
    assert clients["user"].get("/ai/admin/requests/rule/data").status_code == 403
    assert clients["admin"].get("/ai/admin/requests/rule/data").status_code == 200


def test_bundle_request_and_accept(clients, users):
    bundle = make_bundle(users.owner)

    response = clients["user"].post(f"/bundle/{bundle.id}/ai_analysis/request", json={"message": "please"})
    assert response.status_code == 201

    clients["admin"].post("/ai/admin/requests/bundle/decide", json={"action": "accept", "all": True})

    job = BackgroundJob.query.filter_by(job_type="ai_bundle_analysis").one()
    assert job.payload["bundle_id"] == bundle.id
    assert AIAnalysisRequest.query.one().status == "accepted"
