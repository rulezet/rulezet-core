"""Rule formats — syntax: every format accepts a valid rule and refuses an
invalid one with an error message, through the same entry point the create /
edit / import paths use (verify_syntax_rule_by_format)."""
import shutil

import pytest

from app.features.rule.rule_format.main_format import verify_syntax_rule_by_format
from tests.helpers.formats import SAMPLES, registered_formats

FORMATS = sorted(SAMPLES)


def test_every_registered_format_has_samples(app):
    assert set(registered_formats()) == set(SAMPLES)


@pytest.mark.parametrize("fmt", FORMATS)
def test_valid_rule_is_accepted(fmt, app):
    ok, error = verify_syntax_rule_by_format({"format": fmt, "to_string": SAMPLES[fmt].valid})

    assert ok, error


@pytest.mark.parametrize("fmt", FORMATS)
def test_invalid_rule_is_refused_with_a_message(fmt, app):
    if fmt == "nse" and shutil.which("luac") is None:
        pytest.skip("NSE syntax is checked with `luac`, not installed here — every script passes")

    ok, error = verify_syntax_rule_by_format({"format": fmt, "to_string": SAMPLES[fmt].invalid})

    assert not ok and error


@pytest.mark.parametrize("fmt", ["YARA", "Sigma"])
def test_format_name_is_case_insensitive(fmt, app):
    ok, error = verify_syntax_rule_by_format({"format": fmt, "to_string": SAMPLES[fmt.lower()].valid})

    assert ok, error


def test_format_name_with_surrounding_spaces_is_understood(app):
    ok, error = verify_syntax_rule_by_format({"format": " yara ", "to_string": SAMPLES["yara"].valid})

    assert ok, error


@pytest.mark.parametrize("rule_dict, message", [
    ({"format": "not-a-format", "to_string": "x"}, "not supported"),
    ({"format": "no format", "to_string": "x"}, "not supported"),
    ({"format": "", "to_string": "x"}, "Missing rule format"),
    ({"format": None, "to_string": "x"}, "Missing rule format"),
    ({"to_string": "x"}, "Missing rule format"),
    ({"format": "yara"}, "empty"),
    ({"format": "yara", "to_string": ""}, "empty"),
])
def test_unusable_input_is_refused_without_crashing(rule_dict, message, app):
    ok, error = verify_syntax_rule_by_format(rule_dict)

    assert not ok and message in error


@pytest.mark.parametrize("content", [
    'SecRule REQUEST_URI',                                   # no operator, no actions
    'SecRule REQUEST_URI "@rx /x" "id:1,phase:1,deny',       # unterminated quote
])
def test_incomplete_crs_rule_is_refused(content, app):
    ok, _ = verify_syntax_rule_by_format({"format": "crs", "to_string": content})

    assert not ok


def test_yara_rule_using_a_module_gets_its_import_added(app):
    from tests.helpers.formats import registered_formats as formats
    yara = formats()["yara"]

    result = yara.validate("rule p { condition: pe.number_of_sections > 1 }")

    assert result.ok and result.normalized_content.startswith('import "pe"')
