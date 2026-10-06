"""
Unit tests for the Elastic Security detection rule format adapter.

The adapter mirrors the contract documented in
`app/features/rule/rule_format/abstract_rule_type/rule_type_abstract.py`
and is structured to match the existing `splunk_format`/`atr_format`
adapters for consistency.
"""
from __future__ import annotations

from textwrap import dedent

import pytest

from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import ValidationResult
from app.features.rule.rule_format.available_format.elastic_format import ElasticRule


# -------------------------------------------------------------------------
#                           Sample rule fixtures
# -------------------------------------------------------------------------

# A trimmed but real-shaped rule from elastic/detection-rules — one .toml
# file per rule, [metadata] + [rule], nested [[rule.threat]] arrays of
# tables, a [rule.threat.tactic] single table, triple-quoted multi-line
# strings, and a nested [rule.alert_suppression.duration] table.
_VALID_ESQL_RULE = dedent(
    """\
    [metadata]
    creation_date = "2026/07/14"
    integration = ["endpoint"]
    maturity = "production"
    min_stack_version = "9.3.0"
    updated_date = "2026/08/06"

    [rule]
    author = ["Elastic"]
    description = \"\"\"
    Detects non-allowlisted curl activity on Linux, macOS, and Windows hosts and uses an LLM to assess whether the
    activity is malicious, benign, or requires investigation.
    \"\"\"
    false_positives = [
        \"\"\"
        Routine automation, CI/CD jobs, infrastructure tooling.
        \"\"\",
    ]
    from = "now-20m"
    interval = "15m"
    language = "esql"
    license = "Elastic License v2"
    max_signals = 100
    name = "LLM-Based Curl Activity Triage"
    note = \"\"\"## Triage and analysis
    Some investigation notes.
    \"\"\"
    references = [
        "https://www.elastic.co/security-labs/beyond-behaviors",
    ]
    risk_score = 47
    rule_id = "d3851f38-ce10-4d13-a056-99fe711e6bcc"
    setup = \"\"\"## Setup
    Some setup instructions.
    \"\"\"
    severity = "medium"
    tags = [
        "Domain: Endpoint",
        "OS: Linux",
        "Tactic: Command and Control",
    ]
    timestamp_override = "event.ingested"
    type = "esql"

    query = '''
    FROM logs-endpoint.events.process-*
    | WHERE process.name == "curl"
    | LIMIT 50
    '''

    [[rule.threat]]
    framework = "MITRE ATT&CK"
    [[rule.threat.technique]]
    id = "T1105"
    name = "Ingress Tool Transfer"
    reference = "https://attack.mitre.org/techniques/T1105/"

    [rule.threat.tactic]
    id = "TA0011"
    name = "Command and Control"
    reference = "https://attack.mitre.org/tactics/TA0011/"

    [rule.alert_suppression]
    group_by = ["host.name"]
    missing_fields_strategy = "suppress"

    [rule.alert_suppression.duration]
    unit = "h"
    value = 6
    """
)

_VALID_EQL_RULE_MINIMAL = dedent(
    """\
    [metadata]
    creation_date = "2026/01/01"

    [rule]
    author = ["Community"]
    description = "A minimal but complete EQL rule."
    language = "eql"
    name = "Suspicious Process Creation"
    query = "process where process.name == \\"whoami.exe\\""
    references = []
    risk_score = 21
    rule_id = "11111111-1111-1111-1111-111111111111"
    severity = "low"
    tags = []
    type = "eql"
    """
)

_VALID_ML_RULE_NO_QUERY = dedent(
    """\
    [rule]
    author = ["Elastic"]
    description = "A machine_learning rule referencing a job, no query field."
    language = "ml"
    name = "Anomalous ML Job Alert"
    risk_score = 21
    rule_id = "22222222-2222-2222-2222-222222222222"
    severity = "low"
    type = "machine_learning"
    """
)

