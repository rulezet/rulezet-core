"""Create issue — the Markdown report of a rule / of a Git source (issue_report.py)."""
import pytest

from app import db
from app.core.db_class.git import GithubRepo
from app.core.db_class.rule import InvalidRuleModel, RuleReview
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from tests_new.helpers.rules import make_rule

ADMINS = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}
REPO = "https://github.com/example/rules"


@pytest.mark.parametrize("role, expected", matrix(ADMINS))
def test_rule_report_admins_only(role, expected, clients, users):
    rule = make_rule(users.owner)
    assert_outcome(clients[role].get(f"/rule/{rule.id}/issue_report"), expected)


def test_rule_report_says_what_is_wrong_and_links_its_repository(clients, users):
    rule = make_rule(users.owner, source=REPO, github_path="yara/x.yar")
    db.session.add(RuleReview(uuid="rv", rule_id=rule.id, user_id=users.user.id, verdict="changes_requested",
                              comment="the <script> condition is too broad", content_hash="old"))
    db.session.commit()

    data = clients["admin"].get(f"/rule/{rule.id}/issue_report").get_json()

    assert data["provider"] == "github" and data["issue_url"].startswith(REPO + "/issues/new?title=")
    md = data["markdown"]
    assert "### Summary" in md and "Quality score" in md
    assert f"{REPO}/blob/" in md                               # link to the rule's file
    assert "<script>" not in md                                # user text never injected as HTML


def test_deleted_rule_has_no_report(clients, users):
    rule = make_rule(users.owner)
    rule.is_deleted = True
    db.session.commit()
    assert clients["admin"].get(f"/rule/{rule.id}/issue_report").status_code == 404


@pytest.mark.parametrize("role, expected", matrix(ADMINS))
def test_repo_report_admins_only(role, expected, clients, users):
    db.session.add(GithubRepo(uuid="g1", url=REPO, rule_count=0))
    db.session.commit()
    assert_outcome(clients[role].get(f"/rule/github/issue_report?url={REPO}"), expected)


def test_repo_report_groups_bad_rules_by_error(clients, users):
    db.session.add(GithubRepo(uuid="g1", url=REPO, rule_count=0))
    for n in range(3):
        db.session.add(InvalidRuleModel(file_name=f"r{n}.yar", error_message=f'line {n}: undefined identifier "rule_{n}"',
                                        user_id=users.admin.id, url=REPO, github_path=f"yara/r{n}.yar", rule_type="yara"))
    db.session.add(InvalidRuleModel(file_name="s.yml", error_message="['status \\'removed\\' is not one of: [\\'a\\', \\'b\\']']",
                                    user_id=users.admin.id, url=REPO, github_path="sigma/s.yml", rule_type="sigma"))
    db.session.commit()

    data = clients["admin"].get(f"/rule/github/issue_report?url={REPO}").get_json()

    md = data["markdown"]
    assert "Files that could not be imported (4)" in md
    assert '<b>undefined identifier "…"</b> — 3 file(s)' in md   # the 3 YARA errors grouped
    assert "References that do not resolve (3)" in md
    assert f"{REPO}/blob/HEAD/yara/r0.yar" in md
    assert data["issue_url"].startswith(REPO + "/issues/new?")


def test_unknown_repo(clients):
    assert clients["admin"].get("/rule/github/issue_report?url=https://github.com/no/such").status_code == 404
