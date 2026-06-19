# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Rulezet** is an open-source community platform for sharing, evaluating, and managing cybersecurity detection rules (YARA, Sigma, Suricata, Zeek, CRS, Nova, NSE, Wazuh, Elastic). It is a Flask + Vue.js 3 application backed by PostgreSQL. Live at [rulezet.org](https://rulezet.org/).

---

## Commands

### Run the app (development)
```bash
source env/bin/activate
./launch.sh -l       # or: FLASKENV=development python3 app.py
```

### Initialize the database (first time)
```bash
python3 app.py -i    # creates tables + admin user, prints credentials
```

### Recreate the database (drop + reinit)
```bash
python3 app.py -r
```

### Run all tests
```bash
./launch.sh -t       # or: FLASKENV=testing pytest tests
```

### Run a single test file
```bash
FLASKENV=testing pytest tests/rules/test_rule.py
FLASKENV=testing pytest tests/rules/test_search_rules.py -k "test_name"
```

### Database migrations
```bash
flask db migrate -m "description"
flask db upgrade
```

### Gunicorn (production)
```bash
gunicorn -w 4 wsgi:app
```

### Backup / restore
```bash
./backup/scripts/backup_rulezet.sh
./backup/scripts/restore_rulezet.sh
```

---

## Configuration

`config.py` defines three environments selected via `FLASKENV`:

| `FLASKENV`    | DB                             | Notes                        |
|---------------|--------------------------------|------------------------------|
| `development` | `postgresql:///rulezet`        | `DEBUG=True`, sessions in PG |
| `testing`     | `sqlite:///rulezet-test.sqlite`| CSRF disabled, sessions in FS|
| `production`  | `postgresql:///rulezet`        | `DEBUG=False`                |

Secrets live in `.env` (`SECRET_KEY`, `MAIL_PASSWORD`). The app runs on `127.0.0.1:7009` by default.

### Additional `.env` variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_URL` | `127.0.0.1` | Host the app binds to |
| `FLASK_PORT` | `7009` | Port the app listens on |
| `INSTANCE_PUBLIC_URL` | *(none)* | Public-facing URL reported in telemetry (e.g. `https://myinstance.example.com`). If unset, `http://FLASK_URL:FLASK_PORT` is used. |
| `IS_OFFICIAL_INSTANCE` | `false` | **Set to `true` only on rulezet.org.** Enables the Instance Registry admin page and makes `/api/instance/register` accept incoming pings. All other instances return 404 on that endpoint. |
| `TELEMETRY_URL` | `https://rulezet.org/api/instance/register` | Override ping destination (for local testing only — remove in production). |
| `TELEMETRY_STARTUP_DELAY` | `90` | Seconds to wait after boot before first ping. |
| `TELEMETRY_INTERVAL` | `86400` | Seconds between pings (default 24 h). |

---

## Architecture

### Entry points

| File | Role |
|------|------|
| `app.py` | CLI entry point — parses `-i/-r/-d` flags, starts Flask dev server |
| `wsgi.py` | Gunicorn entry point |
| `app/__init__.py → create_app()` | Flask application factory; registers blueprints, extensions, starts background worker |

### Blueprints (UI layer — `app/features/`)

| Blueprint | URL prefix | Module |
|-----------|-----------|--------|
| `home_blueprint` | `/` | `app/home.py` |
| `account_blueprint` | `/account` | `app/features/account/account.py` |
| `rule_blueprint` | `/rule` | `app/features/rule/rule.py` |
| `bundle_blueprint` | `/bundle` | `app/features/bundle/bundle.py` |
| `tags_blueprint` | `/tags` | `app/features/tags/tags.py` |
| `jobs_blueprint` | `/jobs` | `app/features/jobs/jobs.py` |
| `api_blueprint` | `/api` | `app/api/api.py` (Flask-RESTX, CSRF exempt) |

### REST API (Flask-RESTX — `app/api/`)

Swagger UI is accessible at `/api/`. Namespaces:

| Path | Module | Auth |
|------|--------|------|
| `/api/rule/public` | `app/api/rule/rule_public_api.py` | None |
| `/api/rule/private` | `app/api/rule/rule_private_api.py` | `X-API-KEY` header |
| `/api/bundle/public` | `app/api/bundle/bundle_public_api.py` | None |
| `/api/bundle/private` | `app/api/bundle/bundle_private_api.py` | `X-API-KEY` header |
| `/api/account/public` | `app/api/account/account_public_api.py` | None |
| `/api/account/private` | `app/api/account/account_private_api.py` | `X-API-KEY` header |

API key auth is enforced via `@api_required` from `app/core/utils/decorators.py`, which calls `verif_api_key()` in `app/core/utils/utils.py`. The key is passed in the `X-API-KEY` request header.

### Data model (`app/core/db_class/db.py`)

All SQLAlchemy models live in one file. Key models:

