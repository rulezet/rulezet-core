"""Rule page: whole page cached for anonymous visitors, shared parts for everyone — step 2."""
from app import db
from app.core.db_class.rule import Rule


def _rule(app):
    with app.app_context():
        return Rule.query.filter_by(is_deleted=False).first().id


def _login(client):
    client.post("/account/login", data={"email": "t@t.t", "password": "password1@A", "remember_me": False},
                follow_redirects=True)


def test_anonymous_page_from_the_cache(app, real_cache):
    rid = _rule(app)
    c = app.test_client()
    assert c.get(f'/rule/detail_rule/{rid}').headers['X-App-Cache'] == 'MISS'
    r = c.get(f'/rule/detail_rule/{rid}')
    assert r.headers['X-App-Cache'] == 'HIT' and r.status_code == 200
    assert app.test_client().get(f'/rule/detail_rule/{rid}?tab=history').headers['X-App-Cache'] == 'MISS'


def test_edit_gives_a_fresh_page(app, real_cache):
    rid = _rule(app)
    c = app.test_client()
    c.get(f'/rule/detail_rule/{rid}')
    with app.app_context():
        r = db.session.get(Rule, rid)
        r.title = 'Brand new title for the cache test'
        db.session.commit()
    r = c.get(f'/rule/detail_rule/{rid}')
    assert r.headers['X-App-Cache'] == 'MISS'
    assert 'Brand new title for the cache test' in r.get_data(as_text=True)


def test_signed_in_never_gets_the_shared_page(app, real_cache):
    rid = _rule(app)
    app.test_client().get(f'/rule/detail_rule/{rid}')         # anonymous copy in the cache
    c = app.test_client()
    _login(c)
    r = c.get(f'/rule/detail_rule/{rid}')
    assert 'X-App-Cache' not in r.headers
    assert 'private' in r.headers['Cache-Control']


def test_visitor_with_a_flash_message_gets_a_live_page(app, real_cache):
    rid = _rule(app)
    app.test_client().get(f'/rule/detail_rule/{rid}')
    c = app.test_client()
    with c.session_transaction() as s:
        s['_flashes'] = [('info', 'only for this visitor')]
    r = c.get(f'/rule/detail_rule/{rid}')
    assert 'X-App-Cache' not in r.headers
    assert app.test_client().get(f'/rule/detail_rule/{rid}').headers['X-App-Cache'] == 'HIT'


def test_shared_parts_computed_once_for_everybody(app, real_cache, monkeypatch):
    import app.features.rule.rule as rule_view
    calls = []
    real = rule_view.get_rule_misp_event
    monkeypatch.setattr(rule_view, 'get_rule_misp_event', lambda rid: calls.append(rid) or real(rid))
    rid = _rule(app)
    c = app.test_client()
    _login(c)
    c.get(f'/rule/detail_rule/{rid}')
    c.get(f'/rule/detail_rule/{rid}')
    app.test_client().get(f'/rule/detail_rule/{rid}')        # anonymous: same parts
    assert calls == [rid]
