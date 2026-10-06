from app import db
from app.core.db_class.db import Rule, RuleRelation
from app.features.rule_relation.rule_relation_core import resolve_and_link_relations


def _make_rule(title, fmt='wazuh', original_uuid=None, source=None):
    rule = Rule(title=title, format=fmt, to_string=f'<rule id="{original_uuid}"></rule>',
                original_uuid=original_uuid, source=source, is_deleted=False, vote_up=0, vote_down=0)
    db.session.add(rule)
    db.session.commit()
    return rule


class _FakeFormat:
    """Stands in for a real RuleType subclass — extract_relations is the
    only method resolve_and_link_relations calls on it."""
    def __init__(self, relations):
        self._relations = relations

    def extract_relations(self, content, metadata):
        return self._relations


def test_target_ref_resolves_against_existing_rule_in_db(app):
    with app.app_context():
        base = _make_rule('Base rule', original_uuid='100', source='https://example.com/repo')
        dependent = _make_rule('Dependent rule', original_uuid='200', source='https://example.com/repo')

        fmt = _FakeFormat([{'kind': 'target_ref', 'target_identifier': '100', 'relation_type': 'if_sid'}])
        metadata = {'format': 'wazuh', 'source': 'https://example.com/repo'}

        resolve_and_link_relations(fmt, dependent.to_string, metadata, dependent, correlation_seen={})

        rel = RuleRelation.query.filter_by(source_rule_id=dependent.id, target_rule_id=base.id).first()
        assert rel is not None
        assert rel.relation_type == 'if_sid'
        assert rel.source == 'auto'
        assert rel.note == '100'


def test_target_ref_silently_skipped_when_target_not_found(app):
    with app.app_context():
        dependent = _make_rule('Orphan reference', original_uuid='999', source='https://example.com/repo')
        fmt = _FakeFormat([{'kind': 'target_ref', 'target_identifier': 'does-not-exist', 'relation_type': 'if_sid'}])
        metadata = {'format': 'wazuh', 'source': 'https://example.com/repo'}

        # Must not raise, and must not create anything.
        resolve_and_link_relations(fmt, dependent.to_string, metadata, dependent, correlation_seen={})
        assert RuleRelation.query.filter_by(source_rule_id=dependent.id).count() == 0


def test_correlation_key_links_rules_pairwise_within_the_same_batch(app):
    with app.app_context():
        rule_a = _make_rule('Rule A', fmt='kunai', original_uuid='a', source='https://example.com/kunai')
        rule_b = _make_rule('Rule B', fmt='kunai', original_uuid='b', source='https://example.com/kunai')
        rule_c = _make_rule('Rule C', fmt='kunai', original_uuid='c', source='https://example.com/kunai')

        shared_hash = 'deadbeef' * 8
        fmt = _FakeFormat([{'kind': 'correlation_key', 'key': shared_hash, 'relation_type': 'correlation_hash'}])
        metadata = {'format': 'kunai', 'source': 'https://example.com/kunai'}
        correlation_seen = {}

        # Simulate the three rules being processed one after another in the
        # same import batch, sharing one correlation_seen dict — same as a
        # real import pipeline call site would.
        resolve_and_link_relations(fmt, rule_a.to_string, metadata, rule_a, correlation_seen)
        resolve_and_link_relations(fmt, rule_b.to_string, metadata, rule_b, correlation_seen)
        resolve_and_link_relations(fmt, rule_c.to_string, metadata, rule_c, correlation_seen)

        # Each already-seen peer links to the newly-processed rule
        # (a -> b, a -> c, b -> c) — 3 edges total for 3 mutually-correlated
        # rules. Direction doesn't matter for display (both sides show up
        # via outgoing/incoming), only that every pair got linked once.
        all_relations = RuleRelation.query.filter_by(relation_type='correlation_hash').all()
        assert len(all_relations) == 3
        pairs = {(r.source_rule_id, r.target_rule_id) for r in all_relations}
        assert (rule_a.id, rule_b.id) in pairs
        assert (rule_a.id, rule_c.id) in pairs
        assert (rule_b.id, rule_c.id) in pairs


def test_no_relations_reported_is_a_no_op(app):
    with app.app_context():
        rule = _make_rule('Solo rule', original_uuid='1', source='https://example.com/repo')
        fmt = _FakeFormat([])
        resolve_and_link_relations(fmt, rule.to_string, {'format': 'wazuh', 'source': 'x'}, rule, correlation_seen={})
        assert RuleRelation.query.count() == 0
