Flask + Vue.js 3 + PostgreSQL. Community platform for cybersecurity detection rules (YARA, Sigma, Suricata, Zeek, etc.). Live at rulezet.org.

Run dev: `source env/bin/activate && ./launch.sh -l`
Run tests: `./launch.sh -t` or `FLASKENV=testing pytest tests`
Single test: `FLASKENV=testing pytest tests/rules/test_rule.py -k "test_name"`
DB init: `python3 app.py -i` — DB reset: `python3 app.py -r`
Migrations: `flask db migrate -m "desc" && flask db upgrade`
Environments via `FLASKENV`: `development` (pg, debug), `testing` (sqlite, no csrf), `production` (pg).
App runs on `127.0.0.1:7009` by default. Secrets in `.env`.

All SQLAlchemy models in `app/core/db_class/db.py`.
Feature logic split: blueprint in `app/features/<feature>/<feature>.py`, DB logic in `*_core.py`.
REST API (Flask-RESTX, CSRF exempt) under `/api/`, swagger at `/api/`. Public/private namespaces per feature.
API key auth via `@api_required` decorator, key in `X-API-KEY` header.
Background jobs: `BackgroundJob` rows, handlers registered with `@register_handler('type')` in `job_handlers.py`, worker polls every 2s.
Activity log everywhere: `from app.core.utils.activity_log import log_activity` — action dot-namespaced e.g. `rule.create`.

CRITICAL: never use `Rule.query` directly — always use `_active()` from `rule_core.py` which filters `is_deleted == False`.
Rules are soft-deleted (fields: `is_deleted`, `deleted_at`, `deleted_by_id`, `delete_batch_uuid`). Trash admin at `/rule/trash`.
Default tags `tlp:clear` and `pap:clear` auto-attached to every new rule via `_attach_default_tags()`.

Vue.js 3 UMD (not build step), ES modules, delimiters `['[[', ']]']` in templates.
Toasts via `create_message(msg, class)` from `/static/js/toaster.js` — never inline alert divs.
Pagination: use `PaginationComponent` from `/static/js/rule/paginationComponent.js`.
`ChartViewer` needs `window.echarts` (ECharts CDN) loaded globally; data format: `{ categories: [...], series: [{ name, values: [...] }] }`.

Page banner structure (all nav pages use this):
```html
<div class="explorer-banner mb-4">
  <i class="fa-solid fa-[icon] banner-watermark"></i>
  <div class="d-flex align-items-center gap-3 mb-3">
    <div class="banner-icon"><i class="fa-solid fa-[icon]"></i></div>
    <div><h2 class="fw-bold mb-1">Title</h2><div class="banner-accent"></div></div>
  </div>
  <p class="text-muted mb-0" style="max-width:600px;font-size:.95rem;">Description.</p>
</div>
```
Banner gradient uses only blue tones: `#0d6efd → #0a58ca`.

Style reference for new pages: `app/templates/account/detail_user.html` + `app/static/css/account/user_detail.css`.
KPI cards: `.ud-kpi-card.ud-kpi-card--blue/teal/green/gold/purple/orange`
Info cells: `.ud-info-cell` in a `.ud-info-grid` container
Section headers: `.ud-section-header` with `.ud-section-icon`, `.ud-section-title`, `.ud-section-sub`
Chart cards: `.ud-chart-card.ud-chart-card--accent-blue/teal/purple/orange/green/gold`

Dark mode CSS vars: `--text-color`, `--subtle-text-color`, `--card-bg-color`, `--border-color`, `--light-bg-color`.
Use `var(--subtle-text-color)` for secondary text — `var(--color-text)` does not exist.

Shared components in `app/static/js/components/` (ES modules, each has matching CSS in `css/components/`):
SmartEditor, CodeViewer, DiffViewer, AnsiTerminal, ChartViewer, FileTree, GraphViewer, RequestBuilder, Timeline.

RuleList component (`app/static/js/rule/ruleList.js`) — always register with TagsDisplaysList + VulnerabilityDisplaysList.
RuleList CSS deps: `dataTable.css`, `code-viewer.css`, `ruleList.css`.
RuleList modes: `read`, `select`, `manage`. Bulk actions `delete`/`download`/`bundle` are internal.
ATT&CK chips use `AttackDisplayList` from `/static/js/attack/attackDisplayList.js` — CSS is in `ruleList.css` (adl-* classes).
MultiAttackFilter `apiEndpoint` prop must return `{ id: technique_id_string, name, tactic_keys, count }` — id must be the string like "T1068", not the integer PK.

Tag tooltips use Vue `<teleport to="body">` with `position:fixed` to escape overflow:hidden parents.
Connectors (federation sync) admin-only. Pull modes: soft (skip existing) / hard (update in place). Match by uuid only.
Instance telemetry: phone-home to rulezet.org every 24h. `IS_OFFICIAL_INSTANCE=true` only on rulezet.org.
Tests: SQLite, no CSRF. Fixtures in `conftest.py`: `create_user_test()`, `create_admin_test()`, `create_rule_test()`.
