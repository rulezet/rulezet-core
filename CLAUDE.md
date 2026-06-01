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
| `User` | Auth + profile; has `api_key`, `admin`, `is_verified`, gamification backref |
| `Rule` | Core entity: `format`, `title`, `to_string` (raw content), `uuid`, `source`, `github_path` |
| `FormatRule` | Registry of supported rule formats |
| `Bundle` | Named collection of rules (many-to-many via `BundleRuleAssociation`) |
| `BundleNode` | Tree node for bundle's file-explorer view (`folder` or `file`, recursive self-ref) |
| `Tag` | Taxonomy tags with color/icon/galaxy metadata; linked to rules and bundles via association tables |
| `RuleEditProposal` | PR-style edit request with `status` (pending/approved/rejected) |
| `Comment` / `CommentBundle` | Comments on rules and bundles |
| `RuleVote` / `BundleVote` | Per-user up/down votes |
| `RuleFavoriteUser` | User favorites |
| `InvalidRuleModel` | Rules that failed validation on import |
| `BackgroundJob` + `BackgroundJobLog` | Persistent job queue for long-running tasks |
| `Gamification` | Per-user contribution points and level; auto-updated via SQLAlchemy `before_flush` event listener `receive_before_flush()` |
| `RuleSimilarity` / `SimilarResult` | Fuzzy similarity scores between rules (TF-IDF + FAISS + rapidfuzz) |
| `ImporterResult` / `UpdateResult` / `RuleStatus` / `NewRule` | History tracking for GitHub imports and rule update scans |

### Business logic layer (`app/features/*/` and `app/core/`)

Each feature has a `*_core.py` file with pure Python DB logic, called by both blueprints and API namespaces:

| File | Key functions |
|------|--------------|
| `app/features/rule/rule_core.py` | `add_rule_core()`, `get_rule()`, `get_rule_by_content()`, `rule_exists()`, `get_rules_page_filter()` |
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

### GitHub import pipeline

1. User submits a GitHub repo URL via UI or API.
2. `utils_import_update.py` — `clone_or_access_repo()` clones or `git pull`s the repo into `Rules_Github/<owner>/<repo>/`.
3. `Session_class` (`import_rule/session_class.py`) — multi-threaded worker that walks the repo directory, matches files to format subclasses, validates and inserts rules via `rule_core.add_rule_core()`. Invalid rules go to `InvalidRuleModel`.
4. Results stored in `ImporterResult`.

### Rule update pipeline

`Update_class` (`update_rule/update_class.py`) — checks existing rules against their GitHub source for new versions. Supports three modes: `by_url` (whole repo), `by_rule` (specific rules). Results stored in `UpdateResult` + `RuleStatus` + `NewRule`.

### Background job system

`create_app()` calls `start_worker(app)` which starts a daemon thread running `_worker_loop()`.

- Jobs are rows in `BackgroundJob` with a `job_type` string.
- Handlers are registered with `@register_handler('job_type')` in `job_handlers.py`.
- Worker polls every 2 seconds, picks the oldest pending job, calls its handler.
- Jobs interrupted by server restart are auto-recovered to `pending`.
- Handlers support pause/resume via `_should_pause()` / `_is_cancelled()` checked between batches, with `_resume_offset` stored in `job.payload`.

Existing job types: `bulk_add_tag_to_rules`, `bulk_remove_tag_from_rules`, `delete_github_rules`.

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
- `target_type` — `"rule"` | `"bundle"` | `"user"` | `"tag"` | `"job"` (nullable)
- `target_id` / `target_uuid` — used by the UI to build redirect links
- `extra` — arbitrary JSON dict for additional context
- Never raises: all failures are silently swallowed

**Admin UI**: `/admin/logs` — paginated table, filters by action/search, per-row delete, checkbox mass-delete via background job `delete_activity_logs`, click on row → opens target resource.

**Logged everywhere**: rule create/edit/delete/vote/favorite/bulk-delete, bundle create/edit/delete, user login/logout/register/edit/delete, admin promote/demote/request approve/reject, tag create/edit/delete/toggle, job create/cancel/pause/resume/delete.

### Tests (`tests/`)

- `conftest.py` — creates a fresh SQLite DB per test session with `create_user_test()`, `create_admin_test()`, `create_rule_test()`.
- Tests use `FLASKENV=testing` which uses `TestingConfig` (SQLite, no CSRF).
- Test files: `tests/account/test_user.py`, `tests/bundle/test_bundle.py`, `tests/rules/test_rule.py`, `tests/rules/test_search_rules.py`.
