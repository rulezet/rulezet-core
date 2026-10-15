# Refactor — code conventions

Working folder for the clean-up of the Rulezet code base (branch `refactor/code-conventions`).
One file per category: what is wrong today, the target convention, and the steps to get there.

| # | File | Scope |
|---|------|-------|
| 00 | [conventions.md](00_conventions.md) | The rules every other file applies: naming, folders, layering |
| 01 | [database_models.md](01_database_models.md) | `db.py` split into one module per domain |
| 02 | [db_access_layer.md](02_db_access_layer.md) | Where queries live, who may call the DB |
| 03 | [routes_blueprints.md](03_routes_blueprints.md) | Web routes / blueprints split and naming |
| 04 | [api.md](04_api.md) | REST API (`app/api/`) structure |
| 05 | [hardcoded_config.md](05_hardcoded_config.md) | Lists / dicts / JSON written in the code → admin page or API |
| 06 | [background_jobs.md](06_background_jobs.md) | Job handlers and scheduler |
| 07 | [frontend_js_css.md](07_frontend_js_css.md) | JS components / feature code / CSS |
| 08 | [templates.md](08_templates.md) | Jinja templates |
| 09 | [naming_legacy.md](09_naming_legacy.md) | Legacy names (`github_*` that means "git", French names, typos) |
| 10 | [tests.md](10_tests.md) | Tests that follow the new layout |
| 11 | [migration_plan.md](11_migration_plan.md) | Order of work, one PR per step, how to avoid breaking prod |

Status of each file: **skeleton** — measured facts only, content to be written.
