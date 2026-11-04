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

### ✅ Step 2 — Rule page (`app/core/utils/page_cache.py`, `app/features/rule/rule.py`)
- **Anonymous visitors: the whole page** — `anonymous_page(rule_key('page', id, host, path+query), render)`.
  Served / stored only when the page is the same for every anonymous visitor: GET, nobody signed in, no API key,
  a session holding nothing but the shared anonymous CSRF value (no flash message, no per-visitor token).
  Kept `cache.rule_page_seconds` (30 min), always below the CSRF token lifetime (`WTF_CSRF_TIME_LIMIT` − 10 min).
- **Everybody: the shared parts** — `_rule_detail_parts()`: MISP object + event, Velociraptor artifact,
  risk flags, mirror links, metadata display, public tab counts (similarity, history, proposals, scope, links).
  Kept `cache.rule_parts_seconds` (10 min) — bounds what depends on other rules (SID collisions) or settings.
- **Always live** (depend on the viewer): the JSON tab (`is_favorited`), the user's vote, bundle count
  (private bundles), test / AI-analysis / sample counts, sample results.
- Header `X-App-Cache: HIT / MISS` on cached answers.

**Tests:** `tests/cache/test_rule_page_cache.py` — MISS then HIT, other `?tab=` = other entry, an edit gives
a fresh page with the new title, signed-in user never gets the shared page (and gets `private`), a visitor
with a flash message gets a live page (and nothing of theirs is stored), shared parts computed once for a
signed-in user + an anonymous one. **5 pass.**

