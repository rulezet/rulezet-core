"""GitHub for rules — layer 1: who can do what.

Permission model ("manager" = a non-admin holding `github.manage`, the
GitHub Manager role; admins have every right below):
- importing a repository (GitHub URL or ZIP), starting an update check on a
  whole repository, deleting a GitHub source's rules, the import / update
  history clean-up, the repo registry tools and Sync Schedules (every
  action) are for admins and managers;
- any logged-in user browses the GitHub sources, their own import / update
  history, and checks updates of the rules they own (the "owner");
- a pending update of a rule is accepted / rejected by the rule's owner or
  a manager; the bulk decisions on a whole update check by a manager or the
  user who started that (per-rule) check;
- any logged-in user proposes a repository; the requester reads and cancels
  their own proposal, managers review (list, accept / reject, delete) them.
"""
import io
import zipfile

import pytest

from app.core.db_class.db import (
    BackgroundJob, GithubProposal, GithubSyncRun, GithubSyncSchedule, ImporterResult, Rule,
    RuleUpdateHistory, UpdateResult,
)
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, Outcome, assert_outcome, matrix
from tests_new.helpers.db import count, reload
from tests_new.helpers.github import (
    GITHUB, make_github_rule, make_import_result, make_new_rule, make_pending_update, make_proposal,
    make_schedule, make_update_result, saved, schedule_payload,
)
from tests_new.helpers.rules import yara_rule

LOGGED_IN = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK, "manager": OK}
MANAGER = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK, "manager": OK}
OWNER_OR_MANAGER = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK, "manager": OK}
REQUESTER_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": FORBIDDEN, "manager": FORBIDDEN}
# The proposal review endpoints answer 403 (not a login redirect) to anonymous visitors.
MANAGER_JSON = {**MANAGER, "anonymous": FORBIDDEN}
# Actions that are queued or started and answer 202 Accepted.
STARTED = Outcome("STARTED", (202,))
MANAGER_STARTS = {**MANAGER, "admin": STARTED, "manager": STARTED}


@pytest.fixture
def as_role(clients_and_manager):
    return clients_and_manager


def _sample_repo(github):
    return github.repo("acme/rules", {"rules/sample.yar": yara_rule("sample_rule")})


def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    buffer.seek(0)
    return buffer


# ── Importing ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_import_from_github(role, expected, as_role, github):
    url = _sample_repo(github)

    response = as_role[role].post("/rule/import_rules_from_github", json={"url": url, "license": "MIT"})

    assert_outcome(response, expected)
    assert count(Rule, source=url) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_import_from_zip(role, expected, as_role):
    data = {"zipfile": (_zip({"rules/zipped.yar": yara_rule("zipped_rule")}), "rules.zip"), "license": "MIT"}

    response = as_role[role].post("/rule/import_rules_from_zip", data=data, content_type="multipart/form-data")

    assert_outcome(response, expected)
    assert count(Rule, title="zipped_rule") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_view_an_import_result(role, expected, as_role, users):
    result = make_import_result(users.owner)

    response = as_role[role].get(f"/rule/import_loading_status/{result.uuid}")

    assert_outcome(response, expected)
    if expected is OK:
        assert response.get_json()["uuid"] == result.uuid


@pytest.mark.parametrize("role, sees_it", [("user", False), ("owner", True), ("admin", True), ("manager", True)])
def test_import_history_lists_only_your_own_imports_unless_manager(role, sees_it, as_role, users):
    result = make_import_result(users.owner)

    response = as_role[role].get("/rule/history_github_importer/list")

    assert response.status_code == 200
    assert (result.uuid in [h["uuid"] for h in response.get_json()["history"]]) is sees_it


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_delete_an_import_from_the_history(role, expected, as_role, users):
    result = make_import_result(users.owner)

    response = as_role[role].get(f"/rule/history_github_importer/delete?uuid={result.uuid}")

    assert_outcome(response, expected)
    assert (reload(result) is None) is (expected is OK)


