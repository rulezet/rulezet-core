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

**Logged everywhere**: rule create/edit/delete/vote/favorite/bulk-delete/scope change, bundle create/edit/delete, user login/logout/register/edit/delete, admin promote/demote/request approve/reject, tag create/edit/delete/toggle, job create/cancel/pause/resume/delete, GitHub source delete.

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

### Tests (`tests/`)

- `conftest.py` — creates a fresh SQLite DB per test session with `create_user_test()`, `create_admin_test()`, `create_rule_test()`.
- Tests use `FLASKENV=testing` which uses `TestingConfig` (SQLite, no CSRF).
- Test files: `tests/account/test_user.py`, `tests/bundle/test_bundle.py`, `tests/rules/test_rule.py`, `tests/rules/test_search_rules.py`.
