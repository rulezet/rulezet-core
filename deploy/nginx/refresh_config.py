#!/usr/bin/env python3
"""Re-generates the live nginx config from deploy/nginx/rulezet.conf.template after an update,
KEEPING the values of the config in place (server name, ports, rate limits, real-IP and forwarded
headers, dry-run state) — what setup_nginx.sh asked once. Used by `deploy/nginx_switch.sh refresh`
(and `manage.py deploy` when it runs as root).

    python3 deploy/nginx/refresh_config.py <template> <live config> <out> [--app-dir DIR] [--session-cookie NAME]

Writes <out> (never the live file itself: the caller tests it with nginx -t, then swaps).
Exit 0 = written, 3 = nothing changed, 1 = cannot read the live config.
Standard library only.
"""
import argparse
import re
import sys


def extract(live):
    """Values setup_nginx.sh put in the live config."""
    def one(pattern, default=None):
        m = re.search(pattern, live, re.M)
        return m.group(1).strip() if m else default

    v = {
        'SERVER_NAME': one(r'^\s*server_name\s+([^;]+);'),
        'SITE_PORT': one(r'upstream rulezet_site\s*\{\s*server 127\.0\.0\.1:(\d+)'),
        'API_PORT': one(r'upstream rulezet_api\s*\{\s*server 127\.0\.0\.1:(\d+)'),
        'SITE_RATE': one(r'zone=rz_site:\S+\s+rate=([^;\s]+)'),
        'API_RATE': one(r'zone=rz_api:\S+\s+rate=([^;\s]+)'),
        'SITE_BURST': one(r'limit_req zone=rz_site burst=(\d+)'),
        'API_BURST': one(r'limit_req zone=rz_api\s+burst=(\d+)'),
        'DRY_RUN': one(r'limit_req_dry_run\s+(on|off);', 'on'),
    }
    real_ip = re.findall(r'^\s*(set_real_ip_from [^;]+;|real_ip_header [^;]+;|real_ip_recursive [^;]+;)\s*$', live, re.M)
    v['REAL_IP'] = ''.join(f'    {x}\n' for x in real_ip)
    fwd = re.findall(r'^\s*(proxy_set_header X-Forwarded-(?:For|Proto|Host)\s+[^;]+;)\s*$', live, re.M)
    v['FORWARD_HEADERS'] = '\n'.join(f'    {x}' for x in fwd)
    if 'pass-through' in live:
        v['FORWARD_HEADERS'] = '    # pass-through: the upstream proxy already set these, keep them unchanged\n' + v['FORWARD_HEADERS']
    v['APP_DIR'] = one(r'^\s*root\s+(\S+/app);')
    v['SESSION_COOKIE'] = one(r'\(\^\|;\\s\*\)\(([\w.-]+)\|remember_token\)=')
    return v


def render(template, v, app_dir, session_cookie):
    missing = [k for k in ('SERVER_NAME', 'SITE_PORT', 'API_PORT', 'SITE_RATE', 'API_RATE', 'SITE_BURST', 'API_BURST') if not v.get(k)]
    if missing:
        raise ValueError(f"cannot find {', '.join(missing)} in the live config — run deploy/setup_nginx.sh")
    out = template
    for key in ('SERVER_NAME', 'SITE_PORT', 'API_PORT', 'SITE_RATE', 'SITE_BURST', 'API_RATE', 'API_BURST'):
        out = out.replace(f'__{key}__', v[key])
    out = out.replace('__REAL_IP__', v['REAL_IP'].rstrip('\n'))
    out = out.replace('__FORWARD_HEADERS__', v['FORWARD_HEADERS'])
    out = out.replace('__APP_DIR__', v.get('APP_DIR') or app_dir)
    out = out.replace('__SESSION_COOKIE__', v.get('SESSION_COOKIE') or session_cookie)
    out = out.replace('__DRY_RUN__', v['DRY_RUN'])             # never switches rate limiting on or off by itself
    left = re.findall(r'__[A-Z_]+__', out)
    if left:
        raise ValueError(f'unreplaced placeholders: {left}')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('template')
    ap.add_argument('live')
    ap.add_argument('out')
    ap.add_argument('--app-dir', required=True)
    ap.add_argument('--session-cookie', default='session')
    a = ap.parse_args(argv)
    try:
        live = open(a.live).read()
    except OSError as e:
        print(f'✘ cannot read {a.live}: {e}')
        return 1
    try:
        new = render(open(a.template).read(), extract(live), a.app_dir, a.session_cookie)
    except ValueError as e:
        print(f'✘ {e}')
        return 1
    if new == live:
        print('nginx config already up to date')
        return 3
    open(a.out, 'w').write(new)
    return 0


if __name__ == '__main__':
    sys.exit(main())
