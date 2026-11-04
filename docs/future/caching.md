# Caching — plan

More and more users, the API and AI crawlers (Claude…) reading rule pages: time to cache.
The proposal, step by step, cheapest / biggest win first. Work on branch `cache`; what is done is in **§6 Progress**.

---

## 1. What already exists

| Piece | Where | State |
|---|---|---|
| `cache` (Flask-Caching) | `app/__init__.py`, `config.py` | FileSystemCache by default, Redis if `.env` has `CACHE_TYPE=RedisCache` |
| `memory_cache` | `app/__init__.py` | in-process SimpleCache, 60 s — **not shared** between the site and API processes |
| Rule lists / filters | `app/features/rule/rule.py` | 60 s, anonymous only |
| Usage stats (sources, licences, authors…) | `rule.py` | 60 s |
| Suricata feed | `rule.py` `/feed/suricata.rules` | 1 h |
| Home, sitemaps, ATT&CK | `home.py`, `seo.py`, `attack.py` | 6 h – 24 h |
| API `search_rules_by_cve` | `app/api/rule/rule_public_api.py` | 60 s |
| Static files | `static_versions.py` | versioned URL + `immutable` 1 year ✅ |

Gunicorn: **1 worker `gthread`** per process (site + API), behind nginx (`deploy/nginx/rulezet.conf.template`).

---

## 2. What is expensive today

### 🔴 Rule page `/rule/detail_rule/<id>` — no cache at all
On **every** view (crawlers included):
- MISP object + MISP event generated
- Velociraptor artifact generated
- `json.dumps(rule.to_json_detail())`
- risk flags computed
- `_nav_counts()` → **~10 `COUNT` queries** (bundles, similarity, history, proposals, scope, tests, AI…)

### 🔴 Public API — almost no cache
`/api/rule/public/detail/<id>`, `search`, `searchPage`, `all_by_user`: computed every time.

### 🟠 nginx proxies `/static/` to gunicorn
Every CSS / JS / image takes a Python thread instead of being served from disk by nginx.

---

## 3. The plan

### Step 0 — Measure first (≈ 1 h)
nginx already logs with the `rz_timed` format. A small script → ranking of routes by
**total time**, **number of calls**, **user-agent** (bots / Claude / API / humans).
We then know exactly where to act.

### Step 1 — nginx (biggest win, almost no code)
- [ ] Serve `/static/` **directly from disk** (`alias`, `expires max`, `gzip`).
- [ ] **Micro-cache 30–60 s** (`proxy_cache`) on anonymous GETs: rule pages, public API, home, sitemaps.
- [ ] **Bypass** automatically when there is a session cookie, an `X-API-KEY` header, or a non-GET.

> Crawlers and Claude are almost always anonymous → answered by nginx, no Python, no PostgreSQL.

### Step 2 — Rule page, versioned cache key
- Key: `rule:<id>:<last_modif>` → a rule edit changes the key, **no manual invalidation**.
- **Anonymous**: the whole rendered HTML is cached.
- **Logged in**: only the heavy, same-for-everyone parts (MISP, Velociraptor, JSON, risk flags,
  public counts). The user's vote and rights stay live.

### Step 3 — Public API
- [ ] Same versioned cache on `detail`, `search`, `searchPage`.
- [ ] `ETag` / `Last-Modified` + **304 Not Modified**: a crawler coming back downloads nothing
  if the rule did not change.

### Step 4 — Global "rules generation" counter in Redis
A counter bumped on every rule create / edit / delete, part of the list & search cache keys.
→ TTL can go from **60 s to 10 min+** with never stale data.

### Step 5 — Redis for both caches in production
- [ ] `memory_cache` on Redis too → site and API processes share one cache.
- [ ] Drop FileSystemCache in prod.

---

## 4. Watch out

| Risk | Answer |
|---|---|
| TLP:RED / AMBER rule, or a page that depends on the viewer's rights, in a public cache | explicit bypass, never cached publicly |
| CSRF token / logged-in navbar inside the HTML | full-page cache **anonymous only** |
| Stale data after an edit | versioned keys (`last_modif`, rules generation) instead of long TTLs |
| Tests run with `NullCache` | add a few tests that check versioned invalidation |

---

## 5. Order

