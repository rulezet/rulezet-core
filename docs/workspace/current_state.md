# Workspace — current state

> Status: **implemented**, single-owner, no collaboration model yet.
> This document describes what exists in the codebase today (2026-09-18).
> It's the baseline every future proposal in this folder should build on.

## What it is today

A Workspace is a private, personal folder a user creates to group rules
around a theme (a campaign, a CVE, a project) with a bit of context around
them: freeform notes/documents, external reference links, per-rule notes,
tags/CVEs/ATT&CK techniques on the workspace itself, and the ability to
export the workspace's current rule set as a Bundle. It is **not** a
collaboration space — there is exactly one owner, no member list, no
sharing.

It is already a fairly built-out feature (documents with autosave, bulk rule
actions, bundle export with drag-organize, KPI filtering by rule status) —
not a placeholder. The gaps described below are structural (code
organization, missing multi-user model) rather than missing functionality.

## URLs

Blueprint: `workspace_blueprint`, registered with `url_prefix='/workspace'`
in `app/__init__.py`.

| URL | Method | View | Purpose |
|---|---|---|---|
| `/workspace` | GET | `my_rules` | Gallery/listing of the current user's workspaces (renders `workspace/my_rules.html`) |
| `/workspace/<uuid>` | GET | `workspace_detail` | One workspace's detail page (renders `workspace/workspace_detail.html`) |
| `/workspace/<uuid>` | PATCH | `update_workspace` | Update name/description/icon/color |
| `/workspace/<uuid>` | DELETE | `delete_workspace` | Delete the workspace |

(As of 2026-09-18: renamed from `/workspace/my_rules` and
`/workspace/<uuid>/detail` — the GET/PATCH/DELETE trio above deliberately
share the same URL, one verb per action.)

Everything else is a JSON API consumed by the two pages' own inline Vue
apps — no other page renders HTML:

