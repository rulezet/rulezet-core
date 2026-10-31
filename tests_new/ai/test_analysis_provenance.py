"""AI analysis provenance and request lifecycle — issues #88 / #89 (ai_provenance.py, ai_request_core.py,
the ai_generate job). The model is replaced by a fake agent: what is tested is which input it gets and
what is recorded around it."""
from types import SimpleNamespace

from app import db
from app.core.db_class.ai import AIAnalysisRequest, AIGeneration
from app.core.db_class.job import BackgroundJob
from app.features.ai import ai_request_core as AIRequest
from app.features.ai.ai_provenance import content_hash
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule


class FakeAgent:
    """Records the rule content it was given, answers a fixed report."""
    def __init__(self):
        self.seen = []

    def run(self, **kw):
        stub = kw.get("rule_stub")
        self.seen.append(stub.to_string if stub else kw.get("rule_content"))
        return SimpleNamespace(ok=True, content="# Report", meta={"headline": "ok"}, model_used="fake-model", error=None)


def _request(client, rule, script="standard"):
    return client.post(f"/rule/detail_rule/{rule.id}/ai_analysis/request", json={"script": script})


def _accept(clients):
    r = clients["admin"].post("/ai/admin/requests/rule/decide", json={"action": "accept", "all": True})
    assert r.status_code == 200, r.get_json()
    return BackgroundJob.query.filter_by(job_type="ai_generate").order_by(BackgroundJob.id.desc()).first()


def _run(job, monkeypatch):
    from app.features.jobs import job_handlers
    agent = FakeAgent()
    monkeypatch.setattr("app.features.ai.ai_core.get_agent", lambda key: agent)
    job.status = "running"
    db.session.commit()
    job_handlers.handle_rule_analysis(job, None)
    db.session.expire_all()
    return agent


def _edit(rule, text):
    rule.to_string = rule.to_string.replace("condition", f"// {text}\n    condition")
    db.session.commit()


# ── #89 permissions ───────────────────────────────────────────────────────

def test_owner_first_policy_and_the_instance_switch(clients, users, monkeypatch):
    rule = make_rule(users.owner)
    state = clients["user"].get(f"/rule/detail_rule/{rule.id}/ai_analysis/request").get_json()
    assert state["can_request"] is False and "owner" in state["why_not"] and state["launch_needs"]
    assert _request(clients["user"], rule).status_code == 403            # someone else's rule
    assert _request(clients["owner"], rule).status_code == 201           # its owner
    monkeypatch.setattr(AIRequest, "request_policy", lambda: "anyone")
    assert _request(clients["user"], rule, "deep").status_code == 201    # instance opened to everyone


# ── #89 revision-aware deduplication over the whole lifecycle ─────────────

def test_same_revision_never_twice_while_waiting_queued_or_running(clients, users):
    rule = make_rule(users.owner)
    assert _request(clients["owner"], rule).status_code == 201
    assert _request(clients["owner"], rule).get_json()["created"] is False       # pending: same one
    _accept(clients)
    req = AIAnalysisRequest.query.one()
    assert req.execution_status == "queued"
    again = _request(clients["owner"], rule)                                       # approved, queued (scenario C)
    assert again.status_code == 200 and again.get_json()["created"] is False
    assert count(AIAnalysisRequest) == 1


def test_another_revision_is_another_request(clients, users):
    rule = make_rule(users.owner)
    _request(clients["owner"], rule)
    _edit(rule, "v4")
    assert _request(clients["owner"], rule).status_code == 201
    hashes = {r.content_hash for r in AIAnalysisRequest.query.all()}
    assert len(hashes) == 2 and content_hash(reload(rule).to_string) in hashes


# ── #88 / #89 the pinned revision is what gets analysed ───────────────────

def test_edit_while_awaiting_approval_analyses_the_requested_version(clients, users, monkeypatch):
    rule = make_rule(users.owner)
    v3 = rule.to_string
    _request(clients["owner"], rule)
    _edit(rule, "v4 written after the request")                                   # scenario A
    job = _accept(clients)
    agent = _run(job, monkeypatch)
    assert agent.seen == [v3]                                                     # never the newer v4
    gen = AIGeneration.query.one()
    req = AIAnalysisRequest.query.one()
    assert gen.content_hash == content_hash(v3) and req.content_hash == gen.content_hash
    assert (req.execution_status, req.generation_id) == ("completed", gen.id)
    # provenance: who asked, who approved, who started it, which request and job
    assert (gen.requested_by_id, gen.approved_by_id, gen.initiated_by_id) == (users.owner.id, users.admin.id, users.admin.id)
    assert (gen.request_id, gen.job_uuid) == (req.id, job.uuid)
    # the page says it describes an older version
    item = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}/ai_analysis/list").get_json()["items"][0]
    p = item["provenance"]
    assert p["outdated"] is True and p["recorded"] is True and p["model"] == "fake-model"
    assert p["requested_by"]["id"] == users.owner.id and p["scope"]["inputs"] and p["scope"]["not_checked"]


def test_two_revisions_accepted_together_go_to_two_jobs(clients, users, monkeypatch):
    monkeypatch.setattr(AIRequest, "request_policy", lambda: "anyone")
    rule = make_rule(users.owner)
    _request(clients["owner"], rule)
    _edit(rule, "v4")
    _request(clients["user"], rule)                                               # scenario B: another revision
    clients["admin"].post("/ai/admin/requests/rule/decide", json={"action": "accept", "all": True})
    jobs = BackgroundJob.query.filter_by(job_type="ai_generate").all()
    assert len(jobs) == 2                                                         # a rule at most once per job
    pinned = sorted(next(iter(j.payload["pinned"].values()))["hash"] for j in jobs)
    assert pinned == sorted(r.content_hash for r in AIAnalysisRequest.query.all())


def test_direct_run_records_its_revision_and_no_request(clients, users, monkeypatch):
    rule = make_rule(users.owner)
    job = BackgroundJob(uuid="direct-run", job_type="ai_generate", status="running", total=0, done=0,
                        created_by=users.admin.id, payload={"agent_key": "rule_analysis", "script": "standard",
                                                            "rule_ids": [rule.id], "regenerate_existing": True})
    db.session.add(job)
    db.session.commit()
    _run(job, monkeypatch)
    gen = AIGeneration.query.one()
    assert gen.content_hash == content_hash(rule.to_string) and gen.request_id is None
    assert (gen.requested_by_id, gen.approved_by_id, gen.initiated_by_id) == (None, None, users.admin.id)
    p = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}/ai_analysis/list").get_json()["items"][0]["provenance"]
    assert p["outdated"] is False and p["requested_by"] is None


def test_old_reports_say_not_recorded_and_a_dead_job_frees_the_request(clients, users):
    rule = make_rule(users.owner)
    db.session.add(AIGeneration(uuid="legacy", agent_key="rule_analysis", rule_id=rule.id, user_id=users.admin.id,
                                content="old", model="m", is_public=True))
    db.session.commit()
    p = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}/ai_analysis/list").get_json()["items"][0]["provenance"]
    assert p["recorded"] is False and p["requested_by"] is None and p["outdated"] is False   # never guessed
    _request(clients["owner"], rule)
    job = _accept(clients)
    job.status = "failed"                                                         # crashed / cancelled
    db.session.commit()
    state = clients["owner"].get(f"/rule/detail_rule/{rule.id}/ai_analysis/request").get_json()
    assert state["pending"] == [] and state["recent"][0]["execution"] == "failed"
    assert _request(clients["owner"], rule).status_code == 201                   # can be requested again
