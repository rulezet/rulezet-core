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


def safe_url_fetcher(own_base_url=None):
    from weasyprint import default_url_fetcher
    own = None
    if own_base_url:
        p = urlparse(own_base_url)
        if p.scheme in ('http', 'https') and p.netloc:
            own = f'{p.scheme}://{p.netloc}/'

    def fetch(url, *args, **kwargs):
        if url.startswith(FONT_HOSTS) or (own and url.startswith(own) and urlparse(url).netloc == urlparse(own).netloc):
            return default_url_fetcher(url, *args, **kwargs)
        raise ValueError(f'blocked resource in a PDF export: {url[:80]}')
    return fetch
