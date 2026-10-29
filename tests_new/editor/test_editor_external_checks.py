"""External checks of the YARA editor (app/features/editor/external_checks.py): YARA-X, the CCCS
standard and yaraQA give advice next to Rulezet's own validation — never a verdict on saving."""
import pytest

from app.features.editor import external_checks as ExternalChecks

RULE = '''rule Ext_Check_Demo
{
    meta:
        description = "demo"
        author = "tests"
    strings:
        $a = "DownloadString" nocase
        $b = "ab"
    condition:
        $a or $b or true
}
'''


def _post(client, text, tools=None):
    return client.post("/editor-api/external-checks", json={"format": "yara", "text": text, **({"tools": tools} if tools else {})})


def test_for_editor_users_only_and_yara_only(clients):
    assert set(_post(clients["user"], RULE).json["results"]) == {"yarax", "cccs", "yaraqa"}
    assert clients["anonymous"].post("/editor-api/external-checks", json={"text": RULE}).status_code == 401
    other = clients["user"].post("/editor-api/external-checks", json={"format": "sigma", "text": "title: x"})
    assert other.json == {"results": {}}


def test_each_tool_gives_its_advice(clients):
    results = _post(clients["user"], RULE).json["results"]
    yx = results["yarax"]
    if yx["available"]:
        assert any(w["code"] == "invariant_expr" and w["line"] for w in yx["warnings"])     # `or true`
    cccs = results["cccs"]
    if cccs["available"]:
        assert any("status" in e["message"] for e in cccs["errors"])                       # required CCCS meta
    qa = results["yaraqa"]
    if qa["available"]:
        assert qa["ok"] is True and any(w["code"] for w in qa["warnings"])                 # advice, never an error


def test_yarax_offers_a_formatted_version(clients):
    res = _post(clients["user"], 'rule fmt_me { strings: $a = "hello world" condition: $a }', ["yarax"]).json["results"]["yarax"]
    if not res["available"]:
        pytest.skip(res["reason"])
    assert res["ok"] and res["fixed_text"].startswith("rule fmt_me {\n")


def test_yarax_never_reads_a_server_file(clients):
    res = _post(clients["user"], 'include "/etc/passwd"\nrule x { condition: true }', ["yarax"]).json["results"]["yarax"]
    if not res["available"]:
        pytest.skip(res["reason"])
    assert res["ok"] is False and "root:" not in str(res)


def test_switched_off_tools_do_not_run(clients, monkeypatch):
    monkeypatch.setattr(ExternalChecks, "enabled_tools", lambda: ["yaraqa"])
    assert set(_post(clients["user"], RULE).json["results"]) == {"yaraqa"}


def test_bad_input_is_refused_cleanly(clients):
    assert clients["user"].post("/editor-api/external-checks", json={"text": ""}).status_code == 400
    assert clients["user"].post("/editor-api/external-checks", json={"text": 12}).status_code == 400
    big = _post(clients["user"], "rule a { condition: true }\n" * 10000).json["results"]
    assert all(r["available"] is False for r in big.values())


def test_create_job_has_an_external_checks_step_that_never_blocks(app, clients):
    from tests_new.editor.test_editor_yara_import import _run_job, body
    state = _run_job(app, clients["user"], body('rule ext_job_rule { strings: $a = "zzz_ext" condition: $a or true }'))
    step = next(s for s in state["steps"] if s["id"] == "external")
    assert step["status"] in ("ok", "warning") and state["ok"] is True
