# Bundle forks, merge requests and contributors — "GitHub for bundles"

Status: **planned — next big thing to build.** Nothing here exists yet.

A signed-in user can **fork** a bundle to work on their own copy, change it (rules, files, folders,
description), then **propose the changes back** to the original as a *merge request*. The owner
(or an admin) reviews it with the same interface as rule edit proposals — diff, schema, discussion —
and merges it, resolving conflicts. Forks stay connected to their origin: everyone sees "forked from",
the origin sees its forks and their proposals, both sides can pull the other's new changes.

Everything below reuses what exists: `Bundle` / `BundleNode` / `BundleRuleAssociation`,
`BundleHistory` (snapshots), `BundleRelease` (frozen snapshot + notes), `RuleEditProposal`
(pending / accepted / rejected / superseded, reviewer, reason, chain), `DiffViewer`, `CommentThread`,
`FileTree`, `BundleStructureEditor`, notifications, activity log, background jobs, connectors.

---

## 1. Vocabulary

| Term | Meaning |
|---|---|
| **Upstream** | the bundle a fork was made from |
| **Fork** | a bundle with `forked_from_id` = upstream; a full bundle of its own (owner, access, releases…) |
| **Base snapshot** | the upstream's snapshot at fork time, or at the last sync / merge — the common ancestor for 3-way merges |
| **Merge request (MR)** | "take these changes from bundle A into bundle B": fork → upstream (contribute) or upstream → fork (sync) |
| **Contributor** | a user with write rights on a bundle without owning it (roles below) |

---

## 2. Data model (new tables / columns — migrations only add)

### `bundle` (new columns)
- `forked_from_id` → bundle.id, `ondelete SET NULL` (an upstream deleted ≠ fork deleted)
- `forked_from_uuid` (kept when the upstream disappears, and across instances)
- `fork_base_snapshot` JSON — the common ancestor (see §5)
- `fork_base_at` DateTime — last sync / merge with upstream
- `fork_count` Integer (denormalised, for lists and sort)
- `accepts_proposals` Boolean default True — owner can close the bundle to merge requests
- `fork_policy` String: `anyone` | `contributors` | `nobody` (default `anyone` for public bundles)

### `bundle_merge_request`
- `id`, `uuid`
- `source_bundle_id`, `target_bundle_id` (both → bundle, `ondelete CASCADE` on target, `SET NULL` on source + `source_bundle_uuid` kept)
- `user_id` (author), `title`, `message` (markdown)
- `status`: `open` | `merged` | `closed` | `superseded` | `stale` (source deleted / made private) | `draft`
- `base_snapshot` JSON (ancestor), `source_snapshot` JSON (frozen at open / last update), `target_snapshot_at_open` JSON
- `diff` JSON (computed changeset, cached, recomputed when either side changes)
- `conflicts` JSON (list, see §5), `resolution` JSON (choices made by the reviewer)
- `reviewed_by_id`, `reviewed_at`, `review_note`
- `merged_release_id` → bundle_release (optional: "merge and release")
- `previous_mr_id` (chain, like `RuleEditProposal.previous_proposal_id`)
- `created_at`, `updated_at`

### `bundle_merge_request_item`
One row per change, so a reviewer can accept / reject **item by item** (partial merge):
- `mr_id`, `kind`: `rule_added` | `rule_removed` | `rule_modified` | `file_added` | `file_removed` |
  `file_modified` | `node_moved` | `node_renamed` | `folder_added` | `folder_removed` | `meta_changed` (name, description, tags, CVEs)
- `path` (node path in the tree), `rule_uuid`, `old_value`, `new_value`, `base_value` (JSON / text)
- `decision`: `pending` | `accept` | `reject` | `custom` (+ `custom_value`)
- `conflict` Boolean + `conflict_kind`

### `bundle_contributor`
- `bundle_id`, `user_id`, `role`: `maintainer` (merge MRs, edit, release) | `editor` (edit directly, no merge) | `reviewer` (comment / approve MRs)
- `added_by_id`, `added_at`; invitation flow: `status` `invited` | `active` | `declined`

