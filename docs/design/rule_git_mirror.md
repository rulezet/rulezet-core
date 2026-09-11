# Rule Git Mirror ("Rulesets") — Design Plan

> Status: **implemented**, multi-repo, verified against a real GitHub push.
> RuleMirrorConfig (now multi-row — an instance can run several mirror
> targets, not just one), the admin "Rulesets" settings page (a table of
> configs, not a single form), the how-it-works page, the
> `rule_git_mirror_sync` job handler, and the Task Scheduler entry all
> exist and are wired together. Off by default; nothing runs until an
> admin adds a config and enables it. Verified end to end against a real
> repo (`rulezet/rulezet-rulesets`) with real rules — initial sync,
> incremental sync, and the mandatory pre-push connection test all
> confirmed working live, not just in a scratch/local test repo.
>
> Since first going live, three real bugs surfaced and were fixed (see
> "Fixed since going live" below): a background-job current_user crash, an
> incremental-sync cutoff comparing timestamps in two different timezone
> conventions (made every incremental sync think everything had changed),
> and index.add() silently failing to stage a rule's old filename after a
> title-driven rename (the direct cause of a real diverged-history incident
> on the official mirror, resolved with a force-push once diagnosed).
> Steps 4–5 (the real ~600k-rule initial load on rulezet.org, then turning
> on the recurring schedule) are still an operational action for whoever
> runs that instance — see "Set it up on your own instance" in the in-app
> how-it-works page for the exact steps.

## Changes since the initial implementation

- **Multi-repo**: `RuleMirrorConfig` gained `uuid`, `name`, `created_at` —
  an instance can configure several independent mirror targets (e.g. the
  official rulezet.org mirror plus a private team mirror), each with its
  own repo/branch/token, each syncable independently. The settings page is
  now a table (`rulesetsTable.js`, same pattern as the MISP/Velociraptor
  connector tables) with create/edit/delete/enable/run-now per row.
- **Mandatory connection test**: `RuleMirrorConfig` gained `is_verified`,
  `last_error`, `last_tested_at`. `test_config()` hits the GitHub API (no
  clone/push) to confirm the token authenticates and has push access.
  Changing repo URL/branch/token resets `is_verified`. "Run now" always
  calls `test_config()` itself immediately before creating the sync job —
  there is no code path to launch a sync without that check having just
  passed, by construction, not just a disabled button in the UI.
- **Per-config history**: a per-row expandable timeline (same pattern as
  MISP/Velociraptor's per-server history) reading `ActivityLog` filtered by
  `target_type='rule_mirror_config'` — every create/edit/delete, test
  pass/fail, manual trigger, and sync success/failure for that one config.
- **Repo layout**: `rules/<source>/<format>/<shard>/<uuid>/` (added the
  `<source>` level — grouped by the GitHub Sources repo a rule was
  imported from, or `manual`), `metadata.json` instead of `metadata.yaml`,
  and the rule's content file is named after a slug of its own title
  (e.g. `detect-f5-tmui-rce-cve-2020-5902.yar`) instead of the generic
  `rule.<ext>` — renamed automatically (old filename `git rm`'d) if the
  rule's title changes on a later sync.
- **README.md**: auto-generated at the repo root on every sync — Rulezet
  version, last-synced time, and a table of every source currently
  mirrored with its rule count, each linking back to it.
- **Pull-before-push**: `_ensure_local_repo`/`_align_with_remote` now
  fetch + merge the remote branch (using the configured token, not an
  anonymous clone) before the local clone is used, and again immediately
  before every push — a remote that already has commits the local clone
  doesn't (someone pushed directly, or the repo was seeded with an initial
  commit) no longer means a silently-broken or crashing sync; a real
  unresolvable conflict raises a clear error instead of being force-pushed
  over automatically.

## Fixed since going live

- **Background-job `current_user` crash**: `get_tags_for_rules_batch()`
  checks flask_login's `current_user.is_authenticated` to decide
  public-only vs. full tag visibility. Outside any Flask request (a
  background job runs in an app context only), that proxy resolves to
  `None`, and `None.is_authenticated` crashed the sync immediately. Fixed
  by calling it inside a throwaway `current_app.test_request_context()`,
  which gives flask_login a real (logged-out) `current_user` to check —
  this is what actually makes it "public tags only", not just not-broken.
- **Timezone mismatch broke incremental syncing**: `last_synced_at` was
  written with `datetime.utcnow()` (naive), while `Rule.creation_date`/
  `last_modif` use `datetime.now(tz=utc)` (aware) — Postgres converts the
  aware one to the session's local timezone before storing it in a
  timezone-less column, so the two ended up ~2h apart on this instance
  (Europe/Luxembourg). Every incremental sync's cutoff comparison
  (`Rule.creation_date > cutoff`) therefore matched *every* active rule,
  not just genuinely new/changed ones — defeating the point of
  "incremental" and creating one real commit per rule every single run.
  Fixed by switching `RuleMirrorConfig`'s own timestamps to the same
  `now(tz=utc)` convention Rule already uses.
- **Renamed rule's old file silently left uncommitted**: GitPython's
  `index.add(rel_dir)` on a directory does not detect that a file
  disappeared from it — after the title-slug filename change above, a
  rule's old `rule.yar`/`metadata.yaml` (or a previous title's slug) got
  deleted from disk correctly but the deletion was never staged, so it sat
  as an unstaged working-tree change that no commit ever captured. Combined
  with the timezone bug above (which made an entire incremental sync
  reprocess all 253 rules at once) and a stray manual commit pushed
  directly to the remote outside of Rulezet, this produced a real diverged
  local/remote history on the official mirror, resolved with an explicit,
  user-approved force-push once diagnosed. Fixed at the root: staging now
  uses `repo.git.add(rel_dir)` (the CLI form, which correctly stages
  adds/modifies/deletes under a path in one call) instead of
  `repo.index.add()`.
