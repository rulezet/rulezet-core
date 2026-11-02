"""Sigma conversions (exporters/sigma_convert_exporter.py): a rule a target can't express is an expected
"not available" answer, never an application error in the logs."""
import logging

from tests_new.helpers.rules import make_rule

SIGMA = """title: Hash match
id: 7c3f1a8e-2b4d-4e6f-9a1b-3c5d7e9f1a2b
status: test
logsource:
    product: windows
    category: process_creation
detection:
    selection:
        Hashes|contains: 'IMPHASH=0123456789ABCDEF0123456789ABCDEF'
    condition: selection
level: high
"""


def _sigma_rule(users):
    return make_rule(users.owner, format="sigma", to_string=SIGMA, title="Hash match")


def test_xdr_target_converts_or_explains(clients, users):
    rule = _sigma_rule(users)
    data = clients["anonymous"].get(f"/rule/get_sigma_convert/{rule.id}?target=xdr").get_json()
    assert data["success"] or "can't" in data["error"] or "isn't available" in data["error"]


def test_unavailable_conversion_is_not_logged(clients, users, caplog):
    rule = _sigma_rule(users)
    with caplog.at_level(logging.ERROR):
        for target in ("xdr", "sentinel"):
            clients["anonymous"].get(f"/rule/get_sigma_convert/{rule.id}?target={target}")
            r = clients["anonymous"].get(f"/rule/download_rule?rule_id={rule.id}&format={target}")
            assert r.status_code == 200
    assert not [rec for rec in caplog.records if "Unhandled error" in rec.getMessage()]


BOOLEAN_SIGMA = """title: Boolean field
id: 5f1a0bd6-7b4e-4c3c-9d7e-8d2b1c6a9e11
status: test
logsource:
    product: windows
    category: process_creation
detection:
    selection:
        Image|endswith: '\\\\x.exe'
        Enabled: true
    condition: selection
level: low
"""


def test_backend_refusing_a_boolean_is_explained_not_logged(clients, users, caplog):
    # Loki and SecOps raise a plain NotImplementedError for a boolean value: "can't express this rule"
    rule = make_rule(users.owner, format="sigma", to_string=BOOLEAN_SIGMA, title="Boolean field")
    with caplog.at_level(logging.ERROR):
        for target in ("loki", "secops"):
            data = clients["anonymous"].get(f"/rule/get_sigma_convert/{rule.id}?target={target}").get_json()
            assert data["success"] is False and "can't express this rule" in data["error"]
    assert not [rec for rec in caplog.records if "Unhandled error" in rec.getMessage()]
