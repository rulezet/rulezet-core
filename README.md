<div align="center">
  <img width="524" height="524" alt="Rulezet Logo" src="https://github.com/user-attachments/assets/8f583c28-8138-40b4-b532-371bb45622f4" />

  <br>

  <p>
    <a href="https://github.com/rulezet/rulezet-core/releases/latest">
      <img src="https://img.shields.io/github/v/release/rulezet/rulezet-core?style=for-the-badge&logo=github" alt="Release" />
    </a>
    <img src="https://img.shields.io/badge/license-AGPL--3.0-green?style=for-the-badge" alt="License" />
    <img src="https://img.shields.io/badge/platform-cybersecurity-red?style=for-the-badge" alt="Cybersecurity" />
  </p>

  <p>
    <img src="https://img.shields.io/badge/engine-YARA-informational?style=flat" alt="YARA" />
    <img src="https://img.shields.io/badge/engine-Sigma-orange?style=flat" alt="Sigma" />
    <img src="https://img.shields.io/badge/engine-Suricata-yellow?style=flat" alt="Suricata" />
    <img src="https://img.shields.io/badge/engine-Zeek-blue?style=flat" alt="Zeek" />
    <img src="https://img.shields.io/badge/engine-Wazuh-teal?style=flat" alt="Wazuh" />
    <img src="https://img.shields.io/badge/integration-MISP-purple?style=flat" alt="MISP" />
    <img src="https://img.shields.io/badge/integration-MITRE%20ATT%26CK-red?style=flat" alt="ATT&CK" />
  </p>
</div>

## Community-Driven Detection Rules Platform

**Rulezet** is an open-source web platform for sharing, evaluating, improving and managing
cybersecurity detection rules — YARA, Sigma, Suricata, Zeek, Wazuh, Snort-family (Sagan), CRS, Nova,
NSE, Elastic, KQL, Splunk, Kunai, ATR, Plum. Security teams publish rules, test them, review each
other's work and keep them in sync with their sources and their tools.