- **`ROOT_DIR` was one `dirname()` short of the actual repo root**: landed
  the local working clone at `app/data/rule_mirror_repo/` instead of the
  top-level `data/rule_mirror_repo/` every other regenerable-mirror
  feature uses (see `RULE_VALIDATION_MIRROR_DIR` in job_handlers.py) — and
  critically, `app/data/rule_mirror_repo/` was *not* covered by the
  `.gitignore` entry (`data/rule_mirror_repo/`, anchored at the true repo
  root since it contains a mid-pattern slash), so the whole local clone
  would have been picked up by a broad `git add`. Fixed by correcting
  `ROOT_DIR`'s dirname-call count and moving the existing local clone to
  match; no `.gitignore` change was needed once the path was right.

## Goal

Mirror every active Rulezet rule (~600,000 today) into a git repository as
plain files, one folder per rule, so that anyone who wants "all the rules"
can just `git clone` instead of going through the app/API. Kept in sync on
a recurring schedule: new rules get added, updated rules get a new commit
on their existing file (so `git log` on that file is its version history),
deleted (trashed) rules get removed.

## Key decisions (confirmed)

1. **History = native git history.** No `historique/` folder with
   duplicated old versions. Every time a rule's content changes, the sync
   job writes the new content to the *same path* and commits — `git log
   --follow rules/<source>/<format>/<shard>/<uuid>/<rule-name>.<ext>` gives
   the full version history for free (git's `--follow` tracks it across a
   rename, e.g. if the rule's title changes and its filename slug with
   it), with real diffs, no wasted space, nothing to invent server-side.
   Rules are grouped by `<source>` first (the GitHub Sources repo they
   were imported from, or `manual`) since a busy instance can have many
   different import sources, then by `<format>` within each one.
2. **First load starts clean.** The initial sync takes each of the
   ~600,000 existing rules' *current* content only — it does not replay
   `RuleUpdateHistory` back to rule creation. Git history for a rule starts
   at "the day the mirror went live"; everything the rule did before that
   stays in Rulezet's own history feature, not in this mirror. This keeps
   the first sync fast and the initial repo state simple.
3. **Hosting: a new public GitHub repo** — for rulezet.org specifically,
   that'll be `rulezet/rulezet-rules-mirror` on the official org. But see
   "Configuration & security" below: this is **not** hardcoded to that
   repo or to the existing `GITHUB_TOKEN` — it's a per-instance,
   admin-configured, off-by-default feature, so a self-hosted instance can
   point it at their own repo with their own token, or leave it disabled
   entirely.
4. **Deletions are mirrored.** A rule soft-deleted (trashed) in Rulezet
   gets `git rm`'d from the mirror in the next sync — the mirror reflects
   Rulezet's live, active rule set. The content isn't lost: it's still in
   git history for that path if anyone needs it.

## Configuration & security

This is the part that needed the most care — it's an admin-configurable
feature that pushes potentially the entire rule corpus to a third-party
service using a stored credential. Design:

