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
   (see "Old tests"), and the new suite is written from scratch in `tests_new/`.
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

- **Same layout everywhere.** `tests_new/<feature>/test_access.py`,
  `test_crud.py`, `test_api.py`, `test_robustness.py` — nothing else at the
  top of a feature folder. A new feature copies `tests_new/_template/`.
  Logic that isn't about access / CRUD / API / robustness gets its own folder
  named after what it tests, with files named after the behaviour — e.g.
  `tests_new/rule_formats/test_syntax.py` and `test_parser.py` for every rule
  format.
- **Names say the expectation.** `test_<action>_<who>_<expected>`, e.g.
  `test_delete_rule_as_non_owner_is_forbidden` — the name alone tells what
  broke when it fails.
- **One behaviour per test**, a one-line docstring for the *why* when it isn't
  obvious, no comments restating the code.
- **Arrange / act / assert** in that order, separated by a blank line.
- **No copy-paste setup.** Users, logged-in clients, API clients and resource
  factories come from shared fixtures (`conftest.py`, `tests_new/helpers/`); a
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

`tests_new/_template/` holds the four files with one commented example each, and
the "Testing" chapter of the official documentation walks through adding a
feature from it.

## Out of scope (for now)

- Anything frontend (see rule 1).
- Exhaustive testing of every feature on the first pass — the 4 layers above
  first, finer-grained tests later.
- Performance / load testing.

## Structure

