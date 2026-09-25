#!/usr/bin/env bash
# Rulezet — install a local Redis and switch the Flask cache to it.
#
# Why: the default FileSystemCache is a directory of files on disk; Redis
# keeps the cache in memory, is fast whatever its size, and can be shared
# by several gunicorn processes later on.
#
# Safe by design:
#   - Redis only listens on 127.0.0.1 (never reachable from the internet)
#   - memory capped (256 MB), oldest entries evicted automatically
#   - .env is backed up before being touched
#   - if Redis is ever down when Rulezet starts, Rulezet falls back to the
#     old file cache by itself (see app/__init__.py)
#
# Usage (as root, from the rulezet-core folder):
#   bash deploy/setup_redis.sh            # install + enable in .env
#   bash deploy/setup_redis.sh --undo     # go back to the file cache
# Then restart Rulezet in its screen:  python3 manage.py restart-prod
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE=".env"

[ "$(id -u)" -eq 0 ] || { echo "Run this as root (sudo)."; exit 1; }
[ -f "$ENV_FILE" ] || { echo "No .env found in $(pwd) — run this from rulezet-core."; exit 1; }

strip_cache_lines() { sed -i '/^CACHE_TYPE=/d;/^CACHE_REDIS_URL=/d;/^# Redis cache (deploy\/setup_redis.sh)/d' "$ENV_FILE"; }

if [ "${1:-}" = "--undo" ]; then
    cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d-%H%M%S)"
    strip_cache_lines
    echo "✔ .env no longer uses Redis (backup saved next to it)."
    echo "→ Restart Rulezet in its screen:  python3 manage.py restart-prod"
    echo "  (Redis itself is still installed; 'systemctl disable --now redis-server' to stop it.)"
    exit 0
fi

echo "==> Installing Redis…"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq redis-server

echo "==> Configuring Redis (local only, 256 MB max)…"
CONF=/etc/redis/redis.conf
cp -n "$CONF" "$CONF.rulezet-orig" || true
sed -i 's/^#\?\s*bind .*/bind 127.0.0.1 -::1/' "$CONF"
sed -i 's/^#\?\s*protected-mode .*/protected-mode yes/' "$CONF"
grep -q '^maxmemory ' "$CONF" && sed -i 's/^maxmemory .*/maxmemory 256mb/' "$CONF" || echo 'maxmemory 256mb' >> "$CONF"
grep -q '^maxmemory-policy ' "$CONF" && sed -i 's/^maxmemory-policy .*/maxmemory-policy allkeys-lru/' "$CONF" || echo 'maxmemory-policy allkeys-lru' >> "$CONF"
systemctl enable --now redis-server
systemctl restart redis-server
sleep 1
redis-cli ping | grep -q PONG || { echo "✘ Redis does not answer — nothing changed in .env."; exit 1; }
echo "✔ Redis is running (redis-cli ping → PONG)."

echo "==> Installing the Python client in Rulezet's venv…"
./env/bin/pip install -q redis

echo "==> Switching the cache to Redis in .env…"
cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d-%H%M%S)"
strip_cache_lines
{
    echo "# Redis cache (deploy/setup_redis.sh)"
    echo "CACHE_TYPE=RedisCache"
    echo "CACHE_REDIS_URL=redis://127.0.0.1:6379/0"
} >> "$ENV_FILE"

echo
echo "✔ Done. Last step: restart Rulezet in its screen:"
echo "    screen -r <rulezet screen>   → Ctrl-C → python3 manage.py restart-prod → Ctrl-A D"
echo "  On startup Rulezet prints '[cache] Redis unavailable … falling back' if something is wrong"
echo "  (the site keeps working either way). Undo at any time: bash deploy/setup_redis.sh --undo"
