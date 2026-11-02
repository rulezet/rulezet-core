"""PDF exports never read a local file nor reach another host (app/core/utils/pdf_fetcher.py)."""
import pytest

from app.core.utils.pdf_fetcher import safe_url_fetcher


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://169.254.169.254/latest/meta-data/",
                                 "http://127.0.0.1:5432/", "https://evil.example/x.png",
                                 "http://rulezet.org.evil.example/x.png"])
def test_blocked(url):
    with pytest.raises(ValueError):
        safe_url_fetcher("https://rulezet.org/")(url)


def test_fonts_and_own_site_allowed(monkeypatch):
    import weasyprint
    monkeypatch.setattr(weasyprint, "default_url_fetcher", lambda url, *a, **k: {"string": b"ok", "url": url})
    fetch = safe_url_fetcher("https://rulezet.org/blog/post/x")
    assert fetch("https://fonts.googleapis.com/css2?family=Inter")["string"] == b"ok"
    assert fetch("https://rulezet.org/static/uploads/blog/a.png")["string"] == b"ok"
    with pytest.raises(ValueError):
        safe_url_fetcher()("https://rulezet.org/static/x.png")              # LLM exports: fonts only
