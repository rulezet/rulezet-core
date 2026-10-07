"""GitHub for rules — layer 2: what importing, checking for updates,
deciding on them, proposals and Sync Schedules leave in the database.

An update check never overwrites a rule: it records the upstream change as
a pending update (a RuleUpdateHistory row + a RuleStatus row of the check),
and the rule only changes once that update is accepted. Rules found
upstream that Rulezet doesn't have yet wait as NewRule rows.
"""
import io
import json
import zipfile

import pytest

from app import db
from app.core.db_class.db import (
    ActivityLog, BackgroundJob, GithubProposal, GithubSyncRun, GithubSyncRunRepo, GithubSyncSchedule,
    ImporterResult, InvalidRuleModel, NewRule, Rule, RuleStatus, RuleTagAssociation, RuleUpdateHistory, Tag,
    UpdateResult,
)
from app.features.jobs.job_handlers import (
    handle_bulk_new_rules_decision, handle_bulk_update_decision, handle_github_proposal_bulk_import,
    handle_github_sync_schedule_run,
)
from tests_new.helpers.db import count, reload
from tests_new.helpers.formats import SAMPLES
from tests_new.helpers.github import (
    GITHUB, make_github_rule, make_import_result, make_new_rule, make_pending_update, make_proposal,
    make_schedule, make_update_result, saved, schedule_payload,
)
from tests_new.helpers.rules import make_rule, yara_rule

PENDING = "Update found for this rule."


def _v2(name):
    """`yara_rule(name)` with a different string — the upstream change."""
    return yara_rule(name).replace(f'"{name}"', f'"{name}_v2"')


def _import(client, url, **extra):
    return client.post("/rule/import_rules_from_github", json={"url": url, "license": "MIT", **extra})


def _check_repo(client, url, **extra):
    return client.post("/rule/check_updates_by_url", json={"url": [{"url": url, **extra}]})


def _imported_repo(github, client, files):
    url = github.repo("acme/rules", files)
    _import(client, url)
    return url


def _the_check():
    return UpdateResult.query.one()


def _run(handler, job, app):
    handler(job, app)
    return reload(job)


# ── Import ────────────────────────────────────────────────────────────────────

def test_import_creates_one_rule_per_valid_rule_with_its_github_source(clients, users, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a"), "sigma/s.yml": SAMPLES["sigma"].valid,
                                     "README.md": "not a rule"})

    response = _import(clients["admin"], url)

    assert response.status_code == 201
    rule_a = Rule.query.filter_by(title="rule_a").one()
    assert (rule_a.source, rule_a.github_path, rule_a.license, rule_a.user_id) == (url, "rules/a.yar", "MIT", users.admin.id)
    assert Rule.query.filter_by(format="sigma", source=url).one().github_path == "sigma/s.yml"
    assert count(Rule) == 2


def test_import_attaches_the_default_tags(clients, github):
    _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})

    rule = Rule.query.one()
    names = {t.name for t in Tag.query.join(RuleTagAssociation).filter(RuleTagAssociation.rule_id == rule.id)}
    assert {"tlp:clear", "PAP:CLEAR"} <= names


def test_import_keeps_invalid_rules_as_bad_rules_not_as_rules(clients, github):
    url = _imported_repo(github, clients["admin"], {"rules/bad.yar": SAMPLES["yara"].invalid})

    assert count(Rule) == 0
    bad = InvalidRuleModel.query.one()
    assert (bad.url, bad.github_path) == (url, "rules/bad.yar")


