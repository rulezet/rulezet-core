"""deploy/nginx/top_routes.py — ranks routes from nginx rz_timed logs."""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location('top_routes', os.path.join(os.getcwd(), 'deploy', 'nginx', 'top_routes.py'))
top_routes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(top_routes)

LOG = [
    '1.2.3.4 - [04/Nov/2026:10:00:00 +0100] "GET /rule/detail_rule/12?tab=x HTTP/1.1" 200 5120 0.400 "Mozilla/5.0 ClaudeBot/1.0"\n',
    '1.2.3.4 - [04/Nov/2026:10:00:01 +0100] "GET /rule/detail_rule/99 HTTP/1.1" 200 5120 0.600 "Mozilla/5.0 Firefox/140"\n',
    '1.2.3.5 - [04/Nov/2026:10:00:02 +0100] "GET /api/rule/public/detail/7 HTTP/1.1" 500 10 1.000 "python-requests/2.32"\n',
    '1.2.3.6 - [04/Nov/2026:10:00:03 +0100] "GET /static/css/core.css?v=1 HTTP/1.1" 200 10 0.001 "Googlebot/2.1"\n',
    '1.2.3.6 - [04/Nov/2026:10:00:04 +0100] "GET /vulnerability/CVE-2024-1234 HTTP/1.1" 200 10 0.2 "-"\n',
    'garbage line\n',
]


def test_route_grouping():
    assert top_routes.route_of('/rule/detail_rule/12?tab=x') == '/rule/detail_rule/:id'
    assert top_routes.route_of('/rule/detail_rule_by_uuid/3f2b1c4d-1111-2222-3333-444455556666') == '/rule/detail_rule_by_uuid/:id'
    assert top_routes.route_of('/attack/technique/T1059.001') == '/attack/technique/:id'
    assert top_routes.route_of('/static/js/a.js') == '/static/*'


def test_client_grouping():
    assert top_routes.client_of('Mozilla/5.0 ClaudeBot/1.0') == 'ai'
    assert top_routes.client_of('Googlebot/2.1') == 'bot'
    assert top_routes.client_of('python-requests/2.32') == 'api'
    assert top_routes.client_of('-') == 'api'
    assert top_routes.client_of('Mozilla/5.0 Firefox/140') == 'browser'


def test_aggregate_and_report():
    stats = top_routes.aggregate(top_routes.parse(LOG))
    detail = stats[('GET', '/rule/detail_rule/:id')]
    assert detail['count'] == 2 and abs(detail['total'] - 1.0) < 1e-9 and detail['max'] == 0.6
    assert dict(detail['clients']) == {'ai': 1, 'browser': 1}
    assert stats[('GET', '/api/rule/public/detail/:id')]['errors'] == 1
    assert len(stats) == 4                      # garbage line skipped
    text = top_routes.report(stats, top=2)
    lines = text.splitlines()
    assert 'GET /rule/detail_rule/:id' in lines[1] or 'GET /api/rule/public/detail/:id' in lines[1]
    assert 'calls per client' in text