- **Off by default, per-instance, admin-only, and not limited to one
  repository.** `RuleMirrorConfig` holds one row per configured mirror
  target — each with its own `uuid`, `name`, `enabled` (default `False`),
  `repo_url`, `github_token`, `branch`, `last_synced_at` — so an instance
  can push the same active/public rule set to several independent
  repositories (e.g. the official rulezet.org mirror plus a private
  team mirror) at once. Read/write gated to `current_user.is_admin()`,
  same `before_request` admin-only pattern as every other admin page —
  never exposed to regular users, and never auto-enabled by install/update
  scripts. rulezet.org's own admin turns on its own row pointed at the
  official org repo; a self-hosted instance's admin can add their own
  row(s) pointed at their own repo(s), or never touch any of it.
- **A separate token from `GITHUB_TOKEN`, on purpose.** The existing
  `GITHUB_TOKEN` env var (used for GitHub rule import / issue filing) is
  shared, instance-wide, and potentially scoped more broadly than "push to
  one specific repo". This feature gets its **own** admin-entered token
  instead of silently reusing that one — least privilege: whatever token
  is configured here should be a fine-grained GitHub PAT restricted to
  just the mirror repo, nothing else. This is called out explicitly in
  the admin UI's help text, not just left implicit.
- **Storage**: `github_token` is a plain DB column, following the exact
  precedent already in this codebase (`Connector.api_key_outbound` is
  stored the same way, not field-level encrypted) — consistent with the
  app's existing trust boundary (DB access = trusted), rather than
  inventing a different security model for just this one field. In the
  admin UI, once saved, the token is **never redisplayed** — the field
  shows a masked placeholder and requires re-entering a new value to
  change it (same convention as changing a password), not round-tripped
  back to the browser like the account API key page does (that page's
  "reveal" is deliberate self-service; an admin secret used to auth to a
  third party should not have a reveal button at all).
- **Never put the token in the git remote URL string.** Embedding it as
  `https://<token>@github.com/...` is the common shortcut but leaks
  through `ps aux`, error messages, and any logged remote URL. Using a git
  library (pygit2/GitPython) with an explicit credentials callback keeps
  the token out of argv and out of anything that gets logged entirely.
- **Only mirror what's actually public.** The sync must select rules the
  same way the *public* API/browsing already would — active,
  non-deleted, not a private workspace draft if that distinction applies
  — so this feature can't accidentally publish something that isn't
  already visible to anonymous users on the instance itself. Worth an
  explicit check against whatever query already backs the public rule
  listing, rather than re-deriving the "is this public" condition from
  scratch.
- **Audit trail.** `log_activity()` on: config changed (enabled/disabled,
  repo URL changed — never log the token value itself), and each sync
  run's start/finish/failure — same convention as every other admin
  action in this codebase.

## Remaining decisions (made — flag if you want any of these changed)

- **License scope**: mirror every rule regardless of license, but
  `metadata.json`'s `license` field makes the original license explicit
  per rule, and non-permissive-looking values (`NOASSERTION`, empty,
  anything not on a small recognized allow-list like MIT/Apache-2.0/
  GPL-*/CC-*) get an extra `license_verified: false` flag. This matches
  what Rulezet already does for browsing/API access (nothing is hidden
  today based on license), just makes the license status visible instead
  of silently dropping content or silently assuming it's fine.
- **Commit granularity on the initial 600k-rule load**: batched (e.g. one
  commit per ~500 rules per format), not one commit per rule — decision
  #2 already means the initial load carries no per-rule history to
  preserve, so per-rule commits here would only add ~600k slow
  round-trips for no benefit. Every commit *after* the initial load (i.e.
  every real future update) is still one commit per changed rule.
- **Push frequency**: push every ~1,000 commits during the initial load
  (a crash mid-run then loses at most that last partial batch, not
  everything), and a single push at the end of each (much smaller) weekly
  incremental run.

## Proposed repo layout

```
README.md                        # auto-generated, refreshed every sync — see below
rules/
  <source>/                      # the GitHub Sources repo a rule was
                                  # imported from (e.g. github.com_org_repo),
                                  # or "manual" for hand-authored rules
    <format>/                     # yara, sigma, suricata, splunk, elastic,
                                  # kql, wazuh, nse, crs, nova, atr, zeek, ...
      <shard>/                   # first 2 hex chars of the rule's uuid
        <uuid>/
          <rule-name>.<ext>         # slug of the rule's title, e.g.
                                     # detect-f5-tmui-rce-cve-2020-5902.yar —
                                     # correct extension per format, so a
                                     # plain clone gets working syntax
                                     # highlighting in any editor. Renamed
                                     # on the next sync if the rule's title
                                     # changes (old filename is git rm'd).
          metadata.json              # see below
```

