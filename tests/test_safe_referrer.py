"""safe_referrer() feeds redirect() after form posts: it must only ever
send the browser back to a path on this site."""

import pytest

from app.core.utils.utils import safe_referrer


@pytest.mark.parametrize("ref,expected", [
    ("http://localhost/rule/1?x=2", "/rule/1?x=2"),
    ("/bundle/list", "/bundle/list"),
    ("https://evil.com/a", "/"),
    ("//evil.com", "/"),
    ("/\\evil.com", "/"),
    ("http://localhost//evil.com", "/"),
    ("javascript:alert(1)", "/"),
    (None, "/"),
])
def test_safe_referrer(app, ref, expected):
    headers = {"Referer": ref} if ref else {}
    with app.test_request_context("/", base_url="http://localhost", headers=headers):
        assert safe_referrer() == expected
