"""
pdf_fetcher.py — what a WeasyPrint PDF export may load.

The exports render Markdown written by users or by an LLM (rule / bundle AI analysis, blog posts): an injected
<img> / <link> must not make the server read a local file (file:///etc/passwd) or reach an internal address
(http://169.254.169.254/…) and embed the answer in the PDF. Only the print templates' Google Fonts and, when
given, this instance's own public URL (blog images, graphs) are fetched; anything else is refused.

    HTML(string=…, url_fetcher=safe_url_fetcher(base_url)).write_pdf()
"""
from urllib.parse import urlparse

FONT_HOSTS = ('https://fonts.googleapis.com/', 'https://fonts.gstatic.com/')


def _allowed(url, own):
    if url.startswith(FONT_HOSTS):
        return True
    return bool(own) and url.startswith(own) and urlparse(url).netloc == urlparse(own).netloc


def safe_url_fetcher(own_base_url=None):
    own = None
    if own_base_url:
        p = urlparse(own_base_url)
        if p.scheme in ('http', 'https') and p.netloc:
            own = f'{p.scheme}://{p.netloc}/'

    try:                                   # WeasyPrint >= 70: a URLFetcher (no redirect: an allowed address
        from weasyprint.urls import URLFetcher   # must not bounce the request somewhere else)

        class _Safe(URLFetcher):
            def fetch(self, url, headers=None):
                if not _allowed(url, own):
                    raise ValueError(f'blocked resource in a PDF export: {url[:80]}')
                return super().fetch(url, headers)

        return _Safe(allowed_protocols={'http', 'https'}, allow_redirects=False, timeout=10)
    except ImportError:                    # older WeasyPrint: a plain function
        from weasyprint import default_url_fetcher

        def fetch(url, *args, **kwargs):
            if not _allowed(url, own):
                raise ValueError(f'blocked resource in a PDF export: {url[:80]}')
            return default_url_fetcher(url, *args, **kwargs)
        return fetch
