"""Security of the rule editor and of every YARA compilation on the server: a rule can never make
the server read one of its files (YARA `include`), and one user cannot queue Create jobs at will."""
import pytest

from app.core.db_class.job import BackgroundJob
from app.core.db_class.rule import Rule
from app.features.editor import editor_core as EditorModel
from tests_new.editor.test_editor_yara_import import body

INCLUDE = 'include "/etc/passwd"\nrule leak { condition: true }'


def test_editor_validation_never_reads_a_server_file(clients):
    res = clients["user"].post("/editor-api/yara/plan", json=body('rule ok_inc { condition: true }') | {"rules": [{"name": "leak", "text": INCLUDE}]})
    text = str(res.json)
    assert "root:" not in text and "/etc/passwd(" not in text


def test_creating_a_rule_never_reads_a_server_file(clients):
    from tests_new.helpers.rules import new_rule_form
    form = new_rule_form()
    form["to_string"] = INCLUDE
    page = clients["user"].post("/rule/create_rule", data=form).get_data(as_text=True)
    assert "/etc/passwd(" not in page and "unterminated regular expression" not in page
    assert Rule.query.filter_by(title=form["title"]).count() == 0


def test_one_create_at_a_time_per_user(clients):
    first = clients["user"].post("/editor-api/yara/jobs", json=body('rule one_job { condition: true }'))
    assert first.status_code == 202
    second = clients["user"].post("/editor-api/yara/jobs", json=body('rule two_job { condition: true }'))
    assert second.status_code == 429
    assert BackgroundJob.query.filter_by(job_type="editor_yara_import").count() == 1


def test_this_servers_own_files_are_only_used_when_an_admin_allows_it(clients, monkeypatch):
    if EditorModel.tests is None:
        pytest.skip("rule tests are switched off")
    from app.core.utils import app_settings
    real = app_settings.get_setting
    ids = lambda: {s["id"] for s in clients["user"].get("/editor-api/test/sets?format=yara").json["sets"]}   # noqa: E731
    assert "benign-usr-bin" not in ids()                                    # off by default
    monkeypatch.setattr(app_settings, "get_setting", lambda k: True if k == "editor.test_system_sets" else real(k))
    assert "benign-usr-bin" in ids()


@pytest.mark.parametrize("mode,user_ok,admin_ok", [("off", False, False), ("admins", False, True), ("everyone", True, True)])
def test_who_may_use_the_tests(clients, users, monkeypatch, mode, user_ok, admin_ok):
    from app.features.rule_tester import sample_test_core as SampleTests
    from tests_new.helpers.rules import make_rule
    monkeypatch.setattr(SampleTests, "test_access", lambda: mode)
    rule = make_rule(users.owner)
    for who, allowed in (("user", user_ok), ("admin", admin_ok)):
        sets = clients[who].get("/editor-api/test/sets?format=yara").json
        assert (sets["available"] if EditorModel.tests else allowed) == allowed or not EditorModel.tests
        start = clients[who].post("/editor-api/test/", json={"format": "yara", "text": "rule x { condition: true }", "sets": []})
        assert (start.status_code == 403) == (not allowed)
        assert (clients[who].get(f"/rule/detail_rule/{rule.id}/samples").status_code == 200) == allowed
        page = clients[who].get(f"/rule/detail_rule/{rule.id}").get_data(as_text=True)
        assert (f"/rule/detail_rule/{rule.id}/samples" in page) == allowed
    assert clients["anonymous"].get(f"/rule/detail_rule/{rule.id}/samples").status_code == (200 if mode == "everyone" else 404)


def test_admin_sets_the_access_from_the_settings_page(clients):
    from app.core.utils.app_settings import clear_cache, get_setting
    assert get_setting("editor.test_access") == "admins"                       # private by default
    assert clients["user"].post("/admin/settings/rule_tests_access", json={"mode": "off"}).status_code == 403
    res = clients["admin"].post("/admin/settings/rule_tests_access", json={"mode": "everyone"})
    assert res.json == {"success": True, "mode": "everyone"}
    clear_cache()
    assert get_setting("editor.test_access") == "everyone"
    assert clients["admin"].post("/admin/settings/rule_tests_access", json={"mode": "nope"}).status_code == 400