_MISSING_NAME = dedent(
    """\
    [rule]
    description = "x"
    language = "eql"
    query = "process where true"
    rule_id = "33333333-3333-3333-3333-333333333333"
    risk_score = 21
    severity = "low"
    """
)

_BAD_UUID = dedent(
    """\
    [rule]
    name = "Bad UUID Rule"
    description = "x"
    language = "eql"
    query = "process where true"
    rule_id = "not-a-uuid"
    risk_score = 21
    severity = "low"
    """
)

_MISSING_LANGUAGE_AND_BAD_SEVERITY = dedent(
    """\
    [rule]
    name = "Bad Enum Rule"
    description = "x"
    query = "process where true"
    rule_id = "44444444-4444-4444-4444-444444444444"
    risk_score = 21
    severity = "apocalyptic"
    """
)

# "kuery" (Kibana Query Language) is real and legitimate — Elastic's rule
# schema spells KQL this way, not "kql" (an earlier version of this set got
# that wrong, rejecting real elastic/detection-rules files). An outright
# unrecognized value is still accepted, just flagged as a warning, since
# this project doesn't have full confidence in an exhaustive enum here.
_KUERY_LANGUAGE_RULE = dedent(
    """\
    [rule]
    name = "Kuery Language Rule"
    description = "x"
    language = "kuery"
    query = "process.name: \\"whoami.exe\\""
    rule_id = "77777777-7777-7777-7777-777777777777"
    risk_score = 21
    severity = "low"
    """
)

_UNRECOGNIZED_LANGUAGE_RULE = dedent(
    """\
    [rule]
    name = "Unrecognized Language Rule"
    description = "x"
    language = "cobol"
    query = "process where true"
    rule_id = "88888888-8888-8888-8888-888888888888"
    risk_score = 21
    severity = "low"
    """
)

_MISSING_QUERY_NON_ML = dedent(
    """\
    [rule]
    name = "No Query Rule"
    description = "x"
    language = "eql"
    type = "eql"
    rule_id = "55555555-5555-5555-5555-555555555555"
    risk_score = 21
    severity = "low"
    """
)

_BAD_RISK_SCORE = dedent(
    """\
    [rule]
    name = "Bad Risk Score Rule"
    description = "x"
    language = "eql"
    query = "process where true"
    rule_id = "66666666-6666-6666-6666-666666666666"
    risk_score = 500
    severity = "low"
    """
)

_UNRELATED_TOML = dedent(
    """\
    [project]
    name = "my-package"
    version = "1.2.3"
    dependencies = ["requests"]
    """
)


@pytest.fixture(scope="module")
def elastic() -> ElasticRule:
    return ElasticRule()


def test_format_identifier(elastic: ElasticRule) -> None:
    assert elastic.format == "elastic"
    assert elastic.get_class() == "ElasticRule"


# ---- detect() ---------------------------------------------------------------


def test_detect_matches_esql_rule(elastic: ElasticRule) -> None:
    assert elastic.detect(_VALID_ESQL_RULE) is True


def test_detect_matches_eql_rule(elastic: ElasticRule) -> None:
    assert elastic.detect(_VALID_EQL_RULE_MINIMAL) is True


def test_detect_rejects_unrelated_toml(elastic: ElasticRule) -> None:
    assert elastic.detect(_UNRELATED_TOML) is False


def test_detect_rejects_non_toml(elastic: ElasticRule) -> None:
    assert elastic.detect("not { valid [ toml") is False


def test_detect_rejects_empty(elastic: ElasticRule) -> None:
    assert elastic.detect("") is False


# ---- validate() ---------------------------------------------------------------


def test_validate_accepts_esql_rule(elastic: ElasticRule) -> None:
    result = elastic.validate(_VALID_ESQL_RULE)
    assert isinstance(result, ValidationResult)
    assert result.ok is True, result.errors
    assert result.errors == []
    assert result.normalized_content == _VALID_ESQL_RULE


