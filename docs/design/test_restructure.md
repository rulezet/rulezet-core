# Test suite rework — plan

Branch: `tests-restructure` (from `development`).

## Why

The current suite (~1300 tests) is not structured enough and spends effort on
things that don't matter, while the cases that actually break during
development — who is allowed to do what — have to be re-checked by hand, role
by role, after every change. The new suite must catch those automatically.

## Ground rules

1. **Backend behaviour only.** Never test the frontend: no "click this button
   and a modal opens", no JS, no layout, no CSS. We test routes, API endpoints,
   the data they return and what ends up in the database.
2. **Feature by feature, not everything at once.** We start with **rules**, then
   **bundles**, then the other features one by one. A feature is finished
   (see "Definition of done") before moving to the next. More precise tests
   only come once every feature has this clean base.
3. **The old tests are kept, not deleted.** They are moved to a backup folder
   (see "Old tests"), and the new suite is written from scratch in `tests/`.
4. **No network, no external services.** GitHub, MISP, Ollama/AI providers,
   Vulnerability Lookup, mail… are mocked.

## What every feature gets — 4 layers

### 1. Access control (data access by role)

For every action of the feature, test what happens for each kind of visitor:

| Who | Meaning |
|---|---|
| anonymous | not logged in |
| user | logged in, **not** the owner of the resource |
| owner | logged in, owner of the resource (`resource.user_id`) |
| admin | `user.admin = True` |
| special role | only where a feature uses one (e.g. `ai.use`, `ai.manage`, `rule.tag_any`) |

For each (action × who): expected HTTP status **and** the effect — the data is
returned or not, the change is applied in the DB or not (e.g. a forbidden
delete must leave the row untouched, a private resource must not leak in a
list or a search). Private vs public resources are part of the matrix.

Written as one table per feature (parametrized tests), so adding a role or an
action is one line, and reading the table tells you the feature's permission
model.

### 2. CRUD

Create, read (detail + list), edit, delete for the feature's resources —
including the feature-specific lifecycle (e.g. rules: soft delete →
`is_deleted`, trash, restore; default tags `tlp:clear` / `pap:clear` attached
on create). Checked through the DB state, not only the status code.

### 3. API

When the feature has a REST API (`/api/...`, Flask-RESTX), the same access
matrix and CRUD through the API:

- authentication with `X-API-KEY`: no key, invalid key, user key, owner key,
  admin key;
