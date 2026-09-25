#!/usr/bin/env bash
# Rulezet — install nginx and generate its config. DOES NOT TOUCH LIVE TRAFFIC:
# nginx is installed but left stopped; Rulezet keeps serving port 80 itself.
# Switching traffic to nginx is a separate, reversible step:
#     bash deploy/nginx_switch.sh on
#
# Usage (as root, from the rulezet-core folder):
#   bash deploy/setup_nginx.sh
#
# Optional environment overrides (otherwise asked or defaulted):
#   SERVER_NAME=rulezet.org        server_name (default: rulezet.org + catch-all)
#   UPSTREAM_PROXY_IPS="10.0.0.5"  IP(s)/CIDR of the proxy already in front of this server
#   SITE_PORT=7009 API_PORT=7010   internal gunicorn ports (localhost only)
#   SITE_RATE=30r/s SITE_BURST=200 API_RATE=20r/s API_BURST=100   rate limits
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
STATE=/etc/nginx/rulezet.state
TEMPLATE="$ROOT/deploy/nginx/rulezet.conf.template"
SITE_CONF=/etc/nginx/sites-available/rulezet
ALLOWLIST=/etc/nginx/rulezet-allowlist.conf

die() { echo "✘ $*"; exit 1; }
[ "$(id -u)" -eq 0 ] || die "Run this as root (sudo)."
[ -f .env ] || die "No .env found in $ROOT — run this from rulezet-core."
[ -f "$TEMPLATE" ] || die "Template missing: $TEMPLATE"

env_get() { grep -E "^$1=" .env | tail -n1 | cut -d= -f2- | tr -d '"'"'" || true; }
PROXY_COUNT="$(env_get TRUSTED_PROXY_COUNT)"; PROXY_COUNT="${PROXY_COUNT:-0}"
CURRENT_PORT="$(env_get PORT)"; CURRENT_PORT="${CURRENT_PORT:-80}"
SITE_PORT="${SITE_PORT:-7009}"
API_PORT="${API_PORT:-7010}"
SERVER_NAME="${SERVER_NAME:-rulezet.org}"

echo "==> Checking the current setup…"
if ss -Hltn '( sport = :443 )' | grep -q .; then
    die "Something already listens on port 443 on this machine — this script only handles the
   case where HTTPS is terminated before this server (or not used). Stopping, nothing changed."
fi
for p in "$SITE_PORT" "$API_PORT"; do
    if ss -Hltn "( sport = :$p )" | grep -q . && [ "$p" != "$CURRENT_PORT" ]; then
        die "Port $p is already in use — pick others: SITE_PORT=… API_PORT=… bash deploy/setup_nginx.sh"
    fi
done
echo "   Rulezet currently serves port $CURRENT_PORT, TRUSTED_PROXY_COUNT=$PROXY_COUNT"

# ── Is there a proxy in front of this server already? ─────────────────────
REAL_IP_BLOCK=""
if [ "$PROXY_COUNT" -gt 0 ]; then
    MODE=passthrough
    echo "   → a proxy already sits in front of Rulezet (TRUSTED_PROXY_COUNT=$PROXY_COUNT)."
    echo "     nginx will pass its X-Forwarded-* headers through unchanged, so Rulezet"
    echo "     sees exactly what it sees today (TRUSTED_PROXY_COUNT stays $PROXY_COUNT)."
    if [ -z "${UPSTREAM_PROXY_IPS:-}" ]; then
        DETECTED="$(ss -Htn state established "( sport = :$CURRENT_PORT )" 2>/dev/null \
                    | awk '{print $4}' | sed -E 's/^\[?(.*)\]?:[0-9]+$/\1/; s/^::ffff://' \
                    | sort | uniq -c | sort -rn | head -3 | awk '{print $2}' | tr '\n' ' ')"
        echo
        echo "   For per-visitor rate limiting, nginx must know the IP of that proxy."
        echo "   Connections currently open to port $CURRENT_PORT come mostly from: ${DETECTED:-<none>}"
        read -r -p "   Upstream proxy IP(s), space-separated [${DETECTED%% *}]: " UPSTREAM_PROXY_IPS
        UPSTREAM_PROXY_IPS="${UPSTREAM_PROXY_IPS:-${DETECTED%% *}}"
    fi
    if [ -n "${UPSTREAM_PROXY_IPS// /}" ]; then
        for ip in $UPSTREAM_PROXY_IPS; do REAL_IP_BLOCK+="    set_real_ip_from $ip;"$'\n'; done
        REAL_IP_BLOCK+="    real_ip_header X-Forwarded-For;"$'\n'"    real_ip_recursive on;"$'\n'
    else
        echo "   ⚠ No upstream proxy IP given: rate limiting will stay in dry-run (it would"
        echo "     otherwise treat every visitor as the same IP)."
    fi
    FORWARD_BLOCK='    # pass-through: the upstream proxy already set these, keep them unchanged
    proxy_set_header X-Forwarded-For   $http_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    proxy_set_header X-Forwarded-Host  $http_x_forwarded_host;'
