"""Public API answers cached + ETag / 304 — step 3."""
from app import db
from app.core.db_class.rule import Rule


def _rid(app):
    with app.app_context():
        return Rule.query.filter_by(is_deleted=False).first().id


def test_detail_cached_and_refreshed_on_edit(app, real_cache):
    rid = _rid(app)
    c = app.test_client()
    r1 = c.get(f'/api/rule/public/detail/{rid}')
    assert r1.status_code == 200 and r1.headers['X-App-Cache'] == 'MISS'
    r2 = c.get(f'/api/rule/public/detail/{rid}')
    assert r2.headers['X-App-Cache'] == 'HIT' and r2.get_json() == r1.get_json()
    with app.app_context():
        db.session.get(Rule, rid).title = 'API title changed'
        db.session.commit()
    r3 = c.get(f'/api/rule/public/detail/{rid}')
    assert r3.headers['X-App-Cache'] == 'MISS' and r3.get_json()['title'] == 'API title changed'


def test_etag_gives_304(app, real_cache):
    rid = _rid(app)
    c = app.test_client()
    etag = c.get(f'/api/rule/public/detail/{rid}').headers['ETag']
    r = c.get(f'/api/rule/public/detail/{rid}', headers={'If-None-Match': etag})
    assert r.status_code == 304 and r.data == b''


def test_search_cached_and_refreshed_on_any_rule_change(app, real_cache):
    c = app.test_client()
    assert c.get('/api/rule/public/searchPage?search=test').headers['X-App-Cache'] == 'MISS'
    assert c.get('/api/rule/public/searchPage?search=test').headers['X-App-Cache'] == 'HIT'
    assert c.get('/api/rule/public/searchPage?search=other').headers['X-App-Cache'] == 'MISS'
    assert c.get('/api/rule/public/search?search=test').headers['X-App-Cache'] == 'MISS'
    with app.app_context():
        Rule.query.filter_by(is_deleted=False).first().description = 'changed'
        db.session.commit()
    assert c.get('/api/rule/public/searchPage?search=test').headers['X-App-Cache'] == 'MISS'


def test_errors_and_keys_are_never_cached(app, real_cache):
    c = app.test_client()
    assert c.get('/api/rule/public/detail/999999').status_code == 404
    assert 'X-App-Cache' in c.get('/api/rule/public/detail/999999').headers   # MISS each time
    assert c.get('/api/rule/public/detail/999999').headers['X-App-Cache'] == 'MISS'
    rid = _rid(app)
    c.get(f'/api/rule/public/detail/{rid}')
    r = c.get(f'/api/rule/public/detail/{rid}', headers={'X-API-KEY': 'whatever'})
    assert 'X-App-Cache' not in r.headers


def test_deleted_rule_not_served_by_the_api(app, real_cache):
    rid = _rid(app)
    c = app.test_client()
    assert c.get(f'/api/rule/public/detail/{rid}').status_code == 200
    with app.app_context():
        db.session.get(Rule, rid).is_deleted = True
        db.session.commit()
    assert c.get(f'/api/rule/public/detail/{rid}').status_code == 404