| # | Step | Effort | Gain |
|---|---|---|---|
| 0 | Measure (logs) | 🟢 low | knows where to act |
| 1 | nginx static + micro-cache | 🟢 low | 🔥🔥🔥 |
| 2 | Rule page cache | 🟠 medium | 🔥🔥 |
| 3 | API cache + ETag/304 | 🟠 medium | 🔥🔥 |
| 4 | Rules generation counter | 🟠 medium | 🔥 |
| 5 | Redis for both caches | 🟢 low | 🔥 |

**Recommendation:** step 0 then step 1, then step 2.

---

## 6. Progress

### ✅ Step 0 — Measure (`deploy/nginx/top_routes.py`)
Reads nginx `rz_timed` logs (plain or `.gz`), groups routes (numbers / UUIDs / CVE / ATT&CK ids → `:id`,
query string dropped) and clients (`ai`, `bot`, `api`, `browser`), ranks by total time.

```bash
python3 deploy/nginx/top_routes.py /var/log/nginx/rulezet-site.access.log* /var/log/nginx/rulezet-api.access.log*
python3 deploy/nginx/top_routes.py --by count --top 40 /var/log/nginx/*.access.log
```
Standard library only — runs on the server without the venv.
**Tests:** `tests/cache/test_top_routes.py` (route / client grouping, aggregation, report).
**To do on prod:** run it once and paste the top 20 here, to confirm the targets of steps 2–3.

### ✅ Step 1 — nginx (`deploy/nginx/rulezet.conf.template`, `deploy/setup_nginx.sh`)
- **Static files from disk**: `location /static/` → `root <repo>/app`, `try_files` falls back to the app
  if nginx cannot read a file. `?v=` URLs get `public, max-age=31536000, immutable`, others 1 h; `nosniff` kept.
  `setup_nginx.sh` makes `app/static` readable by `www-data` (and its parent folders traversable).
- **gzip** for CSS / JS / JSON / SVG / XML / text.
- **Micro-cache** `rz_cache` (`/var/cache/nginx/rulezet`, 1 GB max): 200 / 301 / 302 kept 60 s, 404 10 s.
  `proxy_cache_lock` (a cold page hit 100 times = 1 render), `use_stale updating / error / timeout / 502–504`
  (visitors keep getting pages during a restart), background update. Header `X-Cache-Status` (HIT / MISS / BYPASS / STALE).
- **Never cached**: session or `remember_token` cookie, `X-API-KEY`, `Authorization`, non-GET,
  answers with `Set-Cookie` (any page that touches the session, e.g. a form with a CSRF token),
  answers with `Cache-Control: private / no-store`.
- **App side** (`app/__init__.py`, `_private_when_signed_in`): every answer to a signed-in user gets
  `Cache-Control: private` (belt and braces with the cookie bypass), every page `Vary: Cookie`.

**Tests:**
- `bash deploy/nginx/test_nginx_cache.sh` — a real nginx (Docker, `nginx:1.24-alpine`) with the generated
  config in front of a fake backend that counts hits. Checks: config accepted, anonymous page + public API
  served from the cache (backend hit once), session / remember cookie / API key / Authorization bypass,
  a harmless cookie still hits, `Set-Cookie` answers not stored, POST not cached, static from disk
  (immutable when versioned, gzip, nosniff), missing static file falls back to the app. **All pass.**
- `tests/cache/test_cache_headers.py` — anonymous rule page not private + `Vary: Cookie`; signed-in rule page,
  home, rule list private; versioned static stays public.

#### Found while testing: every anonymous page created a session
`base.html` calls `csrf_token()` on every page → for a visitor without a cookie, Flask-Session
created a **`flask_sessions` row + `Set-Cookie` on every hit** (crawlers included: one DB write per page),
and nginx can never cache an answer with `Set-Cookie`. So the micro-cache would only have helped the API.

Fix — `app/core/utils/anon_csrf.py`:
- anonymous visitor **without** a session → the token is derived from a raw value shared by all
  anonymous visitors (`HMAC(SECRET_KEY, "rz-anon-csrf:<day>")`, today or yesterday accepted);
  the session is dropped before it is saved → **no cookie, no DB row, page cacheable**;