# ── Checking for updates ──────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_check_updates_of_a_repository(role, expected, as_role, github, users):
    url = _sample_repo(github)
    rule = make_github_rule(users.owner, url, path="rules/sample.yar", title="sample_rule",
                            content=yara_rule("sample_rule"))
    github.commit(url, {"rules/sample.yar": yara_rule("sample_rule").replace('"sample_rule"', '"v2"')})

    response = as_role[role].post("/rule/check_updates_by_url", json={"url": [{"url": url}]})

    assert_outcome(response, expected)
    assert count(UpdateResult) == (1 if expected is OK else 0)
    assert count(RuleUpdateHistory, rule_id=rule.id, message="Update found for this rule.") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_check_updates_of_a_rule(role, expected, as_role, github, users):
    url = _sample_repo(github)
    rule = make_github_rule(users.owner, url, path="rules/sample.yar", title="sample_rule",
                            content=yara_rule("sample_rule"))

    response = as_role[role].post("/rule/check_updates_by_rule", json={"rules": [rule.id]})

    assert_outcome(response, expected)
    assert count(UpdateResult, mode="by_rule") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, sees_it", [("user", False), ("owner", True), ("admin", True), ("manager", True)])
def test_update_history_lists_only_your_own_checks_unless_manager(role, sees_it, as_role, users):
    result = make_update_result(users.owner, mode="by_rule")

    response = as_role[role].get("/rule/history_github_updater/list")

    assert response.status_code == 200
    assert (result.uuid in [h["uuid"] for h in response.get_json()["history"]]) is sees_it


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_view_an_update_check(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    result, _, _ = make_pending_update(rule, yara_rule("changed"), checked_by=users.owner)

    response = as_role[role].get(f"/rule/update_loading_status/{result.uuid}/get_rules")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_delete_an_update_check_from_the_history(role, expected, as_role, users):
    result = make_update_result(users.owner)

    response = as_role[role].get(f"/rule/history_github_updater/delete?uuid={result.uuid}")

    assert_outcome(response, expected)
    assert (reload(result) is None) is (expected is OK)


# ── Deciding on a pending update (rule owner or manager) ──────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_accept_an_update(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    result, _, history = make_pending_update(rule, yara_rule("accepted_content"), checked_by=users.admin)

    response = as_role[role].get(
        f"/rule/update_github_rule/decision_rule?rule_id={history.id}&decision=accepted&sid={result.uuid}")

    assert_outcome(response, expected)
    assert ("accepted_content" in saved(rule).to_string) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_reject_an_update(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    result, _, history = make_pending_update(rule, yara_rule("rejected_content"), checked_by=users.admin)

    response = as_role[role].get(
        f"/rule/update_github_rule/decision_rule?rule_id={history.id}&decision=rejected&sid={result.uuid}")

    assert_outcome(response, expected)
    assert (reload(history).message == "rejected") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_accept_an_update_from_the_pending_list(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    _, _, history = make_pending_update(rule, yara_rule("accepted_content"), checked_by=users.admin)

    response = as_role[role].get(f"/rule/changes_decision?history_id={history.id}&decision=accepted")

    assert_outcome(response, expected)
    assert ("accepted_content" in saved(rule).to_string) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_accept_an_update_from_the_diff_page(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    _, _, history = make_pending_update(rule, yara_rule("accepted_content"), checked_by=users.admin)

    response = as_role[role].get(f"/rule/update_github_rule?rule_id={history.id}&decision=accepted")

    assert_outcome(response, expected)
    assert ("accepted_content" in saved(rule).to_string) is (expected is OK)


# The "owner" of a whole update check is the user who started it (per-rule check).

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_accept_every_update_of_a_check(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    result = make_update_result(users.owner, mode="by_rule")
    make_pending_update(rule, yara_rule("accepted_content"), checked_by=users.owner, result=result)

    response = as_role[role].get(f"/rule/accept_all_update/{result.uuid}")

    assert_outcome(response, expected)
    assert ("accepted_content" in saved(rule).to_string) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_bulk_decide_the_updates_of_a_check(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    result = make_update_result(users.owner, mode="by_rule")
    make_pending_update(rule, yara_rule("accepted_content"), checked_by=users.owner, result=result)

    response = as_role[role].post(f"/rule/bulk_update_decision/{result.uuid}", json={"action": "accept"})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="bulk_update_decision") == (1 if expected is OK else 0)


def test_the_starter_of_a_whole_repository_check_needs_the_manager_role_to_bulk_decide(client_as, users):
    """Only a per-rule check is the starter's own: a repository-wide check
    covers other people's rules."""
    result = make_update_result(users.owner, mode="by_url")

    response = client_as(users.owner).post(f"/rule/bulk_update_decision/{result.uuid}", json={"action": "accept"})

    assert_outcome(response, FORBIDDEN)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_bulk_decide_the_new_rules_of_a_check(role, expected, as_role, users):
    result = make_update_result(users.owner)
    make_new_rule(result, yara_rule("brand_new"))

    response = as_role[role].post(f"/rule/bulk_new_rules_decision/{result.uuid}", json={"action": "add"})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="bulk_new_rules_decision") == (1 if expected is OK else 0)


# ── GitHub sources ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", ["/rule/github/list_github_url", "/rule/get_url_github", "/rule/github/manage",
                                 f"/rule/github_detail?url={GITHUB}/acme/rules",
                                 f"/rule/github/repo_live_info?url={GITHUB}/acme/rules",
                                 f"/rule/get_github_branches?url={GITHUB}/acme/rules"])
@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_browse_github_sources(role, expected, url, as_role, github):
    _sample_repo(github)

    response = as_role[role].get(url)

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(MANAGER_STARTS))
def test_delete_every_rule_of_a_source(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")

    response = as_role[role].post(f"/rule/delete_all_rule_github?url={GITHUB}/acme/rules")

    assert_outcome(response, expected)
    assert reload(rule).is_deleted is (expected is STARTED)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_bulk_delete_sources(role, expected, as_role, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")

    response = as_role[role].post("/rule/bulk_action_github",
                                  json={"action": "delete", "selected_ids": [f"{GITHUB}/acme/rules"]})

    assert_outcome(response, expected)
    assert reload(rule).is_deleted is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_backfill_rule_branches(role, expected, as_role):
    response = as_role[role].post("/rule/github/backfill_branches")

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="github_repo_branch_backfill") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix({k: v for k, v in MANAGER.items() if v is not OK}))
def test_resync_the_repo_registry_is_refused_to_non_managers(role, expected, as_role):
    """The resync itself uses a PostgreSQL-only regex: only the refusals run on SQLite."""
    response = as_role[role].post("/rule/github/resync_repos")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_read_the_github_rate_limit(role, expected, as_role):
    response = as_role[role].get("/rule/github/rate_limit_status")

    assert_outcome(response, expected)


# ── Proposals ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_propose_a_repository(role, expected, as_role):
    url = f"{GITHUB}/acme/proposed"

    response = as_role[role].post("/rule/github_proposal/create", json={"repo_url": url, "license": "MIT"})

    assert_outcome(response, expected)
    assert count(GithubProposal, repo_url=url) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(MANAGER_JSON))
