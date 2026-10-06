from app.features.rule.rule_format.available_format.kunai_format import KunaiRule

# Real Kunai composition example (dependency + detection + FP-exclusion
# detection), per https://why.kunai.rocks/docs/next/advanced/rule_syntax_reference
SHARED_DEPENDENCY_RULE = """\
name: shared.network.activity
type: dependency
matches:
  $external_ip: .data.dst.public == true
  $http: .data.dst.port == 80
  $https: .data.dst.port == 443
condition: $external_ip and any of $http
"""

DETECTION_USING_DEPENDENCY_RULE = """\
name: detect.suspicious.connection
type: detection
matches:
  $shared: rule(shared.network.activity)
  $trusted: .data.exe.path ~= '^/usr/(bin|sbin)/'
condition: $shared and not $trusted
"""

EXCLUSION_DETECTION_RULE = """\
name: suspicious.connection.exclude.false.positives
type: detection
matches:
  $broad_match: rule(detect.suspicious.connection)
  $whitelist: .data.exe.path == "/usr/bin/known-good"
condition: $broad_match and not $whitelist
"""

BOTH_RULES = SHARED_DEPENDENCY_RULE + "\n---\n\n" + DETECTION_USING_DEPENDENCY_RULE

# A rule with meta/match-on, the original example shape used to seed this format.
KILL_RULE = """\
name: kill.critical.service
meta:
    tags: [ 'os:linux' ]
    authors: [ qjerome ]
    attack: [ T1489 ]
    comments:
        - detect kill attempt on critical services
match-on:
    events:
        kunai: [ kill ]
matches:
    $wl0: .data.exe.path ~= '{{systemd-dir}}/systemd'
    $wl1: .data.exe.path == '/usr/sbin/sshd'
    $s1: .data.target.exe.path == '/usr/sbin/sshd'
    $s2: .data.target.exe.path == '/usr/lib/openssh/sftp-server'
condition: none of $wl and any of $s
severity: 9
"""

SIGMA_LOOKALIKE = """\
title: Something
logsource:
    category: process_creation
detection:
    selection:
        Image: '*\\\\cmd.exe'
    condition: selection
"""


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def test_get_rule_files_matches_kun_and_yaml_extensions():
    k = KunaiRule()
    assert k.get_rule_files('rules/kill.kun') is True
    assert k.get_rule_files('rules/kill.yml') is True
    assert k.get_rule_files('rules/kill.yaml') is True
    assert k.get_rule_files('rules/kill.txt') is False


def test_detect_distinguishes_kunai_from_sigma():
    k = KunaiRule()
    assert k.detect(KILL_RULE) is True
    assert k.detect(SIGMA_LOOKALIKE) is False


def test_detect_works_for_a_dependency_rule_with_no_meta_or_match_on():
    """A type: dependency rule legitimately has neither meta: nor
    match-on: — detect() must not require them."""
    k = KunaiRule()
    assert k.detect(SHARED_DEPENDENCY_RULE) is True


def test_extract_rules_from_file_splits_multi_document_stream(tmp_path):
    k = KunaiRule()
    path = _write(tmp_path, 'both.kun', BOTH_RULES)
    rules = k.extract_rules_from_file(path)
    assert len(rules) == 2


def test_validate_requires_core_fields_only():
    k = KunaiRule()
    assert k.validate(KILL_RULE).ok is True
    assert k.validate(SHARED_DEPENDENCY_RULE).ok is True   # no meta/match-on required
    assert k.validate("name: incomplete\n").ok is False    # missing matches/condition


def test_validate_rejects_unknown_type():
    k = KunaiRule()
    result = k.validate("name: x\ntype: bogus\nmatches: {a: 'b'}\ncondition: a\n")
    assert result.ok is False


def test_parse_metadata_uses_name_as_title_and_identifier():
    k = KunaiRule()
    vr = k.validate(KILL_RULE)
    meta = k.parse_metadata(KILL_RULE, {'repo_url': 'https://github.com/kunai-project/community-rules'}, vr)
    assert meta['title'] == 'kill.critical.service'
    assert meta['original_uuid'] == 'kill.critical.service'
    assert meta['format'] == 'kunai'
    assert meta['author'] == 'qjerome'
    assert meta['source'] == 'https://github.com/kunai-project/community-rules'


def test_parse_metadata_captures_rule_type():
    k = KunaiRule()
    vr = k.validate(SHARED_DEPENDENCY_RULE)
    meta = k.parse_metadata(SHARED_DEPENDENCY_RULE, {}, vr)
    assert meta['kunai_rule_type'] == 'dependency'


def test_extract_relations_finds_rule_composition_reference():
    """The real Kunai relation mechanism: matches: { $x: rule(other.name) }
    — an explicit, directional dependency on another rule by name."""
    k = KunaiRule()
    vr = k.validate(DETECTION_USING_DEPENDENCY_RULE)
    meta = k.parse_metadata(DETECTION_USING_DEPENDENCY_RULE, {}, vr)
    relations = k.extract_relations(DETECTION_USING_DEPENDENCY_RULE, meta)
    assert relations == [{'kind': 'target_ref', 'target_identifier': 'shared.network.activity', 'relation_type': 'rule_ref'}]


def test_extract_relations_finds_multiple_distinct_references():
    content = (
        "name: composed\n"
        "type: detection\n"
        "matches:\n"
        "  $a: rule(first.dep)\n"
        "  $b: rule(second.dep)\n"
        "condition: $a and $b\n"
    )
    k = KunaiRule()
    relations = k.extract_relations(content, {})
    targets = {r['target_identifier'] for r in relations}
    assert targets == {'first.dep', 'second.dep'}


def test_extract_relations_empty_when_no_rule_reference_present():
    k = KunaiRule()
    vr = k.validate(KILL_RULE)
    meta = k.parse_metadata(KILL_RULE, {}, vr)
    assert k.extract_relations(KILL_RULE, meta) == []


def test_multi_document_stream_does_not_imply_a_relation_by_itself():
    """Two independent rules sitting in the same ----separated file (with
    no rule() reference between them) must NOT produce any relation —
    the --- separator is just "a batch of rules in one file", not a
    relationship marker."""
    k = KunaiRule()
    unrelated_a = "name: a\nmatches: {x: '.data.a == 1'}\ncondition: x\n"
    unrelated_b = "name: b\nmatches: {y: '.data.b == 2'}\ncondition: y\n"
    assert k.extract_relations(unrelated_a, {}) == []
    assert k.extract_relations(unrelated_b, {}) == []