### ✅ Step 3 — Public API (`page_cache.api_cached`, `app/api/rule/rule_public_api.py`)
- `@api_cached('detail', rule_arg='rule_id')` on `/api/rule/public/detail/<id>` (follows that rule's version),
  `@api_cached('search')` / `('search_page')` on `search` / `searchPage` (follow every rule change).
  Kept `cache.api_seconds` (5 min). Only 200 answers are stored.
- **ETag + 304**: every answer of these endpoints carries a strong ETag; `If-None-Match` → `304`, empty body.
- Never cached: a call with `X-API-KEY`, `Authorization` or a signed-in session.

**Tests:** `tests/cache/test_api_cache.py` — detail MISS → HIT → MISS after an edit (new title), ETag → 304,
search / searchPage per query + refreshed by any rule change, 404 never stored, API key bypasses,
a rule in the trash is a 404.

#### 🔒 Security review — steps 2 & 3
| Risk | Answer | Checked by |
|---|---|---|
| One visitor's page (flash message, CSRF token of their own session, their name) served to others | whole-page cache only when the session holds nothing but the shared anonymous value; checked again after rendering before storing | `test_visitor_with_a_flash_message_gets_a_live_page` |
| A signed-in user getting the anonymous copy (missing their rights / buttons) or the reverse | signed-in → never read, never stored | `test_signed_in_never_gets_the_shared_page` |
| Viewer-dependent values in the shared parts (private bundles, private AI analyses, visible tests, favourite) | those stay live, listed above; only values identical for every viewer are shared | code review + `test_shared_parts_computed_once_for_everybody` |
| Host-dependent links (Velociraptor `base_url`, API `next` URLs) mixed between hosts | host is part of every key | — |
| A CSRF token in a cached page outliving its validity | page kept at most token lifetime − 10 min | `_max_timeout` |
| API answer built for a key holder served to the public | `X-API-KEY` / `Authorization` / session → no cache | `test_errors_and_keys_are_never_cached` |
| **Found during review:** `/api/rule/public/detail/<id>` returned rules that are in the **trash** | now 404 (and never cached) | `test_deleted_rule_not_served_by_the_api` |

### ✅ Admin control — Admin → Settings → **Cache** tab (expert) — `/admin/settings?tab=cache`
`app/features/admin/cache/` (`cache_core.py`, `cache_routes.py` — JSON status + actions; `/admin/cache`
redirects to the tab), component `static/js/admin/cachePanel.js` (loaded only when the tab is opened),
`static/css/admin/cache.css`. Not in the admin navs: it lives in Settings. The old *Caches* box of the System
tab (same action as *Empty both caches*) and its route `/admin/settings/cache/clear` were removed.
- **Status**: backend (Redis: keys + memory; warns when the cache is not shared between processes), app cache
  on / off, share of anonymous pages and of shared parts / API answers served from the cache (hit / miss counters).
- **Settings** (Admin → Configuration, category *Cache*, files `app/config/cache.*.json`):
  `cache.enabled`, `cache.rule_page_seconds` (1800), `cache.rule_parts_seconds` (600), `cache.api_seconds` (300).
- **Actions** (each logged: `cache.refresh_rules`, `cache.refresh_rule`, `cache.clear_all`, `cache.reset_stats`):
  refresh every rule, refresh one rule, empty both caches (with a confirmation), reset the counters.
- **Admins only** (`before_request`: anonymous → login, signed-in non-admin → 403, POST included).

### ✅ Workflows
- Task types `cache_refresh_rules` (*Caches — refresh every rule page*) and `cache_warm_rules`
  (*Caches — warm the most voted rule pages*, option `limit`, default 200, at most 5000; renders as an anonymous
  visitor at `INSTANCE_PUBLIC_URL` so the warmed key is the one real visitors read). Handlers in `job_handlers.py`.
- Template **Cache maintenance** (`workflows.templates.json` → `cache_maintenance`): daily 04:00 UTC refresh →
  (if it succeeds) warm 200 → log line.
- The existing `clear_caches` task and the *Weekly maintenance* template are unchanged.

**Tests:** `tests/cache/test_cache_admin.py` — admin only (anonymous redirect, user 403 on page and action),
page + status, every action (+ bad / unknown input, activity log written), hit ratio counted, `cache.enabled` off →
live pages, both workflow tasks (refresh changes keys, warm makes the next visit a HIT), template valid
(known task types, `after` references exist, daily trigger).

### ✅ Documentation
- In the app: *Full documentation* → chapter 25 *Administration* → **Cache & performance**.
- This file: plan, progress, tests, security reviews.

#### 🔒 Security review — admin & workflows
| Risk | Answer |
|---|---|
| A non-admin emptying the cache (slows the site) or reading its state | `before_request` admin check on the whole blueprint, POST with CSRF |
| Warm task used to hammer the site | runs in the worker, in-process (no HTTP), capped at 5000 rules |
| Untraceable changes | every action in the activity log with the admin's name |

### ✅ `/api/rule/public/search_rules_by_cve` — never restricted
Called heavily by the **vulnerability-lookup** tool, which depends on its exact answer format.
- nginx: its own exact `location =` **without `limit_req`** — never rate-limited, whatever the dry-run state.
  It still goes through the 60 s micro-cache (only faster, same answer).
- App: route, parameters and JSON format untouched; its existing 60 s `memory_cache` kept; no `api_cached` on it.
- **Test:** `test_nginx_cache.sh` §8 — with real limits on (1 r/s, burst 25), 40 CVE lookups in a row → no 429,
  while 40 calls to another API route do get 429.

### ✅ User page — Activity data (`/account/user_activity_stats/<id>`)
Loaded every rule of the user as full objects on each visit (thousands for a big contributor). Now only the 4 columns
used, and the answer from the shared cache: `rules_key('user_activity', id)` (any rule change → fresh), setting
`cache.user_activity_seconds` (300 s, bounds bundle votes). Same answer as before.
**Tests:** `tests/cache/test_user_activity_cache.py` — a vote shows at once, cached answer = live answer, login + 404 kept.

### ✅ Workflow task — Similar rules (`similar_rules_scan`)
Runs **exactly** the analysis of Admin → Similar rules (same `Similarity_class`, same parameters as its buttons):
*New rules only* → `{mode: new_only}`, *Every rule* → `{mode: all}`. The run shows in that page's history; the task
waits for it (polls its status like the progress page — that is also what lets it save its figures), never more than
6 h, and returns at once if the run ended early (nothing to scan, error).
**Found during review:** `/rule/similar_rules/update` was open to any signed-in user — including the GET that
**wipes every similarity pair** (and a GET has no CSRF protection). Now: whole-instance runs (GET, `all`, `new_only`)
admins only; a signed-in user may only refresh one rule (the button of the rule page).
**Tests:** `tests/cache/test_similar_rules_task.py` — registered, same parameters as the page for both scopes, does not
wait for a run that ended, bad scope fails, who may launch what.

### ✅ Freshness — "always the latest rules"
| Change | What visitors see |
|---|---|
| Rule edited, voted, commented, tagged, linked, bundled | that rule's page, parts and API answer: **at once** (new key at commit) |
| New rule, deleted rule, any rule change | lists, searches, API search, user activity: **at once** (global generation) |
| Bulk jobs (tags, ATT&CK, similarity, soft-delete batches, imports) — `query.update()`, `bulk_insert_mappings` | every rule key: **at once** (bulk generation) |
| A deploy (new code / templates) | **at once**: the keys hold the git commit (`code_version`); dev (debug) also the process start |
| nginx micro-cache, anonymous visitors only | at most **60 s** later |
| Home figures, ATT&CK / CVE stats (not versioned) | their own timeouts, or the `clear_caches` task |

### ✅ Workflows that clear the caches — still right
`clear_caches` is the last task of the templates *Weekly maintenance*, *Bad rules cleanup*, *Threat intel refresh*,
*Rules enrichment*, *Quality refresh*. Still useful and kept: it resets what is **not** versioned (home figures, ATT&CK /
CVE stats, leaderboard) — rule pages no longer need it (they refresh themselves). Nothing to change in them.
Note: emptying the cache also forgets "update notice dismissed" and the generations (they come back as new values: safe).

### ✅ Deploy — `manage.py deploy` / `nginx_switch.sh refresh`
- `bash deploy/nginx_switch.sh refresh` (root): re-generates the nginx config from the template **keeping the values of
  the config in place** (server name, ports, rate limits, real-IP / forwarded headers, dry-run state) —
  `deploy/nginx/refresh_config.py`; creates `/var/cache/nginx/rulezet`, makes `app/static` readable by nginx, tests the
  new config with `nginx -t`, reloads, **puts the previous one back if nginx rejects it**. Re-running `setup_nginx.sh`
  is not needed (it would stop nginx).
- `manage.py deploy` (= start-prod) calls it after the update when nginx is set up and it runs as root; otherwise prints
  the command. Never fatal for the deploy.
- The app cache needs nothing at deploy: keys hold the code version.
**Tests:** `tests/cache/test_nginx_refresh.py` — same template = no change, values (incl. dry-run off, real IP, app dir)
kept when the template changes, foreign / missing config refused.

### 🔒 Admin-only check (all routes)
`tests/cache/test_admin_only_routes.py` — `/admin/cache`, `/admin/cache/status`, `/admin/cache/action`,
`/admin/settings` (+ system, config, instance), `/rule/github/settings/cache` (+ clear, pull): anonymous → redirect,
signed-in user → 403, and a non-admin `clear_all` empties nothing. **11 pass.**
