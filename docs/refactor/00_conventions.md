# 00 — Conventions

> Status: draft — to validate before any code moves

## Goal

A human opening the project must be able to:

1. **find** where something is, from its name alone (feature → folder → file);
2. **understand** what a function does from its name, without reading its body;
3. **follow** one request from the URL to the database through the same layers every time.

Every rule below serves one of these three points. If a rule doesn't help a human read the code, drop it.

## 1. One feature = one folder, same shape everywhere

```
app/features/<feature>/
    routes.py        # web pages + their JSON endpoints (Flask blueprint) — thin
    service.py       # what the feature does (business logic) — no Flask, no HTML
    queries.py       # every DB read/write of the feature — the only place with Model.query
    models.py        # SQLAlchemy models of the feature
    forms.py         # WTForms, if any
    jobs.py          # background job handlers of the feature, if any
app/api/<feature>/   # REST API — calls service.py, never queries.py or models directly
app/templates/<feature>/
app/static/js/<feature>/   app/static/css/<feature>/
```

A feature that grows too big is split into sub-features (`rule/crud`, `rule/import`, `rule/trash`…),
each with the same shape — never into a 5,000-line file.

## 2. Layers — who may call whom

```
routes.py / api  →  service.py  →  queries.py  →  models.py
```

- A route never builds a query; a query never knows about `request` or `current_user`.
- Permission checks happen in routes (who is calling), business rules in the service (what is allowed).

## 3. Names

- **English only**, `snake_case` for Python, `camelCase` for JS, `kebab-case` for URLs and file names in `static/`.
- A function name is **verb + object**, and says what it returns:
  `get_rule(id)` → one rule or None · `list_rules(filters)` → a list · `count_rules(...)` → an int ·
  `create_rule` / `update_rule` / `delete_rule` / `restore_rule` · `is_…` / `has_…` / `can_…` → a bool.
- No vague words alone: `core`, `utils`, `helper`, `manager`, `data`, `info`, `handle`, `process`.
- One concept = one word everywhere: `git` (not `github` when any host is meant), `rule` (not `rule_` / `r`),
  `source` vs `repository` decided once.
- Booleans read as questions: `is_deleted`, `has_token`, `can_edit`.

## 4. Configuration

- Lists that an admin may want to change (formats, licenses, providers, icons, task types…) are **data**, not code:
  stored in the DB, editable from an admin page, or served by an API route — see `05_hardcoded_config.md`.
- Code keeps only real constants (limits, regexes, enum values the code branches on).

## 5. Comments

- A comment explains **why**, never what the next line does.
- Each module starts with 2–3 lines: what it is for, and what it must not do.

## To decide

- Folder name for models: `app/features/<feature>/models.py` (per feature) or `app/models/<domain>.py` (central)?
- Rename DB tables/columns too (`github_repo` → `git_repository`), or only Python names?
- Old URLs: redirect, or keep both for one release?
