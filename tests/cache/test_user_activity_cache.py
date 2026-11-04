"""User page Activity Overview: same figures, from the cache, refreshed by a rule change."""
from app import db
from app.core.db_class.rule import Rule


def _login(client):
    client.post('/account/login', data={'email': 't@t.t', 'password': 'password1@A', 'remember_me': False}, follow_redirects=True)
    return client


def test_activity_cached_and_refreshed(app, real_cache):
    with app.app_context():
        r = Rule.query.filter_by(is_deleted=False).first()
        rid, uid = r.id, r.user_id
    c = _login(app.test_client())
    first = c.get(f'/account/user_activity_stats/{uid}').get_json()
    assert first['activity_stats']['total_rules'] >= 1
    with app.app_context():
        db.session.get(Rule, rid).vote_up = 41
        Rule.query.filter(Rule.id == rid).first()     # noqa
        db.session.commit()
    again = c.get(f'/account/user_activity_stats/{uid}').get_json()
    assert again['activity_stats']['rules_likes'] >= 41                  # the vote shows at once


def test_activity_same_answer_with_and_without_cache(app, real_cache):
    with app.app_context():
        uid = Rule.query.filter_by(is_deleted=False).first().user_id
    c = _login(app.test_client())
    a = c.get(f'/account/user_activity_stats/{uid}').get_json()
    b = c.get(f'/account/user_activity_stats/{uid}').get_json()          # from the cache
    assert a == b


def test_activity_needs_login_and_existing_user(app):
    assert app.test_client().get('/account/user_activity_stats/1').status_code in (302, 401)
    assert _login(app.test_client()).get('/account/user_activity_stats/999999').status_code == 404