def test_validate_accepts_minimal_eql_rule(elastic: ElasticRule) -> None:
    result = elastic.validate(_VALID_EQL_RULE_MINIMAL)
    assert result.ok is True, result.errors


def test_validate_accepts_queryless_ml_rule(elastic: ElasticRule) -> None:
    result = elastic.validate(_VALID_ML_RULE_NO_QUERY)
    assert result.ok is True, result.errors


def test_validate_rejects_missing_name(elastic: ElasticRule) -> None:
    result = elastic.validate(_MISSING_NAME)
    assert result.ok is False
    assert any("name" in e for e in result.errors)


def test_validate_rejects_bad_uuid(elastic: ElasticRule) -> None:
    result = elastic.validate(_BAD_UUID)
    assert result.ok is False
    assert any("UUID" in e or "rule_id" in e for e in result.errors)


def test_validate_rejects_missing_language_and_bad_severity(elastic: ElasticRule) -> None:
    result = elastic.validate(_MISSING_LANGUAGE_AND_BAD_SEVERITY)
    assert result.ok is False
    assert any("language" in e for e in result.errors)
    assert any("severity" in e for e in result.errors)


def test_validate_accepts_kuery_language(elastic: ElasticRule) -> None:
    result = elastic.validate(_KUERY_LANGUAGE_RULE)
    assert result.ok is True, result.errors


def test_validate_warns_but_accepts_unrecognized_language(elastic: ElasticRule) -> None:
    result = elastic.validate(_UNRECOGNIZED_LANGUAGE_RULE)
    assert result.ok is True, result.errors
    assert any("language" in w for w in result.warnings)


def test_validate_rejects_missing_query_for_non_ml_type(elastic: ElasticRule) -> None:
    result = elastic.validate(_MISSING_QUERY_NON_ML)
    assert result.ok is False
    assert any("query" in e for e in result.errors)


def test_validate_rejects_out_of_range_risk_score(elastic: ElasticRule) -> None:
    result = elastic.validate(_BAD_RISK_SCORE)
    assert result.ok is False
    assert any("risk_score" in e for e in result.errors)


def test_validate_rejects_empty_toml(elastic: ElasticRule) -> None:
    result = elastic.validate("")
    assert result.ok is False


def test_validate_rejects_toml_parse_error(elastic: ElasticRule) -> None:
    result = elastic.validate("[rule\nname = broken")
    assert result.ok is False
    assert any("TOML parse error" in e for e in result.errors)


def test_validate_rejects_missing_rule_section(elastic: ElasticRule) -> None:
    result = elastic.validate("[metadata]\ncreation_date = \"2026/01/01\"\n")
    assert result.ok is False
    assert any("[rule]" in e for e in result.errors)


def test_validate_warns_but_accepts_missing_threat_and_optional_fields(elastic: ElasticRule) -> None:
    result = elastic.validate(_VALID_EQL_RULE_MINIMAL)
    assert result.ok is True
    assert any("threat" in w for w in result.warnings)


# ---- parse_metadata() ---------------------------------------------------------


def test_parse_metadata_basic_fields(elastic: ElasticRule) -> None:
    meta = elastic.parse_metadata(_VALID_ESQL_RULE, info={"repo_url": "https://github.com/elastic/detection-rules"})
    assert meta["title"] == "LLM-Based Curl Activity Triage"
    assert meta["format"] == "elastic"
    assert meta["license"] == "Elastic License v2"
    assert meta["author"] == "Elastic"
    assert meta["original_uuid"] == "d3851f38-ce10-4d13-a056-99fe711e6bcc"
    assert meta["severity"] == "medium"
    assert meta["source"] == "https://github.com/elastic/detection-rules"


def test_parse_metadata_extracts_nested_mitre_technique_ids(elastic: ElasticRule) -> None:
    meta = elastic.parse_metadata(_VALID_ESQL_RULE)
    assert "T1105" in meta["tags"]


