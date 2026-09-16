"""
github_repo_core.py — Incremental sync for the GithubRepo registry.

GithubRepo caches, per distinct GitHub repo URL referenced by active
(non-deleted) rules, its rule_count plus per-repo format/license/CVE/
similarity-conflict aggregates — so the GitHub Sources list
(/rule/github/list_github_url) can paginate/filter/sort/search against a
small indexed table instead of a live GROUP BY over the whole Rule table
(which took 1.3-1.4s per page load on this instance's ~368k-row corpus).

Every place that changes a rule's (source, format, license, cve_id) must
call one of the functions below, in the SAME transaction as the rule
change where practical (or immediately after commit). As of this writing,
that's:

  Create:
    - rule_core.add_rule_core()                           -> apply_delta(+1, rule=new_rule)
    - connector_core._upsert_rule() (federation sync, create branch)
                                                            -> apply_delta(+1, rule=rule)
    - job_handlers.py connector_pull's 2 new-rule staging loops
      (via _prepare_new_rule())                -> apply_deltas_for_new_rules()
  Edit (source/format/license/cve_id are all plain editable form fields):
    - rule_core.edit_rule_core()          -> sync_rule_edit(old, new, old_snapshot, new_snapshot)
  Soft-delete:
    - rule_core.soft_delete_rule()                 -> apply_delta(-1, rule=rule)
    - rule_core.soft_delete_rule_list()   -> apply_deltas_for_rule_ids(-1)
    - job_handlers.handle_delete_github_rules()    -> apply_deltas_for_rule_ids(-1)
  Restore:
    - rule_core.restore_rule()                     -> apply_delta(+1, rule=rule)
    - rule_core.restore_rules_bulk()      -> apply_deltas_for_rule_ids(+1)
    - rule_core.restore_batch()           -> apply_deltas_for_rule_ids(+1)
    - job_handlers.handle_trash_restore_bulk()      -> apply_deltas_for_rule_ids(+1)

  Similarity conflicts (conflict_count) are the one field NOT updated at
  these sites — RuleSimilarity is produced/removed by two separate places,
  neither of them a per-rule create/edit/delete:
    - similarity_class.py's SimilaritySession (the corpus-wide scan job)
                                              -> sync_conflict_counts()
    - rule_core.delete_similarity_history() (admin: delete a past scan's
      RuleSimilarity rows)                   -> sync_conflict_counts()

This list is deliberately documented here (not just scattered as isolated
comments) since forgetting a call site is exactly how this kind of cache
silently drifts. rebuild_github_repos_from_rules() is the correctness
backstop — a full recompute from Rule (+ RuleSimilarity for conflicts),
safe to re-run any time (e.g. from the admin "Resync" action) to repair
any drift a future write site misses.
"""
import re
import uuid as uuid_mod
import datetime

from sqlalchemy.exc import IntegrityError

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


def _rule_has_cve(cve_id) -> bool:
    """Same truthiness rule the old live query used: a rule "has a CVE" iff
    its cve_id field is a non-empty, non-'[]' JSON string."""
    return bool(cve_id) and cve_id not in ('[]', '')


