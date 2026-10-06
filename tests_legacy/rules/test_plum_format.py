"""
Unit tests for the Plum-Antibodies format adapter.

The adapter mirrors the contract documented in
`app/features/rule/rule_format/abstract_rule_type/rule_type_abstract.py`
and is structured to match the existing `atr_format`/`kunai_format`
adapters for consistency. Sample rules are modeled after the real
upstream corpus: https://github.com/D4-project/Plum-Antibodies/tree/main/tags
"""
from __future__ import annotations

from textwrap import dedent

import pytest

from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import ValidationResult
from app.features.rule.rule_format.available_format.plum_format import PlumRule


# -------------------------------------------------------------------------
#                           Sample rule fixtures
# -------------------------------------------------------------------------

_VALID_PLUM_RULE = dedent(
    """\
    name: alfresco
    description: Detect Alfresco
    uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9
    query: http_favicon_mmhash:1333537166
    tags:
    - proto:http
    - product:alfresco
    - vendor:alfresco
    version: 20260918T053418Z
    """
)

_VALID_PLUM_RULE_WITH_REFERENCES = dedent(
    """\
    name: adobe-campaign-classic
    description: Detect Adobe Campaign Classic
    uuid: 3e32e845-abca-5609-901c-f473d6a2beca
    query: http_favicon_mmhash:-333791179
    tags:
    - proto:http
    - product:adobe-campaign-classic
    - vendor:adobe
    references:
    - https://www.adobe.com/
    version: 20260918T053418Z
    """
)

_VALID_PLUM_RULE_OR_GROUPS = dedent(
    """\
    name: airwatch
    description: Detect Airwatch
    uuid: 36fb043d-bf7d-50c2-8b48-38ab6ff8e76c
    query: http_favicon_mmhash:321909464 OR http_favicon_mmhash:-1153873472
    tags:
    - proto:http
    - product:airwatch
    - vendor:airwatch
    version: 20260918T053418Z
    """
)

_VALID_PLUM_RULE_NOT_AND_HEADVAL = dedent(
    """\
    name: plesk-panel
    description: Detect Plesk control panel
    uuid: afb4ef43-da13-5a98-b80e-499e2f908ef1
    query: http_headval:x-powered-by.lk:plesklin AND port:443 AND NOT http_server.lk:apache
    tags:
    - proto:http
    - product:plesk
    version: 20260918T053418Z
    """
)

_INVALID_PLUM_MISSING_FIELDS = dedent(
    """\
    name: incomplete
    description: Missing several required fields
    """
)

_INVALID_PLUM_BAD_NAME = dedent(
    """\
    name: This-Is-Not-A-Slug
    description: Detect something
    uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9
    query: port:443
    tags:
    - product:something
    version: 20260918T053418Z
    """
)

_INVALID_PLUM_BAD_UUID = dedent(
    """\
    name: bad-uuid
    description: Detect something
    uuid: not-a-uuid
    query: port:443
    tags:
    - product:something
    version: 20260918T053418Z
    """
)

_INVALID_PLUM_BAD_VERSION = dedent(
    """\
    name: bad-version
    description: Detect something
    uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9
    query: port:443
    tags:
    - product:something
    version: 2026-09-18
    """
)

_INVALID_PLUM_BAD_TAG = dedent(
    """\
    name: bad-tag
    description: Detect something
    uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9
    query: port:443
    tags:
    - "product bad tag"
    version: 20260918T053418Z
    """
)

_INVALID_PLUM_UNSUPPORTED_FIELD = dedent(
    """\
    name: bad-field
    description: Detect something
    uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9
    query: made_up_field:foo
    tags:
    - product:something
    version: 20260918T053418Z
    """
)

_INVALID_PLUM_TRAILING_OR = dedent(
    """\
    name: trailing-or
    description: Detect something
    uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9
    query: port:443 OR
    tags:
    - product:something
    version: 20260918T053418Z
    """
)