def test_list_every_proposal(role, expected, as_role, users):
    proposal = make_proposal(users.owner)

    response = as_role[role].get("/rule/github_proposal/list")

    assert_outcome(response, expected)
    if expected is OK:
        assert proposal.uuid in [p["uuid"] for p in response.get_json()["items"]]


@pytest.mark.parametrize("role, sees_it", [("user", False), ("owner", True)])
def test_my_proposals_lists_only_your_own(role, sees_it, as_role, users):
    proposal = make_proposal(users.owner)

    response = as_role[role].get("/rule/github_proposal/mine")

    assert response.status_code == 200
    assert (proposal.uuid in [p["uuid"] for p in response.get_json()["items"]]) is sees_it


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_view_a_proposal(role, expected, as_role, users):
    proposal = make_proposal(users.owner)

    response = as_role[role].get(f"/rule/github_proposal/{proposal.uuid}")

    assert_outcome(response, expected)
    if expected is OK:
        assert response.get_json()["proposal"]["uuid"] == proposal.uuid


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_MANAGER))
def test_open_a_proposal_page(role, expected, as_role, users):
    proposal = make_proposal(users.owner)

    response = as_role[role].get(f"/rule/github_proposal_detail/{proposal.uuid}")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(REQUESTER_ONLY))
def test_cancel_a_proposal(role, expected, as_role, users):
    proposal = make_proposal(users.owner)

    response = as_role[role].post(f"/rule/github_proposal/{proposal.uuid}/cancel")

    assert_outcome(response, expected)
    assert (reload(proposal) is None) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(MANAGER_JSON))
