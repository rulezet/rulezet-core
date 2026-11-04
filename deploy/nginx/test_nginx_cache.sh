#!/usr/bin/env bash
# End-to-end check of the nginx caching config (deploy/nginx/rulezet.conf.template) in Docker:
# a real nginx in front of a fake backend that counts the requests it gets.
#   bash deploy/nginx/test_nginx_cache.sh        (needs docker; uses ports 18080-18082 on localhost)
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
mkdir -p "$ROOT/data"; WORK="$(mktemp -d "$ROOT/data/nginx-test.XXXXXX")"   # under the repo: snap docker cannot mount /tmp; trap 'docker rm -f rz-nginx-test >/dev/null 2>&1 || true; kill $BACKEND 2>/dev/null || true; rm -rf "$WORK"' EXIT
IMAGE="${NGINX_IMAGE:-nginx:1.24-alpine}"
fail() { echo "✘ $*"; exit 1; }

# Fake backend: counts hits per path; ?cookie=1 answers with Set-Cookie, a session cookie gets "private"
cat > "$WORK/backend.py" <<'PY'
import http.server, sys
hits = {}
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        hits[self.path] = hits.get(self.path, 0) + 1
        body = f"{self.path} hit {hits[self.path]} host={self.headers.get('X-Forwarded-Host')}\n".encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        if 'cookie=1' in self.path:
            self.send_header('Set-Cookie', 'session=abc')
        if 'session=' in (self.headers.get('Cookie') or ''):
            self.send_header('Cache-Control', 'private')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)
    do_POST = do_GET
http.server.ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()
PY
fuser -s 18081/tcp 2>/dev/null && fail "port 18081 already in use"
python3 "$WORK/backend.py" 18081 >/dev/null 2>&1 & BACKEND=$!

# The config as setup_nginx.sh writes it (port 18080 instead of 80, no real-IP block)
python3 - "$ROOT/deploy/nginx/rulezet.conf.template" "$WORK/rulezet.conf" <<'PY'
import re, sys
s = open(sys.argv[1]).read()
for k, v in {'__SERVER_NAME__': '_', '__SITE_PORT__': '18081', '__API_PORT__': '18081', '__SITE_RATE__': '100r/s',
             '__SITE_BURST__': '100', '__API_RATE__': '100r/s', '__API_BURST__': '100', '__REAL_IP__': '',
             '__FORWARD_HEADERS__': '', '__APP_DIR__': '/srv/app', '__SESSION_COOKIE__': 'session', '__DRY_RUN__': 'on'}.items():
    s = s.replace(k, v)
s = s.replace('listen 80 default_server;', 'listen 18080 default_server;').replace('listen [::]:80 default_server;', '')
assert not re.search(r'__[A-Z_]+__', s)
open(sys.argv[2], 'w').write(s)
PY
mkdir -p "$WORK/snippets"; cp "$ROOT/deploy/nginx/maintenance.conf" "$WORK/snippets/rulezet-maintenance.conf"
echo "" > "$WORK/allowlist.conf"
cat > "$WORK/nginx.conf" <<'NG'
events {}
http { include /etc/nginx/mime.types; include /etc/nginx/conf.d/rulezet.conf; }
NG
docker run -d --name rz-nginx-test --network host \
    -v "$WORK/nginx.conf:/etc/nginx/nginx.conf:ro" -v "$WORK/rulezet.conf:/etc/nginx/conf.d/rulezet.conf:ro" \
    -v "$WORK/snippets:/etc/nginx/snippets:ro" -v "$WORK/allowlist.conf:/etc/nginx/rulezet-allowlist.conf:ro" \
    -v "$ROOT/app/static:/srv/app/static:ro" "$IMAGE" sh -c 'mkdir -p /var/cache/nginx/rulezet /var/log/nginx && nginx -g "daemon off;"' >/dev/null
for _ in $(seq 30); do curl -s -o /dev/null http://127.0.0.1:18080/ && break; sleep 0.2; done
docker exec rz-nginx-test nginx -t >/dev/null 2>&1 || fail "nginx -t rejected the config"
echo "✔ nginx accepts the config"

get() { curl -s -m 5 "$@"; }
status() { curl -s -m 5 -o /dev/null -D - "$@" | tr -d '\r' | awk 'tolower($1)=="x-cache-status:"{print $2}'; }

# 1. Anonymous GET: second hit comes from the cache (backend saw it once)
get http://127.0.0.1:18080/rule/detail_rule/1 >/dev/null
[ "$(status http://127.0.0.1:18080/rule/detail_rule/1)" = HIT ] || fail "anonymous page not cached"
get http://127.0.0.1:18080/rule/detail_rule/1 | grep -q "hit 1" || fail "backend called twice"
echo "✔ anonymous page served from the cache"
get http://127.0.0.1:18080/api/rule/public/detail/1 >/dev/null
[ "$(status http://127.0.0.1:18080/api/rule/public/detail/1)" = HIT ] || fail "anonymous API answer not cached"
echo "✔ anonymous public API answer served from the cache"

