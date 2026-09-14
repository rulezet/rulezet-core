from app import db
from app.core.db_class.db import Rule, RuleRelation
from app.features.rule_relation import rule_relation_core as relation_core


def _make_rule(title, is_deleted=False):
    rule = Rule(title=title, format='yara', to_string=f'rule {title.replace(" ", "_")} {{ condition: true }}',
                is_deleted=is_deleted, vote_up=0, vote_down=0)
    db.session.add(rule)
    db.session.commit()
    return rule


def test_add_relation_creates_row(app):
    with app.app_context():
        a, b = _make_rule('A'), _make_rule('B')
        relation, status = relation_core.add_relation(a.id, b.id, 'depends_on')
        assert status == 'created'
        assert relation.source_rule_id == a.id
        assert relation.target_rule_id == b.id
        assert relation.relation_type == 'depends_on'
        assert relation.source == 'manual'


def test_add_relation_rejects_self_link(app):
    with app.app_context():
        a = _make_rule('SelfLink')
        relation, status = relation_core.add_relation(a.id, a.id, 'references')
        assert status == 'self_link_rejected'
        assert relation is None


def test_add_relation_rejects_invalid_manual_type(app):
    with app.app_context():
        a, b = _make_rule('A2'), _make_rule('B2')
        relation, status = relation_core.add_relation(a.id, b.id, 'not_a_real_type')
        assert status == 'invalid_relation_type'
        assert relation is None


def test_add_relation_allows_auto_type_outside_manual_vocabulary(app):
    with app.app_context():
        a, b = _make_rule('A3'), _make_rule('B3')
        relation, status = relation_core.add_relation(a.id, b.id, 'if_sid', source='auto')
        assert status == 'created'
        assert relation.relation_type == 'if_sid'
        assert relation.source == 'auto'


def test_add_relation_is_idempotent_per_pair_and_type(app):
    with app.app_context():
        a, b = _make_rule('A4'), _make_rule('B4')
        first, status1 = relation_core.add_relation(a.id, b.id, 'related')
        second, status2 = relation_core.add_relation(a.id, b.id, 'related')
        assert status1 == 'created'
        assert status2 == 'already_exists'
        assert first.id == second.id
        # A different relation_type between the same pair is a distinct edge.
        third, status3 = relation_core.add_relation(a.id, b.id, 'variant_of')
        assert status3 == 'created'
        assert third.id != first.id


def test_add_relation_rejects_missing_or_deleted_target(app):
    with app.app_context():
        a = _make_rule('A5')
        deleted = _make_rule('Deleted', is_deleted=True)

        _, status = relation_core.add_relation(a.id, 999999, 'references')
        assert status == 'target_not_found'

        _, status = relation_core.add_relation(a.id, deleted.id, 'references')
        assert status == 'target_not_found'


def test_add_relation_enforces_manual_cap_but_not_auto(app):
    with app.app_context():
        source = _make_rule('Source')
        targets = [_make_rule(f'Target {i}') for i in range(relation_core.MAX_MANUAL_RELATIONS_PER_RULE + 2)]

        created = 0
        last_status = None
        for t in targets:
            _, last_status = relation_core.add_relation(source.id, t.id, 'references')
            if last_status == 'created':
                created += 1

        assert created == relation_core.MAX_MANUAL_RELATIONS_PER_RULE
        assert last_status == 'limit_reached'
        assert RuleRelation.query.filter_by(source_rule_id=source.id, source='manual').count() == relation_core.MAX_MANUAL_RELATIONS_PER_RULE

        # Auto-detected links (import-time) are never capped.
        extra_target = _make_rule('AutoTarget')
        _, auto_status = relation_core.add_relation(source.id, extra_target.id, 'if_sid', source='auto')
        assert auto_status == 'created'


def test_remove_relation(app):
    with app.app_context():
        a, b = _make_rule('A6'), _make_rule('B6')
        relation, _ = relation_core.add_relation(a.id, b.id, 'references')
        assert relation_core.remove_relation(relation.uuid) is True
        assert RuleRelation.query.filter_by(uuid=relation.uuid).first() is None
        assert relation_core.remove_relation(relation.uuid) is False


def test_get_relations_for_rule_both_directions(app):
    with app.app_context():
        a, b, c = _make_rule('A7'), _make_rule('B7'), _make_rule('C7')
        relation_core.add_relation(a.id, b.id, 'references')
        relation_core.add_relation(c.id, a.id, 'depends_on')

        result = relation_core.get_relations_for_rule(a.id)
        assert len(result['outgoing']) == 1
        assert result['outgoing'][0]['rule_id'] == b.id
        assert result['outgoing'][0]['relation_type'] == 'references'
        assert len(result['incoming']) == 1
        assert result['incoming'][0]['rule_id'] == c.id
        assert result['incoming'][0]['relation_type'] == 'depends_on'


def test_get_relations_for_rule_hides_soft_deleted_other_side(app):
    with app.app_context():
        a, b = _make_rule('A8'), _make_rule('B8')
        relation_core.add_relation(a.id, b.id, 'references')

        b.is_deleted = True
        db.session.commit()

        result = relation_core.get_relations_for_rule(a.id)
        assert result['outgoing'] == []
        # The row itself is untouched, not deleted.
        assert RuleRelation.query.filter_by(source_rule_id=a.id).count() == 1


def test_count_relations_for_rule_sums_both_directions(app):
    with app.app_context():
        a, b, c = _make_rule('A10'), _make_rule('B10'), _make_rule('C10')
        relation_core.add_relation(a.id, b.id, 'references')
        relation_core.add_relation(c.id, a.id, 'depends_on')
        assert relation_core.count_relations_for_rule(a.id) == 2
        assert relation_core.count_relations_for_rule(b.id) == 1


def test_get_relations_page_paginates_and_filters_soft_deleted(app):
    with app.app_context():
        source = _make_rule('PageSource')
        targets = [_make_rule(f'PageTarget {i}') for i in range(5)]
        for t in targets:
            relation_core.add_relation(source.id, t.id, 'references')

        targets[0].is_deleted = True
        db.session.commit()

        page1 = relation_core.get_relations_page(source.id, 'outgoing', page=1, per_page=2)
        assert page1['total'] == 4  # 5 created, 1 soft-deleted other side excluded
        assert len(page1['items']) == 2
        assert page1['total_pages'] == 2

        page2 = relation_core.get_relations_page(source.id, 'outgoing', page=2, per_page=2)
        assert len(page2['items']) == 2


def test_hard_delete_wipes_relations_via_wipe_rule_children(app):
    from app.features.rule import rule_core as RuleModel
    with app.app_context():
        a, b = _make_rule('A9'), _make_rule('B9')
        relation, _ = relation_core.add_relation(a.id, b.id, 'references')
        relation_uuid = relation.uuid  # captured before the bulk delete expires the instance

        a.is_deleted = True
        b.is_deleted = True
        db.session.commit()

        RuleModel._wipe_rule_children([a.id, b.id])
        db.session.commit()

        assert RuleRelation.query.filter_by(uuid=relation_uuid).first() is None