def test_import_records_the_result_and_its_counts(clients, users, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a"), "rules/bad.yar": SAMPLES["yara"].invalid})

    session_uuid = _import(clients["admin"], url).get_json()["session_uuid"]

    result = ImporterResult.query.filter_by(uuid=session_uuid).one()
    assert (result.imported, result.bad_rules, result.skipped, result.total) == (1, 1, 0, 2)
    assert result.user_id == users.admin.id
    assert json.loads(result.info)["repo_url"] == url
    assert count(ActivityLog, action="github.import_finished") == 1


def test_import_skips_a_rule_already_in_rulezet_with_the_same_content(clients, users, github):
    make_rule(users.owner, title="Already here", to_string=yara_rule("rule_a"))
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a") + "\r\n\r\n"})

    session_uuid = _import(clients["admin"], url).get_json()["session_uuid"]

    assert count(Rule) == 1
    assert ImporterResult.query.filter_by(uuid=session_uuid).one().skipped == 1


def test_import_of_the_same_rule_in_two_files_creates_it_once(clients, github):
    _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a"), "copy/a.yar": yara_rule("rule_a")})

    assert count(Rule, title="rule_a") == 1


def test_importing_a_repository_twice_creates_nothing_new(clients, github):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})

    _import(clients["admin"], url)

    assert count(Rule) == 1
    assert ImporterResult.query.order_by(ImporterResult.id.desc()).first().skipped == 1


def test_import_of_a_branch_takes_its_rules_and_records_the_branch(clients, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("on_main")})
    github.branch(url, "dev", {"rules/b.yar": yara_rule("on_dev")})

    _import(clients["admin"], url, branch="dev")

    assert Rule.query.filter_by(title="on_dev").one().branch == "dev"
    assert Rule.query.filter_by(title="on_main").one().branch == "dev"


def test_import_of_a_missing_repository_creates_nothing_and_reports_the_error(clients, github):
    response = _import(clients["admin"], f"{GITHUB}/acme/does-not-exist")

    status = clients["admin"].get(f"/rule/import_loading_status/{response.get_json()['session_uuid']}").get_json()
    assert status["phase"] == "error" and status["error"]
    assert count(Rule) == 0 and count(ImporterResult) == 0


def test_import_from_a_generic_git_host_never_calls_the_github_api(clients, github):
    url = github.repo("team/rules", {"rules/a.yar": yara_rule("rule_a")}, host="https://git.example.org")

    _import(clients["admin"], url, is_generic_source=True)

    assert Rule.query.one().source == url
    assert [r for r in github.requests if r[0] != "clone"] == []


def test_import_from_zip_creates_the_rules(clients, users):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("rules/a.yar", yara_rule("zipped"))
        archive.writestr("rules/bad.yar", SAMPLES["yara"].invalid)
    buffer.seek(0)

    response = clients["admin"].post("/rule/import_rules_from_zip", content_type="multipart/form-data",
                                     data={"zipfile": (buffer, "rules.zip"), "license": "MIT"})

    assert response.status_code == 201
    rule = Rule.query.one()
    assert (rule.title, rule.user_id) == ("zipped", users.admin.id)
    assert count(InvalidRuleModel) == 1


def test_delete_an_import_from_the_history(clients, users):
    result = make_import_result(users.owner)

    clients["admin"].get(f"/rule/history_github_importer/delete?uuid={result.uuid}")

    assert count(ImporterResult) == 0


# ── Proposals ─────────────────────────────────────────────────────────────────

def test_propose_stores_a_pending_proposal_with_a_clean_url(clients, users):
    response = clients["user"].post("/rule/github_proposal/create", json={
        "repo_url": f"{GITHUB}/acme/proposed.git/", "branch": " dev ", "license": "MIT", "message": "Please"})

    assert response.status_code == 201
    proposal = GithubProposal.query.one()
    assert (proposal.repo_url, proposal.branch, proposal.license, proposal.message) == (
        f"{GITHUB}/acme/proposed", "dev", "MIT", "Please")
    assert (proposal.status, proposal.user_id) == ("pending", users.user.id)


def test_propose_a_repository_already_proposed_is_refused(clients, users):
    make_proposal(users.owner, f"{GITHUB}/acme/proposed")

    response = clients["user"].post("/rule/github_proposal/create", json={"repo_url": f"{GITHUB}/acme/proposed"})

    assert response.status_code == 400
    assert count(GithubProposal) == 1


def test_propose_a_repository_already_in_rulezet_is_refused(clients, users):
    make_github_rule(users.owner, f"{GITHUB}/acme/rules")

    response = clients["user"].post("/rule/github_proposal/create", json={"repo_url": f"{GITHUB}/acme/rules"})

    assert response.status_code == 400
    assert count(GithubProposal) == 0