# 2. Signed-in (session / remember cookie), API key, Authorization: never from the cache
[ "$(status -H 'Cookie: theme=dark; session=x' http://127.0.0.1:18080/rule/detail_rule/1)" = BYPASS ] || fail "session cookie not bypassed"
[ "$(status -H 'Cookie: remember_token=x' http://127.0.0.1:18080/rule/detail_rule/1)" = BYPASS ] || fail "remember cookie not bypassed"
[ "$(status -H 'X-API-KEY: k' http://127.0.0.1:18080/api/rule/public/detail/1)" = BYPASS ] || fail "API key not bypassed"
[ "$(status -H 'Authorization: Bearer k' http://127.0.0.1:18080/api/rule/public/detail/1)" = BYPASS ] || fail "Authorization not bypassed"
[ "$(status -H 'Cookie: theme=dark' http://127.0.0.1:18080/rule/detail_rule/1)" = HIT ] || fail "a harmless cookie should not bypass"
echo "✔ session / remember cookie, API key, Authorization bypass the cache"

# 3. A response with Set-Cookie is never stored
get "http://127.0.0.1:18080/login?cookie=1" >/dev/null
get "http://127.0.0.1:18080/login?cookie=1" | grep -q "hit 2" || fail "a Set-Cookie answer was cached"
echo "✔ answers with Set-Cookie are not cached"

# 4. POST never cached
curl -s -X POST http://127.0.0.1:18080/rule/x >/dev/null
curl -s -X POST http://127.0.0.1:18080/rule/x | grep -q "hit 2" || fail "POST cached"
echo "✔ POST is not cached"

# 5. Static: from disk (backend never sees it), versioned = immutable, missing file falls back to the app
CSS="$(cd app/static && ls css/*.css | head -1)"
H="$(curl -s -o /dev/null -D - "http://127.0.0.1:18080/static/$CSS?v=123" | tr -d '\r')"
echo "$H" | grep -qi '^cache-control: public, max-age=31536000, immutable' || fail "versioned static not immutable"
echo "$H" | grep -qi '^x-content-type-options: nosniff' || fail "static without nosniff"
curl -s -D - -o /dev/null -H 'Accept-Encoding: gzip' "http://127.0.0.1:18080/static/$CSS" | tr -d '\r' | grep -qi '^content-encoding: gzip' || fail "static CSS not gzipped"
get http://127.0.0.1:18080/static/does/not/exist.js | grep -q "/static/does/not/exist.js hit 1" || fail "missing static file did not fall back to the app"
echo "✔ static files from disk (immutable when versioned, gzip, nosniff), fallback to the app"

# 6. Cache poisoning: a forged X-Forwarded-Host never reaches the page others get
get -H 'X-Forwarded-Host: evil.example' http://127.0.0.1:18080/rule/poison | grep -q "host=evil.example" || fail "backend did not see the header"
get http://127.0.0.1:18080/rule/poison | grep -q "evil.example" && fail "poisoned page served to everybody"
echo "✔ X-Forwarded-Host / -Proto are part of the cache key (no poisoning)"

# 7. Uploads sandboxed, dotfiles never served, security headers on static
mkdir -p app/static/uploads/blog && UP="app/static/uploads/blog/_nginx_test.svg"
echo '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>' > "$UP"; chmod o+r "$UP"
H="$(curl -s -o /dev/null -D - http://127.0.0.1:18080/static/uploads/blog/_nginx_test.svg | tr -d '\r')"; rm -f "$UP"
echo "$H" | grep -qi '^content-security-policy:.*sandbox' || fail "uploads without the CSP sandbox"
echo "$H" | grep -qi '^x-content-type-options: nosniff' || fail "uploads without nosniff"
[ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/static/uploads/nope.svg)" = 404 ] || fail "missing upload not 404"
[ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/static/.gitignore)" = 404 ] || fail "dotfile served"
for u in '/static/../../etc/passwd' '/static/%2e%2e/%2e%2e/etc/passwd' '/static/css/..%2f..%2f..%2fetc/passwd'; do
    curl -s --path-as-is "http://127.0.0.1:18080$u" | grep -q 'root:' && fail "path traversal: $u"
done
H="$(curl -s -o /dev/null -D - "http://127.0.0.1:18080/static/$CSS" | tr -d '\r')"
for h in 'x-frame-options: SAMEORIGIN' "content-security-policy: frame-ancestors 'self'" 'referrer-policy: strict-origin-when-cross-origin'; do
    echo "$H" | grep -qi "^$h" || fail "static without $h"
done
echo "✔ uploads sandboxed (CSP), no dotfile, no traversal, security headers on static files"

echo "All nginx cache checks passed."
