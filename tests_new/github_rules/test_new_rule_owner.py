"""Who the new rules found by a GitHub update belong to: chosen by an admin / GitHub Manager
(the user add-all / add-one / a Sync Schedule repo), else the owner of most rules of the same
source, else the user acting. Anyone else always owns what they add."""
from app.core.db_class.git import GithubSyncScheduleRepo
from app.core.db_class.job import BackgroundJob
from app.core.db_class.rule import Rule
from app.features.jobs.job_handlers import handle_bulk_new_rules_decision
from app.features.rule.rule_core import resolve_new_rule_owner, source_owner_suggestion
from tests_new.helpers.db import reload
from tests_new.helpers.github import GITHUB, make_new_rule, make_schedule, make_update_result
from tests_new.helpers.rules import make_rule, yara_rule

URL = f"{GITHUB}/acme/rules"


def _add_all(client, result, app, **body):
    client.post(f"/rule/bulk_new_rules_decision/{result.uuid}", json={"action": "add", **body})
    job = BackgroundJob.query.filter_by(job_type="bulk_new_rules_decision").order_by(BackgroundJob.id.desc()).first()
    handle_bulk_new_rules_decision(job, app)
    return reload(job)


def test_the_source_owner_is_the_automatic_choice(app, users):
    make_rule(users.owner, source=URL)
    make_rule(users.owner, source=URL + ".git")
    make_rule(users.user, source=URL)
    assert source_owner_suggestion(URL + "/")["id"] == users.owner.id
    assert resolve_new_rule_owner(users.admin, URL).id == users.owner.id          # auto
    assert resolve_new_rule_owner(users.admin, URL, users.user.id).id == users.user.id   # chosen
    assert resolve_new_rule_owner(users.admin, f"{GITHUB}/other/repo").id == users.admin.id   # nobody: the actor
    # someone who may not give rules away always gets them
    assert resolve_new_rule_owner(users.user, URL, users.owner.id).id == users.user.id


def test_add_all_gives_the_new_rules_to_the_owner_of_the_source(clients, users, app):
    make_rule(users.owner, source=URL)
    result = make_update_result(users.admin, repo_url=URL)
    make_new_rule(result, yara_rule("auto_owned"), name="auto_owned")
    _add_all(clients["admin"], result, app)
    assert Rule.query.filter_by(title="auto_owned").one().user_id == users.owner.id


def test_add_all_with_a_chosen_owner_or_me(clients, users, app):
    make_rule(users.owner, source=URL)
    result = make_update_result(users.admin, repo_url=URL)
    make_new_rule(result, yara_rule("for_user"), name="for_user")
    _add_all(clients["admin"], result, app, owner_id=users.user.id)
    assert Rule.query.filter_by(title="for_user").one().user_id == users.user.id
    result2 = make_update_result(users.admin, repo_url=URL)
    make_new_rule(result2, yara_rule("for_me"), name="for_me")
    _add_all(clients["admin"], result2, app, owner_id="me")
    assert Rule.query.filter_by(title="for_me").one().user_id == users.admin.id


def test_add_one_with_a_chosen_owner(clients, users, app):
    result = make_update_result(users.admin, repo_url=URL)
    nr = make_new_rule(result, yara_rule("one_rule"), name="one_rule")
    res = clients["admin"].get(f"/rule/add_new_rule?new_rule_id={nr.id}&sid={result.uuid}&owner_id={users.user.id}")
    assert res.status_code == 200
    assert Rule.query.filter_by(title="one_rule").one().user_id == users.user.id


def test_owner_info_endpoint(clients, users):
    make_rule(users.owner, source=URL)
    result = make_update_result(users.admin, repo_url=URL)
    data = clients["admin"].get(f"/rule/new_rules_owner/{result.uuid}").json
    assert data["can_choose"] is True and data["suggestion"]["id"] == users.owner.id
    assert data["me"]["id"] == users.admin.id


def test_a_schedule_repo_keeps_its_new_rules_owner(clients, users):
    schedule_body = {
        "title": "Owner test", "frequency": "daily", "hour": 3, "minute": 0, "timezone": "UTC",
        "repo_mode": "partial", "selected_repo_urls": [URL],
        "repo_settings": [{"repo_url": URL, "auto_add_new_rule": True, "new_rule_owner_id": users.user.id}],
    }
    res = clients["admin"].post("/rule/github/schedule/create", json=schedule_body)
    assert res.status_code == 201, res.json
    repo = GithubSyncScheduleRepo.query.filter_by(repo_url=URL).one()
    assert repo.new_rule_owner_id == users.user.id
    assert res.json["schedule"]["repos"][0]["new_rule_owner"]["id"] == users.user.id