def test_my_proposals_lists_only_the_pending_ones(clients, users):
    pending = make_proposal(users.owner)
    make_proposal(users.owner, status="rejected")

    items = clients["owner"].get("/rule/github_proposal/mine").get_json()["items"]

    assert [p["uuid"] for p in items] == [pending.uuid]


def test_cancel_a_proposal_removes_it(clients, users):
    proposal = make_proposal(users.owner)

    clients["owner"].post(f"/rule/github_proposal/{proposal.uuid}/cancel")

    assert count(GithubProposal) == 0


def test_cancel_a_decided_proposal_is_refused(clients, users):
    proposal = make_proposal(users.owner, status="rejected")

    response = clients["owner"].post(f"/rule/github_proposal/{proposal.uuid}/cancel")

    assert response.status_code == 400
    assert reload(proposal) is not None


def test_reject_a_proposal_records_the_decision(clients, users):
    proposal = make_proposal(users.owner)

    clients["admin"].post("/rule/github_proposal/bulk_decision",
                          json={"uuids": [proposal.uuid], "decision": "reject", "note": "Out of scope"})

    proposal = reload(proposal)
    assert (proposal.status, proposal.decided_by_id, proposal.decision_note) == ("rejected", users.admin.id, "Out of scope")
    assert count(BackgroundJob) == 0


def test_accept_proposals_queues_one_import_job(clients, users):
    first, second = make_proposal(users.owner), make_proposal(users.user)

    response = clients["admin"].post("/rule/github_proposal/bulk_decision", json={
        "uuids": [first.uuid, second.uuid], "decision": "accept", "ownership_mode": "requester"})

    job = BackgroundJob.query.filter_by(job_type="github_proposal_bulk_import").one()
    assert response.get_json()["job_uuid"] == job.uuid
    assert set(job.payload["proposal_uuids"]) == {first.uuid, second.uuid}
    assert {reload(first).status, reload(second).status} == {"accepted"}
    assert reload(first).job_uuid == job.uuid


def test_accept_a_proposal_without_an_ownership_choice_is_refused(clients, users):
    proposal = make_proposal(users.owner)

    response = clients["admin"].post("/rule/github_proposal/bulk_decision",
                                     json={"uuids": [proposal.uuid], "decision": "accept"})

    assert response.status_code == 400
    assert reload(proposal).status == "pending"


@pytest.mark.parametrize("mode, new_owner", [("requester", "owner"), ("admin", "admin")])
def test_the_import_job_of_an_accepted_proposal_imports_the_repository(mode, new_owner, clients, users, github, app):
    url = github.repo("acme/proposed", {"rules/a.yar": yara_rule("proposed_rule")})
    proposal = make_proposal(users.owner, url, license="MIT")
    clients["admin"].post("/rule/github_proposal/bulk_decision",
                          json={"uuids": [proposal.uuid], "decision": "accept", "ownership_mode": mode})
    job = BackgroundJob.query.filter_by(job_type="github_proposal_bulk_import").one()

    _run(handle_github_proposal_bulk_import, job, app)

    rule = Rule.query.one()
    assert (rule.title, rule.source, rule.user_id) == ("proposed_rule", url, getattr(users, new_owner).id)
    proposal = reload(proposal)
    assert proposal.status == "imported"
    assert count(ImporterResult, uuid=proposal.importer_result_uuid) == 1


def test_the_import_job_of_a_proposal_whose_repository_is_gone_marks_it_failed(clients, users, app):
    proposal = make_proposal(users.owner, f"{GITHUB}/acme/vanished")
    clients["admin"].post("/rule/github_proposal/bulk_decision",
                          json={"uuids": [proposal.uuid], "decision": "accept", "ownership_mode": "admin"})
    job = BackgroundJob.query.filter_by(job_type="github_proposal_bulk_import").one()

    _run(handle_github_proposal_bulk_import, job, app)

    assert reload(proposal).status == "failed"
    assert count(Rule) == 0


def test_delete_a_proposal_removes_it(clients, users):
    proposal = make_proposal(users.owner)

    clients["admin"].post(f"/rule/github_proposal/{proposal.uuid}/delete")

    assert count(GithubProposal) == 0


# ── Checking a repository for updates ─────────────────────────────────────────

