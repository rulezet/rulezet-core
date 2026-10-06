"""One sample set per rule format — used by tests/rule_formats/.

Every format registered in Rulezet (a RuleType subclass in
app/features/rule/rule_format/available_format/) must have an entry here:
tests/rule_formats/test_syntax.py fails otherwise, so a new format can't be
added without its tests.

    valid       content the format's validate() accepts
    invalid     content it refuses
    title       what parse_metadata() extracts as the title of `valid`
    files       (a file name it imports, one it ignores)
    two_rules   a file holding two rules, split by extract_rules_from_file()
"""
from dataclasses import dataclass

from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import RuleType, load_all_rule_formats


@dataclass(frozen=True)
class FormatSamples:
    valid: str
    invalid: str
    title: str
    files: tuple
    two_rules: str


ATR = """id: ATR-2026-00001
title: Minimal ATR rule
severity: high
tags:
  category: prompt-injection
agent_source:
  type: llm_io
detection:
  conditions:
    - field: user_input
      operator: contains
      value: ignore previous instructions
"""

PLUM = """name: alfresco
description: Detect Alfresco
uuid: d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9
query: http_favicon_mmhash:1333537166
tags:
- proto:http
- product:alfresco
- vendor:alfresco
version: 20260918T053418Z
"""

SPLUNK = """name: Minimal Splunk detection
id: ea688274-9c06-4473-b951-e4cb7a5d7a45
description: Detects TOR traffic.
search: '| tstats count FROM datamodel=Network_Traffic WHERE All_Traffic.app=tor'
status: production
type: Hunting
security_domain: network
"""
_SPLUNK_FILE_RULE = ("name: A\nid: x1\ndescription: d\nsearch: s\nhow_to_implement: h\n"
                     "known_false_positives: k\nstatus: production\ntype: Hunting\nsecurity_domain: network\n")

KUNAI = """name: detect.minimal
matches:
  $a: .data.exe.path == '/usr/bin/curl'
condition: $a
"""

NOVA = 'rule A\n{\n meta:\n  description = "a"\n keywords:\n  $a = "x"\n condition:\n  keywords.$a\n}\n'