| Model | Description |
|-------|-------------|
| `User` | Auth + profile; has `api_key`, `admin`, `is_verified`, `bio`, gamification backref |
| `Rule` | Core entity: `format`, `title`, `to_string` (raw content), `uuid`, `source`, `github_path`; soft-delete fields: `is_deleted`, `deleted_at`, `deleted_by_id`, `delete_batch_uuid` |
| `FormatRule` | Registry of supported rule formats |
| `Bundle` | Named collection of rules (many-to-many via `BundleRuleAssociation`) |
| `BundleNode` | Tree node for bundle's file-explorer view (`folder` or `file`, recursive self-ref) |
| `Tag` | Taxonomy tags with `name`, `color`, `icon`, `galaxy_meta`, `visibility`; linked to rules and bundles via association tables |
| `RuleTagAssociation` | Rule ↔ Tag many-to-many with `uuid`, `user_id`, `added_at` |
| `RuleEditProposal` | PR-style edit request with `status` (pending/approved/rejected) |
| `RuleEditComment` | Comments on edit proposals |
| `RuleEditContribution` | Contribution records for edit proposals |
| `Comment` / `CommentBundle` | Comments on rules and bundles |
| `RuleCommentReaction` / `BundleReactionComment` | Per-user reactions (emoji) on rule/bundle comments |
| `RuleVote` / `BundleVote` | Per-user up/down votes |
| `RuleFavoriteUser` | User favorites |
| `InvalidRuleModel` | Rules that failed validation on import |
| `RequestOwnerRule` | Ownership requests for rules (`rule_id`, `user_id`, `status`, `request_date`) |
| `RepportRule` | User reports/flags on rules (`rule_id`, `user_id`, `reason`, `status`) |
| `BackgroundJob` + `BackgroundJobLog` | Persistent job queue for long-running tasks |
| `Gamification` | Per-user contribution points and level; auto-updated via SQLAlchemy `before_flush` event listener `receive_before_flush()` |
| `RuleSimilarity` / `SimilarResult` | Fuzzy similarity scores between rules (TF-IDF + FAISS + rapidfuzz) |
| `ImporterResult` / `UpdateResult` / `RuleStatus` / `NewRule` / `RuleUpdateHistory` | History tracking for GitHub imports and rule update scans |
| `ActivityLog` | Audit trail entry: `action`, `description`, `user_id`, `target_type`, `target_id`, `target_uuid`, `ip_address`, `is_public`, `icon`, `extra` (JSON) |
| `RuleScope` | User-specific environment declarations per rule: whether a rule works in their environment, with structured entries (OS, version, etc.) and a comment |

### Business logic layer (`app/features/*/` and `app/core/`)

Each feature has a `*_core.py` file with pure Python DB logic, called by both blueprints and API namespaces:

| File | Key functions |
|------|--------------|
| `app/features/rule/rule_core.py` | `add_rule_core()`, `_attach_default_tags()`, `get_rule()`, `get_rule_by_content()`, `rule_exists()`, `get_rules_page_filter()`, `get_all_rule_by_url_github_page()`; soft-delete: `_active()`, `soft_delete_rule()`, `soft_delete_all_by_url()`, `restore_rule()`, `restore_batch()`, `permanent_delete_rule()`, `get_deleted_rules()`, `get_deleted_batches()`; scopes: `get_scopes()`, `upsert_scope()`, `delete_scope()` |
| `app/features/account/account_core.py` | `add_user_core()`, `add_favorite()`, `remove_favorite()` |
| `app/features/bundle/bundle_core.py` | Bundle CRUD, tag association |
| `app/features/jobs/jobs_core.py` | `create_job()`, `cancel_job()`, `pause_job()`, `resume_job()`, `get_zombie_jobs()`, `kill_all_zombies()` |

### Rule format system (`app/features/rule/rule_format/`)

The format system uses an **abstract base class** pattern so new formats can be added without changing the import/validation pipeline:

- `rule_type_abstract.py` — defines `RuleType` (ABC) and `ValidationResult`. Any new format must subclass `RuleType`.
- `available_format/` — one file per format (`yara_format.py`, `sigma_format.py`, …). Each class implements:
  - `format` — short identifier string (e.g. `"yara"`)
  - `validate(content)` → `ValidationResult`
  - `parse_metadata(content, info, validation_result)` → dict matching `Rule` fields
  - `get_rule_files(filepath)` → bool (does this file extension match?)
  - `extract_rules_from_file(filepath)` → `List[str]`
  - `find_rule_in_repo(repo_dir, rule_id)` → `(str, bool)`
- `main_format.py` — orchestration functions:
  - `extract_rule_from_repo()` — iterates all `RuleType.__subclasses__()` to import a full repo
  - `verify_syntax_rule_by_format()` — validate a rule dict by its format
  - `parse_rule_by_format()` — validate + parse + insert a single rule
  - `process_and_import_fixed_rule()` — re-import a corrected `InvalidRuleModel`
  - `Process_rules_by_format()` — batch processing for a specific format

Adding a new format: create a file in `available_format/`, subclass `RuleType`, implement all abstract methods. `load_all_rule_formats()` auto-discovers it via `pkgutil.iter_modules`.

### Default tag system

Every new rule receives `tlp:clear` and `pap:clear` tags automatically at creation time.

Implemented in `rule_core.py`:
- `_DEFAULT_TAG_NAMES = ['tlp:clear', 'pap:clear']`
- `_attach_default_tags(rule, user_id)` — called inside `add_rule_core()` before `db.session.commit()`
- Tags are looked up by name (`ilike`) — silently skipped if they don't exist in the DB
- Idempotent — no duplicate associations are created
- Covers **all** creation flows: manual UI, parse, GitHub import (`session_class.py`), bad-rule re-import, API

**Prerequisite**: the tags `tlp:clear` and `pap:clear` must be created in the DB (via Tags admin) for auto-attachment to work.

### GitHub import pipeline

1. User submits a GitHub repo URL via UI or API.
2. `utils_import_update.py` — `clone_or_access_repo()` clones or `git pull`s the repo into `Rules_Github/<owner>/<repo>/`.
3. `Session_class` (`import_rule/session_class.py`) — multi-threaded worker that walks the repo directory, matches files to format subclasses, validates and inserts rules via `rule_core.add_rule_core()`. Invalid rules go to `InvalidRuleModel`.
4. Results stored in `ImporterResult`.