### `bundle_mr_review`
Approvals like GitHub reviews: `mr_id`, `user_id`, `verdict` (`approve` | `request_changes` | `comment`), `body`, `created_at`.
Optional setting "N approvals before merge" per bundle.

### `bundle_watch`
`bundle_id`, `user_id`, `level` (`all` | `releases` | `merge_requests` | `none`) — drives alerts (§9).

---

## 3. Forking

**Who:** signed-in users; the bundle must be visible to them **and** `fork_policy` must allow it.
Private bundle → only owner / contributors / admin can fork (fork is private by default).
Admin can always fork.

**What is copied (background job `bundle_fork`, big bundles):**
- the tree (`BundleNode`, folders, custom files) — new ids, same names / order
- rule links: **the fork points to the same `Rule` rows** (no copy) until the fork's owner edits one
  (copy-on-write, §4)
- name (`"<name> (fork)"`, editable), description, tags, CVEs, license
- NOT copied: votes, views, downloads, favorites, notes (option "copy notes"), releases (the fork starts
  at none, but records the upstream release it came from: "forked from v1.4"), contributors, verified badge,
  connector link
- `fork_base_snapshot` = upstream snapshot now (same format as `BundleHistory.new_snapshot`)

**Can't fork:** your own bundle (offer "duplicate" instead — same code, no link), a fork of a fork is allowed
(chain shown as "forked from X, itself forked from Y"), a bundle in the trash, a connector-mirrored bundle
(fork allowed but marked "upstream lives on instance Z").

**Limits:** max forks per user per day (setting `bundle.fork_daily_limit`), max bundle size for
synchronous fork (else job).

---

## 4. Rules inside a fork — copy-on-write

The hard part: a bundle references **rules**, which have their own owners.

- Editing a rule in a fork that the fork owner **doesn't own** → Rulezet creates a **new rule** (copy, new uuid,
  `forked_from_rule_uuid`, author kept in metadata, license kept and checked) and swaps the link in the fork only.
  The original rule is untouched. The MR then shows "rule modified" with the diff original → copy.