SAMPLES = {
    "atr": FormatSamples(
        valid=ATR,
        invalid="id: NOT-AN-ATR-ID\ntitle: x\n",
        title="Minimal ATR rule",
        files=("rule.yaml", "rule.yar"),
        two_rules=ATR + "---\n" + ATR.replace("00001", "00002").replace("title: Minimal ATR rule", "title: B"),
    ),
    "crs": FormatSamples(
        valid='SecRule REQUEST_URI "@rx /x" "id:1003,phase:1,deny"',
        invalid="this is not a rule",
        title="CRS Rule 1003",
        files=("rules.conf", "rules.yaml"),
        two_rules='SecRule REQUEST_URI "@rx /a" "id:1001,phase:1,deny"\nSecRule ARGS "@rx b" "id:1002,phase:2,deny"\n',
    ),
    "elastic": FormatSamples(
        valid='''[rule]
name = "Minimal Elastic rule"
rule_id = "d3851f38-ce10-4d13-a056-99fe711e6bcc"
description = "Detects curl"
type = "query"
language = "kuery"
query = "process.name : curl"
severity = "low"
risk_score = 21
''',
        invalid='[metadata]\nmaturity = "production"\n',
        title="Minimal Elastic rule",
        files=("rule.toml", "rule.yml"),
        two_rules="",   # one rule per file
    ),
    "kql": FormatSamples(
        valid="// Title: Failed logons\nSecurityEvent\n| where EventID == 4625\n",
        invalid="| where x == 1",
        title="Failed logons",
        files=("query.kql", "query.txt"),
        two_rules="",   # one query per file
    ),
    "kunai": FormatSamples(
        valid=KUNAI,
        invalid="name: incomplete\n",
        title="detect.minimal",
        files=("rule.kun", "rule.toml"),
        two_rules=KUNAI + "---\n" + KUNAI.replace("detect.minimal", "detect.other"),
    ),
    "nova": FormatSamples(
        valid=NOVA,
        invalid='rule Bad\n{\n    keywords:\n        $a = "x"\n    condition:\n        keywords.$a\n}',
        title="A",
        files=("rule.nov", "rule.nova"),
        two_rules=NOVA + "\n" + NOVA.replace("rule A", "rule B"),
    ),
    "nse": FormatSamples(
        valid='''-- http-minimal.nse
description = [[Minimal NSE script.]]
author = "Tester"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"safe", "discovery"}
portrule = function(host, port) return port.number == 80 end
action = function(host, port) return "ok" end
''',
        invalid="action = function( end end end",
        title="http-minimal",
        files=("http-minimal.nse", "http-minimal.lua"),
        two_rules="",   # one script per file
    ),
    "plum": FormatSamples(
        valid=PLUM,
        invalid="name: incomplete\ndescription: Missing several required fields\n",
        title="alfresco",
        files=("rule.yaml", "rule.kun"),
        two_rules=PLUM + "---\n" + PLUM.replace("alfresco", "airwatch").replace(
            "d313f1e4-bbb6-559a-bc5b-20a5f4a9e2a9", "36fb043d-bf7d-50c2-8b48-38ab6ff8e76c"),
    ),
    "sagan": FormatSamples(
        valid=('alert syslog $EXTERNAL_NET any -> $HOME_NET any (msg:"[OSSEC] Ossec started"; '
               'content:"Ossec started"; classtype:system-event; program:ossec; sid:5000287; rev:1;)'),
        invalid='alert altemplate any any -> any any (msg:"t"; sid:1; rev:1;)',
        title="[OSSEC] Ossec started",
        files=("local.rules", "local.conf"),
        two_rules=('alert syslog any any -> any any (msg:"a"; program:x; sid:1; rev:1;)\n'
                   'alert any any any -> any any (msg:"b"; sid:2; rev:1;)\n'),
    ),
    "sigma": FormatSamples(
        valid="title: Minimal\nlogsource:\n  product: windows\ndetection:\n  selection:\n    EventID: 4624\n  condition: selection\n",
        invalid="title: Missing logsource\ndetection:\n  selection:\n    EventID: 1\n  condition: selection\n",
        title="Minimal",
        files=("rule.yml", "rule.json"),
        two_rules=("- title: A\n  logsource:\n    product: windows\n  detection:\n    sel:\n      EventID: 1\n    condition: sel\n"
                   "- title: B\n  logsource:\n    product: windows\n  detection:\n    sel:\n      EventID: 2\n    condition: sel\n"),
    ),
    "splunk": FormatSamples(
        valid=SPLUNK,
        invalid="name: x\nid: y\n",
        title="Minimal Splunk detection",
        files=("detection.yml", "detection.toml"),
        two_rules=_SPLUNK_FILE_RULE + "---\n" + _SPLUNK_FILE_RULE.replace("name: A", "name: B"),
    ),
    "suricata": FormatSamples(
        valid='alert tcp any any -> any any (msg:"Minimal rule"; content:"x"; sid:1000001; rev:2;)',
        invalid='alert foo any any -> any any (msg:"t"; sid:1; rev:1;)',
        title="Minimal rule",
        files=("local.rules", "local.conf"),
        two_rules=('alert tcp any any -> any any (msg:"a"; sid:1; rev:1;)\n'
                   'alert udp any any -> any any (msg:"b"; sid:2; rev:1;)\n'),
    ),
    "wazuh": FormatSamples(
        valid='<rule id="100002" level="5"><description>normal</description></rule>',
        invalid='<rule id="1"><description>x</rule>',
        title="normal",
        files=("local_rules.xml", "local_rules.yml"),
        two_rules=('<group name="local,"><rule id="100001" level="3"><description>a</description></rule>'
                   '<rule id="100002" level="5"><if_sid>100001</if_sid><description>b</description></rule></group>'),
    ),
    "yara": FormatSamples(
        valid='''rule minimal_yara
{
    meta:
        description = "Detects CVE-2021-44228 marker"
        author = "Tester"
        version = "2"
        id = "1234"
    strings:
        $a = "jndi:ldap"
    condition:
        $a
}''',
        invalid="rule broken { condition: }",
        title="minimal_yara",
        files=("rules.yar", "rules.yr"),
        two_rules='rule a { strings: $s = "}" condition: $s }\nrule b { condition: true }\n',
    ),
    "zeek": FormatSamples(
        valid='event zeek_init()\n\t{\n\tprint "hello";\n\t}\n',
        invalid="event zeek_init( {",
        title="zeek_init",
        files=("detect.zeek", "detect.sig"),
        two_rules='event zeek_init()\n\t{\n\tprint "a";\n\t}\n\nfunction f(x: count): count\n\t{\n\treturn x;\n\t}\n',
    ),
}

# What the importer passes to parse_metadata() as `info`.
INFO = {"license": "MIT", "author": "Tester", "repo_url": "https://example.com/repo"}


def registered_formats():
    """{format name: RuleType instance} for every format Rulezet knows."""
    load_all_rule_formats()
    return {cls().format.lower(): cls() for cls in RuleType.__subclasses__()}
