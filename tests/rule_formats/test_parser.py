"""Rule formats — parser: what each format extracts from a rule
(parse_metadata), which files it imports (get_rule_files) and how it splits a
file holding several rules (extract_rules_from_file)."""
import json

import pytest

from app.features.rule.rule_format.main_format import verify_syntax_rule_by_format
from tests.helpers.formats import INFO, SAMPLES, registered_formats

FORMATS = sorted(SAMPLES)
SPLITTABLE = [f for f in FORMATS if SAMPLES[f].two_rules]


@pytest.fixture
def formats(app):
    return registered_formats()


def _metadata(rule_type, content):
    validation = rule_type.validate(content)
    return rule_type.parse_metadata(content, dict(INFO), validation)


def _extract(rule_type, tmp_path, content, filename="rules"):
    path = tmp_path / filename
    path.write_text(content)
    return rule_type.extract_rules_from_file(str(path))


# ── parse_metadata ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fmt", FORMATS)
def test_metadata_has_the_title_and_the_format(fmt, formats):
    metadata = _metadata(formats[fmt], SAMPLES[fmt].valid)

    assert metadata["format"] == fmt
    assert metadata["title"] == SAMPLES[fmt].title
    assert metadata["to_string"].strip()


@pytest.mark.parametrize("fmt", FORMATS)
def test_metadata_cve_field_is_a_json_list(fmt, formats):
    """cve_id is stored as a JSON list on the rule — every format must give one."""
    metadata = _metadata(formats[fmt], SAMPLES[fmt].valid)

    assert isinstance(json.loads(metadata["cve_id"]), list)


def test_yara_metadata_reads_the_meta_block_and_finds_the_cve(formats):
    metadata = _metadata(formats["yara"], SAMPLES["yara"].valid)

    assert metadata["description"] == "Detects CVE-2021-44228 marker"
    assert metadata["author"] == "Tester" and metadata["version"] == "2" and metadata["original_uuid"] == "1234"
    assert json.loads(metadata["cve_id"]) == ["CVE-2021-44228"]


def test_suricata_metadata_uses_sid_and_rev(formats):
    metadata = _metadata(formats["suricata"], SAMPLES["suricata"].valid)

    assert metadata["original_uuid"] == "1000001" and metadata["version"] == "2"


def test_kql_metadata_finds_a_cve_in_the_header(formats):
    content = "// Title: Failed logons\n// Description: Detects CVE-2024-21412 stuff\nSecurityEvent\n| where EventID == 4625\n"

    metadata = _metadata(formats["kql"], content)

    assert json.loads(metadata["cve_id"]) == ["CVE-2024-21412"]


# ── get_rule_files ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fmt", FORMATS)
def test_imports_its_own_files_only(fmt, formats):
    accepted, ignored = SAMPLES[fmt].files

    assert formats[fmt].get_rule_files(accepted)
    assert not formats[fmt].get_rule_files(ignored)


# ── extract_rules_from_file ───────────────────────────────────────────────────

@pytest.mark.parametrize("fmt", SPLITTABLE)
def test_a_file_with_two_rules_gives_two_valid_rules(fmt, formats, tmp_path):
    rules = _extract(formats[fmt], tmp_path, SAMPLES[fmt].two_rules)

    assert len(rules) == 2
    for content in rules:
        ok, error = verify_syntax_rule_by_format({"format": fmt, "to_string": content})
        assert ok, error


@pytest.mark.parametrize("fmt", ["suricata", "sagan"])
def test_commented_out_rules_are_not_imported(fmt, formats, tmp_path):
    content = SAMPLES[fmt].two_rules + '# alert tcp any any -> any any (msg:"disabled"; sid:3; rev:1;)\n'

    rules = _extract(formats[fmt], tmp_path, content)

    assert len(rules) == 2
    assert not any("disabled" in r for r in rules)


def test_wazuh_file_with_several_groups_imports_every_rule(formats, tmp_path):
    content = ('<group name="a,"><rule id="100001" level="3"><description>a</description></rule></group>\n'
               '<group name="b,"><rule id="100002" level="5"><description>b</description></rule></group>\n')

    rules = _extract(formats["wazuh"], tmp_path, content, "local_rules.xml")

    assert len(rules) == 2


def test_sigma_multi_document_file_imports_every_rule(formats, tmp_path):
    one = SAMPLES["sigma"].valid
    content = one + "---\n" + one.replace("title: Minimal", "title: Other").replace("4624", "4625")

    rules = _extract(formats["sigma"], tmp_path, content, "rules.yml")

    assert len(rules) == 2


def test_yara_extraction_keeps_private_and_global_modifiers(formats, tmp_path):
    content = 'private rule helper { condition: true }\nglobal rule gate { condition: true }\n'

    rules = _extract(formats["yara"], tmp_path, content, "rules.yar")

    assert any(r.startswith("private rule helper") for r in rules)
    assert any(r.startswith("global rule gate") for r in rules)


def test_nova_rule_mentioning_the_word_rule_is_not_split(formats, tmp_path):
    content = 'rule A\n{\n meta:\n  description = "the rule is a rule"\n keywords:\n  $a = "x"\n condition:\n  keywords.$a\n}\n'

    rules = _extract(formats["nova"], tmp_path, content, "rules.nov")

    assert len(rules) == 1


def test_sigma_schema_is_found_whatever_the_working_directory(app, tmp_path, monkeypatch):
    from app.features.rule.rule_format.available_format.sigma_format import SigmaRule
    monkeypatch.chdir(tmp_path)

    assert SigmaRule().schema is not None


def test_sigma_rule_collection_with_a_global_part_stays_whole(formats, tmp_path):
    content = ("action: global\ntitle: Shared\nlogsource:\n  product: windows\n---\n"
               "detection:\n  sel:\n    EventID: 1\n  condition: sel\n")

    rules = _extract(formats["sigma"], tmp_path, content, "collection.yml")

    assert rules == [content]
