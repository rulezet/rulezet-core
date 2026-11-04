"""deploy/nginx/refresh_config.py — re-generates the nginx config after an update, keeping its values."""
import importlib.util
import os
import subprocess

ROOT = os.getcwd()
_spec = importlib.util.spec_from_file_location('refresh_config', os.path.join(ROOT, 'deploy', 'nginx', 'refresh_config.py'))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)
TEMPLATE = open(os.path.join(ROOT, 'deploy', 'nginx', 'rulezet.conf.template')).read()

VALUES = {
    '__SERVER_NAME__': 'rulezet.org www.rulezet.org _', '__SITE_PORT__': '7009', '__API_PORT__': '7010',
    '__SITE_RATE__': '30r/s', '__SITE_BURST__': '200', '__API_RATE__': '20r/s', '__API_BURST__': '100',
    '__REAL_IP__': '    set_real_ip_from 10.0.0.5;\n    real_ip_header X-Forwarded-For;\n    real_ip_recursive on;',
    '__FORWARD_HEADERS__': '    # pass-through: the upstream proxy already set these, keep them unchanged\n'
                           '    proxy_set_header X-Forwarded-For   $http_x_forwarded_for;\n'
                           '    proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;\n'
                           '    proxy_set_header X-Forwarded-Host  $http_x_forwarded_host;',
    '__APP_DIR__': '/srv/rulezet/app', '__SESSION_COOKIE__': 'session', '__DRY_RUN__': 'off',
}


def _live():
    s = TEMPLATE
    for k, v in VALUES.items():
        s = s.replace(k, v)
    return s


def _run(tmp_path, live_text):
    live = tmp_path / 'live.conf'
    live.write_text(live_text)
    out = tmp_path / 'new.conf'
    code = rc.main([os.path.join(ROOT, 'deploy', 'nginx', 'rulezet.conf.template'), str(live), str(out),
                    '--app-dir', '/other/app'])
    return code, (out.read_text() if out.exists() else None)


def test_same_template_is_a_no_op(tmp_path):
    code, _ = _run(tmp_path, _live())
    assert code == 3


def test_values_kept_when_the_template_changes(tmp_path):
    # an older live config: no cache section yet, rate limiting enforced (dry-run off)
    old = _live().replace('proxy_cache rz_cache;', '').replace('location = /api/rule/public/search_rules_by_cve', 'location = /old')
    code, new = _run(tmp_path, old)
    assert code == 0
    assert new == _live()                                 # every value of the live config kept, dry-run 'off' kept
    assert 'limit_req_dry_run off;' in new and 'set_real_ip_from 10.0.0.5;' in new
    assert '/srv/rulezet/app' in new                      # app dir from the live config, not the argument


def test_unreadable_or_foreign_config(tmp_path):
    assert _run(tmp_path, 'server { listen 80; }')[0] == 1
    assert rc.main([os.path.join(ROOT, 'deploy', 'nginx', 'rulezet.conf.template'), str(tmp_path / 'nope'),
                    str(tmp_path / 'o'), '--app-dir', '/x']) == 1