def test_an_upstream_change_becomes_a_pending_update_not_an_overwrite(clients, github):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})
    rule = Rule.query.one()
    github.commit(url, {"rules/a.yar": _v2("rule_a")})

    response = _check_repo(clients["admin"], url)

    assert response.status_code == 201
    assert reload(rule).to_string == yara_rule("rule_a")
    history = RuleUpdateHistory.query.filter_by(rule_id=rule.id, message=PENDING).one()
    assert "rule_a_v2" in history.new_content
    status = RuleStatus.query.filter_by(rule_id=str(rule.id)).one()
    assert (status.update_available, status.history_id) == (True, str(history.id))
    assert _the_check().uuid == response.get_json()["session_uuid"]


def test_an_unchanged_repository_has_no_pending_update(clients, github):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})

    _check_repo(clients["admin"], url)

    status = RuleStatus.query.one()
    assert (status.found, status.update_available) == (True, False)
    assert count(RuleUpdateHistory, message=PENDING) == 0


def test_a_rule_added_upstream_waits_as_a_new_rule(clients, github):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})
    github.commit(url, {"rules/b.yar": yara_rule("rule_b")})

    _check_repo(clients["admin"], url)

    new_rule = NewRule.query.one()
    assert (new_rule.name_rule, new_rule.github_path, new_rule.rule_syntax_valid) == ("rule_b", "rules/b.yar", True)
    assert count(Rule) == 1


def test_an_invalid_upstream_change_is_recorded_as_invalid_and_the_rule_kept(clients, github):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})
    rule = Rule.query.one()
    github.commit(url, {"rules/a.yar": "rule rule_a { condition: }"})

    _check_repo(clients["admin"], url)

    assert reload(rule).to_string == yara_rule("rule_a")
    status = RuleStatus.query.one()
    assert (status.update_available, status.rule_syntax_valid) == (True, False)


def test_a_rule_removed_upstream_is_reported_not_found(clients, github):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a"), "rules/b.yar": yara_rule("rule_b")})
    github.commit(url, delete=["rules/b.yar"])

    _check_repo(clients["admin"], url)

    rule_b = Rule.query.filter_by(title="rule_b").one()
    status = RuleStatus.query.filter_by(rule_id=str(rule_b.id)).one()
    assert (status.found, status.update_available) == (False, False)


def test_a_rule_in_the_trash_is_not_checked(clients, users, github):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})
    rule = Rule.query.one()
    rule.is_deleted, rule.deleted_by_id = True, users.admin.id
    db.session.commit()
    github.commit(url, {"rules/a.yar": _v2("rule_a")})

    _check_repo(clients["admin"], url)

    assert count(RuleUpdateHistory, rule_id=rule.id, message=PENDING) == 0
    assert count(RuleStatus, rule_id=str(rule.id)) == 0