**URL normalization**: GitHub clone URLs ending with `.git` are stripped before DB lookup and before being passed to templates. The `get_all_rule_by_url_github_page()` and `get_rules_page_filter()` functions normalize the URL and match both `url` and `url.git` patterns in the `source` column.

### Rule update pipeline

`Update_class` (`update_rule/update_class.py`) — checks existing rules against their GitHub source for new versions. Supports three modes: `by_url` (whole repo), `by_rule` (specific rules). Results stored in `UpdateResult` + `RuleStatus` + `NewRule`.

### Background job system

`create_app()` calls `start_worker(app)` which starts a daemon thread running `_worker_loop()`.

- Jobs are rows in `BackgroundJob` with a `job_type` string.
- Handlers are registered with `@register_handler('job_type')` in `job_handlers.py`.
- Worker polls every 2 seconds, picks the oldest pending job, calls its handler.
- Jobs interrupted by server restart are auto-recovered to `pending`.
- Handlers support pause/resume via `_should_pause()` / `_is_cancelled()` checked between batches, with `_resume_offset` stored in `job.payload`.

Existing job types:

| Job type | Description |
|----------|-------------|
| `bulk_add_tag_to_rules` | Add tags to a filtered set of rules |
| `bulk_remove_tag_from_rules` | Remove tags from a filtered set of rules |
| `delete_github_rules` | Delete rules imported from a GitHub source |
| `delete_activity_logs` | Bulk-delete activity log entries by ID list or filter |
| `trash_restore_bulk` | Restore soft-deleted rules in chunks; supports specific IDs, a whole batch UUID, or all trash; pause/resume safe |
| `trash_permanent_delete_bulk` | Irreversibly delete soft-deleted rules from DB in chunks; same pause/resume support; **irreversible** |
| `update_misp_data` | 3-step: git pull MISP submodules → update already-imported taxonomies → update already-imported galaxies |

### Soft-delete / Trash system

Rules are never hard-deleted by default. Instead they are soft-deleted and land in a trash that admins can manage.

**Rule model fields** (added via migration `31e4523a751b`):

| Field | Type | Purpose |
|-------|------|---------|
| `is_deleted` | Boolean (indexed) | Soft-delete flag; default `False` |
| `deleted_at` | DateTime | Timestamp of deletion |
| `deleted_by_id` | Integer FK | User who triggered the deletion |
| `delete_batch_uuid` | String(36, indexed) | Groups all rules deleted from the same GitHub source in one operation |

**Critical invariant**: all user-facing queries must use `_active()` from `rule_core.py`:

```python
def _active():
    return Rule.query.filter(Rule.is_deleted == False)
```

Never call `Rule.query` directly — it will silently return deleted rules.

**Core functions** (`app/features/rule/rule_core.py`):

| Function | Purpose |
|----------|---------|
| `soft_delete_rule(rule_id, user_id, batch_uuid)` | Soft-delete one rule |
| `soft_delete_rule_list(rule_ids, user_id, batch_uuid)` | Batch soft-delete |
| `soft_delete_all_by_url(urls, user_id)` | Soft-delete all rules from a GitHub source as one batch |
| `restore_rule(rule_id)` | Restore single rule |
| `restore_rules_bulk(rule_ids)` | Restore a list of rules |
| `restore_batch(batch_uuid)` | Restore an entire GitHub deletion batch |
| `permanent_delete_rule(rule_id)` | Hard-delete from DB (only already soft-deleted rules) |
| `permanent_delete_bulk(rule_ids)` | Batch hard-delete |
| `get_deleted_rules(page, search, source, batch_uuid, …)` | Paginated trash listing with filters |
| `get_deleted_batches()` | Metadata on all batch groups (source, count, deleted_at) |
| `count_deleted_rules()` | Total trash count |
| `_find_in_trash_by_content(content)` | Check during rule creation if a matching deleted rule exists |

**Routes** (`/rule/trash`, `/rule/delete_rule`, `/rule/delete_rule_list`, `/rule/get_trash_rules`, `/rule/conflict_resolve`).

**Templates**: `app/templates/rule/trash.html` (admin trash management with filters, bulk restore/delete, batch operations) and `app/templates/rule/rule_in_trash.html` (single deleted rule detail).

**Conflict resolution**: if a new upload's content matches a deleted rule still in trash, the UI offers to restore it instead of creating a duplicate.

**Async operations**: large restore/delete operations are dispatched as `trash_restore_bulk` / `trash_permanent_delete_bulk` background jobs.

### RuleScope declarations

Users can declare whether a detection rule works in their specific environment.