- on their first POST the session is created with that raw value → Flask-WTF validates as usual;
- **kept as before** (own random value): signed-in users, visitors who already have a session,
  account pages (`login`, `add_user`, `verify`, `forgot_password`, `reset_password`, `oidc_login`).

#### 🔒 Security review — step 1
| Risk | Answer | Checked by |
|---|---|---|
| A signed-in page in the shared cache | bypass on session / remember cookie, API key, Authorization; app adds `Cache-Control: private` to every signed-in answer; nginx never stores `Set-Cookie` / `private` answers | `test_nginx_cache.sh` §2–3, `test_cache_headers.py` |
| **Cache poisoning** (forged `X-Forwarded-Host` / `-Proto`, trusted by ProxyFix when a proxy is in front, builds links in the page) | both headers are part of the cache key | `test_nginx_cache.sh` §6 |
| Static files from nginx lose the app's security headers | `nosniff`, `X-Frame-Options`, `frame-ancestors`, `Referrer-Policy` set by nginx | `test_nginx_cache.sh` §7 |
| Uploaded SVG / HTML in `/static/uploads/` running a script | `Content-Security-Policy: …; sandbox` on uploads (nginx **and** app — stricter than before) | `test_nginx_cache.sh` §7, `test_uploads_are_sandboxed` |
| Dotfiles / path traversal from disk | dotfiles → 404, `root` limited to `app/static`, traversal attempts checked | `test_nginx_cache.sh` §7 |
| Shared anonymous CSRF value known to anyone | only ever for **anonymous** actions (nothing tied to an account); never on account pages (no login CSRF: the shared token cannot log in); a session holding it swaps it for its own on sign-in or on an account page; **refused when the POST comes from another site** (`Origin` / `Referer` not ours, or `Origin: null`); disabled when `SECRET_KEY` is empty | `test_anon_csrf.py` (no cookie, POST ok, bad / missing token refused, login page own token, shared token cannot log in, token rotated after sign-in, cross-site refused, no secret) |
| Cache filled with unique URLs (DoS) | `max_size=1g`, `inactive=10m`, rate limits still apply before the cache | — |
| Stale page after an edit | 60 s at most for anonymous visitors (signed-in users always live) | — |

**To deploy:** `sudo bash deploy/setup_nginx.sh` (re-generates the config), then `nginx -t && systemctl reload nginx`.
Check: `curl -sI https://rulezet.org/rule/detail_rule/1 | grep -i x-cache` twice → `MISS` then `HIT`.

### ✅ Step 4 — Rule generations (`app/core/utils/cache_versions.py`) — done before 2 and 3, which use it
- `rule_key(kind, rule_id, *parts)` → `rz:rule:<kind>:<id>:<rule gen>:<bulk gen>[:<hash>]`
- `rules_key(kind, *parts)` → `rz:rules:<kind>:<global gen>:<hash>` (lists, searches, stats)
- **Bumped automatically on commit** (SQLAlchemy `after_flush` / `after_commit`): a change to a `Rule` row
  or to **any row with a `rule_id`** (votes, comments, tags, history, bundle links, proposals…) bumps that
  rule + the global generation. `query.update()` / `delete()` on a rule table (soft-delete batches, bulk jobs)
  bump the *bulk* generation, part of every rule key. Rollback → nothing bumped.
- A generation is a unique value (`time_ns`), never a counter: evicted → comes back new, an old entry can
  never become valid again. Stored in the shared `cache` (Redis in prod): site, API and worker all see it.
- No manual invalidation to remember anywhere.

**Tests:** `tests/cache/test_cache_versions.py` — stable keys, edit → new rule + list key, a vote (row with
`rule_id`) → new rule key, other rules untouched, rollback bumps nothing, bulk update → every key new,
evicted generation never brings old entries back. **7 pass.** (`tests/cache/conftest.py` gives these tests a
real SimpleCache — the suite runs with NullCache.)

#### 🔒 Security review — step 4
| Risk | Answer |
|---|---|
| Stale data shown after a change made outside the ORM (raw SQL on a connection) | not bumped → bounded by the entry's own timeout; every write path in the app goes through the session |
| Cache growing without end | one generation key per rule (no expiry), entries themselves always have a timeout |
| A cache failure breaking a commit | every cache call is wrapped: a failing cache = no bump, never an exception |

**Regression run:** `tests/cache tests/account tests/home` → **90 passed**.