def test_a_check_of_a_branch_only_looks_at_that_branch(clients, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a")})
    github.branch(url, "dev", {"rules/b.yar": yara_rule("rule_b")})
    _import(clients["admin"], url, branch="dev")
    github.commit(url, {"rules/a.yar": _v2("rule_a")})

    _check_repo(clients["admin"], url, branch="dev")

    assert count(RuleUpdateHistory, message=PENDING) == 0
    assert _the_check().to_json_list()["info"]["branch"] == "dev"


def test_check_my_own_rule_creates_a_pending_update(clients, users, github):
    url = github.repo("acme/rules", {"rules/a.yar": _v2("rule_a")})
    rule = make_github_rule(users.owner, url, path="rules/a.yar", title="rule_a", content=yara_rule("rule_a"))

    response = clients["owner"].post("/rule/check_updates_by_rule", json={"rules": [rule.id]})

    assert response.status_code == 201
    assert reload(rule).to_string == yara_rule("rule_a")
    assert "rule_a_v2" in RuleUpdateHistory.query.filter_by(rule_id=rule.id, message=PENDING).one().new_content
    assert _the_check().mode == "by_rule"


def test_check_rules_drops_the_ones_you_do_not_own(clients, users, github):
    url = github.repo("acme/rules", {"rules/a.yar": _v2("mine"), "rules/b.yar": _v2("theirs")})
    mine = make_github_rule(users.owner, url, path="rules/a.yar", title="mine", content=yara_rule("mine"))
    theirs = make_github_rule(users.user, url, path="rules/b.yar", title="theirs", content=yara_rule("theirs"))

    clients["owner"].post("/rule/check_updates_by_rule", json={"rules": [mine.id, theirs.id]})

    assert count(RuleUpdateHistory, rule_id=mine.id, message=PENDING) == 1
    assert count(RuleUpdateHistory, rule_id=theirs.id, message=PENDING) == 0


def test_delete_an_update_check_removes_it(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    result, _, _ = make_pending_update(rule, _v2("x"), checked_by=users.admin)
    make_new_rule(result, yara_rule("brand_new"))

    clients["admin"].get(f"/rule/history_github_updater/delete?uuid={result.uuid}")

    assert count(UpdateResult) == 0


# ── Deciding on pending updates ───────────────────────────────────────────────

def test_accept_an_update_applies_the_new_content(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="rule_a", content=yara_rule("rule_a"))
    result, status, history = make_pending_update(rule, _v2("rule_a"), checked_by=users.admin)

    clients["owner"].get(f"/rule/update_github_rule/decision_rule?rule_id={history.id}&decision=accepted&sid={result.uuid}")

    assert saved(rule).to_string == _v2("rule_a")
    assert saved(history).message == "accepted"
    assert saved(status).update_available is False


def test_reject_an_update_keeps_the_rule(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="rule_a", content=yara_rule("rule_a"))
    result, status, history = make_pending_update(rule, _v2("rule_a"), checked_by=users.admin)

    clients["owner"].get(f"/rule/update_github_rule/decision_rule?rule_id={history.id}&decision=rejected&sid={result.uuid}")

    assert saved(rule).to_string == yara_rule("rule_a")
    assert saved(history).message == "rejected"
    assert saved(status).update_available is False


def test_accept_an_update_with_an_invalid_syntax_keeps_the_rule(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="rule_a", content=yara_rule("rule_a"))
    result, _, history = make_pending_update(rule, "rule rule_a { condition: }", checked_by=users.admin,
                                             syntax_valid=False)

    clients["owner"].get(f"/rule/update_github_rule/decision_rule?rule_id={history.id}&decision=accepted&sid={result.uuid}")

    assert saved(rule).to_string == yara_rule("rule_a")
    assert saved(history).message == "rejected"


def test_accept_an_update_from_the_pending_list_applies_the_new_content(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="rule_a", content=yara_rule("rule_a"))
    _, _, history = make_pending_update(rule, _v2("rule_a"), checked_by=users.admin)

    clients["owner"].get(f"/rule/changes_decision?history_id={history.id}&decision=accepted")

    assert saved(rule).to_string == _v2("rule_a")
    assert saved(history).message == "accepted"


def test_reject_an_update_from_the_pending_list_keeps_the_rule(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="rule_a", content=yara_rule("rule_a"))
    _, _, history = make_pending_update(rule, _v2("rule_a"), checked_by=users.admin)

    clients["owner"].get(f"/rule/changes_decision?history_id={history.id}&decision=rejected")

    assert saved(rule).to_string == yara_rule("rule_a")
    assert saved(history).message == "rejected"


def test_accept_from_the_pending_list_an_update_that_no_longer_validates_keeps_the_rule(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="rule_a", content=yara_rule("rule_a"))
    _, _, history = make_pending_update(rule, "rule rule_a { condition: }", checked_by=users.admin)

    clients["owner"].get(f"/rule/changes_decision?history_id={history.id}&decision=accepted")

    assert saved(rule).to_string == yara_rule("rule_a")
    assert saved(history).message == "rejected"


def test_accept_every_update_of_a_check_applies_only_the_valid_ones(clients, users):
    good = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="good", content=yara_rule("good"))
    bad = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="bad", content=yara_rule("bad"))
    result = make_update_result(users.admin)
    _, good_status, _ = make_pending_update(good, _v2("good"), checked_by=users.admin, result=result)
    _, bad_status, _ = make_pending_update(bad, "rule bad { condition: }", checked_by=users.admin, result=result,
                                           syntax_valid=False)

    clients["admin"].get(f"/rule/accept_all_update/{result.uuid}")

    assert (saved(good).to_string, saved(bad).to_string) == (_v2("good"), yara_rule("bad"))
    assert saved(good_status).message == "Updated successfully"
    assert "Rejected" in saved(bad_status).message


