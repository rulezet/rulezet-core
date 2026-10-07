"""GitHub for rules — layer 4: inputs and repositories meant to break Rulezet.

Expected every time: a clean answer (< 500, a 4xx when the input is
refused), nothing cloned from a URL that isn't a repository on GitHub,
nothing read outside the cloned repository, and no half-written row.
"""
import io
import os
import zipfile

import pytest

from app import db
from app.core.db_class.db import (
    BackgroundJob, GithubProposal, GithubSyncSchedule, ImporterResult, InvalidRuleModel, NewRule, Rule,
    RuleUpdateHistory, UpdateResult,
)
from tests_new.helpers.db import count, reload
from tests_new.helpers.formats import SAMPLES
from tests_new.helpers.github import (
    GITHUB, make_github_rule, make_pending_update, make_proposal, make_schedule, make_update_result, saved,
    schedule_payload,
)
from tests_new.helpers.inputs import BAD_IDS, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests_new.helpers.rules import yara_rule
from tests_new.helpers.users import api_headers

NOT_A_GITHUB_REPOSITORY = [
    "",
    "not a url",
    "github.com/acme/rules",
    "file:///etc/passwd",
    "file://github.com/acme/rules",
    "http://localhost/acme/rules",
    "http://127.0.0.1:7009/acme/rules",
    "http://169.254.169.254/latest/meta-data",
    "https://github.com.evil.example/acme/rules",
    "https://github.com@evil.example/acme/rules",
    "https://evil.example/github.com/acme/rules",
    "https://github.com/acme",
    "javascript:alert(1)",
    "ssh://git@github.com/acme/rules",
    "ext::sh -c touch% /tmp/pwned",
    "git@github.com:acme/rules.git",
]

BAD_BRANCHES = ["../../etc", "-u", "--upload-pack=touch /tmp/pwned", "main;rm -rf /", "main\nfoo", "a" * 300,
                "refs/heads/../../x", ".lock"]

NOT_AN_OBJECT = [[1, 2], "text", 42, None]


def _short(value):
    return repr(value)[:40]


def _import(client, payload):
    return client.post("/rule/import_rules_from_github", json=payload)


def _clones(github):
    return [r for r in github.requests if r[0] == "clone"]


def _import_repo(github, client, files):
    url = github.repo("acme/rules", files)
    response = _import(client, {"url": url, "license": "MIT"})
    assert response.status_code == 201
    return url


# ── Repository URLs ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", NOT_A_GITHUB_REPOSITORY)
def test_import_from_something_that_is_not_a_github_repository_is_refused(url, clients, github):
    response = _import(clients["admin"], {"url": url, "license": "MIT"})

    assert response.status_code == 400
    assert _clones(github) == []
    assert count(Rule) == 0


@pytest.mark.parametrize("url", NOT_A_GITHUB_REPOSITORY)
def test_propose_something_that_is_not_a_github_repository_is_refused(url, clients):
    response = clients["user"].post("/rule/github_proposal/create", json={"repo_url": url})

    assert response.status_code == 400
    assert count(GithubProposal) == 0


@pytest.mark.parametrize("url", NOT_A_GITHUB_REPOSITORY)
def test_check_updates_of_something_that_is_not_a_github_repository_is_refused(url, clients, github):
    response = clients["admin"].post("/rule/check_updates_by_url", json={"url": [{"url": url}]})

    assert response.status_code == 400
    assert _clones(github) == []
    assert count(UpdateResult) == 0


@pytest.mark.parametrize("url", NOT_A_GITHUB_REPOSITORY)
def test_schedule_a_sync_of_something_that_is_not_a_github_repository_is_refused(url, clients):
    response = clients["admin"].post("/rule/github/schedule/create", json=schedule_payload(repo_urls=[url]))

    assert response.status_code == 400
    assert count(GithubSyncSchedule) == 0


@pytest.mark.parametrize("url", NOT_A_GITHUB_REPOSITORY)
def test_check_updates_of_a_rule_whose_source_is_not_a_github_repository_clones_nothing(url, clients, users, github):
    rule = make_github_rule(users.owner, url)

    response = clients["owner"].post("/rule/check_updates_by_rule", json={"rules": [rule.id]})

    assert response.status_code < 500
    assert _clones(github) == []


@pytest.mark.parametrize("url", [f"{GITHUB}/../../../tmp/escape", f"{GITHUB}/acme/rules/../../..",
                                 f"{GITHUB}/acme/..", f"{GITHUB}/%2e%2e/%2e%2e"])