def _apply_repo_counts(url: str, count_delta: int, format_deltas: dict = None,
                        license_deltas: dict = None, cve_delta: int = 0, _retry: bool = True) -> None:
    """Low-level: adjust rule_count, format_counts, license_counts and
    cve_count on one GithubRepo row in one read-modify-write. Creates the
    row on first positive count_delta; deletes it once rule_count would hit
    0 or below (a repo with 0 active rules doesn't belong in a "sources
    with rules" list).

    Not done as a single atomic SQL upsert (Postgres ON CONFLICT vs
    SQLite's own upsert would need dialect-branching) — a plain read-
    modify-write, with a retry-as-update on the unique-constraint race
    below, is good enough here given rebuild_github_repos_from_rules()
    exists as a correctness backstop for anything that still slips through.

    The race this retries: two rules from the same brand-new GitHub source
    get created around the same time (a bulk import is the common case) —
    both read "no GithubRepo row for this url yet" before either commits,
    both try to INSERT one, and the loser hits ix_github_repo_url's unique
    constraint. Caught specifically (not a bare except) so a genuinely
    unexpected DB error still surfaces instead of being silently retried
    into a loop.
    """
    if not is_github_source(url):
        return

    repo = GithubRepo.query.filter_by(url=url).first()
    if repo is None:
        if count_delta <= 0:
            return  # nothing to create, and nothing to subtract from
        repo = GithubRepo(
            uuid=str(uuid_mod.uuid4()),
            url=url,
            author=_extract_author(url),
            rule_count=0,
            format_counts={},
            license_counts={},
            cve_count=0,
        )
        db.session.add(repo)

    new_count = (repo.rule_count or 0) + count_delta
    if new_count <= 0:
        db.session.delete(repo)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return

    repo.rule_count = new_count

    fc = dict(repo.format_counts or {})
    for key, d in (format_deltas or {}).items():
        if not key:
            continue
        fc[key] = fc.get(key, 0) + d
        if fc[key] <= 0:
            fc.pop(key, None)
    repo.format_counts = fc

    lc = dict(repo.license_counts or {})
    for key, d in (license_deltas or {}).items():
        if not key:
            continue
        lc[key] = lc.get(key, 0) + d
        if lc[key] <= 0:
            lc.pop(key, None)
    repo.license_counts = lc

    repo.cve_count = max(0, (repo.cve_count or 0) + cve_delta)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if not _retry:
            raise
        # Someone else's commit for this same url landed between our SELECT
        # and our commit — the row exists now, so retry once as a plain
        # update instead of losing this delta.
        _apply_repo_counts(url, count_delta, format_deltas, license_deltas, cve_delta, _retry=False)


def apply_delta(url: str, delta: int, rule=None) -> None:
    """+delta or -delta to one repo (rule_count, and — when `rule` is given
    — that rule's format/license/cve contribution too). Pass `rule` at
    every create/soft-delete/restore call site; it's always the ORM object
    already in scope there, so there's no reason to skip it and let the
    per-format/license/cve aggregates go stale until the next rebuild."""
    if rule is None:
        _apply_repo_counts(url, delta)
        return
    format_deltas  = {rule.format: delta} if rule.format else None
    license_deltas = {rule.license: delta} if rule.license else None
    cve_delta = delta if _rule_has_cve(rule.cve_id) else 0
    _apply_repo_counts(url, delta, format_deltas, license_deltas, cve_delta)


def apply_deltas_for_rule_ids(rule_ids: list, sign: int, is_deleted: bool = None) -> None:
    """Bulk variant — call BEFORE running a bulk UPDATE that flips
    is_deleted for `rule_ids`, so the per-source aggregates reflect exactly
    what's about to change. `is_deleted` should match whatever filter the
    caller's own bulk UPDATE uses (False when about to soft-delete,
    True when about to restore) so a no-op id in the batch (e.g. one
    that's already in the target state) isn't double-counted.

    sign: -1 for a delete (about to happen), +1 for a restore (about to happen).
    """
    if not rule_ids:
        return
    q = db.session.query(Rule.source, Rule.format, Rule.license, Rule.cve_id).filter(Rule.id.in_(rule_ids))
    if is_deleted is not None:
        q = q.filter(Rule.is_deleted == is_deleted)

    agg = {}
    for source, fmt, lic, cve_id in q.all():
        if not is_github_source(source):
            continue
        a = agg.setdefault(source, {'count': 0, 'formats': {}, 'licenses': {}, 'cve': 0})
        a['count'] += sign
        if fmt:
            a['formats'][fmt] = a['formats'].get(fmt, 0) + sign
        if lic:
            a['licenses'][lic] = a['licenses'].get(lic, 0) + sign
        if _rule_has_cve(cve_id):
            a['cve'] += sign

    for source, a in agg.items():
        _apply_repo_counts(source, a['count'], a['formats'], a['licenses'], a['cve'])


