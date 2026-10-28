"""Editor tests: tests on samples are open to everyone here (setting editor.test_access), so the
suites can use a plain user; test_editor_security.py checks the three modes."""
import pytest

from app.features.rule_tester import sample_test_core as SampleTests


@pytest.fixture(autouse=True)
def _tests_for_everyone(monkeypatch):
    monkeypatch.setattr(SampleTests, "test_access", lambda: "everyone")
