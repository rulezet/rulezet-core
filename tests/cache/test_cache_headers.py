"""Answers for signed-in users are private (never kept by nginx / a proxy), anonymous ones are not."""


def _login(client):
    client.post("/account/login", data={"email": "t@t.t", "password": "password1@A", "remember_me": False},
                follow_redirects=True)


def test_anonymous_rule_page_is_shareable(client):
    r = client.get('/rule/detail_rule/1')
    assert r.status_code == 200
    assert 'private' not in r.headers.get('Cache-Control', '')
    assert 'Cookie' in r.headers.get('Vary', '')


def test_signed_in_answers_are_private(client):
    _login(client)
    for url in ('/rule/detail_rule/1', '/', '/rule/get_rules_page_filter?page=1'):
        r = client.get(url)
        assert 'private' in r.headers.get('Cache-Control', ''), url


def test_versioned_static_stays_public(client):
    _login(client)
    r = client.get('/static/css/core.css?v=1')
    assert r.headers['Cache-Control'] == 'public, max-age=31536000, immutable'


def test_uploads_are_sandboxed(app, client):
    import os
    path = os.path.join(app.root_path, 'static', 'uploads', 'blog', '_test_sandbox.svg')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    try:
        r = client.get('/static/uploads/blog/_test_sandbox.svg')
        assert 'sandbox' in r.headers['Content-Security-Policy']
        assert r.headers['X-Content-Type-Options'] == 'nosniff'
    finally:
        os.remove(path)