def apply_deltas_for_new_rules(rules: list) -> None:
    """Batch variant for a page/chunk of just-created (already flushed, not
    necessarily committed) Rule ORM objects — groups by .source so a page of
    e.g. 50 new rules from the same repo triggers one write per repo instead
    of one per rule. Used by connector_pull's two new-rule staging loops
    (job_handlers.py) right after their per-rule tag/cve/attack/history sync
    succeeds, before the page's own db.session.commit()."""
    if not rules:
        return
    agg = {}
    for rule in rules:
        if not is_github_source(rule.source):
            continue
        a = agg.setdefault(rule.source, {'count': 0, 'formats': {}, 'licenses': {}, 'cve': 0})
        a['count'] += 1
        if rule.format:
            a['formats'][rule.format] = a['formats'].get(rule.format, 0) + 1
        if rule.license:
            a['licenses'][rule.license] = a['licenses'].get(rule.license, 0) + 1
        if _rule_has_cve(rule.cve_id):
            a['cve'] += 1

    for source, a in agg.items():
        _apply_repo_counts(source, a['count'], a['formats'], a['licenses'], a['cve'])


def sync_rule_edit(old_source: str, new_source: str, old_snapshot: dict, new_snapshot: dict) -> None:
    """For an edit — moves/adjusts the rule's contribution between repos.
    old_snapshot/new_snapshot: {'format': str, 'license': str, 'cve_id': str}
    captured immediately before and after mutating the Rule object. Handles
    both cases: source unchanged but format/license/cve_id edited (still
    needs the repo's aggregates updated), and source changed (the rule's
    whole contribution moves from one repo to another, or in/out of being
    a GitHub-sourced rule at all)."""
    old_source = (old_source or '').strip()
    new_source = (new_source or '').strip()
    old_fmt, old_lic = old_snapshot.get('format'), old_snapshot.get('license')
    new_fmt, new_lic = new_snapshot.get('format'), new_snapshot.get('license')
    old_cve = _rule_has_cve(old_snapshot.get('cve_id'))
    new_cve = _rule_has_cve(new_snapshot.get('cve_id'))

    if old_source == new_source:
        if not is_github_source(old_source):
            return
        fd, ld = {}, {}
        if old_fmt != new_fmt:
            if old_fmt:
                fd[old_fmt] = fd.get(old_fmt, 0) - 1
            if new_fmt:
                fd[new_fmt] = fd.get(new_fmt, 0) + 1
        if old_lic != new_lic:
            if old_lic:
                ld[old_lic] = ld.get(old_lic, 0) - 1
            if new_lic:
                ld[new_lic] = ld.get(new_lic, 0) + 1
        cve_delta = (1 if new_cve else 0) - (1 if old_cve else 0)
        if fd or ld or cve_delta:
            _apply_repo_counts(old_source, 0, fd, ld, cve_delta)
        return

    # Source changed — the rule leaves old_source's repo entirely and joins
    # new_source's, each handled independently since they're different rows.
    if is_github_source(old_source):
        fd = {old_fmt: -1} if old_fmt else None
        ld = {old_lic: -1} if old_lic else None
        _apply_repo_counts(old_source, -1, fd, ld, -1 if old_cve else 0)
    if is_github_source(new_source):
        fd = {new_fmt: 1} if new_fmt else None
        ld = {new_lic: 1} if new_lic else None
        _apply_repo_counts(new_source, 1, fd, ld, 1 if new_cve else 0)


