# 05 — Hard-coded configuration

> Status: step 1 done — app/config/ folder, admin page, first 16 settings, formats API

## How it works

- **One JSON file per setting in `app/config/<key>.json`**: `label`, `category`, `description`, `public`, `value`
  (+ optional `python_type`: `tuple`, `set`, `dict_int_keys`). Dropping a file in the folder is enough for it to
  appear on the admin page and be readable by the code.
- Code reads it with `CONST = setting('<key>')` (live value that behaves like the dict/list; `.value` for a real
  object) or `get_setting('<key>')` — `app/core/utils/app_settings.py`.
- Admin changes are stored in the `app_setting` table (cached 30 s per process); the file stays the default and is
  never rewritten, so `git pull` on a server keeps working. "Reset" deletes the DB value.
- **Updates without conflicts**: the row keeps `base_value`, the file value the admin edited. If an update changes
  the file, the value in use is a three-way merge (`merge_values`): dicts take the new file and re-apply the keys the
  admin changed/added/removed (recursively), lists keep the admin's items plus the ones the update added. The page
  flags it ("File updated") with "Keep the merge" / "Use the file".
- **History**: every save / reset / kept merge / restore goes to `app_setting_history`; the History tab of a setting
  shows each version and restores it (with its own base, so a later file update is still merged in).
- `app/core/utils/hardcoded_inventory.py` reads the source files and lists every remaining module-level
  list/dict/tuple/set constant and the JSON/TXT data files.
- Admin page **Admin → Configuration** (`/admin/configuration`): KPI tiles, settings by category (CodeViewer for the
  value, SmartEditor to edit, DiffViewer against the file), every value in the code, data files viewer.
- Public settings: `GET /api/config/settings/<key>`. Formats: `GET /api/config/formats` (always read from the DB).
- The root `config/` folder is gone: `config/default_tags.json` is now `app/config/tags.defaults.json`.

## Editable now

| Key | Was | Used by |
|-----|-----|---------|
| `gamification.points`, `gamification.level_thresholds` | `POINTS`, `LEVEL_THRESHOLDS` | score, levels, "how to earn points" |
| `ai.claude_prices` | `CLAUDE_PRICES` | AI cost estimates |
| `git.public_hosts`, `git.provider_labels`, `git.provider_icons` *(public)* | `git_provider.py` | host detection, icons (server + `git-links.js`) |
| `report.reasons` *(public)* | `VALID_REASONS` + copy in `ReportModal.js` | report validation, report modal |
| `notification.type_icons` | `_TYPE_ICON` | notification icons |
| `bundle.note_tag_prefixes` | `NOTE_TAG_PREFIXES` | bundle notes |
| `tags.risk_colors` | `_RISK_DISPLAY_COLORS` | false-positive risk tags |
| `account.avatar_icons`, `account.avatar_backgrounds`, `account.avatar_borders` | `AVATAR_*` | avatar editor |
| `rulesets.extension_by_format` | `_EXTENSION_BY_FORMAT` | Rulesets mirror file names |
| `formats.catalog` *(public)* | `FORMAT_CATALOG` | Rule formats page, `/api/config/formats`, chatbot |
| `tags.defaults` | `config/default_tags.json` | tags attached to every new rule, namespaces seeded at init |

Also: the chatbot no longer has its own format list or descriptions — it reads the registered formats from the DB
and the descriptions from `formats.catalog`.

## Read-only on purpose

Values the code branches on stay in the code: parser keywords (Suricata/KQL/Plum…), allowed sort columns,
statuses, task types bound to Python handlers, upload extensions/MIME types (security), permission keys.
They are listed on the page as *Read-only*.

## Next candidates

- `chatbot._ROUTES` / `_NAVIGATE_KEYWORDS`, `log_action_defaults.ICONS` / `TITLES` (partly already overridable via
  Log definitions), `attack._TACTIC_LABELS_GLOBAL`, `bundle_history.FIELD_LABELS`, `ai_core._INJECTION_MARKERS`,
  `format_graph.OUTPUT_URLS`, `badges.BADGES`, `config_core` built-in themes.
- `licenses.txt` → served from the SPDX list (`rule_licence.py` already fetches it) instead of a file.
- Front-end copies of server lists (`multiSourceFilter.js`, `alertForm.js`…) → read from the API.
