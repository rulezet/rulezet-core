"""
github_repo_core.py — Incremental sync for the GithubRepo registry.

GithubRepo caches, per distinct GitHub repo URL referenced by active
(non-deleted) rules, its rule_count — so the GitHub Sources list
(/rule/github/list_github_url) can paginate/sort/filter against a small
indexed table instead of a live GROUP BY over the whole Rule table (which
took 1.3-1.4s per page load on this instance's ~368k-row corpus).

Every place that changes how many active rules a source has must call one
of the functions below, in the SAME transaction as the rule change where
practical (or immediately after commit). As of this writing, that's:

  Create:
    - rule_core.add_rule_core()                           -> apply_delta(+1)
    - connector_core._upsert_rule() (federation sync, create branch)
                                                            -> apply_delta(+1)
    - job_handlers.py connector_pull's 2 new-rule staging loops
      (via _prepare_new_rule())                -> apply_deltas_for_new_rules()
  Edit (source field can be freely retyped on the edit form):
    - rule_core.edit_rule_core()          -> sync_source_change(old, new)
  Soft-delete:
    - rule_core.soft_delete_rule()                 -> apply_delta(-1)
    - rule_core.soft_delete_rule_list()   -> apply_deltas_for_rule_ids(-1)
    - job_handlers.handle_delete_github_rules()    -> apply_delta(-count) per url
  Restore:
    - rule_core.restore_rule()                     -> apply_delta(+1)
    - rule_core.restore_rules_bulk()      -> apply_deltas_for_rule_ids(+1)
    - rule_core.restore_batch()           -> apply_deltas_for_rule_ids(+1)
    - job_handlers.handle_trash_restore_bulk()      -> apply_deltas_for_rule_ids(+1)

This list is deliberately documented here (not just scattered as isolated
comments) since forgetting a call site is exactly how this kind of cache
silently drifts. rebuild_github_repos_from_rules() is the correctness
backstop — a full recompute from Rule, safe to re-run any time (e.g. from
the admin "Resync" action) to repair any drift a future write site misses.
"""
import re
import uuid as uuid_mod
import datetime

from ... import db
from ...core.db_class.db import Rule, GithubRepo

# Same pattern already used by get_optimized_github_data()/get_all_github_sources()
# for "is this a GitHub repo URL" — kept identical so GithubRepo tracks
# exactly the same set of sources the old live query did.
_GITHUB_URL_PATTERN = re.compile(r'^https?://(www\.)?github\.com/([\w\-_]+)/([\w\-_]+)')


def _extract_author(url: str) -> str:
    m = _GITHUB_URL_PATTERN.match(url or '')
    return m.group(2) if m else None


def is_github_source(url: str) -> bool:
    return bool(url and _GITHUB_URL_PATTERN.match(url))


def apply_delta(url: str, delta: int) -> None:
    """+delta or -delta to one repo's rule_count. No-op for a falsy/non-
    GitHub url. Creates the row on first positive delta; deletes it once
    rule_count would hit 0 or below (a repo with 0 active rules doesn't
    belong in a "sources with rules" list).

    Not done as a single atomic SQL upsert (Postgres ON CONFLICT vs
    SQLite's own upsert would need dialect-branching) — a plain read-
    modify-write is good enough here given rebuild_github_repos_from_rules()
    exists as a correctness backstop for the rare concurrent-write race.
    """
    if not is_github_source(url):
        return
    repo = GithubRepo.query.filter_by(url=url).first()
    if repo is None:
        if delta <= 0:
            return  # nothing to create, and nothing to subtract from
        repo = GithubRepo(
            uuid=str(uuid_mod.uuid4()),
            url=url,
            author=_extract_author(url),
            rule_count=delta,
        )
        db.session.add(repo)
        db.session.commit()
        return

    new_count = repo.rule_count + delta
    if new_count <= 0:
        db.session.delete(repo)
    else:
        repo.rule_count = new_count
    db.session.commit()


def apply_deltas_for_rule_ids(rule_ids: list, sign: int, is_deleted: bool = None) -> None:
    """Bulk variant — call BEFORE running a bulk UPDATE that flips
    is_deleted for `rule_ids`, so the per-source counts reflect exactly
    what's about to change. `is_deleted` should match whatever filter the
    caller's own bulk UPDATE uses (False when about to soft-delete,
    True when about to restore) so a no-op id in the batch (e.g. one
    that's already in the target state) isn't double-counted.

    sign: -1 for a delete (about to happen), +1 for a restore (about to happen).
    """
    if not rule_ids:
        return
    from sqlalchemy import func
    q = db.session.query(Rule.source, func.count(Rule.id)).filter(Rule.id.in_(rule_ids))
    if is_deleted is not None:
        q = q.filter(Rule.is_deleted == is_deleted)
    for source, count in q.group_by(Rule.source).all():
        apply_delta(source, sign * count)


def apply_deltas_for_new_rules(rules: list) -> None:
    """Batch variant for a page/chunk of just-created (already flushed, not
    necessarily committed) Rule ORM objects — groups by .source so a page of
    e.g. 50 new rules from the same repo triggers one apply_delta() call
    instead of 50. Used by connector_pull's two new-rule staging loops
    (job_handlers.py) right after their per-rule tag/cve/attack/history sync
    succeeds, before the page's own db.session.commit()."""
    if not rules:
        return
    counts = {}
    for rule in rules:
        if not is_github_source(rule.source):
            continue
        counts[rule.source] = counts.get(rule.source, 0) + 1
    for source, count in counts.items():
        apply_delta(source, count)


def sync_source_change(old_url: str, new_url: str) -> None:
    """For an edit that changed a rule's source field — moves the delta
    from old_url to new_url (only actually touches GithubRepo for
    whichever of the two, if either, is a real GitHub URL)."""
    if (old_url or '').strip() == (new_url or '').strip():
        return
    apply_delta(old_url, -1)
    apply_delta(new_url, +1)


def rebuild_github_repos_from_rules() -> dict:
    """Full recompute from Rule — the correctness backstop. Safe to re-run
    any time (e.g. the admin 'Resync' action, or a one-off repair after
    finding drift). Replaces the entire GithubRepo table contents with
    exactly what a live GROUP BY over Rule says right now.

    Returns {'repos': N, 'rules_counted': N} for a confirmation message.
    """
    from sqlalchemy import func
    rows = (
        db.session.query(Rule.source, func.count(Rule.id))
        .filter(Rule.source.op('~')(r'^https?://(www\.)?github\.com/[\w\-_]+/[\w\-_]+'),
                Rule.is_deleted == False)
        .group_by(Rule.source)
        .all()
    )

    existing = {r.url: r for r in GithubRepo.query.all()}
    seen_urls = set()
    total_rules = 0

    for source, count in rows:
        seen_urls.add(source)
        total_rules += count
        repo = existing.get(source)
        if repo:
            repo.rule_count = count
            repo.author = _extract_author(source)
        else:
            db.session.add(GithubRepo(
                uuid=str(uuid_mod.uuid4()),
                url=source,
                author=_extract_author(source),
                rule_count=count,
            ))

    # Prune rows for sources that no longer have any active rules.
    for url, repo in existing.items():
        if url not in seen_urls:
            db.session.delete(repo)

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()

    # Stamp last_synced_at on every surviving row — cheap, informational
    # ("resynced N minutes ago" in the admin UI).
    GithubRepo.query.filter(GithubRepo.url.in_(seen_urls)).update(
        {'last_synced_at': now}, synchronize_session=False
    )
    db.session.commit()

    return {'repos': len(seen_urls), 'rules_counted': total_rules}