Rulezet is available as an online service at [https://rulezet.org/](https://rulezet.org/).

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+ · Flask · Flask-Login · Flask-SQLAlchemy · Flask-Migrate · Flask-RESTX |
| Frontend | Vue.js 3 (UMD, no build step) · Bootstrap 5.3 · Font Awesome 6 · ECharts |
| Database | PostgreSQL (production / development) · SQLite (tests) |
| Background jobs | `worker.py` — its own process, polling the `background_job` table |
| Web server | gunicorn (behind nginx in production), optional Redis cache |
| Dependencies | [uv](https://docs.astral.sh/uv/) — `pyproject.toml` + `uv.lock`, virtual environment in `.venv/` |
| Similarity | TF-IDF + FAISS + rapidfuzz |
| AI (optional) | Ollama, Anthropic or OpenAI-compatible providers |

---

## Installation

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone with the submodules (rule editor, tester, MISP / ATT&CK data…)
git clone --recurse-submodules https://github.com/rulezet/rulezet-core.git
cd rulezet-core

# 3. Install the dependencies (uv sync → .venv/) and initialise the database
python3 manage.py init
```

`init` prints the temporary administrator credentials: the first login asks for your own email and
password.

## Quick Start

```bash
python3 manage.py start-dev        # worker + gunicorn, reloads on code changes
```

The application runs on `http://127.0.0.1:7009` by default.

---

## `manage.py`

Every operation goes through `manage.py` (`python3 manage.py --help` lists them all):

| Command | What it does |
|---|---|
| `init` | first-time setup: `uv sync` (creates `.venv/`) and the database |
| `start-dev` | local run (`FLASKENV=development`): `worker.py` + gunicorn, debug, auto-reload |
| `update` | after `git pull`: sync with origin, `uv sync`, Ollama, `flask db upgrade` |
| `start-prod` / `restart-prod` | production launch (backup, sync, deps, migrations, start) / just restart |
| `deploy` | full production deployment: backup → update → start-prod |
| `test` | the test suite (`FLASKENV=testing`) |
| `db` | Flask-Migrate (`db`, `db migrate -m "…"`, `db downgrade`) |
| `db-init` / `db-reload` | create tables + admin user / drop and recreate everything |
| `backup` / `restore` | PostgreSQL dump to `backup/dumps/` / interactive restore |
| `pivotick` / `pivograph` | rebuild the graph assets from their submodules |

---

## Configuration

`config.py` selects the environment with `FLASKENV`:

| `FLASKENV` | Database | Notes |
|------------|----------|-------|
| `development` | PostgreSQL | debug |
| `testing` | SQLite | CSRF disabled |
| `production` | PostgreSQL | — |

Secrets live in `.env` — `.env_default` lists them all (secret key, mail server, `GITHUB_TOKEN` for
GitHub imports, `INSTANCE_PUBLIC_URL`, Ollama URL / model, AI provider keys…).

Everything else (lists, labels, prices, defaults, feature switches) is a **setting**: one JSON file per
setting in `app/config/`, editable live from **Admin → Configuration** (`/admin/configuration`). Admin
changes are kept apart from the file (three-way merge on update, full history), so `git pull` stays
clean.

---

## Supported Rule Formats

| Format | | Format | |
|---|---|---|---|
| `yara` | malware / file detection | `wazuh` | Wazuh HIDS / SIEM rules |
| `sigma` | generic SIEM detection (+ correlation rules) | `sagan` | Snort-family log rules |
| `suricata` | network IDS / IPS | `crs` | OWASP Core Rule Set (ModSecurity / Coraza) |
| `zeek` | network analysis scripts | `nova` | Nova hunting rules |
| `elastic` | Elastic Security rules | `nse` | Nmap Scripting Engine |
| `kql` | Kusto queries (Sentinel / Defender) | `splunk` | Splunk searches |
| `kunai` | Kunai (Linux) detections | `atr` | Agent Threat Rules |
| `plum` | Plum rules | | |

A new format is one class in `app/features/rule/rule_format/available_format/` (see below).

---

## Features

### Rules
- **Create**, **edit**, **propose edits** (owner review, discussion) and soft-**delete** with a trash
- **Parse** pasted content: format detected, metadata extracted
- **Import** from GitHub / Git repositories (Git Sources registry, scheduled syncs, quality score of each
  source), ZIP archives and JSON
- **Syntax validation** with each format's own engine; invalid rules are kept apart and can be fixed
- Rule **history**, versions, diff; **linked rules** (dependencies, YARA references, Wazuh parents,
  Sigma `related:` and correlations) as a graph
- **Quality score** per rule (documentation, traceability, validity, tests)
- Default **TLP:CLEAR** / **PAP:CLEAR** tags, MISP taxonomies and galaxies, ATT&CK techniques, CVEs

### Rule editor (`app/modules/rulezet-editor`)
- **YARA editor** and **Sigma editor** tabs on the create page: completion, live errors giving Rulezet's
  own verdict, quick fixes, hover help, rename, formatter, rule tools, templates, tutorial, several
  rules per document, a Fields panel that writes Rulezet's metadata into the rule
- **Checks** panel: Rulezet's validation plus external tools — YARA-X, CCCS YARA standard, yaraQA for
  YARA; SIEM conversion and SIEM data models (pySigma), SigmaHQ conventions, sigmalint, rsigma, search
  cost for Sigma; "Already in Rulezet?" for both
- **Create** checks every rule (already in Rulezet, syntax, external checks, samples) before writing
  anything: new rules created, your changed rules updated, other people's proposed to their owner

### Tests on samples (`app/modules/rulezet-tester`)
- Rules run on **sample sets** in a bubblewrap sandbox: YARA on files, Sigma on events (synthetic,
  benign and recorded attacks) — detections, misses and false positives, per rule version

### Explore
- **Rules** and **Bundles** explorers (search, filters, cards / table), bundle tree, **bundle forks
  and merge requests**
- **CVE response kits** (`/vulnerability/<id>`) and **ATT&CK technique pages** (`/attack/technique/<id>`):
  every rule for one subject, coverage per format, gaps, download
- **Workspace**, favourites, votes, comments, reports, notifications, leaderboard

### Federation and integrations
- **Connectors**: pull rules from other Rulezet instances (soft / hard), by uuid
- **Rulesets** mirrors: rules pushed to Git repositories
- **MISP** (taxonomies, galaxies, export), **Velociraptor**, MITRE **ATT&CK** data
- **REST API** with API keys

### Administration
- Users, organisations, verification; activity log (public / private); background jobs with live
  progress
- **Workflows**: scheduled and chained admin tasks (maintenance, data refresh, Rulesets publication…)
  with templates, runs, notes, calendar
- Settings, rule formats, similarity engine, reported rules, trash, AI assistants (chatbot, rule
  analysis, fixer, generator)
- Guided **tour** on every page, light / dark mode

---

## API Access

Swagger UI at `/api/`. Public namespaces read without a key; private ones need `X-API-KEY`
(generated with your account, shown on your profile).

Namespaces: `rule`, `bundle`, `connector`, `account`, `comment`, `config`, `log`, `instance`,
`rule_tester`, `utils`.

```bash
# Create a rule
curl -X POST http://127.0.0.1:7009/api/rule/private/create \
  -H "X-API-KEY: your-key" -H "Content-Type: application/json" \
  -d '{"format": "yara", "title": "My Rule", "to_string": "rule My_Rule { condition: true }"}'

# Validate a rule without saving it
curl -X POST http://127.0.0.1:7009/api/rule/public/validate \
  -H "Content-Type: application/json" \
  -d '{"format": "sigma", "content": "title: …"}'
```

---

## Running Tests

```bash
python3 manage.py test                  # the suite CI runs (tests/)
FLASKENV=testing pytest tests/rules/test_rule.py -k "test_name"
FLASKENV=testing pytest tests_new        # the new suite, by feature (docs/design/test_restructure.md)

# submodules
cd app/modules/rulezet-editor && npm test           # editor (JS)
cd app/modules/rulezet-tester && pytest             # tester
```

Both suites create their app, SQLite schema and baseline data once per run. Each
test uses a transaction that is rolled back afterwards, including changes made by
`db.session.commit()` inside requests. App settings and login throttling are reset
between tests too. Tests that need independent commits across worker contexts use
`@pytest.mark.independent_db` to restore a SQLite snapshot instead; they also reuse
the schema and seed data. Database and session files live in pytest's temporary directory,
separately for each suite and worker; `instance/rulezet-test.sqlite` is not used.
Tests that touch other shared checkout files should still be run sequentially.

---

## UI Previews

| Homepage | Rule Detail | Invalid Rules |
|----------|-------------|---------------|
| ![Home](docs/rulezet_home_final.png) | ![Detail](docs/rulezet_detail_readme.png) | ![Invalid](docs/rulezet_invalid_rule.png) |

---

## Adding a New Rule Format

1. Create `app/features/rule/rule_format/available_format/myformat_format.py`
2. Subclass `RuleType` from `rule_type_abstract.py`
3. Implement `format`, `validate()`, `parse_metadata()`, `detect()`, `get_rule_files()`,
   `extract_rules_from_file()`, `find_rule_in_repo()`
4. `load_all_rule_formats()` discovers it — no other registration

To give it an editor, tests on samples and external checks as YARA and Sigma have, follow the
`rulezet-editor-format` skill (`app/modules/rulezet-editor/skills/`, also in
[rulezet-ai-skill](https://github.com/rulezet/rulezet-ai-skill)).

---

## Contributing

- Pull requests for features and fixes are welcome (commits: `fix: [section] …` / `chg: [section] …`)
- Issues and ideas: [GitHub Issues](https://github.com/rulezet/rulezet-core/issues)
- New rule formats, sample sets, documentation
- Working with an AI coding assistant: [rulezet-ai-skill](https://github.com/rulezet/rulezet-ai-skill)

---

## License

This software is licensed under the [GNU Affero General Public License version 3](http://www.gnu.org/licenses/agpl-3.0.html).

```
Copyright (C) 2025-2026 CIRCL - Computer Incident Response Center Luxembourg
Copyright (C) 2025-2026 Thëo GEFFE @ CIRCL
```

---

## Funding

Rulezet is co-funded by [CIRCL](https://www.circl.lu/) and by the European Union under the [FETTA](https://www.circl.lu/pub/press/20240131/) (Federated European Team for Threat Analysis) project.

![EU logo](https://www.vulnerability-lookup.org/images/eu-funded.jpg)

---

## Inspiration

This project is inspired by [Flask launchpad](https://github.com/ecrou-exact/flask-launchpad), extended with a modern UI, collaborative features, and full integration capabilities.