_INVALID_PLUM_BAD_REFERENCES = dedent(
    """\
    name: bad-refs
    description: Detect something
    uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9
    query: port:443
    tags:
    - product:something
    references:
    - not-a-link
    version: 20260918T053418Z
    """
)

_SIGMA_LOOKALIKE_NOT_PLUM = dedent(
    """\
    title: "A Sigma rule that should not match Plum"
    id: 0c5a0e07-4f80-4cf3-b1c3-7e8a9f12345
    status: stable
    logsource:
      category: process_creation
      product: linux
    detection:
      selection:
        Image|endswith: '/cat'
      condition: selection
    """
)


# -------------------------------------------------------------------------
#                                Tests
# -------------------------------------------------------------------------


@pytest.fixture(scope="module")
def plum() -> PlumRule:
    return PlumRule()


def test_format_identifier(plum: PlumRule) -> None:
    assert plum.format == "plum"
    assert plum.get_class() == "PlumRule"


# ---- detect() --------------------------------------------------------------


def test_detect_matches_canonical_plum_rule(plum: PlumRule) -> None:
    assert plum.detect(_VALID_PLUM_RULE) is True


def test_detect_matches_or_groups_rule(plum: PlumRule) -> None:
    assert plum.detect(_VALID_PLUM_RULE_OR_GROUPS) is True


def test_detect_rejects_sigma_lookalike(plum: PlumRule) -> None:
    assert plum.detect(_SIGMA_LOOKALIKE_NOT_PLUM) is False


def test_detect_rejects_bad_version_stamp(plum: PlumRule) -> None:
    assert plum.detect(_INVALID_PLUM_BAD_VERSION) is False


def test_detect_rejects_non_yaml(plum: PlumRule) -> None:
    assert plum.detect("not: : yaml: :") is False


def test_detect_rejects_non_mapping_yaml(plum: PlumRule) -> None:
    assert plum.detect("- just\n- a\n- list\n") is False


# ---- validate() -------------------------------------------------------------


def test_validate_accepts_canonical_plum_rule(plum: PlumRule) -> None:
    result = plum.validate(_VALID_PLUM_RULE)
    assert isinstance(result, ValidationResult)
    assert result.ok is True, result.errors
    assert result.errors == []
    assert result.normalized_content == _VALID_PLUM_RULE


def test_validate_accepts_references(plum: PlumRule) -> None:
    result = plum.validate(_VALID_PLUM_RULE_WITH_REFERENCES)
    assert result.ok is True, result.errors


def test_validate_accepts_or_groups(plum: PlumRule) -> None:
    result = plum.validate(_VALID_PLUM_RULE_OR_GROUPS)
    assert result.ok is True, result.errors


def test_validate_accepts_not_and_headval(plum: PlumRule) -> None:
    result = plum.validate(_VALID_PLUM_RULE_NOT_AND_HEADVAL)
    assert result.ok is True, result.errors


def test_validate_rejects_missing_fields(plum: PlumRule) -> None:
    result = plum.validate(_INVALID_PLUM_MISSING_FIELDS)
    assert result.ok is False
    assert any("Missing required field" in e for e in result.errors)


def test_validate_rejects_bad_name(plum: PlumRule) -> None:
    result = plum.validate(_INVALID_PLUM_BAD_NAME)
    assert result.ok is False
    assert any("name must be" in e for e in result.errors)


def test_validate_rejects_bad_uuid(plum: PlumRule) -> None:
    result = plum.validate(_INVALID_PLUM_BAD_UUID)
    assert result.ok is False
    assert any("uuid must be" in e for e in result.errors)


def test_validate_rejects_bad_version(plum: PlumRule) -> None:
    result = plum.validate(_INVALID_PLUM_BAD_VERSION)
    assert result.ok is False
    assert any("version must use" in e for e in result.errors)


def test_validate_rejects_bad_tag(plum: PlumRule) -> None:
    result = plum.validate(_INVALID_PLUM_BAD_TAG)
    assert result.ok is False
    assert any("namespace:value" in e for e in result.errors)