@pytest.mark.parametrize("action, applied", [("accept", True), ("reject", False)])
def test_the_bulk_decision_job_applies_or_rejects_the_updates(action, applied, clients, users, app):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="rule_a", content=yara_rule("rule_a"))
    result, status, history = make_pending_update(rule, _v2("rule_a"), checked_by=users.admin)
    clients["admin"].post(f"/rule/bulk_update_decision/{result.uuid}", json={"action": action})
    job = BackgroundJob.query.filter_by(job_type="bulk_update_decision").one()

    job = _run(handle_bulk_update_decision, job, app)

    assert job.status == "done"
    assert (saved(rule).to_string == _v2("rule_a")) is applied
    assert saved(history).message == ("accepted" if applied else "rejected")
    assert saved(status).update_available is False


def test_the_add_new_rules_job_creates_the_valid_ones_from_the_repository(clients, users, app):
    result = make_update_result(users.admin, repo_url=f"{GITHUB}/acme/rules")
    valid = make_new_rule(result, yara_rule("brand_new"), name="brand_new")
    invalid = make_new_rule(result, "rule broken { condition: }", name="broken", valid=False)
    clients["admin"].post(f"/rule/bulk_new_rules_decision/{result.uuid}", json={"action": "add"})
    job = BackgroundJob.query.filter_by(job_type="bulk_new_rules_decision").one()

    _run(handle_bulk_new_rules_decision, job, app)

    rule = Rule.query.one()
    assert (rule.title, rule.source, rule.github_path, rule.user_id) == (
        "brand_new", f"{GITHUB}/acme/rules", "rules/brand_new.yar", users.admin.id)
    assert reload(valid).message == "imported"
    assert reload(invalid).message != "imported"


def test_the_reject_new_rules_job_creates_nothing(clients, users, app):
    result = make_update_result(users.admin)
    new_rule = make_new_rule(result, yara_rule("brand_new"))
    clients["admin"].post(f"/rule/bulk_new_rules_decision/{result.uuid}", json={"action": "reject"})
    job = BackgroundJob.query.filter_by(job_type="bulk_new_rules_decision").one()

    _run(handle_bulk_new_rules_decision, job, app)

    assert count(Rule) == 0
    assert reload(new_rule).message == "rejected"


# ── GitHub sources ────────────────────────────────────────────────────────────

def test_delete_every_rule_of_a_source_moves_only_them_to_the_trash(clients, users):
    gone = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    kept = make_github_rule(users.owner, f"{GITHUB}/acme/other")

    clients["admin"].post(f"/rule/delete_all_rule_github?url={GITHUB}/acme/rules")

    gone = reload(gone)
    assert (gone.is_deleted, gone.deleted_by_id) == (True, users.admin.id)
    assert gone.delete_batch_uuid
    assert reload(kept).is_deleted is False


def test_bulk_delete_sources_records_who_deleted_the_rules(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")

    clients["admin"].post("/rule/bulk_action_github", json={"action": "delete", "selected_ids": [f"{GITHUB}/acme/rules"]})

    rule = reload(rule)
    assert (rule.is_deleted, rule.deleted_by_id) == (True, users.admin.id)


def test_bulk_export_sources_returns_their_rules_as_a_zip(clients, users):
    make_github_rule(users.owner, f"{GITHUB}/acme/rules", title="exported")

    response = clients["admin"].post("/rule/bulk_action_github",
                                     json={"action": "export", "selected_ids": [f"{GITHUB}/acme/rules"]})

    assert response.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(response.data)).namelist()
    assert any("exported" in name for name in names)


# ── Sync Schedules ────────────────────────────────────────────────────────────

