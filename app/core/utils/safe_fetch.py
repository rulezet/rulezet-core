"""safe_fetch.py — read a page from an address a *user* typed, without letting that user point the
server at itself or its network (SSRF).

    fetch_page(url)   -> (final_url, html_text) or raises FetchError
    page_preview(url) -> {'title', 'description', 'site_name', 'url'} or None

Rules:
  - http / https only, default ports or any port on a public address;
  - the host name is resolved here and EVERY address it resolves to must be public (no loopback,
    private, link-local — cloud metadata 169.254.169.254 —, multicast, reserved, unspecified,
    CGNAT, IPv4-mapped private…), then the connection goes to that checked IP (no second DNS
    lookup that could answer something else: DNS rebinding), TLS still checked against the name;
  - redirects followed by hand, at most MAX_REDIRECTS, each new address checked the same way;
  - MAX_BYTES read at most, TIMEOUT seconds per step and TOTAL_TIMEOUT for everything,
    HTML pages only, no cookies sent.
"""
from __future__ import annotations

import ipaddress
import socket
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

TIMEOUT = 5
TOTAL_TIMEOUT = 12          # whole fetch, redirects included (a page trickled byte by byte can't hold a worker)
MAX_BYTES = 512 * 1024
MAX_REDIRECTS = 3
USER_AGENT = 'Mozilla/5.0 (compatible; RulezetLinkPreview/1.0)'


class FetchError(Exception):
    pass


def _public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    if (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast
            or addr.is_reserved or addr.is_unspecified):
        return False
    if isinstance(addr, ipaddress.IPv4Address) and addr in ipaddress.ip_network('100.64.0.0/10'):  # CGNAT
        return False
    return addr.is_global


def _resolve(host: str, port: int) -> str:
    """One public IP for *host*; FetchError if any of its addresses is not public."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise FetchError('host not found')
    ips = list(dict.fromkeys(info[4][0] for info in infos))
    if not ips:
        raise FetchError('host not found')
    for ip in ips:
        if not _public_ip(ip):
            raise FetchError('address not allowed')
    return ips[0]


def _get_once(url: str):
    import urllib3
    parts = urlparse(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise FetchError('only http and https addresses')
    host = parts.hostname
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    ip = _resolve(host, port)
    path = parts.path or '/'
    if parts.query:
        path += '?' + parts.query
    host_header = host if parts.port is None else f'{host}:{parts.port}'
    timeout = urllib3.Timeout(connect=TIMEOUT, read=TIMEOUT)
    if parts.scheme == 'https':
        pool = urllib3.HTTPSConnectionPool(ip, port=port, server_hostname=host, assert_hostname=host,
                                           cert_reqs='CERT_REQUIRED', timeout=timeout, retries=False)
    else:
        pool = urllib3.HTTPConnectionPool(ip, port=port, timeout=timeout, retries=False)
    try:
        resp = pool.urlopen('GET', path, headers={'Host': host_header, 'User-Agent': USER_AGENT,
                                                  'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.1'},
                            redirect=False, preload_content=False, assert_same_host=False)
    except urllib3.exceptions.HTTPError as e:
        raise FetchError(f'request failed ({type(e).__name__})')
    return pool, resp


def fetch_page(url: str):
    """(final url, text of the page) — FetchError when anything is not allowed or fails."""
    deadline = time.monotonic() + TOTAL_TIMEOUT
    for _ in range(MAX_REDIRECTS + 1):
        if time.monotonic() > deadline:
            raise FetchError('too slow')
        pool, resp = _get_once(url)
        try:
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.headers.get('Location')
                if not location:
                    raise FetchError('redirect without a location')
                url = urljoin(url, location)
                continue
            if resp.status != 200:
                raise FetchError(f'HTTP {resp.status}')
            ctype = (resp.headers.get('Content-Type') or '').lower()
            if 'html' not in ctype:
                raise FetchError('not an HTML page')
            data = b''
            for chunk in resp.stream(16384):
                data += chunk
                if len(data) >= MAX_BYTES:
                    break
                if time.monotonic() > deadline:
                    raise FetchError('too slow')
            charset = 'utf-8'
            if 'charset=' in ctype:
                charset = ctype.split('charset=')[-1].split(';')[0].strip() or 'utf-8'
            try:
                return url, data[:MAX_BYTES].decode(charset, errors='replace')
            except LookupError:
                return url, data[:MAX_BYTES].decode('utf-8', errors='replace')
        finally:
            resp.release_conn()
            pool.close()
    raise FetchError('too many redirects')


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.title = ''
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            key = (a.get('property') or a.get('name') or '').lower()
            if key and 'content' in a and key not in self.meta:
                self.meta[key] = a['content']

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and len(self.title) < 500:
            self.title += data


def _clean(text, limit):
    text = ' '.join((text or '').split())
    return text[:limit - 1] + '…' if len(text) > limit else text


def page_preview(url: str):
    """Title / description / site name of a page (OpenGraph first, then <title> and
    meta description), or None when it can't be read. Never raises."""
    try:
        final_url, html = fetch_page(url)
        parser = _MetaParser()
        parser.feed(html)
    except Exception:
        return None
    m = parser.meta
    preview = {
        'title': _clean(m.get('og:title') or m.get('twitter:title') or parser.title, 200),
        'description': _clean(m.get('og:description') or m.get('twitter:description') or m.get('description'), 400),
        'site_name': _clean(m.get('og:site_name') or urlparse(final_url).hostname or '', 100),
        'url': final_url,
    }
    return preview if (preview['title'] or preview['description']) else None
