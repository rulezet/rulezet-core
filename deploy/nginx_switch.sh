#!/usr/bin/env bash
# Rulezet — put nginx in front of Rulezet, or take it away again.
# Run deploy/setup_nginx.sh once before.
#
#   bash deploy/nginx_switch.sh on        switch traffic to nginx (asks you to restart Rulezet)
#   bash deploy/nginx_switch.sh off       back to Rulezet serving port 80 itself
#   bash deploy/nginx_switch.sh status    what is running where
#   bash deploy/nginx_switch.sh report    who WOULD have been rate-limited (dry-run log)
#   bash deploy/nginx_switch.sh enforce   rate limiting for real (429 above the limits)
#   bash deploy/nginx_switch.sh dry-run   back to "log only"
set -euo pipefail
cd "$(dirname "$0")/.."
STATE=/etc/nginx/rulezet.state
SITE_CONF=/etc/nginx/sites-available/rulezet
BACKUP=.env.before-nginx

die() { echo "✘ $*"; exit 1; }
[ "$(id -u)" -eq 0 ] || die "Run this as root (sudo)."
[ -f "$STATE" ] || die "Run deploy/setup_nginx.sh first."
# shellcheck disable=SC1090
. "$STATE"

env_set() {   # env_set KEY VALUE — replace or append in .env
    if grep -qE "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
port_open() { ss -Hltn "( sport = :$1 )" | grep -q .; }
screen_hint() {
    echo "    screen -r            (attach to Rulezet's screen)"
    echo "    Ctrl-C               (stop the running Rulezet)"
    echo "    python3 manage.py restart-prod"
    echo "    Ctrl-A then D        (detach — never close the screen with Ctrl-C twice)"
}

case "${1:-}" in
on)
    systemctl is-active --quiet nginx && die "nginx is already on."
    [ -f "$BACKUP" ] || cp .env "$BACKUP"
    env_set GUNICORN_BIND_HOST 127.0.0.1
    env_set PORT "$SITE_PORT"
    env_set API_PORT "$API_PORT"
    [ "$MODE" = direct ] && env_set TRUSTED_PROXY_COUNT 1
    echo "✔ .env updated (backup: $BACKUP)."
    echo
    echo "Now restart Rulezet so it moves to 127.0.0.1:$SITE_PORT (site) and :$API_PORT (API):"
    screen_hint
    echo
    echo "Waiting for it (this script finishes the switch by itself)…"
    for _ in $(seq 600); do
        if port_open "$SITE_PORT" && ! port_open 80; then break; fi
        sleep 1
    done
    port_open "$SITE_PORT" || die "Rulezet did not come up on port $SITE_PORT after 10 min.
   To go back: bash deploy/nginx_switch.sh off"
    port_open 80 && die "Port 80 is still taken — is the old Rulezet still running? Stop it, then re-run: bash deploy/nginx_switch.sh on"
    systemctl enable --now nginx
    sleep 2
    code="$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' http://127.0.0.1/ || true)"
    api="$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' http://127.0.0.1/api/ || true)"
    echo
    echo "✔ nginx is serving port 80 — home page: HTTP $code, API: HTTP $api"
    echo "  Open the site in your browser now. If anything is wrong: bash deploy/nginx_switch.sh off"
    echo "  Logs: /var/log/nginx/rulezet-site.access.log and rulezet-api.access.log (last column before the"
    echo "        user-agent = response time in seconds)"
    ;;
off)
    [ -f "$BACKUP" ] || die "No $BACKUP — nothing to restore (was 'on' ever run?)."
    systemctl disable --now nginx || true
    cp .env ".env.with-nginx.$(date +%Y%m%d-%H%M%S)"
    # Put back ONLY the keys 'on' changed (anything else edited since is kept).
    for key in GUNICORN_BIND_HOST PORT API_PORT TRUSTED_PROXY_COUNT; do
        if grep -qE "^$key=" "$BACKUP"; then
            env_set "$key" "$(grep -E "^$key=" "$BACKUP" | tail -n1 | cut -d= -f2-)"
        else
            sed -i "/^$key=/d" .env
        fi
    done
    rm -f "$BACKUP"
    echo "✔ nginx stopped, .env back to its pre-nginx launch settings (copy of the nginx one kept)."
    echo
    echo "Now restart Rulezet so it serves port 80 itself again:"
    screen_hint
    ;;
status)
    echo "nginx:    $(systemctl is-active nginx || true)"
    for p in 80 "$SITE_PORT" "$API_PORT"; do
        printf 'port %-5s %s\n' "$p" "$(port_open "$p" && ss -Hltnp "( sport = :$p )" | grep -oE 'users:\(\("[^"]+' | head -1 | cut -d'"' -f2 || echo '-')"
    done
    echo "rate limiting: $(grep -q 'limit_req_dry_run on' "$SITE_CONF" && echo 'dry-run (log only)' || echo 'ENFORCED')"
    ;;
report)
    LOG=/var/log/nginx/rulezet.error.log
    [ -f "$LOG" ] || die "No $LOG yet."
    echo "Requests that WOULD have been limited, per client IP and zone (most first):"
    grep -E 'limiting requests' "$LOG" | grep -oE 'client: [^,]+|zone "[^"]+"' | paste - - \
        | sort | uniq -c | sort -rn | head -20
    echo
    echo "If a legitimate tool shows up, never limit it:  echo '<IP> 1;' >> /etc/nginx/rulezet-allowlist.conf && systemctl reload nginx"
    ;;
enforce|dry-run)
    if [ "$1" = enforce ]; then
        [ "$REAL_IP_CONFIGURED" = yes ] || die "The upstream proxy IP is not configured — enforcing would
   rate-limit every visitor together. Re-run setup_nginx.sh with UPSTREAM_PROXY_IPS=… first."
        sed -i 's/limit_req_dry_run on;/limit_req_dry_run off;/' "$SITE_CONF"
    else
        sed -i 's/limit_req_dry_run off;/limit_req_dry_run on;/' "$SITE_CONF"
    fi
    nginx -t && systemctl reload nginx
    echo "✔ rate limiting: $([ "$1" = enforce ] && echo 'ENFORCED (HTTP 429 above the limits)' || echo 'dry-run')"
    ;;
*)
    sed -n '2,12p' "$0"; exit 1 ;;
esac