def test_create_a_sync_schedule_stores_it_and_registers_its_trigger(clients, users, _paused_scheduler):
    payload = schedule_payload(repo_settings=[{"repo_url": f"{GITHUB}/acme/rules", "auto_accept_update": True}])

    response = clients["admin"].post("/rule/github/schedule/create", json=payload)

    assert response.status_code == 201
    schedule = GithubSyncSchedule.query.one()
    assert (schedule.title, schedule.frequency, schedule.hour, schedule.minute) == ("Nightly sync", "daily", 4, 30)
    assert (schedule.editor_id, schedule.is_active) == (users.admin.id, True)
    assert [(r.repo_url, r.auto_accept_update, r.auto_add_new_rule) for r in schedule.repos] == [
        (f"{GITHUB}/acme/rules", True, False)]
    assert schedule.next_run_at is not None
    assert _paused_scheduler.get_job(schedule.uuid) is not None


def test_create_a_sync_schedule_keeps_only_valid_repositories(clients):
    clients["admin"].post("/rule/github/schedule/create", json=schedule_payload(
        repo_urls=[f"{GITHUB}/acme/rules", "https://evil.example/acme/rules", "not a url"]))

    assert [r.repo_url for r in GithubSyncSchedule.query.one().repos] == [f"{GITHUB}/acme/rules"]


@pytest.mark.parametrize("fields", [
    {"frequency": "weekly", "days_of_week": [0, 2, 4]},
    {"frequency": "monthly", "day_of_month": -1},
    {"frequency": "cron", "cron_expr": "*/30 * * * *"},
])
def test_create_a_sync_schedule_with_each_frequency(fields, clients):
    response = clients["admin"].post("/rule/github/schedule/create", json=schedule_payload(**fields))

    assert response.status_code == 201
    assert GithubSyncSchedule.query.one().frequency == fields["frequency"]


def test_edit_a_sync_schedule_changes_it_and_its_trigger(clients, users, _paused_scheduler):
    schedule = make_schedule(users.admin)

    clients["admin"].post(f"/rule/github/schedule/{schedule.uuid}/update",
                          json=schedule_payload(title="Weekly", frequency="weekly", days_of_week=[1],
                                                repo_urls=[f"{GITHUB}/acme/other"]))

    schedule = reload(schedule)
    assert (schedule.title, schedule.frequency, schedule.days_of_week) == ("Weekly", "weekly", "1")
    assert [r.repo_url for r in schedule.repos] == [f"{GITHUB}/acme/other"]
    assert "day_of_week='1'" in str(_paused_scheduler.get_job(schedule.uuid).trigger)


def test_edit_only_the_repository_toggles_keeps_the_repositories(clients, users):
    schedule = make_schedule(users.admin)
    payload = schedule_payload(repo_settings=[{"repo_url": f"{GITHUB}/acme/rules", "auto_add_new_rule": True}])
    del payload["repo_mode"], payload["selected_repo_urls"]

    clients["admin"].post(f"/rule/github/schedule/{schedule.uuid}/update", json=payload)

    assert [(r.repo_url, r.auto_add_new_rule) for r in reload(schedule).repos] == [(f"{GITHUB}/acme/rules", True)]


def test_delete_a_sync_schedule_removes_it_and_its_trigger(clients, users, _paused_scheduler):
    schedule = make_schedule(users.admin)
    clients["admin"].post("/rule/github/schedule/bulk_set_active", json={"selected_uuids": [schedule.uuid], "is_active": True})

    clients["admin"].post(f"/rule/github/schedule/{schedule.uuid}/delete")

    assert count(GithubSyncSchedule) == 0
    assert _paused_scheduler.get_job(schedule.uuid) is None


def test_bulk_delete_sync_schedules_by_selection(clients, users):
    first, second = make_schedule(users.admin), make_schedule(users.admin)

    clients["admin"].post("/rule/github/schedule/bulk_delete", json={"mode": "partial", "selected_uuids": [first.uuid]})

    assert [s.uuid for s in GithubSyncSchedule.query.all()] == [second.uuid]


def test_bulk_delete_every_sync_schedule_but_the_excluded_ones(clients, users):
    first, second, kept = make_schedule(users.admin), make_schedule(users.admin), make_schedule(users.admin)

    clients["admin"].post("/rule/github/schedule/bulk_delete", json={"mode": "all", "excluded_uuids": [kept.uuid]})

    assert [s.uuid for s in GithubSyncSchedule.query.all()] == [kept.uuid]