def test_reject_a_proposal(role, expected, as_role, users):
    proposal = make_proposal(users.owner)

    response = as_role[role].post("/rule/github_proposal/bulk_decision",
                                  json={"uuids": [proposal.uuid], "decision": "reject"})

    assert_outcome(response, expected)
    assert (reload(proposal).status == "rejected") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(MANAGER_JSON))
def test_accept_a_proposal(role, expected, as_role, users):
    proposal = make_proposal(users.owner)

    response = as_role[role].post("/rule/github_proposal/bulk_decision",
                                  json={"uuids": [proposal.uuid], "decision": "accept", "ownership_mode": "requester"})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type="github_proposal_bulk_import") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(MANAGER_JSON))
def test_delete_a_proposal(role, expected, as_role, users):
    proposal = make_proposal(users.owner)

    response = as_role[role].post(f"/rule/github_proposal/{proposal.uuid}/delete")

    assert_outcome(response, expected)
    assert (reload(proposal) is None) is (expected is OK)


# ── Sync Schedules (every action: admin or manager) ───────────────────────────

@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_list_sync_schedules(role, expected, as_role, users):
    make_schedule(users.admin)

    response = as_role[role].get("/rule/github/schedule/list")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_create_a_sync_schedule(role, expected, as_role):
    response = as_role[role].post("/rule/github/schedule/create", json=schedule_payload())

    assert_outcome(response, expected)
    assert count(GithubSyncSchedule) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_edit_a_sync_schedule(role, expected, as_role, users):
    schedule = make_schedule(users.admin)

    response = as_role[role].post(f"/rule/github/schedule/{schedule.uuid}/update",
                                  json=schedule_payload(title="Renamed"))

    assert_outcome(response, expected)
    assert (reload(schedule).title == "Renamed") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_delete_a_sync_schedule(role, expected, as_role, users):
    schedule = make_schedule(users.admin)

    response = as_role[role].post(f"/rule/github/schedule/{schedule.uuid}/delete")

    assert_outcome(response, expected)
    assert (reload(schedule) is None) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_bulk_delete_sync_schedules(role, expected, as_role, users):
    schedule = make_schedule(users.admin)

    response = as_role[role].post("/rule/github/schedule/bulk_delete", json={"selected_uuids": [schedule.uuid]})

    assert_outcome(response, expected)
    assert (reload(schedule) is None) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_pause_sync_schedules(role, expected, as_role, users):
    schedule = make_schedule(users.admin)

    response = as_role[role].post("/rule/github/schedule/bulk_set_active",
                                  json={"selected_uuids": [schedule.uuid], "is_active": False})

    assert_outcome(response, expected)
    assert reload(schedule).is_active is not (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(MANAGER_STARTS))
def test_run_a_sync_schedule_now(role, expected, as_role, users):
    schedule = make_schedule(users.admin)

    response = as_role[role].post(f"/rule/github/schedule/{schedule.uuid}/run_now")

    assert_outcome(response, expected)
    assert count(GithubSyncRun, schedule_id=schedule.id) == (1 if expected is STARTED else 0)


@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_pick_repositories_for_a_sync_schedule(role, expected, as_role, users):
    make_github_rule(users.owner, f"{GITHUB}/acme/rules")

    response = as_role[role].get("/rule/github/schedule/repo_candidates")

    assert_outcome(response, expected)


@pytest.mark.parametrize("suffix", ["", "/status"])
@pytest.mark.parametrize("role, expected", matrix(MANAGER))
def test_view_a_sync_run(role, expected, suffix, as_role, users):
    schedule = make_schedule(users.admin)
    as_role["admin"].post(f"/rule/github/schedule/{schedule.uuid}/run_now")
    run = GithubSyncRun.query.filter_by(schedule_id=schedule.id).one()

    response = as_role[role].get(f"/rule/github/sync_run/{run.uuid}{suffix}")

    assert_outcome(response, expected)
