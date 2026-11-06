"""Anonymous pages without a session (cacheable), CSRF still enforced — app/core/utils/anon_csrf.py."""
import re

import pytest

from app.core.utils import anon_csrf


@pytest.fixture(scope="session")
def _app(_test_app_factory, _legacy_seed):
    # Register the probe route once, before this app handles its first request.
    app = _test_app_factory(_legacy_seed)
    @app.route('/_test_anon_post', methods=['POST'])
    def _test_anon_post():
        return 'ok'
    return app


@pytest.fixture
def csrf_app(app):
    app.config['WTF_CSRF_ENABLED'] = True
    return app


def _token(html):
    return re.search(r'id="csrf_token" name="csrf_token" value="([^"]+)"', html).group(1)


def _raw(app, token):
    from itsdangerous import URLSafeTimedSerializer
    return URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='wtf-csrf-token').loads(token)


def test_anonymous_pages_set_no_cookie(csrf_app):
    for url in ('/', '/rule/detail_rule/1', '/rule/rules_list', '/api/rule/public/detail/1'):
        r = csrf_app.test_client().get(url)
        assert r.status_code == 200, url
        assert 'Set-Cookie' not in r.headers, url


def test_anonymous_post_with_the_page_token_works(csrf_app):
    c = csrf_app.test_client()
    token = _token(c.get('/rule/detail_rule/1').get_data(as_text=True))
    with csrf_app.app_context():
        assert _raw(csrf_app, token) == anon_csrf.shared_raw()
    assert c.post('/_test_anon_post', data={'csrf_token': token}).status_code == 200
    assert c.post('/_test_anon_post', headers={'X-CSRFToken': token}).status_code == 200


def test_post_without_or_with_a_bad_token_is_refused(csrf_app):
    c = csrf_app.test_client()
    assert c.post('/_test_anon_post').status_code == 400
    assert c.post('/_test_anon_post', data={'csrf_token': 'forged'}).status_code == 400


def test_account_pages_keep_their_own_session(csrf_app):
    c = csrf_app.test_client()
    r = c.get('/account/login')
    assert 'Set-Cookie' in r.headers
    with csrf_app.app_context():
        assert _raw(csrf_app, _token(r.get_data(as_text=True))) not in anon_csrf._raws()


def test_shared_token_cannot_log_in(csrf_app):
    c = csrf_app.test_client()
    token = _token(c.get('/rule/detail_rule/1').get_data(as_text=True))
    r = c.post('/account/login', data={'email': 't@t.t', 'password': 'password1@A', 'csrf_token': token})
    with c.session_transaction() as s:
        assert '_user_id' not in s                     # login CSRF with the shared token: refused


def test_signed_in_session_gets_its_own_token(csrf_app):
    c = csrf_app.test_client()
    shared = _token(c.get('/rule/detail_rule/1').get_data(as_text=True))
    c.post('/_test_anon_post', data={'csrf_token': shared})       # session created with the shared value
    login_page = c.get('/account/login').get_data(as_text=True)  # account page: own random value
    c.post('/account/login', data={'email': 't@t.t', 'password': 'password1@A', 'csrf_token': _token(login_page)})
    with c.session_transaction() as s:
        own = s.get('csrf_token')
        assert s.get('_user_id')
    with csrf_app.app_context():
        assert own not in anon_csrf._raws()
    page = c.get('/rule/detail_rule/1').get_data(as_text=True)
    with csrf_app.app_context():
        assert _raw(csrf_app, _token(page)) not in anon_csrf._raws()


def test_shared_token_refused_from_another_site(csrf_app):
    c = csrf_app.test_client()
    token = _token(c.get('/rule/detail_rule/1').get_data(as_text=True))
    for headers in ({'Origin': 'https://evil.example'}, {'Origin': 'null'}, {'Referer': 'https://evil.example/x'}):
        assert c.post('/_test_anon_post', data={'csrf_token': token}, headers=headers).status_code == 400, headers


def test_no_secret_key_means_no_shared_token(csrf_app):
    csrf_app.config['SECRET_KEY'] = ''
    with csrf_app.test_request_context('/'):
        from flask_login import AnonymousUserMixin
        assert anon_csrf._applies() is False