def sync_conflict_counts() -> dict:
    """Full recompute of conflict_count (distinct active rules per repo
    with at least one RuleSimilarity row scoring > 0.99) across every known
    GithubRepo. Call this once, right after the similarity engine's own
    full wipe-and-rebuild (similarity_class.py) — RuleSimilarity has no
    incremental per-rule write path to hook GithubRepo's usual create/
    edit/delete sites into, since it's itself a batch/corpus-wide
    recompute, not a per-rule side effect."""
    from sqlalchemy import func
    from ...core.db_class.db import RuleSimilarity

    rows = (
        db.session.query(Rule.source, func.count(func.distinct(Rule.id)))
        .join(RuleSimilarity, RuleSimilarity.rule_id == Rule.id)
        .filter(RuleSimilarity.score > 0.99, Rule.is_deleted == False,
                Rule.source.op('~')(r'^https?://(www\.)?github\.com/[\w\-_]+/[\w\-_]+'))
        .group_by(Rule.source)
        .all()
    )
    counts = dict(rows)

    updated = 0
    for repo in GithubRepo.query.all():
        new_val = counts.get(repo.url, 0)
        if repo.conflict_count != new_val:
            repo.conflict_count = new_val
            updated += 1
    db.session.commit()
    return {'repos_updated': updated, 'repos_with_conflicts': len(counts)}


def rebuild_github_repos_from_rules() -> dict:
    """Full recompute from Rule (+ RuleSimilarity for conflicts) — the
    correctness backstop. Safe to re-run any time (e.g. the admin 'Resync'
    action, or a one-off repair after finding drift). Replaces the entire
    GithubRepo table contents with exactly what a live aggregation over
    Rule says right now.

    Returns {'repos': N, 'rules_counted': N} for a confirmation message.
    """
    from sqlalchemy import func
    from ...core.db_class.db import RuleSimilarity

    github_pattern = r'^https?://(www\.)?github\.com/[\w\-_]+/[\w\-_]+'
    active_github = (Rule.source.op('~')(github_pattern), Rule.is_deleted == False)

    count_rows = (
        db.session.query(Rule.source, func.count(Rule.id))
        .filter(*active_github)
        .group_by(Rule.source)
        .all()
    )
    format_rows = (
        db.session.query(Rule.source, Rule.format, func.count(Rule.id))
        .filter(*active_github, Rule.format.isnot(None))
        .group_by(Rule.source, Rule.format)
        .all()
    )
    license_rows = (
        db.session.query(Rule.source, Rule.license, func.count(Rule.id))
        .filter(*active_github, Rule.license.isnot(None), Rule.license != '')
        .group_by(Rule.source, Rule.license)
        .all()
    )
    cve_rows = (
        db.session.query(Rule.source, func.count(Rule.id))
        .filter(*active_github, Rule.cve_id.isnot(None), Rule.cve_id != '[]', Rule.cve_id != '')
        .group_by(Rule.source)
        .all()
    )
    conflict_rows = (
        db.session.query(Rule.source, func.count(func.distinct(Rule.id)))
        .join(RuleSimilarity, RuleSimilarity.rule_id == Rule.id)
        .filter(RuleSimilarity.score > 0.99, *active_github)
        .group_by(Rule.source)
        .all()
    )

    format_counts_by_url = {}
    for source, fmt, count in format_rows:
        format_counts_by_url.setdefault(source, {})[fmt] = count
    license_counts_by_url = {}
    for source, lic, count in license_rows:
        license_counts_by_url.setdefault(source, {})[lic] = count
    cve_count_by_url = dict(cve_rows)
    conflict_count_by_url = dict(conflict_rows)

    existing = {r.url: r for r in GithubRepo.query.all()}
    seen_urls = set()
    total_rules = 0

    for source, count in count_rows:
        seen_urls.add(source)
        total_rules += count
        repo = existing.get(source)
        if repo is None:
            repo = GithubRepo(uuid=str(uuid_mod.uuid4()), url=source)
            db.session.add(repo)
            existing[source] = repo
        repo.rule_count      = count
        repo.author          = _extract_author(source)
        repo.format_counts   = format_counts_by_url.get(source, {})
        repo.license_counts  = license_counts_by_url.get(source, {})
        repo.cve_count       = cve_count_by_url.get(source, 0)
        repo.conflict_count  = conflict_count_by_url.get(source, 0)

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
