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
    from weasyprint.urls import URLFetcher
    monkeypatch.setattr(URLFetcher, "fetch", lambda self, url, headers=None: url)       # no network in tests
    fetch = safe_url_fetcher("https://rulezet.org/blog/post/x")
    assert fetch("https://fonts.googleapis.com/css2?family=Inter") == "https://fonts.googleapis.com/css2?family=Inter"
    assert fetch("https://rulezet.org/static/uploads/blog/a.png") == "https://rulezet.org/static/uploads/blog/a.png"
    with pytest.raises(ValueError):
        safe_url_fetcher()("https://rulezet.org/static/x.png")              # LLM exports: fonts only


def test_a_pdf_with_an_injected_local_file_still_renders_without_it():
    from weasyprint import HTML
    pdf = HTML(string='<p>report</p><img src="file:///etc/passwd">',
               url_fetcher=safe_url_fetcher()).write_pdf()
    assert pdf.startswith(b"%PDF") and b"root:" not in pdf
