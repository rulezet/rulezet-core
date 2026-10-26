"""Tests on samples from the editor (/editor-api/test, app/modules/rulezet-tester): logged-in users
only, and a run is visible only to the user who started it."""
import pytest

from app.features.editor import editor_core as EditorModel

RULE = 'rule t { strings: $g = "GNU" condition: $g }'


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


def test_anonymous_is_refused(clients, tester):
    assert clients["anonymous"].get("/editor-api/test/sets?format=yara").status_code == 401
    assert clients["anonymous"].post("/editor-api/test/", json={"format": "yara", "text": RULE, "sets": ["benign-text"]}).status_code == 401


def test_sets_and_a_run(clients, tester):
    sets = clients["user"].get("/editor-api/test/sets?format=yara").json
    assert sets["available"] is True
    assert {"benign-text", "synthetic-yara"} <= {s["id"] for s in sets["sets"]}

    res = clients["user"].post("/editor-api/test/", json={"format": "yara", "text": RULE, "sets": ["benign-text"]})
    assert res.status_code == 202
    run = clients["user"].get(f"/editor-api/test/{res.json['id']}").json
    assert run["status"] == "done"
    assert run["summary"]["false_positives"] == 1          # the GNU licence matches "GNU"
    assert all("path" not in s for s in run["samples"])     # never where the samples are


def test_a_run_is_private(clients, tester):
    run_id = clients["user"].post("/editor-api/test/", json={"format": "yara", "text": RULE, "sets": ["benign-text"]}).json["id"]
    assert clients["owner"].get(f"/editor-api/test/{run_id}").status_code == 404
    assert clients["admin"].get(f"/editor-api/test/{run_id}").status_code == 404


def test_refused_rules(clients, tester):
    res = clients["user"].post("/editor-api/test/", json={"format": "yara", "text": 'include "/etc/passwd"\n' + RULE, "sets": ["benign-text"]})
    assert res.status_code == 400 and "include" in res.json["error"]
    assert clients["user"].post("/editor-api/test/", json={"format": "yara", "text": RULE, "sets": []}).status_code == 400