def test_parse_metadata_passes_through_native_tags(elastic: ElasticRule) -> None:
    meta = elastic.parse_metadata(_VALID_ESQL_RULE)
    assert "Domain: Endpoint" in meta["tags"]
    assert "Tactic: Command and Control" in meta["tags"]


def test_parse_metadata_falls_back_to_filename_when_name_missing(elastic: ElasticRule) -> None:
    meta = elastic.parse_metadata(
        _MISSING_NAME,
        info={"github_path": "rules/linux/execution_suspicious_curl_activity.toml"},
    )
    assert meta["title"] == "Execution Suspicious Curl Activity"


def test_parse_metadata_defaults_license_from_info(elastic: ElasticRule) -> None:
    meta = elastic.parse_metadata(_VALID_EQL_RULE_MINIMAL, info={"license": "MIT"})
    # rule.license absent in this fixture -> falls back to info
    assert meta["license"] == "MIT"


def test_parse_metadata_returns_safe_shape_on_parse_error(elastic: ElasticRule) -> None:
    meta = elastic.parse_metadata("not valid [ toml")
    assert meta["format"] == "elastic"
    assert meta["severity"] == "unknown"
    assert meta["tags"] == []
    assert "Error parsing metadata" in meta["description"]


def test_parse_metadata_unknown_severity_falls_back(elastic: ElasticRule) -> None:
    meta = elastic.parse_metadata(_MISSING_LANGUAGE_AND_BAD_SEVERITY)
    assert meta["severity"] == "unknown"


# ---- documentation_signals() ---------------------------------------------------


def test_documentation_signals_all_true_for_rich_rule(elastic: ElasticRule) -> None:
    signals = elastic.documentation_signals(_VALID_ESQL_RULE)
    assert signals == {
        "documents_references": True,
        "documents_false_positives": True,
        "documents_investigation_guide": True,
        "documents_setup": True,
        "documents_attack_mapping": True,
    }


def test_documentation_signals_false_for_minimal_rule(elastic: ElasticRule) -> None:
    signals = elastic.documentation_signals(_VALID_EQL_RULE_MINIMAL)
    assert signals["documents_false_positives"] is False
    assert signals["documents_attack_mapping"] is False


# ---- file listing / extraction -------------------------------------------------


def test_get_rule_files_accepts_toml_extension(elastic: ElasticRule) -> None:
    assert elastic.get_rule_files("some_rule.toml") is True


def test_get_rule_files_rejects_other_extensions(elastic: ElasticRule) -> None:
    assert elastic.get_rule_files("some_rule.yml") is False
    assert elastic.get_rule_files("some_rule.json") is False


def test_extract_rules_from_file_returns_single_rule(elastic: ElasticRule, tmp_path) -> None:
    f = tmp_path / "llm_based_curl_activity_triage.toml"
    f.write_text(_VALID_ESQL_RULE, encoding="utf-8")
    rules = elastic.extract_rules_from_file(str(f))
    assert len(rules) == 1
    assert rules[0] == _VALID_ESQL_RULE


def test_extract_rules_from_unrelated_toml_is_empty(elastic: ElasticRule, tmp_path) -> None:
    f = tmp_path / "pyproject.toml"
    f.write_text(_UNRELATED_TOML, encoding="utf-8")
    rules = elastic.extract_rules_from_file(str(f))
    assert rules == []


def test_extract_rules_from_missing_file_is_empty(elastic: ElasticRule, tmp_path) -> None:
    rules = elastic.extract_rules_from_file(str(tmp_path / "does_not_exist.toml"))
    assert rules == []


# ---- cross-format isolation ------------------------------------------------


def test_no_other_format_claims_toml() -> None:
    from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import RuleType, load_all_rule_formats
    load_all_rule_formats()
    claimants = [cls().format for cls in RuleType.__subclasses__() if cls().get_rule_files("x.toml")]
    assert claimants == ["elastic"]
