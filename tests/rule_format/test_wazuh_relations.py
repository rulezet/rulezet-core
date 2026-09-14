from app.features.rule.rule_format.available_format.wazuh_format import WazuhRule

RULE_WITH_IF_SID = """<rule id="100200" level="10">
    <if_sid>100</if_sid>
    <if_matched_sid>200</if_matched_sid>
    <description>Suspicious follow-up activity</description>
</rule>
"""

RULE_WITH_IF_GROUP = """<rule id="100300" level="5">
    <if_group>authentication_failed</if_group>
    <description>Auth failure correlation</description>
</rule>
"""

RULE_WITH_NOTHING = """<rule id="100400" level="3">
    <description>Standalone rule</description>
</rule>
"""


def test_extract_relations_reads_if_sid_and_if_matched_sid_as_target_refs():
    w = WazuhRule()
    relations = w.extract_relations(RULE_WITH_IF_SID, {})
    kinds = {(r['relation_type'], r['target_identifier']) for r in relations if r['kind'] == 'target_ref'}
    assert ('if_sid', '100') in kinds
    assert ('if_matched_sid', '200') in kinds


def test_extract_relations_reads_if_group_as_correlation_key():
    w = WazuhRule()
    relations = w.extract_relations(RULE_WITH_IF_GROUP, {})
    assert len(relations) == 1
    assert relations[0]['kind'] == 'correlation_key'
    assert relations[0]['relation_type'] == 'if_group'
    assert relations[0]['key'] == 'if_group:authentication_failed'


def test_extract_relations_empty_for_rule_with_no_correlation():
    w = WazuhRule()
    assert w.extract_relations(RULE_WITH_NOTHING, {}) == []
