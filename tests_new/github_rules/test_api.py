"""GitHub for rules — layer 3: the REST API.

One endpoint: POST /api/rule/private/import_rules_from_github, admin only
(the web import also accepts GitHub Managers — see the final report of this
feature: the API keeps the admin-only rule). It imports synchronously and
answers the counts. "nobody" = no key, "bad key" = a key matching no account.
"""
import pytest

from app.core.db_class.db import ActivityLog, InvalidRuleModel, Rule
from tests_new.helpers.db import count
from tests_new.helpers.formats import SAMPLES
from tests_new.helpers.rules import make_rule, yara_rule
from tests_new.helpers.users import api_headers

IMPORT = "/api/rule/private/import_rules_from_github"


def _headers(who, users, manager):
    if who == "nobody":
        return {}
    if who == "bad key":
        return {"X-API-KEY": "no-such-key"}
    if who == "manager":
        return api_headers(manager)
    return api_headers(getattr(users, who))


@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("user", 403), ("manager", 403),
                                         ("admin", 200)])
def test_import_needs_an_admin_key(who, status, app, users, manager, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a")})

    response = app.test_client().post(IMPORT, json={"url": url, "license": "MIT"},
                                      headers=_headers(who, users, manager))

    assert response.status_code == status
    assert count(Rule, source=url) == (1 if status == 200 else 0)


def test_import_answers_the_counts_and_creates_the_rules(app, users, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("rule_a"), "rules/b.yar": yara_rule("rule_b"),
                                     "rules/bad.yar": SAMPLES["yara"].invalid, "rules/dup.yar": yara_rule("dup")})
    make_rule(users.owner, to_string=yara_rule("dup"))

    response = app.test_client().post(IMPORT, json={"url": url, "license": "Apache-2.0"},
                                      headers=api_headers(users.admin))

    assert response.get_json() == {"success": True, "imported": 2, "skipped": 1, "failed": 1}
    rules = Rule.query.filter_by(source=url).all()
    assert sorted(r.title for r in rules) == ["rule_a", "rule_b"]
    assert {(r.license, r.user_id) for r in rules} == {("Apache-2.0", users.admin.id)}
    assert count(InvalidRuleModel) == 1
    assert count(ActivityLog, action="github.import_started") == 1


def test_import_of_a_branch_through_the_query_string(app, users, github):
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("on_main")})
    github.branch(url, "dev", {"rules/b.yar": yara_rule("on_dev")})

    response = app.test_client().post(IMPORT, query_string={"url": url, "license": "MIT", "branch": "dev"},
                                      headers=api_headers(users.admin))

    assert response.status_code == 200
    rule = Rule.query.filter_by(title="on_dev").one()
    assert (rule.branch, rule.github_path) == ("dev", "rules/b.yar")


@pytest.mark.parametrize("payload", [{"license": "MIT"}, {"url": "https://github.com/acme/rules"}])
def test_import_without_url_or_license_is_refused(payload, app, users):
    response = app.test_client().post(IMPORT, json=payload, headers=api_headers(users.admin))

    assert response.status_code == 400
    assert count(Rule) == 0
