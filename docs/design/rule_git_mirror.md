# Rule Git Mirror — Design Plan

> Status: **implemented** (steps 1–3 of "Suggested implementation order").
> RuleMirrorConfig, the admin settings page, the how-it-works page, the
> `rule_git_mirror_sync` job handler, and the Task Scheduler entry all
> exist and are wired together — verified end to end against real rules
> and a local test repo. Off by default; nothing runs until an admin
> configures and enables it. Steps 4–5 (the real ~600k-rule initial load
> on rulezet.org, then turning on the recurring schedule) are an
> operational action for whoever runs that instance, not something this
> session can do — see "Set it up on your own instance" in the
> in-app how-it-works page for the exact steps.

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
   --follow rules/<format>/<shard>/<uuid>/rule.<ext>` gives the full
   version history for free, with real diffs, no wasted space, nothing to
   invent server-side.
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

- **Off by default, per-instance, admin-only.** A new singleton config
  row (`RuleMirrorConfig`, same "single row" pattern as `InstanceConfig`)
  holds `enabled` (default `False`), `repo_url`, `github_token`,
  `branch`, `last_synced_at`. Read/write gated to `current_user.is_admin()`,
  same `before_request` admin-only pattern as every other admin page —
  never exposed to regular users, and never auto-enabled by install/update
  scripts. rulezet.org's own admin turns it on and points it at the
  official org repo; a self-hosted instance's admin can point it at their
  own repo, or never touch it.
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
  `metadata.yaml`'s `license` field makes the original license explicit
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
rules/
  <format>/                      # yara, sigma, suricata, splunk, elastic,
                                  # kql, wazuh, nse, crs, nova, atr, zeek, ...
    <shard>/                     # first 2 hex chars of the rule's uuid
      <uuid>/
        rule.<ext>                # e.g. rule.yar, rule.yml, rule.rules —
                                   # correct extension per format, so a
                                   # plain clone gets working syntax
                                   # highlighting in any editor
        metadata.yaml              # see below
```

Sharding by the first 2 hex chars of the UUID keeps any single directory
listing browsable on GitHub (256 shards; ~600k rules across ~13 formats is
already ~46k/format on average, sharded down to low hundreds per shard).

`metadata.yaml` per rule — human- and machine-readable, e.g.:
```yaml
uuid: 1a2b3c4d-...
title: "Detect F5 TMUI RCE CVE-2020-5902"
format: splunk
author: rdmmf
license: MIT
description: "..."
source: https://github.com/some/repo
tags: [tlp:clear, pap:clear]
attack_techniques: [T1190]
cve: [CVE-2020-5902]
created_at: 2024-03-01
last_modified: 2026-09-10
rulezet_url: https://rulezet.org/rule/detail_rule/312325
```

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
   layout, `metadata.yaml`, extension mapping) — prove the shape end to
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