| URL | Method | Purpose |
|---|---|---|
| `/workspace/list` | GET | List workspaces (`?scope=all` for admins — every user's workspaces) |
| `/workspace/create` | POST | Create a workspace |
| `/workspace/<uuid>/rules` | POST | Add rule(s) to a workspace |
| `/workspace/<uuid>/rules/<rule_id>` | DELETE | Remove one rule |
| `/workspace/<uuid>/rules/bulk` | DELETE | Bulk-remove rules |
| `/workspace/<uuid>/rules/<rule_id>/note` | PATCH | Set a per-rule freeform note |
| `/workspace/<uuid>/rule_ids` | GET | Active rule ids (feeds "Export as Bundle") |
| `/workspace/<uuid>/kpis` | GET | Rule counts by status (total/draft/testing/production/deprecated) |
| `/workspace/<uuid>/documents` | GET/POST | List/create notes-and-docs entries |
| `/workspace/<uuid>/documents/<id>` | PATCH/DELETE | Edit/delete a document |
| `/workspace/<uuid>/links` | GET/POST | List/create external reference links |
| `/workspace/<uuid>/links/<id>` | DELETE | Delete a link |
| `/workspace/<uuid>/link_bundle` | POST | Export the workspace's rules as a new/existing Bundle |
| `/workspace/<uuid>/bundles` | GET | Bundles previously exported from this workspace |
| `/workspace/<uuid>/bundles/<id>` | DELETE | Unlink a bundle (keeps the bundle itself) |
| `/workspace/<uuid>/tags` (+`/<id>`) | GET/POST/DELETE | Tag associations on the workspace |
| `/workspace/<uuid>/attacks` (+`/<id>`) | GET/POST/DELETE | ATT&CK technique associations |

Access control: every route is `@login_required`; owner-or-admin is checked
inline per-route (`ws.user_id != current_user.id and not
current_user.is_admin()`), not via a `before_request` hook. Consistent
across all routes.

## Data model (`app/core/db_class/db.py`)

- **`Workspace`** — `id`, `uuid` (unique), `name` (≤100 chars),
  `description`, `icon` (default `fa-folder`), `color` (default `#0d6efd`),
  `url` (single reference URL), `cve_id` (JSON-encoded list, via a
  `cves_list` property), `other` (reserved/unused), `user_id` FK — the
  **single** owner. `rule_count()` helper, `to_json()`.
  **No membership/sharing field exists at all** — no `is_public`, no
  members table. A workspace is strictly private to its owner (admins can
  see all via `scope=all`, but that's an admin override, not sharing).
- **`WorkspaceRule`** — association table (workspace ↔ rule), unique per
  pair, `added_at`, `note` (per-rule freeform text).
- **`WorkspaceDocument`** — `title`, `content` (markdown), timestamps. A
  lightweight notes/wiki scoped to one workspace.
- **`WorkspaceLink`** — `title`, `url`, `description`. External reference
  links.
- **`WorkspaceTagAssociation`** / **`WorkspaceAttackAssociation`** —
  workspace ↔ Tag / workspace ↔ AttackTechnique, unique per pair.

Bundles relate indirectly: `Bundle.source_workspace_id` records which
workspace a bundle was exported from (set/cleared by `link_bundle` /
`unlink_bundle`) — Workspace itself holds no bundle FK.

Deletion is a **hard delete** (unlike `Rule`, which is soft-deleted) —
cascades via FK `ondelete='CASCADE'` to rule/tag/attack associations.

## Backend logic

`app/features/workspace/workspace_core.py` (94 lines) covers only the
original CRUD:
`get_user_workspaces`, `get_all_workspaces`, `get_workspace_by_uuid`,
`create_workspace`, `update_workspace`, `delete_workspace`,
`add_rule_to_workspace`, `bulk_add_rules_to_workspace`,
`remove_rule_from_workspace`, `get_workspace_rule_ids` (correctly filters
`Rule.is_deleted == False` via the join).

**Everything else — documents, links, tags, attacks, bundle linking,
KPIs — is implemented directly inline in `workspace.py` route handlers**,
not factored into `_core.py`. This is a deviation from the project's usual
feature/`_core.py` split and worth fixing before this file grows further.

## UI / UX

### Listing page — `workspace/my_rules.html` + `css/workspace/my_rules.css`

A card **gallery grid**, not a list: one `.ws-gallery-card` per workspace
(icon, color, name, rule count, owner when in admin scope, description,
delete button, `.card-security-premium` hover), plus an always-present
"New Workspace" empty-state card and a create modal (name / description /
icon picker / color). Breadcrumb + `.explorer-banner` already match the
project's page-banner convention. Admin-only "My Workspaces / All Users"
scope toggle.

### Detail page — `workspace/workspace_detail.html` + `css/workspace/workspace_detail.css`

~1900 lines, all Vue logic inline in the template's own `<script
type="module">` block (**no file exists under `app/static/js/workspace/`**
— a deviation from the project's "feature JS → `app/static/js/<feature>/`"
convention, and the main obstacle to any deeper refactor of this page).

Structure:
- Breadcrumb + banner (icon/color driven by the workspace's own
  `icon`/`color`, via a bespoke `.wd-ws-icon` — intentionally not the
  standard `.banner-icon`, since the icon's background color is
  per-workspace and user-chosen).
- **Metadata + Taxonomy card** — owner (`UserChip`), created date,
  inline-editable reference URL, `vulnerability-display` /
  `tag-display` / `attack-display` for the workspace's own CVEs/tags/ATT&CK.
  Uses the standard `card_detail` / `card-watermark-detail` /
  `premium-accent-line` pattern.
- **KPI strip** — total/draft/testing/production/deprecated rule counts,
  clickable as status filters. Icon+value card style matching
  `account/detail_user.html`'s `.ud-kpi-card` (`.wd-kpi-icon` /
  `.wd-kpi-value` / `.wd-kpi-label`, one color variant per status).
- **Tab nav** (`.dr-nav`, reused from the rule detail page) — five tabs:
  1. **Rules** — full `<rule-list mode="manage">` (status filter, bulk
     status/tag/remove actions), "Add Rules" modal (`rule-list
     mode="select"`), "Export as Bundle" (two-step: pick/create a bundle,
     then `bundle-structure-editor` + `bundle-rule-selector` to organize).
  2. **Notes & Docs** — grid of documents, inline `smart-editor` (markdown,
     autosave), file import, rename/delete.
  3. **External Links** — add-link form + list with delete.
  4. **Bundles** — bundles exported from this workspace (links to
     `/bundle/detail/<id>`, unlink action).
  5. **What's Next** *(added 2026-09-18)* — a non-functional roadmap
     preview: five "coming soon" cards (Connector, Draft Rules, Publish
     Checklist, Test History, Activity Feed). Nothing in this tab is wired
     to anything; it exists purely to communicate direction. A dedicated
     doc fleshing out each of these will land in this folder as we design
     them.

Components already wired in: `RuleList`, `SmartEditor`, `IconPicker`,
`TagInput`, `AttackInput`, `TagDisplay`, `UserChip`, `VulnerabilityInput`,
`VulnerabilityDisplay`, `AttackDisplay`, `RuleBundleManager`,
`BundleRuleSelector`, `BundleStructureEditor` — essentially the full shared
component library already in use here.

Both CSS files consistently use the shared dark-mode tokens
(`var(--card-bg-color)`, `var(--border-color)`, `var(--subtle-text-color)`,
`var(--light-bg-color)`) — not ad-hoc.

## Known gaps (as of 2026-09-18)

1. **No collaboration model.** Single `user_id` owner, no members, no
   sharing. Any "team workspace" direction needs a membership/roles table
   from scratch.
2. **JS is fully inline in the template**, not split into
   `app/static/js/workspace/*.js` files per the project convention. Makes
   the detail page harder to extend and impossible to unit-test in
   isolation.
3. **`workspace_core.py` only covers original rule/workspace CRUD** —
   documents/links/tags/attacks/bundle-linking logic all live directly in
   route handlers in `workspace.py`.
4. **No "quick add to workspace" from outside a workspace.** Getting a rule
   into a workspace today means opening the workspace and using its own
   "Add Rules" search modal — there's no one-click "add to workspace"
   action from a rule's own detail page or from a rule list's bulk actions
   (unlike Bundles, which do have that kind of quick action). This is
   likely the single biggest adoption friction point today.
5. **Hard delete, no soft-delete/trash**, unlike Rule.
6. **Telemetry/discoverability**: nothing today measures or exposes how
   much Workspaces are actually used (no dashboard KPI card for it, e.g.),
   making it hard to know today whether changes are moving adoption.