def test_pause_a_sync_schedule_removes_its_trigger(clients, users, _paused_scheduler):
    schedule = make_schedule(users.admin)
    clients["admin"].post("/rule/github/schedule/bulk_set_active", json={"selected_uuids": [schedule.uuid], "is_active": True})

    clients["admin"].post("/rule/github/schedule/bulk_set_active", json={"selected_uuids": [schedule.uuid], "is_active": False})

    schedule = reload(schedule)
    assert (schedule.is_active, schedule.next_run_at) == (False, None)
    assert _paused_scheduler.get_job(schedule.uuid) is None


def test_run_a_sync_schedule_now_queues_a_run(clients, users):
    schedule = make_schedule(users.admin)

    response = clients["admin"].post(f"/rule/github/schedule/{schedule.uuid}/run_now")

    assert response.status_code == 202
    run = GithubSyncRun.query.one()
    job = BackgroundJob.query.filter_by(job_type="github_sync_schedule_run").one()
    assert (run.status, run.job_uuid) == ("pending", job.uuid)
    assert job.payload == {"schedule_uuid": schedule.uuid, "run_uuid": run.uuid}


def test_run_a_paused_sync_schedule_is_refused(clients, users):
    schedule = make_schedule(users.admin, is_active=False)

    response = clients["admin"].post(f"/rule/github/schedule/{schedule.uuid}/run_now")

    assert response.status_code == 400
    assert count(GithubSyncRun) == 0


def _run_schedule(clients, schedule, app):
    clients["admin"].post(f"/rule/github/schedule/{schedule.uuid}/run_now")
    job = BackgroundJob.query.filter_by(job_type="github_sync_schedule_run").one()
    return _run(handle_github_sync_schedule_run, job, app)


def test_a_sync_schedule_run_checks_each_repository_and_leaves_updates_pending(clients, users, github, app):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})
    rule = Rule.query.one()
    github.commit(url, {"rules/a.yar": _v2("rule_a"), "rules/b.yar": yara_rule("rule_b")})
    schedule = make_schedule(users.admin, [url])

    job = _run_schedule(clients, schedule, app)

    assert job.status == "done"
    run = GithubSyncRun.query.one()
    run_repo = GithubSyncRunRepo.query.one()
    assert (run.status, run_repo.status) == ("done", "done")
    assert count(UpdateResult, uuid=run_repo.update_result_uuid) == 1
    assert saved(rule).to_string == yara_rule("rule_a")
    assert count(RuleUpdateHistory, rule_id=rule.id, message=PENDING) == 1
    assert count(Rule) == 1 and count(NewRule) == 1


def test_a_sync_schedule_run_with_auto_accept_and_auto_add_updates_the_rules(clients, users, github, app):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})
    rule = Rule.query.one()
    github.commit(url, {"rules/a.yar": _v2("rule_a"), "rules/b.yar": yara_rule("rule_b")})
    schedule = make_schedule(users.admin, [url], auto_accept=True, auto_add=True)

    _run_schedule(clients, schedule, app)

    assert saved(rule).to_string == _v2("rule_a")
    assert Rule.query.filter_by(title="rule_b").one().source == url
    run_repo = GithubSyncRunRepo.query.one()
    assert (run_repo.auto_accepted, run_repo.auto_added) == (1, 1)


def test_a_sync_schedule_run_reports_a_repository_it_cannot_reach_and_checks_the_others(clients, users, github, app):
    url = _imported_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})
    github.commit(url, {"rules/a.yar": _v2("rule_a")})
    schedule = make_schedule(users.admin, [f"{GITHUB}/acme/vanished", url])

    job = _run_schedule(clients, schedule, app)

    assert job.status == "done"
    assert GithubSyncRun.query.one().status == "done"
    vanished = GithubSyncRunRepo.query.filter_by(repo_url=f"{GITHUB}/acme/vanished").one()
    assert UpdateResult.query.filter_by(uuid=vanished.update_result_uuid).one().not_found == 1
    assert count(RuleUpdateHistory, message=PENDING) == 1
