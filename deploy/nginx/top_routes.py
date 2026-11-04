#!/usr/bin/env python3
"""Which routes cost the most? Reads nginx access logs in the rz_timed format
(deploy/nginx/rulezet.conf.template) and ranks routes by total response time.

    python3 deploy/nginx/top_routes.py /var/log/nginx/rulezet-site.access.log /var/log/nginx/rulezet-api.access.log
    python3 deploy/nginx/top_routes.py --top 40 --by count /var/log/nginx/*.access.log*   (.gz read too)

Paths are grouped: numbers / UUIDs / CVE / ATT&CK ids become :id, the query string is dropped.
Clients are grouped: ai (Claude, GPT…), bot (search engines, crawlers), api (scripts, curl…), browser.
Standard library only (runs on the server without the venv).
"""
import argparse
import gzip
import re
import sys
from collections import defaultdict

# 1.2.3.4 - [04/Nov/2026:10:00:00 +0100] "GET /rule/detail_rule/12?tab=x HTTP/1.1" 200 5120 0.123 "UA"
LINE = re.compile(r'^\S+ - \[[^\]]+\] "(?P<method>[A-Z]+) (?P<path>\S+)[^"]*" (?P<status>\d{3}) (?P<bytes>\d+|-) '
                  r'(?P<time>[\d.]+) "(?P<ua>[^"]*)"')

ID_PARTS = [
    re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I),
    re.compile(r'^\d+$'),
    re.compile(r'^(CVE|GHSA|GSD|PYSEC)-[\w-]+$', re.I),
    re.compile(r'^T\d{4}(\.\d{3})?$', re.I),
]

AI = re.compile(r'claude|anthropic|gptbot|chatgpt|openai|perplexity|ccbot|bytespider|google-extended|cohere|meta-externalagent', re.I)
BOT = re.compile(r'bot|crawl|spider|slurp|bingpreview|facebookexternalhit|semrush|ahrefs|yandex|baidu', re.I)
API = re.compile(r'curl|wget|python|requests|httpx|aiohttp|go-http|java|okhttp|node-fetch|axios|postman|pymisp|libwww', re.I)


def route_of(path):
    """/rule/detail_rule/12?tab=x -> /rule/detail_rule/:id"""
    path = path.split('?', 1)[0]
    if path.startswith('/static/'):
        return '/static/*'
    parts = [':id' if any(p.match(x) for p in ID_PARTS) else x for x in path.split('/')]
    return '/'.join(parts) or '/'


def client_of(ua):
    if AI.search(ua):
        return 'ai'
    if BOT.search(ua):
        return 'bot'
    if not ua or ua == '-' or API.search(ua):
        return 'api'
    return 'browser'


def parse(lines):
    """Yields (method, route, status, seconds, client) for every rz_timed line (others skipped)."""
    for line in lines:
        m = LINE.match(line)
        if m:
            yield m['method'], route_of(m['path']), int(m['status']), float(m['time']), client_of(m['ua'])


def aggregate(entries):
    stats = defaultdict(lambda: {'count': 0, 'total': 0.0, 'max': 0.0, 'clients': defaultdict(int), 'errors': 0})
    for method, route, status, secs, client in entries:
        s = stats[(method, route)]
        s['count'] += 1
        s['total'] += secs
        s['max'] = max(s['max'], secs)
        s['clients'][client] += 1
        if status >= 500:
            s['errors'] += 1
    return stats


def report(stats, top=25, by='total'):
    rows = sorted(stats.items(), key=lambda kv: kv[1][by], reverse=True)[:top]
    grand = sum(s['total'] for s in stats.values()) or 1
    out = [f"{'route':60} {'calls':>8} {'total s':>9} {'%':>5} {'avg ms':>7} {'max s':>6}  clients"]
    for (method, route), s in rows:
        clients = ' '.join(f"{k}:{v}" for k, v in sorted(s['clients'].items(), key=lambda kv: -kv[1]))
        out.append(f"{(method + ' ' + route)[:60]:60} {s['count']:>8} {s['total']:>9.1f} {100 * s['total'] / grand:>5.1f} "
                   f"{1000 * s['total'] / s['count']:>7.0f} {s['max']:>6.2f}  {clients}")
    by_client = defaultdict(lambda: [0])
    for s in stats.values():
        for c, n in s['clients'].items():
            by_client[c][0] += n
    out.append('')
    out.append('calls per client: ' + ', '.join(f"{c} {n}" for c, (n,) in sorted(by_client.items(), key=lambda kv: -kv[1][0])))
    return '\n'.join(out)


def read_lines(paths):
    for p in paths:
        opener = gzip.open if p.endswith('.gz') else open
        with opener(p, 'rt', errors='replace') as f:
            yield from f


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('logs', nargs='+')
    ap.add_argument('--top', type=int, default=25)
    ap.add_argument('--by', choices=['total', 'count', 'max'], default='total')
    a = ap.parse_args(argv)
    print(report(aggregate(parse(read_lines(a.logs))), a.top, a.by))


if __name__ == '__main__':
    sys.exit(main())