Grouping by source first keeps rules pulled from the same GitHub repo
together — a busy instance can have many different import sources — with
format as the next split within each one. Sharding by the first 2 hex
chars of the UUID within that keeps any single directory listing
browsable on GitHub.

`metadata.json` per rule — human- and machine-readable, e.g.:
```json
{
  "uuid": "1a2b3c4d-...",
  "title": "Detect F5 TMUI RCE CVE-2020-5902",
  "format": "splunk",
  "author": "rdmmf",
  "license": "MIT",
  "description": "...",
  "source": "https://github.com/some/repo",
  "tags": ["tlp:clear", "pap:clear"],
  "attack_techniques": ["T1190"],
  "cve": ["CVE-2020-5902"],
  "created_at": "2024-03-01",
  "last_modified": "2026-09-10",
  "rulezet_url": "https://rulezet.org/rule/detail_rule/312325"
}
```

`README.md` at the repo root — rewritten (and committed if changed) on
every sync: the Rulezet version that produced it, when it was last synced,
and a table of every source currently mirrored with its rule count, each
linking straight back to that source.

## Sync mechanism

Rulezet already has exactly the pieces this needs — no new scheduling
system required:

- **Trigger**: the existing **Task Scheduler** (`app/features/admin/task_scheduler/`,
  see `docs/design/admin_task_scheduler.md`) already runs recurring admin
  jobs (GitHub sync, quality score, MISP taxonomy updates, ...) via
  `BackgroundJob` + `job_worker.py`. Adding a new task type
  (`rule_git_mirror_sync`) to that system is the natural fit — "run every
  Sunday at 03:00" is exactly what it's built for. No cron, no new poller.
- **Incremental detection**: `RuleMirrorConfig.last_synced_at` (see
  "Configuration & security" above — no separate table needed). Each run
  selects:
  - `Rule` where `creation_date > last_synced_at OR last_modif > last_synced_at`,
    `is_deleted = False` → write/update.
  - `Rule` where `deleted_at > last_synced_at` → remove from the mirror.
- **Git operations**: use a Python git library (pygit2 or GitPython)
  in-process rather than shelling out to the `git` binary per rule —
  meaningfully faster at this scale and avoids spawning ~600k subprocesses
  during the initial load.
- **Commit message**: one commit per changed rule going forward (e.g.
  `update: splunk/1a2b3c4d - Detect F5 TMUI RCE CVE-2020-5902`), so
  `git log` on the whole repo also reads as a real changelog, not just
  `git log` on one file.
- **Progress/resumability**: same pattern as the GitHub import job
  (`BackgroundJob` row, resumable offset, live log) — a run touching
  tens of thousands of rows needs to survive a restart cleanly, exactly
  like every other bulk job in this codebase already does.

## Rough scale expectations

At ~600,000 rules and an average rule size in the low KB range, the
mirror's *working tree* is likely in the 1–3 GB range initially. Git's own
object storage compresses well across similar rules (many YARA/Sigma
rules share a lot of boilerplate), so packed repo size should end up
smaller than the raw sum — but this is worth confirming empirically with
a sample batch before committing to the full 600k run, rather than
assuming it going in.

## Suggested implementation order

1. `RuleMirrorConfig` model + admin-only settings page (enabled toggle,
   repo URL, token entry with the masked/never-redisplayed behavior,
   branch) — the feature exists and is off by default before any sync
   code is written.
2. Small script/job that can mirror **one rule** correctly (folder
   layout, `metadata.json`, extension mapping) — prove the shape end to
   end on a handful of rules in a scratch repo first, using the
   git-library credentials callback (never the token-in-URL shortcut)
   even at this stage.
3. Wire it into a new `BackgroundJob` type + Task Scheduler entry, with
   the incremental `last_synced_at` logic, tested against a small subset
   (e.g. one format) before running against everything.
4. Run the one-time initial load for all ~600k rules (batched commits,
   periodic pushes, resumable) — only after enabling the feature on
   rulezet.org specifically, pointed at the real official repo.
5. Turn on the weekly recurring schedule for ongoing incremental syncs.

## Explicitly out of scope for now

- Pulling changes *back* from the mirror into Rulezet (this is
  export-only, matching what was asked).
- Any UI in Rulezet to browse the mirror itself — the point is that the
  mirror is just a plain git repo, browsable with git/GitHub directly.