def test_validate_rejects_unsupported_query_field(plum: PlumRule) -> None:
    result = plum.validate(_INVALID_PLUM_UNSUPPORTED_FIELD)
    assert result.ok is False
    assert any("unsupported search field" in e for e in result.errors)


def test_validate_rejects_trailing_or(plum: PlumRule) -> None:
    result = plum.validate(_INVALID_PLUM_TRAILING_OR)
    assert result.ok is False
    assert any("invalid query" in e for e in result.errors)


def test_validate_rejects_bad_references(plum: PlumRule) -> None:
    result = plum.validate(_INVALID_PLUM_BAD_REFERENCES)
    assert result.ok is False
    assert any("invalid reference link" in e for e in result.errors)


def test_validate_rejects_empty_yaml(plum: PlumRule) -> None:
    result = plum.validate("")
    assert result.ok is False
    assert any("Empty" in e for e in result.errors)


def test_validate_rejects_yaml_parse_error(plum: PlumRule) -> None:
    result = plum.validate("title: : :\n: :")
    assert result.ok is False
    assert any("YAML parse" in e for e in result.errors)


# ---- parse_metadata() -------------------------------------------------------


def test_parse_metadata_maps_description_and_uuid(plum: PlumRule) -> None:
    meta = plum.parse_metadata(_VALID_PLUM_RULE, info={"repo_url": "https://example/repo"})
    assert meta["format"] == "plum"
    assert meta["title"] == "alfresco"
    assert meta["original_uuid"] == "d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9"
    assert meta["version"] == "20260918T053418Z"
    assert meta["source"] == "https://example/repo"
    assert meta["license"] == "AGPL-3.0"
    assert "product:alfresco" in meta["tags"]
    assert "vendor:alfresco" in meta["tags"]


def test_parse_metadata_returns_safe_shape_on_parse_error(plum: PlumRule) -> None:
    meta = plum.parse_metadata("title: : :\n: :", info={"repo_url": "x"})
    assert meta["format"] == "plum"
    assert "Error parsing metadata" in meta["description"]
    assert meta["cve_id"] == []
    assert meta["to_string"]  # always preserves raw input


# ---- get_rule_files() -------------------------------------------------------


def test_get_rule_files_accepts_yaml_extensions(plum: PlumRule) -> None:
    assert plum.get_rule_files("tags/alfresco.yaml") is True
    assert plum.get_rule_files("tags/alfresco.yml") is True


def test_get_rule_files_rejects_other_extensions(plum: PlumRule) -> None:
    assert plum.get_rule_files("tags/alfresco.txt") is False
    assert plum.get_rule_files("tags/alfresco.json") is False


# ---- extract_rules_from_file() ----------------------------------------------


def test_extract_rules_from_single_rule_file(plum: PlumRule, tmp_path) -> None:
    p = tmp_path / "alfresco.yaml"
    p.write_text(_VALID_PLUM_RULE, encoding="utf-8")
    rules = plum.extract_rules_from_file(str(p))
    assert len(rules) == 1
    parsed_back = rules[0]
    assert "uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9" in parsed_back


def test_extract_rules_from_non_plum_yaml_is_empty(plum: PlumRule, tmp_path) -> None:
    p = tmp_path / "sigma.yaml"
    p.write_text(_SIGMA_LOOKALIKE_NOT_PLUM, encoding="utf-8")
    rules = plum.extract_rules_from_file(str(p))
    assert rules == []


def test_extract_rules_from_multi_doc_yaml(plum: PlumRule, tmp_path) -> None:
    p = tmp_path / "multi.yaml"
    p.write_text(f"{_VALID_PLUM_RULE}\n---\n{_VALID_PLUM_RULE_WITH_REFERENCES}\n", encoding="utf-8")
    rules = plum.extract_rules_from_file(str(p))
    assert len(rules) == 2