- same expectations as the web routes (a user's API key must not allow what
  the user can't do in the UI);
- response shape of the main endpoints.

### 4. Robustness — trying to break Rulezet

Inputs an attacker or a careless client would send. Expected result: a clean
4xx with a message, **never a 500**, and no corrupted or half-written data.

- values too long for a field / huge payloads;
- forbidden or unusual characters (control chars, null bytes, unicode,
  emojis, RTL), empty strings, whitespace only;
- wrong types (string instead of int, list instead of object…), missing
  required fields, unexpected extra fields;
- XSS / SQL / template injection strings (`<script>`, `' OR 1=1 --`,
  `{{7*7}}`…) — stored and returned escaped, never executed or interpreted;
- invalid / non-existent / negative / overflowing ids, other users' ids;
- duplicates (same title/content/uuid), invalid formats (broken YARA/Sigma…);
- path traversal and odd file names in uploads/imports.

## Conventions — written for the next contributor

The suite must be easy to read and easy to extend by someone who has never
seen it. Every test follows the same conventions:

- **Same layout everywhere.** `tests/<feature>/test_access.py`,
  `test_crud.py`, `test_api.py`, `test_robustness.py` — nothing else at the
  top of a feature folder. A new feature copies `tests/_template/`.
- **Names say the expectation.** `test_<action>_<who>_<expected>`, e.g.
  `test_delete_rule_as_non_owner_is_forbidden` — the name alone tells what
  broke when it fails.
- **One behaviour per test**, a one-line docstring for the *why* when it isn't
  obvious, no comments restating the code.
- **Arrange / act / assert** in that order, separated by a blank line.
- **No copy-paste setup.** Users, logged-in clients, API clients and resource
  factories come from shared fixtures (`conftest.py`, `tests/helpers/`); a
  test never re-implements login or builds a rule by hand.
- **Access rules as data.** Each feature declares its permission table once
  (action × role → expected outcome) and the access-matrix helper runs it —
  changing a permission is a one-line diff, readable by anyone.
- **Assert the effect, not just the status code**: what the DB contains after
  the call, what the response contains (or must not leak).
- **Deterministic and isolated**: fresh DB per test, no ordering dependency,
  no `sleep`, no real network (mocks), no reliance on data left by another
  test.
- **Fast**: a feature's four files run in seconds; anything slow gets a
  `@pytest.mark.slow` marker and stays out of the default run.
- **Only what matters**: no assertion on HTML layout, CSS classes, wording of
  UI text or JS behaviour (see ground rule 1).

`tests/_template/` holds the four files with one commented example each, and
the "Testing" chapter of the official documentation walks through adding a
feature from it.

## Out of scope (for now)

- Anything frontend (see rule 1).
- Exhaustive testing of every feature on the first pass — the 4 layers above
  first, finer-grained tests later.
- Performance / load testing.

## Structure

```
tests/
  conftest.py              # app + DB, users per role, logged-in clients, API clients
  helpers/                 # shared helpers (access-matrix runner, factories)
  _template/               # the four files to copy for a new feature
  rules/
    test_access.py         # layer 1
    test_crud.py           # layer 2
    test_api.py            # layer 3
    test_robustness.py     # layer 4
  bundles/
    ...same four files...
  <feature>/
    ...
```

Shared fixtures (in `conftest.py` / `helpers/`):

- one user per role (anonymous, user, owner, admin, special-role users);
- a test client already logged in as each of them, and an API client per API
  key;
- small factories to create a resource owned by a given user (rule, bundle,
  comment…), public or private;
- an access-matrix helper: give it the route, the method and the expected
  outcome per role, it runs every combination.

Environment stays as today: `FLASKENV=testing`, SQLite, CSRF off
(`python3 manage.py test` / `./launch.sh -t`).

## Old tests

The current `tests/` content is moved to `tests_legacy/` (kept in git,
excluded from the default `pytest` run, still runnable with
`pytest tests_legacy`). When a feature has been rewritten, its legacy tests
are reviewed: anything still useful and not covered is ported, then that
feature's legacy folder is dropped. CI keeps running the new `tests/`.

## Documentation (English)

Once the rework is done, the testing approach is documented in English in the
official documentation, not only in this design note:

- **Official documentation** (`app/templates/docs/full_documentation.html`,
  the in-app docs): a new "Testing" chapter for contributors — the 4 layers,
  the roles of the access matrix, the folder structure, how to run the suite
  (`python3 manage.py test`, one feature, the legacy suite), and a step-by-step
  "adding tests for a new feature" guide. Table of contents and sidebar
  updated with it.
- **`README.md`**: short "Running the tests" section pointing to that chapter.
- **`CLAUDE.md`**: the test commands and conventions updated to the new layout.

Each feature's section of the chapter is written when that feature is done,
so the documentation never describes tests that don't exist yet.

## Workflow and commits

For each section (infrastructure, rules access, rules CRUD, rules API, rules
robustness, bundles access…):

1. Write the section's tests (conventions above).
2. Run them — the feature's tests while iterating, the whole new suite at the
   end of the section.
3. A failing test is investigated: wrong test → fix the test; **bug in
   Rulezet → fix Rulezet**.
4. Commit:
   - **bug fix** — its own commit, containing **only the files the fix
     touches**: `fix: [<section>] <description>`
     (e.g. `fix: [rules] a non-owner can no longer delete a rule through the API`)
   - **tests** — one commit per section: `chg: [test <section>] <description>`
     (e.g. `chg: [test rules] access matrix — anonymous / user / owner / admin`)
   - no `feat:`, no Claude / AI attribution in any message.
5. Update the progress table below.

Nothing is pushed without an explicit go. The legacy suite is run at the end
of a feature to check nothing it covered broke.

## Order of work

1. Infrastructure: backup of the old tests, new `conftest.py`, role fixtures,
   access-matrix helper, factories.
2. **Rules**: access → CRUD → API → robustness.
3. **Bundles**: same.
4. Then the other features, one at a time (to schedule together): comments,
   account/users, tags, connectors, MISP, jobs, admin, AI, community,
   workspace, ATT&CK, rule tester, notifications, reports, blog, docs…
5. Official documentation in English (see "Documentation"), finished once all
   features are done.

## Definition of done (per feature)

- [ ] access matrix covers every action × every role, private and public
- [ ] CRUD covered, checked against the DB
- [ ] API covered (if the feature has one), with API keys per role
- [ ] robustness cases: no 500, no corrupted data
- [ ] no frontend tests, no network
- [ ] legacy tests of the feature reviewed (ported or dropped)
- [ ] whole new suite green
- [ ] the feature's part of the "Testing" chapter written (English)

## Progress

| Feature | Access | CRUD | API | Robustness | Legacy reviewed | Documented |
|---|---|---|---|---|---|---|
| infrastructure | – | – | – | – | – | |
| rules | | | | | | |
| bundles | | | | | | |