```
tests_new/
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

Until the rework is finished, the previous suite stays in `tests/` and is
what CI runs on every commit; the new suite is in `tests_new/` and runs
only when asked (`FLASKENV=testing pytest tests_new`). When a feature has
been rewritten, its legacy tests are reviewed: anything still useful and
not covered is ported, and legacy tests asserting a behaviour that was
deliberately changed are updated so CI stays green. At the end the new
suite takes the `tests/` name and the legacy one is dropped.

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

## Briefing for a feature agent

Features are rewritten in parallel, one agent per feature, each in its own
git worktree (its own branch), then reviewed and merged into
`tests-restructure`. Every agent gets this briefing plus the name of its
feature.

**Before writing anything**

1. Read this whole document, then the reference implementation:
   `tests_new/conftest.py`, `tests_new/helpers/` (users, access, db, inputs, rules)
   and `tests_new/rules/` — the four files there are the model to follow.
2. Map the feature: every web route of its blueprint
   (`app/features/<feature>/`), every API endpoint (`app/api/<feature>/`),
   the decorators and the ownership / admin / permission checks inside, the
   payloads, and the DB effect of each write. Write the expected permission
   model as one sentence per action — that becomes the access tables.

**Writing the tests**

3. `tests_new/<feature>/__init__.py` + the four layer files (copy
   `tests_new/_template/`). Tables first (`matrix()` + `assert_outcome()`), then
   CRUD checked in the DB (`reload()`, `count()`), then API with a key per
   role (`api_headers()`), then robustness with `tests_new/helpers/inputs.py`.
4. Factories for the feature's objects go in **`tests_new/helpers/<feature>.py`**
   (like `helpers/rules.py`). Never edit the other shared helpers, the
   conftest or another feature's tests — if one needs a change, say so in the
   final report instead.
5. Tests describe the **correct** behaviour (what Rulezet should do), not
   whatever the code currently does.

**Running and fixing**

6. Run `FLASKENV=testing pytest -q -p no:cacheprovider tests_new/<feature>` (and
   `tests_new/test_foundation.py`) after each file. Read the failure: a wrong
   test is fixed in the test; **a Rulezet bug is fixed in Rulezet**, with the
   smallest correct change, following CLAUDE.md (e.g. `_active()` for rules,
   owner-or-admin checks, `log_activity`). Shared helpers already exist for
   untrusted input: `as_db_id()` and `json_object()` in
   `app/core/utils/utils.py`.
7. Known patterns from the rules pass, to look for: a refused action
   answering 200 + `access_denied.html` instead of 403 (JSON routes → JSON
   403, pages → template + 403); `int()` / `.get()` / `.strip()` on
   untrusted values → 500; soft-deleted rows leaking into lists; actions on
   a missing id → 500; foreign keys SQLite doesn't enforce but PostgreSQL
   does.
8. A behaviour that is a **product decision**, not a bug (e.g. "should a
   non-owner be allowed to…?"), is not changed: the test is written for the
   current behaviour, and the question goes in the final report.

**Committing** (never push, never `feat:`, never any AI attribution)

9. Check the run is green **before** committing (don't trust a piped
   command's exit code).
10. Each Rulezet fix: its own commit with only the files of that fix —
    `fix: [<feature>] <what was wrong, in user terms>`.
11. Each layer of tests: one commit — `chg: [test <feature>] <layer and what
    it covers>`.

**Final report** (the agent's last message)

- commits (hash + subject), bugs fixed (one line each: the failure, the fix);
- product decisions to take, with the current behaviour;
- anything left out of scope and why;
- any file touched outside `tests_new/<feature>/`, `tests_new/helpers/<feature>.py`
  and the feature's own code.

**Feature batches** (at most 5 agents at a time)

| Batch | Features |
|---|---|
| 1 | bundles, tags, ATT&CK (`attack`), comments (`api/comment`, rule & bundle comments), account |
| 2 | GitHub for rules — import, update / sync schedule and proposals (`app/features/rule/rule_from_github/`, `github.manage`; network mocked), connectors, MISP, jobs, workspace, roles |
| 3 | AI, notifications, reports, blog, community, rule tester, rule relations, Velociraptor, admin / config |

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

> **Folders (2026-10-06):** while the rework is unfinished, the new suite
> lives in **`tests_new/`** and the previous suite is back in **`tests/`** —
> the one CI, `./launch.sh -t` and `manage.py test` run on every commit.
> When every feature is done: swap them back (new suite → `tests/`, old →
> `tests_legacy/` or deleted). Worktree branches made before the swap still
> use `tests/<feature>/` paths: after cherry-picking, `git mv` those files to
> `tests_new/<feature>/` and rename `tests.helpers` → `tests_new.helpers`.

## Progress

_Last update: 2026-10-06._ Merged = cherry-picked into `tests-restructure`
(nothing pushed). Whole new suite after the last merge: green (2672 passed,
1 skipped — `nse` needs `luac`), ~9 min.

| Feature | Access | CRUD | API | Robustness | Legacy reviewed | Documented |
|---|---|---|---|---|---|---|
| infrastructure ✅ | – | – | – | – | – | |
| rules ✅ (+ proposal threads, justification edit/delete) | ✅ | ✅ | ✅ | ✅ | pending | |
| rule formats ✅ (syntax + parser, 15 formats) | – | – | – | – | ✅ (187 legacy pass) | |
| ATT&CK ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| comments ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| tags ✅ (+ `tests_new/imported_tags/`) | ✅ | ✅ | ✅ | ✅ | ✅ | |
| account ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (1 legacy test outdated) | |
| bundles ✅ | ✅ | ✅ | ✅ | ✅ | pending | |
| MISP | ✅ | ✅ | ✅ | ✅ | ✅ | |
| jobs | running | | | | | |
| connectors | ⏸ | ⏸ | ⏸ | ⏸ | | |
| GitHub for rules | ⏸ | ⏸ | ⏸ | ⏸ | | |
| workspace | ⏸ | ⏸ | ⏸ | ⏸ | | |
| roles | not started | | | | | |
| batch 3 (AI, notifications, reports, blog, community, rule tester, rule relations, Velociraptor, admin / config) | not started | | | | | |

### To resume (next session)

Credits: launch **at most one or two agents at a time**, and only after
asking — a feature agent costs ~200–340k tokens.

1. **MISP** — finished on `worktree-agent-a25c7188313fbb269`, not merged
   yet if this line is still here:
   `git cherry-pick 39ca1a5a..worktree-agent-a25c7188313fbb269`
   (watch `app/features/bundle/bundle.py`, also touched by the bundles work).
2. **jobs** — agent still running on `worktree-agent-acabcfd64d80c4d1e`; when
   it reports, cherry-pick its commits from the merge-base
   (`git log $(git merge-base tests-restructure <branch>)..<branch>`).
3. **Stopped agents (⏸)** — their commits are kept on their worktree
   branches (`.claude/worktrees/agent-*`). Resume each with the same brief
   ("finish the remaining layers, green run, final report"), then
   cherry-pick:
   - connectors — `worktree-agent-a2e8b745043534368`: 15 commits, nothing
     uncommitted; was on "the core cleaners for remote payloads".
   - GitHub for rules — `worktree-agent-aee616aa3aec834ba`: 15 commits,
     2 files uncommitted; was about to run its whole suite.
   - workspace — `worktree-agent-a1c82f23a2f45c6d6`: 2 files uncommitted;
     was on a `quick_meta` workspace loophole.
4. **roles**, then **batch 3**, one feature at a time.
5. Run the whole new suite **alone** (two pytest runs in one checkout share
   the SQLite file and corrupt each other), then update this table.
6. Review / drop the legacy tests of rules and bundles; write the "Testing"
   chapter (English) in `full_documentation.html`, README, CLAUDE.md.

Legacy tests now failing **on purpose** (they asserted the old behaviour):
`tests/roles/test_edit_rule_restricted.py` (2 — expect 200 instead
of 403), `tests/account/...test_edit_user_without_authentication`,
`tests/rules/test_proposal_edit.py::test_cannot_edit_decided_proposal`.

### Product decisions already taken (2026-10-06)

- Bundle names are unique **per user** (form, API, create-from-rule, chatbot).
- A bundle's owner (not only an admin) can rebuild its structure.
- A note's author edits / deletes / resolves it; while the bundle is private
  they can't reach it, and it is still theirs once it is public again.
- A proposal's author (or an admin) edits and deletes its justification,
  whatever the proposal's status.
- Proposals page: threads (a proposal + its revisions, in order), collapsed
  by default, filters, "?" help.

### Product decisions still open (tests follow the current behaviour)

- **Tags** — `rule.tag_any` rights are inconsistent (can delete any tag
  incl. `tlp:clear`, make a private tag public, but can't edit others'
  tags); state-changing GETs (`remove_tag`, `toggle_visibility`…) without
  CSRF; users can create `tlp:red`-style tags in taxonomy namespaces; rules
  accept another user's private tag.
- **Account** — emails case-sensitive; unlimited guesses on `/verify` codes
  for unverified accounts; register API returns a working key before
  verification; anyone logged in sees another user's stats (incl. private
  bundles); deleting a user may hit ~70 FKs without cascade on PostgreSQL;
  check `detail_user.html` for Vue `[[ ]]` injection via name / bio.
- **Comments** — `/api/comments` ignores `X-API-KEY`; bundle owner can't
  moderate comments on their bundle; no cap on @mentions per comment;
  dead legacy rule comment routes; `/rule/delete_comment` registered twice.
- **ATT&CK** — owner / admin technique edits not logged; deprecated
  techniques can be mapped; heatmap cached 6 h; admin routes check rights
  per route instead of `before_request`.
- **Bundles** — profile list shows public bundles only (even to the owner);
  `download_count` counts every download.
- **MISP** — an admin's export includes other users' private tags;
  `is_verified` kept after a failing test; `Convert_MISP` has no pagination;
  export includes owner's id and full name.
- **Formats** — NSE validation passes everything without `luac`; Suricata
  unknown keywords pass; "no format" rules can't be edited.
