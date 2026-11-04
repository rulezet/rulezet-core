"""Every cache / settings route is for admins only: anonymous → login, signed-in user → refused."""
import pytest

GET = ['/admin/cache', '/admin/cache/status', '/admin/settings', '/admin/settings/system', '/admin/settings/config',
       '/admin/settings/instance', '/rule/github/settings/cache']
POST = ['/admin/cache/action', '/rule/github/settings/cache/clear', '/rule/github/settings/cache/pull']


def _login(client):
    client.post('/account/login', data={'email': 't@t.t', 'password': 'password1@A', 'remember_me': False}, follow_redirects=True)
    return client


@pytest.mark.parametrize('url', GET)
def test_get_refused(app, url):
    assert app.test_client().get(url).status_code in (302, 401, 403), url
    assert _login(app.test_client()).get(url).status_code in (302, 401, 403), url


@pytest.mark.parametrize('url', POST)
def test_post_refused(app, url):
    for c in (app.test_client(), _login(app.test_client())):
        r = c.post(url, json={'action': 'clear_all'})
        assert r.status_code in (302, 401, 403), (url, r.status_code)


def test_nothing_emptied_by_a_non_admin(app, real_cache):
    with app.app_context():
        real_cache.set('canary', 1)
    _login(app.test_client()).post('/admin/cache/action', json={'action': 'clear_all'})
    with app.app_context():
        assert real_cache.get('canary') == 1