**Model** (`RuleScope` in `db.py`):
- `rule_id` / `user_id` — unique pair (one declaration per user per rule)
- `works` — Boolean (`True` = works, `False` = doesn't work)
- `entries` — JSON list of `{key, value}` pairs (e.g. `[{os: linux}, {version: 10.x}]`)
- `comment` — optional free-text note (max 500 chars)

**Routes** (in `app/features/rule/rule.py`):

| Route | Method | Purpose |
|-------|--------|---------|
| `/rule/get_scopes/<rule_id>` | GET | All declarations + works/nworks counts + caller's own declaration |
| `/rule/scope/<rule_id>` | POST | Create or update own declaration |
| `/rule/scope/<rule_id>` | DELETE | Remove own declaration |

**UI**: bottom section of the rule detail page — badge counters, form for own declaration, list of all user declarations. Activity logged as `rule.scope_add`, `rule.scope_update`, `rule.scope_delete`.

### rulezet-cast module (`app/modules/rulezet-cast/`)

A standalone rule parser and normalizer (Git submodule). It converts multi-format detection signatures into structured JSON before import.

**Pipeline**: detect format → split multi-rule files → validate → parse → normalize → emit JSON.

**Architecture**:
- `main.py` — CLI entry point
- `parsers/engine.py` — `RuleCastEngine` orchestrates the pipeline
- `parsers/base.py` — `BaseRuleParser` (ABC) + `ValidationResult`
- `parsers/formats/*.py` — one file per format (YARA implemented; Sigma, Suricata, Zeek, etc. planned)

**CLI usage**:
```bash
python3 main.py parse -t 'rule X { ... }'      # parse from text
python3 main.py parse -i rules.yar --json       # parse file, JSON output
python3 main.py validate -i rules.yar           # validate only
python3 main.py detect -t 'rule X { ... }'     # auto-detect format
python3 main.py new sigma                        # scaffold new parser
```

**Output schema** (per rule):
```json
{
  "format": "yara",
  "identity": {"name": "...", "tags": [], "scopes": []},
  "metadata": {},
  "content": "...",
  "tags": [],
  "vulnerabilities": [],
  "references": [],
  "sources": [],
  "original_uuid": null,
  "status": "parsed"
}
```

### Similarity engine

`Similarity_class` (`utils/similar_rules/similarity_class.py`) uses TF-IDF + FAISS for candidate retrieval and rapidfuzz `fuzz.ratio` for precise scoring. Results stored in `RuleSimilarity` (top 50 per rule).

### Activity Log system (`app/core/utils/activity_log.py`)

Every significant user action is recorded in the `ActivityLog` DB table. Usage is a single import anywhere:

```python
from app.core.utils.activity_log import log_activity

log_activity("rule.create", f"Created rule '{rule.title}'",
             target_type="rule", target_id=rule.id, target_uuid=rule.uuid)
```

- `action` — dot-namespaced string, e.g. `rule.create`, `user.login`, `admin.delete_user`
- `target_type` — `"rule"` | `"bundle"` | `"user"` | `"tag"` | `"job"` | `"github_import"` | `"github_update"` | `"comment"` | `"bundle_comment"` (nullable)
- `target_id` / `target_uuid` — used by the UI to build redirect links
- `is_public` — whether the log entry is visible in the public activity feed
- `extra` — arbitrary JSON dict for additional context
- Never raises: all failures are silently swallowed

**Admin UI** (`/admin/logs`):
- Paginated table in a rounded card with shadow
- Filters: description search, action type, per-page count
- **Visibility column**: clickable badge (`Public` / `Private`) — single click toggles `is_public` via `POST /admin/logs/edit/:id`
- **Selection bar**: appears when rows are checked — bulk actions: Set Public, Set Private, Delete, Clear
- Bulk visibility endpoint: `POST /admin/logs/set_visibility` with `{ ids: [...], is_public: bool }`
- Bulk delete: `POST /admin/logs/delete_bulk` — creates a `delete_activity_logs` background job
- Click on a row → opens the target resource in a new tab
- Sensitive columns (username, IP) are blurred until revealed via the eye toggle button

**Public activity feed** (`/activity_feed`): only entries with `is_public=True` are shown; the `_is_accessible(log)` helper additionally checks that the linked rule/bundle/comment still exists and is not deleted.

**Logged everywhere**: rule create/edit/delete/vote/favorite/bulk-delete/scope change, bundle create/edit/delete, user login/logout/register/edit/delete, admin promote/demote/request approve/reject, tag create/edit/delete/toggle, job create/cancel/pause/resume/delete, GitHub source delete, connector create/update/delete/test/pull.

### Connector / Federation sync system

Connectors allow an admin to link this Rulezet instance to another and pull detection rules from it. **Accessible to admins only** (enforced via `connector_blueprint.before_request` — non-admins get 403, unauthenticated users are redirected to login). The sidebar link is also hidden for non-admins.

#### Files

| File | Role |
|------|------|
| `app/features/connector/connector.py` | Blueprint — UI routes, all gated by `_require_admin()` before_request |
| `app/features/connector/connector_core.py` | Business logic: CRUD, shadow user, test, pull trigger, sync helpers |
| `app/features/jobs/job_handlers.py` | `handle_connector_pull` — background job handler that drives the actual sync |
| `app/api/connector/connector_sync_api.py` | Sync API exposed **by** this instance to remote connectors (`/api/sync/…`) |
| `app/static/js/connector/connectorTable.js` | Vue 3 component — table + card view, pull dropdown, history timeline |
| `app/templates/connector/connector_list.html` | Page template — uses `ConnectorTable` component |
| `app/static/css/connector/connector.css` | Connector-specific styles |

#### Data model (`Connector` in `db.py`)

| Field | Purpose |
|-------|---------|
| `uuid` | Public identifier |
| `name` / `description` / `icon` | Display info |
| `connector_type` | `'rulezet'` (only type currently implemented) |
| `instance_url` | Base URL of the remote instance (stripped of trailing `/`) |
| `api_key_outbound` | Optional key sent in `X-API-KEY` header when calling the remote |
| `owner_id` | Admin user who created the connector |
| `owner_mode` | `'shadow'` — a ghost account owns imported rules; `'self'` — the triggering admin owns them |
| `sync_rules` / `sync_bundles` | What to synchronize |
| `is_active` | Disabling prevents new pulls |
| `is_system` | `True` for the read-only official Rulezet connector (cannot be modified or deleted) |
| `shadow_user_id` | FK to the auto-created ghost `User` for `owner_mode='shadow'` |
| `last_sync_at` | Timestamp of last completed pull |
| `last_error` | Last connection error string |

#### Rule origin fields (on the `Rule` model)

| Field | Purpose |
|-------|---------|
| `connector_id` | FK to the `Connector` that imported this rule (SET NULL if connector deleted) |
| `remote_rule_uuid` | UUID of the rule **on the remote instance** — used for deduplication |
| `sync_instance_url` | URL of the remote instance — persisted even after connector deletion; shown in rule detail as "Synced from" |

`source` is kept **intact** from the remote (original GitHub URL etc.) — it is never overwritten with the connector URL.

#### Sync API (exposed by this instance — `app/api/connector/connector_sync_api.py`)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/sync/manifest` | None | Instance identity + capabilities |
| `GET /api/sync/stats` | None | Public rule/bundle counts |
| `GET /api/sync/rules` | None | Paginated rules with `?since=`, `?page=`, `?per_page=` |
| `GET /api/sync/bundles` | None | Paginated public bundles |

`_rule_to_sync_json()` includes `update_history` (list of `RuleUpdateHistory` entries) so pulling instances can import the full change history. The exported `uuid` is the **canonical origin uuid** (`remote_rule_uuid or uuid`) so rule identity stays stable across federation hops. `_bundle_to_sync_json()` includes `rules` — the canonical uuids of the bundle's rules — so pulling instances can rebuild bundle membership.

#### Pull modes

Matching is **by uuid only** (remote canonical uuid vs local `remote_rule_uuid` or `uuid`) — content is never compared. Trashed rules are matched too (active first). Both modes fetch the full remote set (`since=1970`).

| Mode | Behaviour |
|------|-----------|
| **Soft** | **If uuid match found (even in the trash) → skip. If no match → create.** Existing rules, local deletions and history are never touched. |
| **Hard** | Same lookup. **If uuid match found and the remote version differs → import it over the local rule in place. A content (`to_string`) change is archived first in `RuleUpdateHistory` (old_content = local, new_content = remote); metadata-only changes (title, description, …) are applied without a history entry. A match found in the trash is restored. Identical active rule → skip. If no match → create + import remote history.** Rules are never deleted/recreated — id, votes, comments and favorites are preserved. |

#### `_upsert_rule` logic (`connector_core.py`)

```python
# 1. Find local match by uuid: or_(remote_rule_uuid == uuid, Rule.uuid == uuid)
# 2. Soft mode + match → return 'skipped'
# 3. Hard mode + match → if content identical → 'skipped';
#    else add RuleUpdateHistory(old_content=local, new_content=remote),
#    update the rule fields in place, _sync_tags(), _import_rule_history()
#    → return 'updated'
# 4. No match → create new Rule(remote_rule_uuid=..., sync_instance_url=..., ...)
#    + _sync_tags() + _import_rule_history(remote['update_history']) → 'created'
```

#### Bundle membership sync

`_upsert_bundle()` calls `_sync_bundle_rules(bundle, remote['rules'])` which attaches local rules matched by uuid via `BundleRuleAssociation`. Additive only — rules a local user added to the bundle are never removed. Membership is repaired on every pull, even for bundles that are otherwise skipped/unchanged. Rules are pulled before bundles in `handle_connector_pull`, so the rules already exist locally when `sync_rules` is enabled.

Owner of the created rule:
- `owner_mode='shadow'` → `shadow_user_id` (the ghost account)
- `owner_mode='self'` + hard pull → the admin who triggered the pull (`triggered_by_id`)

#### Background job (`handle_connector_pull` in `job_handlers.py`)

Job type: `connector_pull`. Payload: `{ connector_id, mode }`.

- Fetches all pages from `/api/sync/rules` (soft: `since=1970`, hard: `since=last_sync_at`)
- Calls `_upsert_rule()` per rule, tallies `rules_created / rules_skipped / rules_errors`
- Fetches bundles if `connector.sync_bundles`, calls `_upsert_bundle()`
- Sets `job.done = job.total` at completion (critical — was hardcoded to 1)
- Logs `connector.pull_done` with full stats in `extra`

#### Self-sync prevention

`_is_self(instance_url)` compares the **full netloc** (`host:port`) of the connector URL against `request.host`. Prevents pulling from the current instance even on a different port (e.g. `127.0.0.1:7009` ≠ `127.0.0.1:7010`).

#### Shadow user

Each connector lazily creates a ghost `User` with email `shadow_<uuid8>@connector.local` and a random unusable password. This user owns all rules imported in `owner_mode='shadow'`. Retrieved via `_get_or_create_shadow_user(connector)`.

#### Official connector

`seed_official_connector()` (called at app start) creates a read-only system connector pointing to `https://rulezet.org` if none exists yet. It cannot be modified or deleted.

#### UI (`connectorTable.js`)

- `ConnectorRow` (table) and `ConnectorCard` (card) Vue components, both in `connectorTable.js`
- Pull button is a single Bootstrap dropdown with **Soft pull** / **Hard pull** options; disabled if `is_self`
- `is_self` connectors show an orange "self" badge; pull is blocked client-side and server-side
- History timeline shows the last 30 `ActivityLog` entries; displayed 2 at a time with "Show more" (+5 per click)
- All notifications use `create_message(msg, class)` from `/static/js/toaster.js` — no inline alert divs
- Bulk pull skips self-connectors automatically

#### Activity actions logged

`connector.create`, `connector.update`, `connector.delete`, `connector.test_ok`, `connector.pull_triggered`, `connector.pull_done`

### UI conventions

#### Page header banner (`.explorer-banner`)

All pages accessible from the navigation use a shared banner component defined in `app/static/css/core.css` (section 18):

```html
<div class="explorer-banner mb-4">
    <i class="fa-solid fa-[icon] banner-watermark"></i>
    <div class="d-flex align-items-center gap-3 mb-3">
        <div class="banner-icon"><i class="fa-solid fa-[icon]"></i></div>
        <div>
            <h2 class="fw-bold mb-1">Page Title</h2>
            <div class="banner-accent"></div>
        </div>
    </div>
    <p class="text-muted mb-0" style="max-width: 600px; font-size: 0.95rem;">Description.</p>
</div>
```

Classes: `.explorer-banner` (card wrapper with blue top accent line), `.banner-icon` (52×52 icon box), `.banner-accent` (36×3 gradient underbar), `.banner-watermark` (decorative background icon), `.banner-formats` (formats pill, rules list only).

The gradient uses only blue tones: `#0d6efd → #0a58ca`.

#### General UI style reference — `detail_user` page

The user detail page (`app/templates/account/detail_user.html` + `app/static/css/account/user_detail.css`) is the **canonical style reference** for all new feature pages. When building any new page or component, follow these patterns from that page:

**Info cells with icons** (`.ud-info-cell`) — the preferred way to display labeled fields:
```html
<div class="ud-info-cell">
    <div class="ud-info-cell-icon" style="background:rgba(13,110,253,.1);color:#0d6efd;">
        <i class="fas fa-user"></i>
    </div>
    <div class="ud-info-cell-body">
        <div class="ud-info-cell-label">Field Label</div>
        <div class="ud-info-cell-value">Field value</div>
    </div>
</div>
```
Place these in a `.ud-info-grid` container (CSS grid, auto-fill `minmax(220px,1fr)`).

**KPI cards** (`.ud-kpi-card`) — for numeric summary stats at the top of a section:
```html
<div class="ud-kpi-card ud-kpi-card--blue">
    <div class="ud-kpi-icon"><i class="fas fa-shield-halved"></i></div>
    <div class="ud-kpi-body">
        <div class="ud-kpi-value">42</div>
        <div class="ud-kpi-label">Rules Published</div>
    </div>
</div>
```
Colour variants: `--blue`, `--teal`, `--green`, `--gold`, `--purple`, `--orange`.

**Section headers** (`.ud-section-header`) — separator between content blocks:
```html
<div class="ud-section-header mb-3">
    <i class="fas fa-chart-bar ud-section-icon"></i>
    <div>
        <div class="ud-section-title">Section Title</div>
        <div class="ud-section-sub">Short description</div>
    </div>
</div>
```

**Chart cards** (`.ud-chart-card`) — wrapper for `<chart-viewer>` with a coloured top accent:
```html
<div class="ud-chart-card ud-chart-card--accent-blue">
    <chart-viewer :data="chartData" views="bar" height="320px"></chart-viewer>
</div>
```
Accent variants: `--accent-blue`, `--accent-teal`, `--accent-purple`, `--accent-orange`, `--accent-green`, `--accent-gold`.

All these classes are defined in `app/static/css/account/user_detail.css`.

#### Tag tooltips (`app/static/js/tags/singleTagDisplay.js`)

Tag tooltips use Vue 3 `<teleport to="body">` with `position: fixed` computed at `mouseenter`. This bypasses `overflow: hidden` on parent containers (e.g. carousels). A 120ms debounce on `mouseleave` allows the mouse to move from the tag to the tooltip without it closing.

#### Dark mode

Core CSS variables (`app/static/css/core.css`):
- `--text-color` — primary text (`#1e1e1e` / `#e2e8f0`)
- `--subtle-text-color` — secondary/muted text (`#6c757d` / `#94a3b8`)
- `--card-bg-color` — card backgrounds
- `--border-color` — borders
- `--light-bg-color` — table headers, subtle backgrounds

Dark mode overrides (section 17-18 of core.css) cover: `.text-muted`, `.table-light`, `.table-hover`, `.bg-*-subtle`, `.text-secondary`, `.table .opacity-50`.

**Important**: use `var(--subtle-text-color)` for secondary text, NOT `var(--color-text)` (that variable does not exist).

#### Sidebar navigation (`app/templates/sidebar.html`)

The trash icon linking to `/rule/trash` is shown only to admins or rule moderators.

### Instance Registry (phone-home system)

Every Rulezet instance automatically identifies itself and reports its existence to rulezet.org. This gives the community a live map of all running instances.

#### How it works

1. **On first boot** — `_init_instance_config()` (called from `create_app()`) generates a persistent UUID and stores it in `InstanceConfig` (single-row table). Never regenerated.
2. **90 seconds after boot** — `_start_telemetry()` launches a daemon thread that POSTs to `https://rulezet.org/api/instance/register`. Repeats every 24 h.
3. **rulezet.org** receives the ping, upserts a `RegisteredInstance` row, and shows all instances in the admin page `/account/admin/instances`.

#### Ping payload

```json
{
  "uuid":          "<endpoint_uuid>",
  "url":           "<reported_url>",
  "version":       "1.5.0",
  "rules_count":   42,
  "bundles_count": 3
}
```

`endpoint_uuid` is derived as `uuid5(base_uuid, reported_url)` — two processes sharing the same DB but on different ports get different endpoint UUIDs and appear as distinct rows.

`reported_url` = `INSTANCE_PUBLIC_URL` if set, otherwise `http://FLASK_URL:FLASK_PORT`.

#### Security

- `/api/instance/register` returns **404** on any instance where `IS_OFFICIAL_INSTANCE=false` (the default). Only rulezet.org accepts pings.
- The ping destination is hardcoded to `https://rulezet.org` — protected by TLS. Nobody else can intercept pings without controlling that domain.
- Even if someone forks the repo and sets `IS_OFFICIAL_INSTANCE=true` on their instance, their endpoint still rejects incoming registrations (404), and community instances still ping rulezet.org via TLS — not them.

#### Models (`db.py`)

| Model | Description |
|-------|-------------|
| `InstanceConfig` | Single-row: this instance's `uuid`, `telemetry_enabled`, `public_url` |
| `RegisteredInstance` | One row per remote instance that has phoned home: `uuid`, `public_url`, `version`, `rules_count`, `bundles_count`, `ping_count`, `first_seen`, `last_seen` |

#### Files

| File | Role |
|------|------|
| `app/__init__.py` | `_init_instance_config()` + `_start_telemetry()` called in `create_app()` |
| `app/api/instance/instance_api.py` | `POST /api/instance/register` — upserts `RegisteredInstance`, rate-limited to 1 update/hour/UUID, requires `IS_OFFICIAL_INSTANCE=true` |
| `app/features/account/account.py` | `GET /account/admin/instances` — admin-only, requires `IS_OFFICIAL_INSTANCE=true` |
| `app/templates/admin/instances.html` | Admin table with Active/Stale/Offline status badges |

#### Opt-out

Any instance admin can disable telemetry by setting `telemetry_enabled = False` on the `InstanceConfig` row in the database. No pings will be sent.

#### Production setup (rulezet.org only)

Add to `.env` on the rulezet.org server — **do not add these to any other instance**:

```
IS_OFFICIAL_INSTANCE=true
INSTANCE_PUBLIC_URL=https://rulezet.org
```

Remove any `TELEMETRY_URL`, `TELEMETRY_STARTUP_DELAY`, `TELEMETRY_INTERVAL` overrides (those are for local testing only).

---

### Tests (`tests/`)

- `conftest.py` — creates a fresh SQLite DB per test session with `create_user_test()`, `create_admin_test()`, `create_rule_test()`.
- Tests use `FLASKENV=testing` which uses `TestingConfig` (SQLite, no CSRF).
- Test files: `tests/account/test_user.py`, `tests/bundle/test_bundle.py`, `tests/rules/test_rule.py`, `tests/rules/test_search_rules.py`.

---

### Shared UI Components (`app/static/js/components/`)

Reusable Vue 3 components ported from the flask-launchpad template project. All are ES modules — import with a `<script type="module">` tag.

#### Dependencies (already in `app/static/js/`)

| File | Purpose |
|------|---------|
| `hljs.min.js` | Syntax highlighting — lazy-loaded by `SmartEditor` and `CodeViewer` |
| `marked.min.js` | Markdown rendering — lazy-loaded by `SmartEditor` |
| `pivotick.iife.js` | Graph visualization library — lazy-loaded by `GraphViewer` |

#### Submodule (`modules/pivotick`)

Pivotick source is tracked as a Git submodule at `modules/pivotick` (https://github.com/Pivotick/Pivotick). The built file `pivotick.iife.js` is committed directly to `app/static/js/` and does **not** need to be rebuilt unless the submodule is updated. After cloning the repo, init submodules with:

```bash
git submodule update --init --recursive
```

#### Component catalogue

| Component | File | CSS | Description |
|-----------|------|-----|-------------|
| `SmartEditor` | `smart-editor.js` | `smart-editor.css` | Multi-mode editor: `code`, `markdown`, `text`. Syntax highlighting (hljs) + markdown preview (marked). |
| `CodeViewer` | `code-viewer.js` | `code-viewer.css` | Read-only code display with syntax highlighting. Props: `code`, `language`, `filename`. |
| `DiffViewer` | `diff-viewer.js` | `diff-viewer.css` | Side-by-side or unified diff between two strings. Props: `old_content`, `new_content`. |
| `AnsiTerminal` | `ansi-terminal.js` | `ansi-terminal.css` | Renders ANSI escape codes as colored terminal output. Prop: `content`. |
| `ChartViewer` | `chart-viewer.js` | `chart-viewer.css` | Wrapper for ApexCharts-style charts. Sub-charts in `charts/` subfolder. Props: `type`, `data`, `options`. |
| `FileTree` | `file-tree.js` | `file-tree.css` | Recursive file/folder tree. Emits `select` on node click. Prop: `node` (tree object). |
| `GraphViewer` | `graph-viewer.js` | `graph-viewer.css` + `pivotick.css` | Network graph powered by Pivotick. Modes: `simple` (viewer) / `dev` (full UI). Props: `nodes`, `edges`. |
| `RequestBuilder` | `request-builder.js` | `request-builder.css` | HTTP request builder UI — method, URL, headers, body. Emits `send`. |
| `Timeline` | `timeline.js` | `timeline.css` | Vertical event timeline. Prop: `events` (array of `{date, label, icon, color}`). |

#### Usage pattern

```html
<!-- In a Jinja template — include the CSS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/components/smart-editor.css') }}">

<!-- Import and register the component in a <script type="module"> block -->
<script type="module">
import { createApp } from '/static/js/vue.global.js'
import SmartEditor from '/static/js/components/smart-editor.js'

createApp({
    components: { SmartEditor },
    // ...
}).mount('#app')
</script>
```

For `GraphViewer`, also include `pivotick.css`:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/components/pivotick.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/components/graph-viewer.css') }}">
```

#### `charts/` subfolder

`chart-viewer.js` lazy-imports individual chart types from `app/static/js/components/charts/`. Available types: `line`, `area`, `bar`, `bar-h`, `pie`, `donut`, `scatter`, and more. Add new chart types there following the same pattern as existing ones.

---

### RuleList component (`app/static/js/rule/ruleList.js`)

A self-contained, paginated rule browser with card and table views, integrated filters, selection, and bulk actions. Test page: `/rule/rulelist_test`.

**CSS dependencies** (include all three in `{% block head %}`):
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/components/dataTable.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/components/code-viewer.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/rule/ruleList.css') }}">
```

**Required companion components** — register all of these alongside `RuleList` in every `createApp()` that mounts it:

```javascript
import RuleList                  from '/static/js/rule/ruleList.js'
import TagsDisplaysList          from '/static/js/tags/tagsDisplaysList.js'
import VulnerabilityDisplaysList from '/static/js/vulnerability/vulnerabilityDisplayList.js'

const sharedComponents = {
    'rule-list':                   RuleList,
    'tags-displays-list':          TagsDisplaysList,
    'vulnerability-displays-list': VulnerabilityDisplaysList,
}
```

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `mode` | String | `'read'` | `'read'` view-only · `'select'` checkboxes + Confirm · `'manage'` checkboxes + bulk bar |
| `default-view` | String | `'card'` | Initial view: `'card'` or `'table'` |
| `fetch-url` | String | `'/rule/data_table'` | Paginated API endpoint |
| `source` | String | — | Filter by GitHub source URL |
| `user-id` | Number | — | Filter rules by owner (not the connected user) |
| `current-user-id` | Number | — | ID of the logged-in user (for OWNER badge and edit/delete visibility) |
| `current-user-is-admin` | Boolean | `false` | Whether the logged-in user is admin |
| `show-filters` | Boolean | `true` | Show/hide filter panel |
| `show-create` | Boolean | `false` | Show "New Rule" button in toolbar |
| `can-vote` | Boolean | `false` | Enable up/down vote buttons |
| `can-favorite` | Boolean | `false` | Enable favorite star |
| `bulk-actions` | Array | `[]` | Custom bulk actions: `[{ key, label, icon?, variant? }]` |
| `initial-per-page` | Number | `12` | Cards per page (table always defaults to 25) |
| `hidden-filters` | Array | `[]` | Filter field keys to hide: `'format'`, `'sources'`, `'tags'`, `'licenses'`, `'vulnerabilities'` |
| `initial-filters` | Object | `{}` | Pre-filled filter values: `{ search, format, tags, sources, licenses, vulnerabilities }` |
| `csrf-token` | String | `''` | CSRF token — required for delete bulk action |
| `current-user-is-authenticated` | Boolean | `false` | Whether user is logged in — controls Export/Bundle "Add to Bundle" option |

**Edit / Delete visibility** is automatic: buttons appear only when `current-user-id` is set AND the user is either the rule owner OR `current-user-is-admin` is `true`. No extra prop needed.

#### Events

| Event | Payload | When |
|-------|---------|------|
| `vote` | `{ ruleId, type }` | User voted — local vote counts update automatically |
| `favorite` | `{ ruleId, isFavorited }` | User toggled favorite — local state updates automatically |
| `delete` | `rule` | User clicked Delete on a rule (single row action) |
| `bulk-action` | `{ action, ids, count }` | Custom bulk action fired (delete/download/bundle are handled internally) |
| `send` | `ids` | Mode `select` — user clicked Confirm; `ids` is an array of IDs or `'ALL'` |

**Internally handled bulk actions** (no `@bulk-action` handler needed for these):
- `delete` → calls `/rule/delete_rule_list` (soft-delete/trash), shows toast, refreshes
- `download` → opens Export modal at Download view with selected IDs
- `bundle` / `export` → opens Export modal at Bundle view with selected IDs

#### Exposed method

`fetchData()` — programmatically refresh the current page (use a `ref` on the component).

#### Minimal usage (read-only)

```html
<div id="app">
    <rule-list
        mode="read"
        default-view="card"
        :can-vote="isAuthenticated"
        :can-favorite="isAuthenticated"
        :current-user-id="currentUserId"
        :current-user-is-admin="isAdmin"
        :csrf-token="csrfToken"
        :current-user-is-authenticated="isAuthenticated">
    </rule-list>
</div>
<script type="module">
import RuleList                  from '/static/js/rule/ruleList.js'
import TagsDisplaysList          from '/static/js/tags/tagsDisplaysList.js'
import VulnerabilityDisplaysList from '/static/js/vulnerability/vulnerabilityDisplayList.js'

const isAuthenticated = {{ current_user.is_authenticated | tojson }}
const isAdmin         = {{ current_user.is_admin()        | tojson }}
const currentUserId   = {{ current_user.id if current_user.is_authenticated else 'null' }}
const csrfToken       = '{{ csrf_token() }}'

createApp({
    components: {
        'rule-list': RuleList,
        'tags-displays-list': TagsDisplaysList,
        'vulnerability-displays-list': VulnerabilityDisplaysList,
    },
    setup() { return { isAuthenticated, isAdmin, currentUserId, csrfToken } }
}).mount('#app')
</script>
```

#### Manage mode with bulk actions

```html
<rule-list
    mode="manage"
    default-view="card"
    :can-vote="isAuthenticated"
    :can-favorite="isAuthenticated"
    :current-user-id="currentUserId"
    :current-user-is-admin="isAdmin"
    :csrf-token="csrfToken"
    :current-user-is-authenticated="isAuthenticated"
    :bulk-actions="[
        { key: 'bundle',   label: 'Add to bundle', icon: 'fa-layer-group' },
        { key: 'download', label: 'Download',        icon: 'fa-download' },
        { key: 'delete',   label: 'Delete',          icon: 'fa-trash', variant: 'danger' },
    ]"
    @delete="onDeleteSingleRule"
    @bulk-action="onCustomBulkAction">
</rule-list>
```

`delete`/`download`/`bundle` keys are reserved and handled internally. Add only custom keys to `@bulk-action`.

#### Selection persistence

Checked rules are stored in a `Map` keyed by rule ID and **survive filter changes and page navigation**. Applying a filter resets "Select all pages" but keeps individual picks. A panel below the toolbar lists the picked rules as removable chips (max 8 visible, expandable).