else
    MODE=direct
    echo "   → no proxy in front: nginx becomes the proxy (TRUSTED_PROXY_COUNT will be set to 1)."
    FORWARD_BLOCK='    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host  $host;'
fi

echo "==> Installing nginx (without starting it)…"
if ! command -v nginx >/dev/null; then
    # policy-rc.d stops the package from starting nginx on :80, which Rulezet still owns.
    printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d; chmod +x /usr/sbin/policy-rc.d
    trap 'rm -f /usr/sbin/policy-rc.d' EXIT
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx
    rm -f /usr/sbin/policy-rc.d; trap - EXIT
fi
systemctl disable --now nginx >/dev/null 2>&1 || true
NGINX_VERSION="$(nginx -v 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
python3 - "$NGINX_VERSION" <<'PY' || die "nginx $NGINX_VERSION is too old (limit_req_dry_run needs ≥ 1.17.1)."
import sys; v = tuple(int(x) for x in sys.argv[1].split('.')); sys.exit(0 if v >= (1, 17, 1) else 1)
PY

echo "==> Writing the config…"
[ -f "$ALLOWLIST" ] || printf '# One line per IP never rate-limited, e.g.\n# 203.0.113.7 1;\n' > "$ALLOWLIST"
SERVER_NAME="$SERVER_NAME www.$SERVER_NAME _" \
SITE_PORT="$SITE_PORT" API_PORT="$API_PORT" \
SITE_RATE="${SITE_RATE:-30r/s}" SITE_BURST="${SITE_BURST:-200}" \
API_RATE="${API_RATE:-20r/s}" API_BURST="${API_BURST:-100}" \
REAL_IP_BLOCK="$REAL_IP_BLOCK" FORWARD_BLOCK="$FORWARD_BLOCK" \
python3 - "$TEMPLATE" "$SITE_CONF" <<'PY'
import os, sys
s = open(sys.argv[1]).read()
for key, env in [('__SERVER_NAME__', 'SERVER_NAME'), ('__SITE_PORT__', 'SITE_PORT'), ('__API_PORT__', 'API_PORT'),
                 ('__SITE_RATE__', 'SITE_RATE'), ('__SITE_BURST__', 'SITE_BURST'),
                 ('__API_RATE__', 'API_RATE'), ('__API_BURST__', 'API_BURST'),
                 ('__REAL_IP__', 'REAL_IP_BLOCK'), ('__FORWARD_HEADERS__', 'FORWARD_BLOCK')]:
    s = s.replace(key, os.environ[env])
s = s.replace('__DRY_RUN__', 'on')          # always start in dry-run
import re
assert not re.search(r'__[A-Z_]+__', s), 'unreplaced placeholder'
open(sys.argv[2], 'w').write(s)
PY
ln -sf "$SITE_CONF" /etc/nginx/sites-enabled/rulezet
if [ -L /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default      # the stock "Welcome to nginx" site (still in sites-available)
fi
nginx -t || die "nginx rejected the config — nothing is running, Rulezet is untouched."

cat > "$STATE" <<EOF
MODE=$MODE
SITE_PORT=$SITE_PORT
API_PORT=$API_PORT
REAL_IP_CONFIGURED=$([ -n "$REAL_IP_BLOCK" ] || [ "$MODE" = direct ] && echo yes || echo no)
ROOT=$ROOT
EOF

echo
echo "✔ nginx is installed and configured, but NOT running — the site is unchanged."
echo "  Config: $SITE_CONF   (mode: $MODE, rate limiting in dry-run)"
echo
echo "  Next step, when you're ready (≈20 s of downtime while Rulezet restarts):"
echo "      bash deploy/nginx_switch.sh on"