- On merge into upstream, the reviewer chooses per rule:
  1. **Update the original rule** (only if the merger owns it or is admin) → becomes a new version in
     `RuleUpdateHistory`, the copy can be retired (soft-deleted) or kept.
  2. **Open a rule edit proposal** on the original (reuses `RuleEditProposal`) when the merger doesn't own it.
  3. **Link the copy instead** (the upstream now points to the fork's rule).
- Rule owned by the fork owner → edited in place like today (it's theirs everywhere — warn: "this rule is
  also in N other bundles").
- Rules added in the fork are normal new rules (owner = fork owner).
- Soft-deleted rules (`is_deleted`) are never merged in; `_active()` always used.
- A rule deleted upstream while modified in the fork = conflict (§5).
- License: a rule whose license forbids modification (setting list) can't be copy-edited → explain why.

---

## 5. Diff, three-way merge and conflicts

### Computing the diff
Compare **base** (ancestor), **source**, **target** snapshots, keyed by stable identities:
- nodes by `uuid` (add a `uuid` column to `BundleNode` — migration with backfill, needed for move/rename detection)
- rules by `rule.uuid` (+ `forked_from_rule_uuid` to match a copy with its original)
- files by node uuid, content compared (text diff via `DiffViewer`)

For each identity: unchanged / changed only in source (→ take it) / changed only in target (→ keep) /
changed on both sides the same way (→ fine) / **changed differently on both → conflict**.

### Conflict kinds (each with a UI and a default)
| Conflict | Example | Resolution offered |
|---|---|---|
| `content` | same rule / file edited differently | side-by-side 3-way diff, take source / target / edit by hand (`SmartEditor`) |
| `modify_delete` | rule edited in fork, removed upstream | keep (re-add) / drop |
| `move_move` | node moved to two different folders | pick a folder |
| `rename_rename` | node renamed differently | pick a name / type one |
| `name_clash` | two different nodes end with the same path | rename one (auto-suffix proposal) |
| `folder_delete_nonempty` | folder deleted on one side, files added inside on the other | keep folder / move files to root / drop |
| `rule_gone` | rule soft-deleted or hard-deleted meanwhile | drop / restore (admin) |
| `meta` | name / description / tags changed both sides | pick / merge tags (union) |
| `license` | incoming rule has a license incompatible with bundle's | block until resolved |
| `invalid` | incoming rule fails validation now | block, or accept with "invalid" flag (admin) |

- Merge button disabled until every conflict has a decision. Decisions saved in `resolution` (resume later).
- **Rebase / sync from upstream**: same engine reversed (upstream → fork MR, auto-merged when no conflict,
  "Sync fork" button, like GitHub's "Sync fork"). After any merge / sync, `fork_base_snapshot` = merged result.
- **Target changed while the MR was open** → MR marked "out of date", diff recomputed, new conflicts flagged,
  previous decisions kept when still valid.
- **Source changed** after opening → MR updates (snapshot refreshed), reviewers notified, approvals reset
  (setting) — like a new push on a PR.
- Merge is **atomic** (one transaction; on error everything rolls back), recorded in `BundleHistory`
  (`action = 'merge'`, link to MR) so it can be **reverted** from history like any bundle change.
- Big merges → background job `bundle_merge` with a `JobTracker`.

### "Overwriting a rule" safety
- Never overwrite a rule silently: a merge that changes a rule shows who owns it, which other bundles use it
  ("also in 3 bundles — they will see the change"), and the version bump.
- Concurrency: optimistic locking (`version` / `updated_at` check) on rule and bundle at merge time — if
  someone edited in between, abort and recompute.

---

## 6. Rights — every case

| Action | Anonymous | User | Fork owner | Bundle contributor (role) | Bundle owner | Admin |
|---|---|---|---|---|---|---|
| See fork link / forks list | public ones | public + own | ✓ | ✓ | ✓ (private forks: count only, names hidden) | ✓ |
| Fork | ✗ | if `fork_policy` | — | ✓ | duplicate instead | ✓ |
| Open MR to upstream | ✗ | own forks only | ✓ | ✓ | ✓ | ✓ |
| Comment / review MR | ✗ | public MRs: comment | ✓ | reviewer+ | ✓ | ✓ |
| Merge / close MR | ✗ | ✗ | ✗ | maintainer | ✓ | ✓ |
| Edit bundle directly | ✗ | ✗ | own fork | editor+ | ✓ | ✓ |
| Manage contributors | ✗ | ✗ | own fork | ✗ | ✓ | ✓ |
| Close bundle to MRs (`accepts_proposals`) | ✗ | ✗ | own fork | ✗ | ✓ | ✓ |

Backend guard on every route (owner / contributor role / `is_admin()`), never only in the template.

### Visibility changes
- **Fork made private** → its open MRs become `stale` (hidden content, kept for the owner); upstream sees
  "a private fork" in counts only, never names / content. Re-public → MRs can be reopened.
- **Upstream made private** → forks keep working, the "forked from" link shows only to people who can still see
  the upstream; new forks blocked for others; open MRs stay (author still sees their own MR + its diff, but not
  the target's private content beyond what they already had).
- **Upstream deleted (trash)** → forks keep `forked_from_uuid`, banner "upstream deleted"; MRs closed
  `stale`. Restored from trash → link back.
- **Fork deleted** → its MRs `stale`, diff kept (snapshots) so history stays readable.
- **User deleted / banned** → their forks follow the normal user-deletion policy; MRs closed.
- **Private bundle shared by link** (`share` param) → no fork through the share link unless owner allows.

---

## 7. Interface (reuse first)

### Bundle detail page
- Header: "**Forked from** _Upstream name_ (link, UserChip of its owner)" + "N commits behind / ahead"
  style counters ("3 changes not in upstream · 1 new upstream change") + **Sync fork** button.
- Buttons: **Fork** (with count, like GitHub), **Compare & open merge request** (on a fork with changes).
- New tabs: **Merge requests** (open / merged / closed, filters, badges), **Forks** (list: owner, changes,
  last activity, open MR), **Contributors**, **Network** (graph, below).

### Merge request page — same look as rule edit proposals
- Reuse the rule proposal page layout: header with status pill, author `UserChip`, message (markdown),
  `CommentThread`, approvals bar, reviewer note on merge / close.
- **Changes** tab: list of `bundle_merge_request_item` grouped by folder, each expandable with `DiffViewer`
  (rules and files), `FileTree` before / after side by side, per-item accept / reject.
- **Conflicts** tab: one card per conflict with the 3 versions and the choice buttons, progress
  "3 / 5 resolved".
- **Schema / graph**: reuse the proposal history graph / ECharts (`ChartViewer` or the graph component used
  for rule proposals) to draw the bundle network: upstream at the root, forks as branches, MRs as arrows,
  merged ones in green — clickable nodes.
- Checks panel (like CI on a PR): every incoming rule validated (`validate_rule_syntax`), quality score
  delta, health score of the bundle after merge, license compatibility, duplicates (similarity) — merge
  allowed with warnings, blocked on errors (setting).
- "Merge and release": merge then create a `BundleRelease` (version bump suggested, notes pre-filled with the
  MR list — reuse release modal).

### Lists
- Bundle list cards / table: fork icon + "forked from …", fork count column, filter "forks only" / "originals only".
- User profile: "My forks", "My merge requests".
- Admin: MR moderation queue (all instances), stuck / stale MRs.

---

## 8. Releases with forks
- A fork records the upstream release it started from; the release page of upstream shows "N forks since".
- Merging into upstream can create a release; release notes list merged MRs + contributors (credits).
- A fork can make its own releases (independent versions, prefixed optional).
- Comparing two releases (existing) extended to compare a release with a fork.

### Release comparison — a full page, much more detailed (replaces today's modal)
Today the comparison of two releases opens in a modal with counts / lists. It becomes a **page of its own**,
GitHub "compare" style: `/bundle/<id>/compare/<from>...<to>` (shareable URL, works for release ↔ release,
release ↔ current state, release ↔ fork, fork ↔ upstream — the same page the merge request "Changes" tab uses).
- **Summary bar**: rules added / removed / modified, files added / removed / modified, folders moved / renamed,
  metadata changed, health score and rule quality before → after, contributors between the two.
- **Every changed file and rule shows its diff** inline with `DiffViewer` (side-by-side / unified toggle,
  collapsed by default when big, "expand all"), rule metadata diff (title, tags, ATT&CK, CVE, license),
  validation status before / after.
- **Tree view** of both versions (`FileTree`) side by side, changed nodes highlighted, click → jump to its diff;
  moves and renames shown as such (needs node uuids, §5), not as delete + add.
- **Filters**: by kind of change, by format, by folder, search in paths / titles; "only rules", "only files".
- **Release notes** of every release in between, and the merged MRs they include.
- **Download** the changes: patch-like JSON, zip of changed rules only, Markdown changelog (reuse the Markdown
  report style of "Create issue").
- Big comparisons: diff computed by a background job, cached per (from, to) pair, paginated per folder.
- Rights: same as viewing the bundle (private releases / forks never leak through a compare URL).

---

## 9. Alerts and notifications (reuse `notification` + preferences + email)
- Owner / maintainers: someone forked your bundle (digest option), new MR, MR updated, comment, approval,
  conflict appeared because the bundle changed.
- MR author: review requested changes, approved, merged, closed, out of date, upstream deleted / private.
- Fork owner: upstream has new changes / new release ("Sync fork"), a rule of your fork was changed upstream.
- Watchers (`bundle_watch`): per level.
- Contributor invitation / role change.
- Each in the activity log: `bundle.fork`, `bundle.mr_open`, `bundle.mr_merge`, `bundle.mr_close`,
  `bundle.sync`, `bundle.contributor_add`…

---

## 10. Export, import, federation
- `.bundle.json` export carries `forked_from_uuid`, `fork_base_at`, and optionally the base snapshot
  (to keep 3-way merge possible on another instance).
- Import on another Rulezet: if the upstream uuid exists there → offer "import as a fork of it" (link) or
  "import as an independent bundle".
- **Connectors (federation)**: an instance can pull a remote bundle (`remote_bundle_uuid`); a fork of a mirrored
  bundle can open an MR **to the remote instance** via API (later phase — needs an API endpoint
  `POST /api/bundle/<uuid>/merge_requests` with API key + the source snapshot). Pull modes soft / hard keep
  their meaning; hard pull on a bundle that has local forks → those forks see "upstream changed".
- API (public / private namespaces): list forks, fork, open / list / get MR, merge (owner key), sync.
- Rulesets git mirror: a fork can be mirrored like any bundle.

## 11. Background jobs (`@register_handler`)
- `bundle_fork` (big trees), `bundle_merge` (atomic, with progress), `bundle_mr_recompute` (when a side
  changes — debounced), `bundle_fork_sync_check` (nightly: compute behind/ahead counters, notify),
  `bundle_mr_stale_cleanup` (close MRs whose source vanished, after N days, setting).
- All idempotent, resumable, with `JobTracker` logs; never two merges on the same target at once
  (lock per target bundle).

## 12. Settings (`app/config/*.json`)
`bundle.fork_enabled`, `bundle.fork_daily_limit`, `bundle.fork_default_policy`, `bundle.mr_required_approvals`,
`bundle.mr_block_on_invalid_rule`, `bundle.mr_reset_approvals_on_update`, `bundle.mr_stale_days`,
`bundle.locked_licenses` (rules that can't be copy-edited).

## 13. Tests (tests_new/bundles/)
- Access matrices for every new route (anonymous / user / fork owner / contributor roles / owner / admin).
- Fork: tree copied, rules shared, private upstream rules, private fork, fork of fork, limits.
- Copy-on-write: editing a foreign rule creates a copy, original untouched, other bundles untouched.
- Diff / merge engine (pure functions, no DB): every conflict kind in §5, rename + move detection,
  idempotent re-merge, partial merge, revert after merge.
- Visibility changes (§6) and deletions mid-MR.
- Concurrency: target edited during merge → abort cleanly.
- Export / import round-trip keeps the fork link; connector pull with local forks.
- Robustness: huge bundle (job path), malformed snapshot, MR to itself, cycle (A fork of B fork of A — impossible
  by construction but checked).

---

## 14. Phases
1. **Model + fork + "forked from" + forks list** (no merge yet) — copy-on-write rules, node uuids.
2. **Diff engine + MR (fork → upstream), no conflicts** (fast-forward only), MR page reusing proposal UI,
   comments, notifications.
3. **Conflicts + 3-way merge + partial merge + Sync fork** + checks panel.
4. **Contributors & roles, reviews / approvals, accepts_proposals, watch levels.**
5. **Network graph, merge-and-release, credits in release notes.**
6. **Export / import / API / federation MRs across instances.**

---

## 15. More GitHub-like ideas for bundles
- **Issues on a bundle** (lighter than MRs: "rule X fires too much", with labels) — reuse `CommentThread`;
  and the new "Create issue" Markdown report could open one *inside Rulezet* for Rulezet bundles.
- **Stars → already favorites; "Used by"**: how many workspaces / connectors / instances use the bundle.
- **Branches inside one bundle** (draft line vs stable) — maybe later; forks cover most needs.
- **Protected bundle**: no direct edit, only MRs (even for maintainers), required approvals, required green checks.
- **CODEOWNERS-like**: per-folder reviewers ("sigma/ → @alice").
- **Templates**: "Use this bundle as a template" (fork without link).
- **Bundle insights**: contributors over time, MR throughput, rule churn (ECharts).
- **Changelog / blame**: who added each rule and through which MR (from `BundleHistory`).
- **Discussions** per bundle (Q&A), **pinned** notes.
- **Automatic MRs**: a workflow / bot proposes updates (e.g. rules updated upstream on GitHub sources,
  new rules matching the bundle's CVE / ATT&CK scope) — reviewed like any MR.
- **Bundle badges** for READMEs (health, rules count, last release) served as SVG.
- **Compare any two bundles** (not only forks) with the same diff view, and "merge these two bundles".
- **Rule-level suggestions in an MR review** ("suggest a change" on a line, applied in one click).
