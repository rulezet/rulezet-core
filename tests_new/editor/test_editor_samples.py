"""Tests on sample sets kept in Rulezet (app/features/rule_tester/sample_test_core.py): runs in the
database, the YARA editor's Create job testing the document (setting editor.test_on_create),
the result kept per rule version and shown on the rule page."""
import pytest

from app.core.db_class.rule import Rule
from app.core.db_class.rule_tester import RuleSampleResult, SampleTestRun
from app.features.editor import editor_core as EditorModel
from app.features.editor import editor_jobs as EditorJobs
from app.features.rule_tester import sample_test_core as SampleTests
from tests_new.editor.test_editor_yara_import import _run_job, body

GNU = 'rule ed_gnu\n{\n    strings:\n        $g = "GNU"\n    condition:\n        $g\n}'
QUIET = 'rule ed_quiet\n{\n    strings:\n        $q = "zz_never_in_any_sample_zz"\n    condition:\n        $q\n}'


@pytest.fixture
def tester():
    """Runs synchronously, sandboxed by resource limits only (CI has no bubblewrap)."""
    rulezet_tester = pytest.importorskip("rulezet_tester")
    service = EditorModel.tests
    if service is None:
        pytest.skip("rule tests are switched off")
    saved = service.sandbox, service.executor
    service.sandbox, service.executor = rulezet_tester.Sandbox(mode="process"), (lambda fn: fn())
    yield service
    service.sandbox, service.executor = saved


def settings(monkeypatch, **value):
    conf = {"enabled": True, "kinds": ["benign"], "block_on_false_positives": False, **value}
    monkeypatch.setattr(EditorJobs, "get_setting", lambda key: conf)


def test_editor_runs_are_kept_in_the_database(clients, tester):
    run_id = clients["user"].post("/editor-api/test/", json={"format": "yara", "text": QUIET, "sets": ["benign-text"]}).json["id"]
    row = SampleTestRun.query.filter_by(run_id=run_id).first()
    assert row and row.status == "done" and row.origin == "editor"
    assert clients["user"].get(f"/editor-api/test/{run_id}").json["summary"]["false_positives"] == 0


def test_create_tests_the_document_and_keeps_the_result(app, clients, tester, monkeypatch):
    settings(monkeypatch)
    state = _run_job(app, clients["user"], body(GNU, QUIET))
    samples = state["steps"][2]
    assert state["ok"] is True and samples["status"] == "warning"       # GNU fires on benign files
    assert "false positive" in samples["detail"]

    gnu, quiet = Rule.query.filter_by(title="ed_gnu").one(), Rule.query.filter_by(title="ed_quiet").one()
    assert SampleTests.latest_result(gnu)["false_positives"] >= 1
    assert SampleTests.latest_result(quiet)["false_positives"] == 0     # per rule, not per document
    assert SampleTestRun.query.filter_by(origin="create").count() == 1

    page = clients["user"].get(f"/rule/detail_rule/{gnu.id}").get_data(as_text=True)
    assert "rule-sample-badge--fp" in page


def test_the_result_belongs_to_the_tested_version(app, clients, tester, monkeypatch):
    settings(monkeypatch)
    _run_job(app, clients["user"], body(QUIET))
    rule = Rule.query.filter_by(title="ed_quiet").one()
    assert SampleTests.latest_result(rule) is not None
    rule.to_string = QUIET.replace("zz_never", "yy_never")
    assert SampleTests.latest_result(rule) is None
    assert RuleSampleResult.query.filter_by(rule_id=rule.id).count() == 1


def test_false_positives_can_block_the_creation(app, clients, tester, monkeypatch):
    settings(monkeypatch, block_on_false_positives=True)
    state = _run_job(app, clients["user"], body(GNU))
    assert state["ok"] is False
    assert [s["status"] for s in state["steps"][2:]] == ["error", "skipped"]
    assert Rule.query.filter_by(title="ed_gnu").count() == 0


def test_switched_off(app, clients, tester, monkeypatch):
    settings(monkeypatch, enabled=False)
    state = _run_job(app, clients["user"], body(QUIET))
    assert state["ok"] is True and state["steps"][2]["status"] == "skipped"
    assert SampleTestRun.query.filter_by(origin="create").count() == 0


def test_rule_counts_only_look_at_that_rule():
    run = {"samples": [
        {"expected": "no_match", "verdict": "match", "hits": [{"rule": "a"}]},
        {"expected": "match", "verdict": "match", "hits": [{"rule": "b"}]},
        {"expected": "match", "verdict": "no_match", "hits": []},
        {"expected": "unknown", "verdict": "timeout", "hits": []},
    ]}
    assert SampleTests.rule_counts(run, "a") == {"total": 4, "detected": 0, "missed": 2, "false_positives": 1, "errors": 1}
    assert SampleTests.rule_counts(run, "b") == {"total": 4, "detected": 1, "missed": 1, "false_positives": 0, "errors": 1}


def test_nothing_new_nothing_tested(app, clients, tester, monkeypatch):
    settings(monkeypatch)
    _run_job(app, clients["user"], body(QUIET))
    again = _run_job(app, clients["user"], body(QUIET))
    assert again["steps"][2]["status"] == "skipped"
    assert Rule.query.filter_by(title="ed_quiet").count() == 1
    assert SampleTestRun.query.filter_by(origin="create").count() == 1


def test_samples_page(app, clients, tester, monkeypatch):
    settings(monkeypatch)
    _run_job(app, clients["user"], body(GNU))
    rule = Rule.query.filter_by(title="ed_gnu").one()
    page = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}/samples")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Tests on samples" in html and "false_positive" in html and "/path" not in html
    details = SampleTests.rule_sample_details(rule)
    assert details["latest"]["false_positives"] >= 1 and details["sets"] and details["samples"]
    assert any(s["hits"] for s in details["samples"] if s["outcome"] == "false_positive")
    assert details["strings"][0]["id"] == "$g" and details["strings"][0]["false_positives"] >= 1
    rule.to_string = GNU.replace("GNU", "GNU_v2")              # another version: not tested
    assert rule_page_latest(rule) is None


def rule_page_latest(rule):
    return SampleTests.rule_sample_details(rule)["latest"]
