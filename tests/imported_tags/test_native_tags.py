"""Imported tags — reading the rule author's own tags out of a rule's content
(YARA `rule X : a b`, Sigma `tags:`, …), one parser per format that carries
tags. Pure functions: no database, no request."""
import time

import pytest

from app.features.tags.imported_tags_core import extract_native_tags

YARA_WITH_TAGS = """rule ExampleRule : malware ransomware windows
{
    meta:
        author = "Example"
        tags = "apt malware"

    condition:
        true
}"""


def test_yara_header_and_meta_tags_are_merged_without_duplicates():
    assert extract_native_tags("yara", YARA_WITH_TAGS) == ["malware", "ransomware", "windows", "apt"]


@pytest.mark.parametrize("fmt, content, expected", [
    ("yara", 'private rule A : One Two { condition: true }\nglobal rule B { meta: tag = "three, one" condition: true }',
     ["one", "two", "three"]),
    ("yara", 'rule A { meta: author = "x // rule Z : fake" \n // tags = "no"\n /* rule Y : nope { */ condition: true }',
     []),
    ("nova", 'rule A\n{\n meta:\n  tags = "prompt injection"\n keywords:\n  $a = "x"\n condition:\n  keywords.$a\n}',
     ["prompt", "injection"]),
    ("sigma", "title: t\ntags:\n  - attack.execution\n  - ATTACK.T1059\n  - attack.execution\nlogsource: {}\n",
     ["attack.execution", "attack.t1059"]),
    ("kunai", "name: x\nmeta:\n  tags:\n  - os:linux\n  - persistence\ncondition: true\n", ["os:linux", "persistence"]),
    ("elastic", '[rule]\nname = "x"\ntags = ["Domain: Endpoint", "OS: Linux"]\n', ["domain:endpoint", "os:linux"]),
    ("splunk", "name: x\ntags:\n  analytic_story:\n    - Ransomware\n    - Log4Shell\n  asset_type: Endpoint\n",
     ["ransomware", "log4shell"]),
    ("atr", "title: x\ntags:\n  category: prompt-injection\n  subcategory: persona\n  confidence: high\n",
     ["prompt-injection", "persona"]),
    ("crs", "SecRule ARGS \"@rx x\" \"id:1,tag:'attack-sqli',tag:'OWASP_CRS',pass\"", ["attack-sqli", "owasp_crs"]),
    ("suricata", 'alert http any any -> any any (msg:"x"; metadata:created_at 2024_01_01, tag Phishing, tag none; sid:1;)',
     ["phishing"]),
    ("nse", 'categories = {"discovery", "safe"}', ["discovery", "safe"]),
    ("wazuh", "<rule id='1'><group>authentication_failed,pci_dss_10.2.4,</group></rule>",
     ["authentication_failed", "pci_dss_10.2.4"]),
    ("kql", "// Tags: identity, brute force\nSigninLogs | take 1", ["identity", "brute force"]),
])
def test_each_format_yields_its_tags(fmt, content, expected):
    assert extract_native_tags(fmt, content) == expected


@pytest.mark.parametrize("content, expected", [
    ('rule A { meta: Tags = "exploit: cve-2017-11882" condition: true }', ["exploit:cve-2017-11882"]),
    ('rule A { meta: tags = "Family: Rhadamanthys, apt malware" condition: true }',
     ["family:rhadamanthys", "apt", "malware"]),
    ('rule A { meta: tags = "exploit :cve-1  exploit:cve-1 x:" condition: true }', ["exploit:cve-1"]),
])
def test_a_namespaced_value_stays_one_tag_whatever_the_spacing(content, expected):
    assert extract_native_tags("yara", content) == expected


@pytest.mark.parametrize("fmt, content", [("zeek", "event x() {}"), ("sigma", "not: [valid"), ("yara", ""),
                                          (None, "rule a : b { condition: true }"), ("yara", None)])
def test_no_tags_from_a_format_without_tags_or_broken_content(fmt, content):
    assert extract_native_tags(fmt, content) == []


@pytest.mark.parametrize("content", ["rule a : b" + " " * 200_000, "rule a : b" + "\t \n" * 100_000])
def test_extraction_stays_linear_on_crafted_content(content):
    """Runs on every new rule: a long run of whitespace after a tag list
    with no "{" used to backtrack quadratically (33 s for 200k spaces)."""
    start = time.monotonic()

    extract_native_tags("yara", content)

    assert time.monotonic() - start < 2