def test_import_with_a_path_traversal_in_the_url_never_writes_outside_the_clone_folder(url, clients, github, tmp_path):
    before = set(os.listdir(tmp_path))

    response = _import(clients["admin"], {"url": url, "license": "MIT"})

    assert response.status_code < 500
    assert set(os.listdir(tmp_path)) - before <= {"clones"}
    assert count(Rule) == 0


def test_import_of_a_repository_that_does_not_exist_imports_nothing(clients, github):
    response = _import(clients["admin"], {"url": f"{GITHUB}/acme/nothing-here", "license": "MIT"})

    assert response.status_code == 201
    assert count(Rule) == 0 and count(ImporterResult) == 0


def test_check_updates_of_a_repository_that_does_not_exist_reports_it(clients, github):
    response = clients["admin"].post("/rule/check_updates_by_url", json={"url": [{"url": f"{GITHUB}/acme/nothing-here"}]})

    assert response.status_code == 201
    assert UpdateResult.query.one().not_found == 1


@pytest.mark.parametrize("branch", BAD_BRANCHES, ids=_short)
def test_import_of_an_odd_branch_imports_nothing(branch, clients, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a")})

    response = _import(clients["admin"], {"url": url, "license": "MIT", "branch": branch})

    assert response.status_code < 500
    assert count(Rule) == 0


@pytest.mark.parametrize("branch", BAD_BRANCHES, ids=_short)
def test_check_updates_of_an_odd_branch_never_errors(branch, clients, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a")})

    response = clients["admin"].post("/rule/check_updates_by_url", json={"url": [{"url": url, "branch": branch}]})

    assert response.status_code < 500
    assert count(RuleUpdateHistory) == 0


# ── What the repository holds ─────────────────────────────────────────────────

def test_import_never_follows_a_symlink_out_of_the_repository(clients, github, tmp_path):
    secret = tmp_path / "outside.yar"
    secret.write_text(yara_rule("leaked_secret"))
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a")})
    github.symlink(url, "rules/link.yar", str(secret))
    github.symlink(url, "linked_dir", str(tmp_path))

    _import(clients["admin"], {"url": url, "license": "MIT"})

    assert [r.title for r in Rule.query.all()] == ["rule_a"]
    assert count(InvalidRuleModel) == 0


def test_check_updates_never_follows_a_symlink_out_of_the_repository(clients, github, tmp_path):
    secret = tmp_path / "outside.yar"
    secret.write_text(yara_rule("leaked_secret"))
    url = _import_repo(github, clients["admin"], {"rules/a.yar": yara_rule("rule_a")})
    github.symlink(url, "rules/link.yar", str(secret))

    clients["admin"].post("/rule/check_updates_by_url", json={"url": [{"url": url}]})

    assert count(NewRule) == 0


def test_import_keeps_malformed_rules_of_every_format_out_of_the_rules(clients, github):
    files = {"rules/bad.yar": SAMPLES["yara"].invalid, "sigma/bad.yml": SAMPLES["sigma"].invalid,
             "suricata/bad.rules": SAMPLES["suricata"].invalid, "rules/good.yar": yara_rule("good")}

    _import_repo(github, clients["admin"], files)

    assert [r.title for r in Rule.query.all()] == ["good"]
    assert count(InvalidRuleModel) >= 2


@pytest.mark.parametrize("content", [
    b"\x00\x01\x02\xff\xfe" * 1000,                       # binary
    "rule caf\xe9 { condition: ".encode("latin-1"),       # not UTF-8
    b"",                                                   # empty
    b"# only a comment\n# and another\n",
    b"rule " + b"x" * 5_000_000,                          # huge
], ids=["binary", "not-utf8", "empty", "comments-only", "huge"])
def test_import_survives_an_odd_file_and_still_imports_the_rest(content, clients, github):
    _import_repo(github, clients["admin"], {"rules/odd.yar": content, "rules/good.yar": yara_rule("good")})

    assert count(Rule, title="good") == 1
    assert ImporterResult.query.one().imported == 1


@pytest.mark.parametrize("name", ["rules/espace et accents é.yar", "rules/emoji 🔥.yar", "rules/<script>.yar",
                                  "rules/'; DROP TABLE rule; --.yar", "a/b/c/d/e/f/g/h/i/j/deep.yar"])
def test_import_of_a_file_with_an_odd_name_records_its_path_verbatim(name, clients, github):
    _import_repo(github, clients["admin"], {name: yara_rule("odd_name")})

    assert Rule.query.one().github_path == name


# ── ZIP uploads ───────────────────────────────────────────────────────────────

def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    buffer.seek(0)
    return buffer


def _upload(client, data):
    return client.post("/rule/import_rules_from_zip", data=data, content_type="multipart/form-data")


@pytest.mark.parametrize("member", ["../escaped.yar", "../../tmp/escaped.yar", "/tmp/escaped_abs.yar",
                                    "rules/../../escaped.yar"])
def test_zip_with_a_path_escaping_the_upload_folder_is_refused(member, clients):
    response = _upload(clients["admin"], {"zipfile": (_zip({member: yara_rule("escaped")}), "evil.zip")})

    assert response.status_code < 500
    assert count(Rule) == 0
    assert not os.path.exists("/tmp/escaped.yar") and not os.path.exists("/tmp/escaped_abs.yar")


@pytest.mark.parametrize("data", [
    {},
    {"zipfile": (io.BytesIO(b"not a zip at all"), "rules.zip")},
    {"zipfile": (io.BytesIO(b""), "")},
])
def test_zip_upload_without_a_valid_zip_is_refused(data, clients):
    response = _upload(clients["admin"], data)

    assert response.status_code == 400
    assert count(Rule) == 0


# ── Wrong-typed JSON bodies ───────────────────────────────────────────────────

@pytest.mark.parametrize("body", NOT_AN_OBJECT + [
    {"url": 5}, {"url": [f"{GITHUB}/acme/rules"]}, {"url": {"x": 1}},
    {"url": f"{GITHUB}/acme/rules", "branch": 5}, {"url": f"{GITHUB}/acme/rules", "branch": ["main"]},
    {"url": f"{GITHUB}/acme/rules", "license": {"x": 1}},
])
def test_import_with_a_wrong_typed_body_is_refused(body, clients, github):
    github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a")})

    response = _import(clients["admin"], body)

    assert 400 <= response.status_code < 500
    assert count(Rule) == 0


@pytest.mark.parametrize("body", NOT_AN_OBJECT + [
    {"url": "text"}, {"url": ["text"]}, {"url": [5]}, {"url": [{"url": 5}]}, {"url": [{"url": None}]},
    {"url": [{"url": f"{GITHUB}/acme/rules", "branch": 5}]},
])
def test_check_updates_of_a_repository_with_a_wrong_typed_body_never_errors(body, clients, github):
    github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a")})

    response = clients["admin"].post("/rule/check_updates_by_url", json=body)

    assert response.status_code < 500


@pytest.mark.parametrize("who", ["admin", "owner"])
@pytest.mark.parametrize("body", NOT_AN_OBJECT + [
    {"rules": "1"}, {"rules": {"1": 1}}, {"rules": ["abc"]}, {"rules": [None]}, {"rules": [{"id": 1}]},
    {"rules": [-1, 0, 2**63, True]},
])
def test_check_updates_of_rules_with_a_wrong_typed_body_never_errors(who, body, clients):
    response = clients[who].post("/rule/check_updates_by_rule", json=body)

    assert response.status_code < 500


@pytest.mark.parametrize("body", NOT_AN_OBJECT + [{"action": 5}, {"action": ["accept"]}, {"action": "explode"},
                                                  {"action": "accept", "f_found": "yes", "f_error": [1]}])
def test_bulk_decide_updates_with_a_wrong_typed_body_never_errors(body, clients, users):
    result = make_update_result(users.admin)

    response = clients["admin"].post(f"/rule/bulk_update_decision/{result.uuid}", json=body)

    assert response.status_code < 500


@pytest.mark.parametrize("body", NOT_AN_OBJECT + [{"action": 5}, {"action": "explode"}])
def test_bulk_decide_new_rules_with_a_wrong_typed_body_is_refused(body, clients, users):
    result = make_update_result(users.admin)

    response = clients["admin"].post(f"/rule/bulk_new_rules_decision/{result.uuid}", json=body)

    assert response.status_code == 400
    assert count(BackgroundJob) == 0


@pytest.mark.parametrize("body", NOT_AN_OBJECT + [
    {"action": "delete", "selected_ids": "text"}, {"action": "delete", "selected_ids": [5, None, {"url": 5}]},
    {"action": "delete", "mode": "all", "excluded_ids": 5}, {"action": 5}, {"action": "export", "selected_ids": 5},
])
def test_bulk_action_on_sources_with_a_wrong_typed_body_deletes_nothing(body, clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")

    response = clients["admin"].post("/rule/bulk_action_github", json=body)

    assert response.status_code < 500
    assert reload(rule).is_deleted is False


@pytest.mark.parametrize("body", NOT_AN_OBJECT + [
    {"repo_url": 5}, {"repo_url": [f"{GITHUB}/acme/rules"]},
    {"repo_url": f"{GITHUB}/acme/rules", "branch": 5},
    {"repo_url": f"{GITHUB}/acme/rules", "license": ["MIT"]},
    {"repo_url": f"{GITHUB}/acme/rules", "message": {"x": 1}},
])
def test_propose_with_a_wrong_typed_body_is_refused(body, clients):
    response = clients["user"].post("/rule/github_proposal/create", json=body)

    assert response.status_code == 400
    assert count(GithubProposal) == 0


@pytest.mark.parametrize("field, value", [("repo_url", f"{GITHUB}/acme/" + "r" * 600), ("branch", "b" * 300),
                                          ("license", "L" * 200)], ids=_short)
def test_propose_with_a_value_too_long_for_its_field_is_refused(field, value, clients):
    payload = {"repo_url": f"{GITHUB}/acme/rules", field: value}

    response = clients["user"].post("/rule/github_proposal/create", json=payload)

    assert response.status_code == 400
    assert count(GithubProposal) == 0


@pytest.mark.parametrize("message", INJECTIONS + ODD_CHARACTERS)
def test_propose_with_a_hostile_message_stores_it_as_plain_text(message, clients):
    response = clients["user"].post("/rule/github_proposal/create",
                                    json={"repo_url": f"{GITHUB}/acme/rules", "message": message})

    assert response.status_code < 500
    if response.status_code == 201:
        assert GithubProposal.query.one().message == message.strip().replace("\x00", "")


@pytest.mark.parametrize("body", NOT_AN_OBJECT + [
    {"uuids": "abc", "decision": "reject"}, {"uuids": 5, "decision": "reject"},
    {"uuids": [5, None, {"x": 1}], "decision": "reject"},
    {"uuids": ["PROPOSAL"], "decision": 5}, {"uuids": ["PROPOSAL"], "decision": "accept", "ownership_mode": 5},
    {"uuids": ["PROPOSAL"], "decision": "reject", "note": {"x": 1}},
    {"uuids": ["PROPOSAL"], "decision": "reject", "note": TOO_LONG},
], ids=_short)
def test_decide_proposals_with_a_wrong_typed_body_never_errors(body, clients, users):
    proposal = make_proposal(users.owner)
    if isinstance(body, dict) and body.get("uuids") == ["PROPOSAL"]:
        body = {**body, "uuids": [proposal.uuid]}

    response = clients["admin"].post("/rule/github_proposal/bulk_decision", json=body)

    assert response.status_code < 500
    if response.status_code >= 400:
        assert saved(proposal).status == "pending"


SCHEDULE_BREAKERS = [
    {"title": 5}, {"title": ["x"]}, {"title": "T" * 151}, {"title": "   "},
    {"frequency": 5}, {"frequency": "hourly"},
    {"hour": "3"}, {"hour": 24}, {"minute": -1}, {"minute": 1.5},
    {"frequency": "weekly", "days_of_week": "1"}, {"frequency": "weekly", "days_of_week": [7]},
    {"frequency": "monthly", "day_of_month": "5"}, {"frequency": "monthly", "day_of_month": 32},
    {"frequency": "monthly", "day_of_month": [1]},
    {"frequency": "cron", "cron_expr": 5}, {"frequency": "cron", "cron_expr": "not a cron"},
    {"timezone": "Not/AZone"}, {"timezone": 5}, {"timezone": ["UTC"]},
    {"selected_repo_urls": 5}, {"selected_repo_urls": [5, None]}, {"selected_repo_urls": {"x": 1}},
    {"repo_settings": "text"}, {"repo_settings": ["text"]}, {"repo_settings": [{"repo_url": 5}]},
    {"default_repo_settings": "text"},
    {"repo_mode": "all", "repo_filters": "text"}, {"repo_mode": "all", "excluded_repo_urls": 5},
    {"description": {"x": 1}},
]


@pytest.mark.parametrize("body", NOT_AN_OBJECT)
def test_create_a_sync_schedule_with_a_body_that_is_not_an_object_is_refused(body, clients):
    response = clients["admin"].post("/rule/github/schedule/create", json=body)

    assert response.status_code == 400
    assert count(GithubSyncSchedule) == 0


@pytest.mark.parametrize("fields", SCHEDULE_BREAKERS, ids=_short)
def test_create_a_sync_schedule_with_bad_fields_never_errors_nor_half_saves(fields, clients):
    response = clients["admin"].post("/rule/github/schedule/create", json=schedule_payload(**fields))

    assert response.status_code < 500
    if response.status_code >= 400:
        assert count(GithubSyncSchedule) == 0


@pytest.mark.parametrize("fields", SCHEDULE_BREAKERS, ids=_short)
def test_edit_a_sync_schedule_with_bad_fields_never_errors_nor_half_saves(fields, clients, users):
    schedule = make_schedule(users.admin, title="Untouched")

    payload = {**schedule_payload(title="Changed"), **fields}

    response = clients["admin"].post(f"/rule/github/schedule/{schedule.uuid}/update", json=payload)

    assert response.status_code < 500
    if response.status_code >= 400:
        assert saved(schedule).title == "Untouched"


@pytest.mark.parametrize("url", ["/rule/github/schedule/bulk_delete", "/rule/github/schedule/bulk_set_active"])
@pytest.mark.parametrize("body", NOT_AN_OBJECT + [
    {"selected_uuids": 5}, {"selected_uuids": "abc"}, {"selected_uuids": [5, None, {"x": 1}]},
    {"mode": "all", "excluded_uuids": 5}, {"mode": "all", "filters": "text"}, {"is_active": "no"},
])
def test_bulk_actions_on_sync_schedules_with_a_wrong_typed_body_never_errors(url, body, clients, users):
    schedule = make_schedule(users.admin)

    response = clients["admin"].post(url, json=body)

    assert response.status_code < 500
    assert reload(schedule) is not None or (isinstance(body, dict) and body.get("mode") == "all")


@pytest.mark.parametrize("title", INJECTIONS + ODD_CHARACTERS)
def test_create_a_sync_schedule_with_a_hostile_title_stores_it_as_plain_text(title, clients):
    response = clients["admin"].post("/rule/github/schedule/create", json=schedule_payload(title=title))

    assert response.status_code < 500
    if response.status_code == 201:
        assert GithubSyncSchedule.query.one().title == title.strip()


# ── Bad ids and uuids ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_id", BAD_IDS)
@pytest.mark.parametrize("url", ["/rule/changes_decision?history_id={}&decision=accepted",
                                 "/rule/update_github_rule?rule_id={}&decision=accepted",
                                 "/rule/update_github/history_json/{}"])
def test_decide_on_an_update_that_does_not_exist_is_not_found(url, bad_id, clients):
    response = clients["admin"].get(url.format(bad_id))

    assert response.status_code == 404


@pytest.mark.parametrize("bad_id", BAD_IDS)
def test_decide_on_an_update_of_a_check_with_a_bad_id_is_not_found(bad_id, clients, users):
    result = make_update_result(users.admin)

    response = clients["admin"].get(
        f"/rule/update_github_rule/decision_rule?rule_id={bad_id}&decision=accepted&sid={result.uuid}")

    assert response.status_code == 404


def test_decide_on_an_update_through_another_check_is_not_found(clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    _, _, history = make_pending_update(rule, yara_rule("changed"), checked_by=users.admin)
    other_check = make_update_result(users.admin)

    response = clients["admin"].get(
        f"/rule/update_github_rule/decision_rule?rule_id={history.id}&decision=accepted&sid={other_check.uuid}")

    assert response.status_code == 404
    assert saved(rule).to_string != yara_rule("changed")


@pytest.mark.parametrize("decision", ["", "maybe", "<script>", "ACCEPTED"])
def test_decide_on_an_update_with_an_unknown_decision_changes_nothing(decision, clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    result, _, history = make_pending_update(rule, yara_rule("changed"), checked_by=users.admin)

    response = clients["admin"].get(
        f"/rule/update_github_rule/decision_rule?rule_id={history.id}&decision={decision}&sid={result.uuid}")

    assert 400 <= response.status_code < 500
    assert saved(rule).to_string != yara_rule("changed")


@pytest.mark.parametrize("decision", ["", "maybe", "<script>", "ACCEPTED"])
def test_decide_from_the_pending_list_with_an_unknown_decision_changes_nothing(decision, clients, users):
    rule = make_github_rule(users.owner, f"{GITHUB}/acme/rules")
    _, status, history = make_pending_update(rule, yara_rule("changed"), checked_by=users.admin)

    response = clients["admin"].get(f"/rule/changes_decision?history_id={history.id}&decision={decision}")

    assert response.status_code == 400
    assert saved(history).message == "Update found for this rule."
    assert saved(status).update_available is True


UNKNOWN_UUIDS = ["nope", "00000000-0000-0000-0000-000000000000", "' OR 1=1 --", "a" * 300]


@pytest.mark.parametrize("sid", UNKNOWN_UUIDS)
@pytest.mark.parametrize("method, url", [
    ("get", "/rule/import_loading/{}"), ("get", "/rule/import_loading_status/{}"),
    ("get", "/rule/import_get_info_session/{}"), ("get", "/rule/update_loading/{}"),
    ("get", "/rule/update_loading_status/{}"), ("get", "/rule/update_loading_status/{}/get_rules"),
    ("get", "/rule/update_loading_status/{}/get_news_rules"), ("get", "/rule/update_get_info_session/{}"),
    ("get", "/rule/accept_all_update/{}"), ("post", "/rule/bulk_update_decision/{}"),
    ("post", "/rule/bulk_new_rules_decision/{}"),
    ("get", "/rule/history_github_importer/delete?uuid={}"), ("get", "/rule/history_github_updater/delete?uuid={}"),
    ("get", "/rule/github_proposal/{}"), ("post", "/rule/github_proposal/{}/cancel"),
    ("post", "/rule/github_proposal/{}/delete"), ("get", "/rule/github_proposal_detail/{}"),
    ("post", "/rule/github/schedule/{}/update"), ("post", "/rule/github/schedule/{}/delete"),
    ("get", "/rule/github/sync_run/{}"), ("get", "/rule/github/sync_run/{}/status"),
])
def test_an_unknown_uuid_is_not_found(method, url, sid, clients):
    client = clients["admin"]

    response = getattr(client, method)(url.format(sid), json={"action": "accept"} if method == "post" else None)

    assert response.status_code == 404


@pytest.mark.parametrize("sid", UNKNOWN_UUIDS)
def test_run_an_unknown_sync_schedule_is_refused(sid, clients):
    response = clients["admin"].post(f"/rule/github/schedule/{sid}/run_now")

    assert 400 <= response.status_code < 500


@pytest.mark.parametrize("query", ["page=-1", "page=0", "page=99999999999", "page=abc", "per_page=-5",
                                   "per_page=100000", "sort=nope&dir=sideways", "search=%27%20OR%201%3D1%20--"])
@pytest.mark.parametrize("url", ["/rule/history_github_importer/list", "/rule/history_github_updater/list",
                                 "/rule/get_url_github", "/rule/github_proposal/list", "/rule/github_proposal/mine",
                                 "/rule/github/schedule/list", "/rule/github/schedule/repo_candidates"])
def test_odd_paging_and_search_never_errors(url, query, clients, users):
    make_github_rule(users.owner, f"{GITHUB}/acme/rules")

    response = clients["admin"].get(f"{url}?{query}")

    assert response.status_code < 500


@pytest.mark.parametrize("url", ["", "not a url", "https://evil.example/a/b", f"{GITHUB}/../../x", f"{GITHUB}/a b/c d"])
def test_ask_github_about_an_odd_url_never_errors(url, clients):
    for route in ("/rule/get_github_branches", "/rule/github/repo_live_info"):
        response = clients["admin"].get(route, query_string={"url": url})

        assert response.status_code < 500


# ── API ───────────────────────────────────────────────────────────────────────

API_IMPORT = "/api/rule/private/import_rules_from_github"


@pytest.mark.parametrize("body", NOT_AN_OBJECT + [
    {"url": 5, "license": "MIT"}, {"url": f"{GITHUB}/acme/rules", "license": 5},
    {"url": f"{GITHUB}/acme/rules", "license": "MIT", "branch": 5},
    {"url": f"{GITHUB}/acme/rules", "license": "MIT", "branch": "../../etc"},
    {"url": f"{GITHUB}/acme/nothing-here", "license": "MIT"},
    {"url": "file:///etc/passwd", "license": "MIT"},
])
def test_api_import_with_a_bad_body_is_refused(body, app, users, github):
    github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a")})

    response = app.test_client().post(API_IMPORT, json=body, headers=api_headers(users.admin))

    assert 400 <= response.status_code < 500
    assert count(Rule) == 0
