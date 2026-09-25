# Production hardening: Redis cache, nginx, separate API process

Everything here is **opt-in and reversible**. Until you run these scripts, Rulezet runs exactly as before
(gunicorn directly on port 80, file cache, one process). Run every command as root from `rulezet-core/`.

Rulezet runs in a `screen` session. "Restart Rulezet" always means:

```
screen -r                        # attach
Ctrl-C                           # stop Rulezet
python3 manage.py restart-prod   # start it again
Ctrl-A then D                    # detach (the site keeps running)
```

## 1. Redis cache (≈ 5 min, ≈ 20 s downtime)

The cache moves from files on disk to memory: fast whatever its size, shareable by several processes.

```
bash deploy/setup_redis.sh       # installs Redis (localhost only, 256 MB), edits .env
# → restart Rulezet
```

If Redis is ever unreachable, Rulezet starts on the old file cache by itself and prints
`[cache] Redis unavailable … falling back to FileSystemCache` — the site keeps working.

**Undo:** `bash deploy/setup_redis.sh --undo` → restart Rulezet.

## 2. nginx in front of Rulezet (≈ 15 min, ≈ 20 s downtime)

What it brings:

- **The API gets its own process**: `/api/…` is served by a second gunicorn. An API flood (an external tool
  calling the CVE search in a loop, a scraper…) saturates that process only — the website keeps its own.
- **Separate logs with response times**: `/var/log/nginx/rulezet-site.access.log` and
  `/var/log/nginx/rulezet-api.access.log` (the number before the user-agent is the time in seconds).
- **Per-IP rate limiting** (site 30 req/s, API 20 req/s, generous bursts; static files never limited).
  It starts in **dry-run**: nginx only *logs* who would have been limited, nobody is blocked.

Steps:

```
bash deploy/setup_nginx.sh       # installs + configures nginx, does NOT start it (site unchanged)
bash deploy/nginx_switch.sh on   # edits .env, then waits while you restart Rulezet,
                                 # then starts nginx and checks the site answers
```

After a few days, check who would have been limited, allowlist legitimate tools, then enforce:

```
bash deploy/nginx_switch.sh report
echo '203.0.113.7 1;' >> /etc/nginx/rulezet-allowlist.conf && systemctl reload nginx   # never limit this IP
bash deploy/nginx_switch.sh enforce       # real 429s above the limits
bash deploy/nginx_switch.sh dry-run       # back to log-only at any time
bash deploy/nginx_switch.sh status        # what runs where
```

**Undo:** `bash deploy/nginx_switch.sh off` → restart Rulezet. nginx is stopped and the four launch settings it
changed in `.env` (`GUNICORN_BIND_HOST`, `PORT`, `API_PORT`, `TRUSTED_PROXY_COUNT`) get their previous values back.

### Notes

- If a proxy already sits in front of this server (`TRUSTED_PROXY_COUNT` > 0 in `.env`), nginx passes its
  `X-Forwarded-*` headers through unchanged, so Rulezet sees exactly what it saw before. `setup_nginx.sh`
  asks for that proxy's IP (it suggests the one currently connecting) — needed for per-visitor limits.
- The script refuses to run if something already listens on port 443 (a TLS setup it doesn't handle).
- Uploads up to 200 MB are allowed (nginx's default of 1 MB would break rule/bundle imports).

## Launch settings (`.env`, read by `manage.py`)

| Key | Default | Meaning |
|---|---|---|
| `PORT` | `80` | port of the website gunicorn |
| `GUNICORN_BIND_HOST` | `0.0.0.0` | listen address (`127.0.0.1` behind nginx) |
| `GUNICORN_THREADS` | `8` | threads of the website process |
| `API_PORT` | — | if set, a second gunicorn dedicated to `/api/` on that port |
| `API_GUNICORN_THREADS` | `8` | threads of the API process |
| `LOG_DIR` | — | write gunicorn logs to `site-*.log` / `api-*.log` there instead of the screen |
