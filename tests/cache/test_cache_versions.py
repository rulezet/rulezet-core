"""Rule generations bumped automatically on commit — app/core/utils/cache_versions.py."""
from app import db
from app.core.db_class.rule import Rule, RuleVote
from app.core.utils import cache_versions as cv


def _rule():
    return Rule.query.filter_by(is_deleted=False).first()


def test_keys_are_stable_until_something_changes(app, real_cache):
    with app.app_context():
        r = _rule()
        assert cv.rule_key('page', r.id) == cv.rule_key('page', r.id)
        assert cv.rules_key('list', {'page': 1}) == cv.rules_key('list', {'page': 1})
        assert cv.rules_key('list', {'page': 1}) != cv.rules_key('list', {'page': 2})


def test_editing_a_rule_changes_its_key_and_the_lists(app, real_cache):
    with app.app_context():
        r = _rule()
        page, lst = cv.rule_key('page', r.id), cv.rules_key('list')
        r.description = (r.description or '') + ' edited'
        db.session.commit()
        assert cv.rule_key('page', r.id) != page
        assert cv.rules_key('list') != lst


def test_a_row_with_rule_id_changes_the_rule_key(app, real_cache):
    with app.app_context():
        r = _rule()
        page = cv.rule_key('page', r.id)
        db.session.add(RuleVote(user_id=r.user_id, rule_id=r.id, vote_type='up'))
        db.session.commit()
        assert cv.rule_key('page', r.id) != page


def test_other_rules_keep_their_key(app, real_cache):
    with app.app_context():
        r = _rule()
        page = cv.rule_key('page', r.id)
        cv.bump_rule(r.id + 1000)
        assert cv.rule_key('page', r.id) == page


def test_rollback_bumps_nothing(app, real_cache):
    with app.app_context():
        r = _rule()
        page = cv.rule_key('page', r.id)
        r.description = 'not kept'
        db.session.flush()
        db.session.rollback()
        db.session.commit()
        assert cv.rule_key('page', r.id) == page


def test_bulk_update_changes_every_rule_key(app, real_cache):
    with app.app_context():
        r = _rule()
        page, lst = cv.rule_key('page', r.id), cv.rules_key('list')
        Rule.query.filter(Rule.id == r.id).update({'description': 'bulk'})
        db.session.commit()
        assert cv.rule_key('page', r.id) != page
        assert cv.rules_key('list') != lst


def test_evicted_generation_never_brings_old_entries_back(app, real_cache):
    with app.app_context():
        r = _rule()
        page = cv.rule_key('page', r.id)
        real_cache.delete(f'rz:gen:rule:{r.id}')
        assert cv.rule_key('page', r.id) != page
