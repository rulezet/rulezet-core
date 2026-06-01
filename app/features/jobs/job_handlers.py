"""
job_handlers.py
Concrete job handlers for bulk tag operations.

Each handler writes structured log lines via log_job() so the UI can
display a real-time activity feed with timestamps and event types.

Resume support:
    '_resume_offset' is saved in job.payload after every batch.
    On restart/resume the handler reads it and skips already-processed rows.

Pause / Cancel support:
    _should_pause() and _is_cancelled() are checked between every batch.
"""

import datetime
import uuid as uuid_mod

from app.features.jobs.job_worker import register_handler
from app import db
from app.core.db_class.db import Rule, Tag, RuleTagAssociation, BackgroundJobLog, ActivityLog

BATCH_SIZE = 2000   # bulk_insert_mappings handles large batches efficiently

LOG_EVERY  = 10     # write a progress log line every N batches


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def log_job(job, message, level='info', event=None):
    """Write one log line for the job. Commits immediately so the UI sees it."""
    try:
        entry = BackgroundJobLog(
            job_id=job.id,
            level=level,
            event=event,
            message=message,
            created_at=_now(),
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[log_job] failed to write log: {e}")


def _reload(job):
    try:
        db.session.expire(job)
        db.session.refresh(job)
    except Exception:
        pass


def _is_cancelled(job):
    _reload(job)
    return job.status == 'cancelled'


def _should_pause(job):
    _reload(job)
    return job.status == 'paused'


def _save_offset(job, offset):
    payload = dict(job.payload or {})
    payload['_resume_offset'] = offset
    job.payload = payload


def _build_rule_query(payload):
    """
    Build a Rule query from the filter payload.
    Mirrors get_rules_page_filter params exactly so the job processes
    the same rules the user previewed in the UI.
    """
    from sqlalchemy import or_, func

    query = Rule.query

    # pick mode — only these specific rule IDs, skip all other filters
    if payload.get('rule_ids'):
        query = query.filter(Rule.id.in_(payload['rule_ids']))
        return query

    # excluded_ids — used in 'all' mode when user deselected some rows
    excluded = payload.get('excluded_ids', [])
    if excluded:
        query = query.filter(Rule.id.notin_(excluded))

    # search
    search = payload.get('search')
    if search:
        search        = search.strip()
        search_field  = payload.get('search_field', 'all')
        exact_match   = payload.get('exact_match', False)

        if exact_match:
            if search_field == 'title':
                query = query.filter(Rule.title == search)
            elif search_field == 'content':
                query = query.filter(Rule.to_string.like(f"%{search}%"))
            else:
                query = query.filter(or_(Rule.title == search,
                                         Rule.to_string.like(f"%{search}%")))
        else:
            s = f"%{search.lower()}%"
            if search_field == 'title':
                query = query.filter(Rule.title.ilike(s))
            elif search_field == 'content':
                query = query.filter(Rule.to_string.ilike(s))
            else:
                query = query.filter(or_(
                    Rule.title.ilike(s),
                    Rule.description.ilike(s),
                    Rule.format.ilike(s),
                    Rule.author.ilike(s),
                    Rule.to_string.ilike(s),
                    Rule.uuid.ilike(s),
                ))

    # format / rule_type
    fmt = payload.get('rule_type') or payload.get('format')
    if fmt:
        query = query.filter(Rule.format.ilike(f"%{fmt}%"))

    # author
    if payload.get('author'):
        query = query.filter(Rule.author.ilike(f"%{payload['author'].lower()}%"))

    # user_id
    if payload.get('user_id'):
        query = query.filter(Rule.user_id == int(payload['user_id']))

    # sources (comma-separated string)
    if payload.get('sources'):
        src_list = [s.strip() for s in payload['sources'].split(',') if s.strip()]
        if src_list:
            query = query.filter(or_(*[Rule.source.ilike(f"%{s}%") for s in src_list]))

    # licenses (comma-separated string)
    if payload.get('licenses'):
        lic_list = [l.strip() for l in payload['licenses'].split(',') if l.strip()]
        if lic_list:
            query = query.filter(or_(*[Rule.license.ilike(f"%{l}%") for l in lic_list]))

    # vulnerabilities / CVEs (comma-separated string)
    if payload.get('vulnerabilities'):
        vuln_list = [v.strip() for v in payload['vulnerabilities'].split(',') if v.strip()]
        if vuln_list:
            query = query.filter(or_(*[Rule.cve_id.ilike(f'%"{v}"%') for v in vuln_list]))

    # filter rules that already have certain tags (comma-separated tag names)
    if payload.get('tags'):
        tag_names = [t.strip().lower() for t in payload['tags'].split(',') if t.strip()]
        if tag_names:
            found    = Tag.query.filter(func.lower(Tag.name).in_(tag_names)).all()
            tag_ids  = [t.id for t in found]
            if tag_ids:
                query = query.join(RuleTagAssociation, Rule.id == RuleTagAssociation.rule_id)\
                             .filter(RuleTagAssociation.tag_id.in_(tag_ids))\
                             .distinct()

    # sort
    sort_by = payload.get('sort_by', 'newest')
    if sort_by == 'oldest':
        query = query.order_by(Rule.creation_date.asc())
    elif sort_by == 'most_likes':
        query = query.order_by(Rule.vote_up.desc())
    elif sort_by == 'least_likes':
        query = query.order_by(Rule.vote_down.desc())
    else:
        query = query.order_by(Rule.creation_date.desc())

    return query


# ─── bulk_add_tag_to_rules ────────────────────────────────────────────────────

@register_handler('bulk_add_tag_to_rules')
def handle_bulk_add_tag_to_rules(job, app):
    payload = job.payload or {}
    tag_ids = payload.get('tag_ids', [])
    filters = payload.get('filters', {})
    user_id = payload.get('user_id')
    offset  = payload.get('_resume_offset', 0)

    if not tag_ids:
        raise ValueError("No tag_ids provided.")

    tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
    if not tags:
        raise ValueError("None of the provided tags were found.")

    tag_names = ', '.join(t.name for t in tags)
    rule_query = _build_rule_query(filters)

    # ── First run: compute total and log start ────────────────────────────────
    if job.total == 0:
        job.total = rule_query.count()
        db.session.commit()

        filter_desc = []
        if filters.get('search'):   filter_desc.append(f"search={filters['search']}")
        if filters.get('format'):   filter_desc.append(f"format={filters['format']}")
        if filters.get('rule_type'): filter_desc.append(f"format={filters['rule_type']}")
        if filters.get('author'):   filter_desc.append(f"author={filters['author']}")
        if filters.get('sources'):  filter_desc.append(f"source={filters['sources']}")
        if filters.get('rule_ids'): filter_desc.append(f"{len(filters['rule_ids'])} rule(s) manually selected")
        filter_str = ' · '.join(filter_desc) if filter_desc else 'all rules'

        log_job(job,
            f"Job started — {job.total} rule(s) targeted · tags: {tag_names} · filters: {filter_str}",
            level='info', event='started')

    # ── Resume: log that we are picking up where we left off ──────────────────
    elif offset > 0:
        log_job(job,
            f"Resuming from offset {offset} ({offset}/{job.total} already processed, "
            f"{job.progress_pct}% done)",
            level='info', event='resumed')

    if job.total == 0:
        log_job(job, "No rules matched the filters — nothing to do.", level='warning', event='done')
        return

    # ── Pre-load existing associations in one query ───────────────────────────
    existing = set(
        db.session.query(
            RuleTagAssociation.rule_id,
            RuleTagAssociation.tag_id,
        ).filter(
            RuleTagAssociation.tag_id.in_(tag_ids)
        ).all()
    )
    log_job(job,
        f"Loaded {len(existing)} existing association(s) to skip — starting bulk insert.",
        level='info', event='preload')

    batch_num   = 0
    total_added = 0
    added_at    = _now()

    while True:
        # ── Check cancel / pause ──────────────────────────────────────────────
        if _is_cancelled(job):
            log_job(job,
                f"Job cancelled at offset {offset} ({job.progress_pct}% done — "
                f"{total_added} association(s) added so far).",
                level='warning', event='cancelled')
            return

        if _should_pause(job):
            _save_offset(job, offset)
            db.session.commit()
            log_job(job,
                f"Job paused at offset {offset} ({job.progress_pct}% done — "
                f"{total_added} association(s) added so far). "
                f"Click Resume to continue.",
                level='info', event='paused')
            return

        # ── Fetch next batch of rule IDs ──────────────────────────────────────
        batch_ids = [
            r[0] for r in
            rule_query.with_entities(Rule.id).offset(offset).limit(BATCH_SIZE).all()
        ]
        if not batch_ids:
            break

        # ── Build insert list — skip already-existing pairs ───────────────────
        to_insert = [
            {
                "uuid":     str(uuid_mod.uuid4()),
                "rule_id":  rule_id,
                "tag_id":   tag_id,
                "user_id":  user_id,
                "added_at": added_at,
            }
            for rule_id in batch_ids
            for tag_id  in tag_ids
            if (rule_id, tag_id) not in existing
        ]

        if to_insert:
            db.session.bulk_insert_mappings(RuleTagAssociation, to_insert)
            for row in to_insert:
                existing.add((row["rule_id"], row["tag_id"]))
            total_added += len(to_insert)

        offset    += len(batch_ids)
        batch_num += 1
        job.done   = offset
        _save_offset(job, offset)
        db.session.commit()

        # ── Periodic progress log ─────────────────────────────────────────────
        if batch_num % LOG_EVERY == 0:
            log_job(job,
                f"Progress: {job.done}/{job.total} rules ({job.progress_pct}%) — "
                f"{total_added} association(s) added so far.",
                level='info', event='progress')

    # ── Done ──────────────────────────────────────────────────────────────────
    log_job(job,
        f"Completed — {job.total} rule(s) processed, "
        f"{total_added} new association(s) created, "
        f"{len(existing) - total_added} skipped (already existed).",
        level='success', event='done')


# ─── bulk_remove_tag_from_rules ───────────────────────────────────────────────

@register_handler('bulk_remove_tag_from_rules')
def handle_bulk_remove_tag_from_rules(job, app):
    payload = job.payload or {}
    tag_ids = payload.get('tag_ids', [])
    filters = payload.get('filters', {})
    offset  = payload.get('_resume_offset', 0)

    tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
    tag_names = ', '.join(t.name for t in tags) if tags else str(tag_ids)

    rule_query = _build_rule_query(filters)

    if job.total == 0:
        job.total = rule_query.count()
        db.session.commit()

        filter_desc = []
        if filters.get('search'):   filter_desc.append(f"search={filters['search']}")
        if filters.get('format'):   filter_desc.append(f"format={filters['format']}")
        if filters.get('rule_type'): filter_desc.append(f"format={filters['rule_type']}")
        if filters.get('author'):   filter_desc.append(f"author={filters['author']}")
        if filters.get('sources'):  filter_desc.append(f"source={filters['sources']}")
        if filters.get('rule_ids'): filter_desc.append(f"{len(filters['rule_ids'])} rule(s) manually selected")
        filter_str = ' · '.join(filter_desc) if filter_desc else 'all rules'

        log_job(job,
            f"Job started — {job.total} rule(s) targeted · tags to remove: {tag_names} · filters: {filter_str}",
            level='info', event='started')

    elif offset > 0:
        log_job(job,
            f"Resuming from offset {offset} ({job.progress_pct}% done).",
            level='info', event='resumed')

    if job.total == 0:
        log_job(job, "No rules matched the filters — nothing to do.", level='warning', event='done')
        return

    all_rule_ids = [r[0] for r in rule_query.with_entities(Rule.id).all()]

    batch_num     = 0
    total_removed = 0

    while offset < len(all_rule_ids):
        if _is_cancelled(job):
            log_job(job,
                f"Job cancelled at offset {offset} ({job.progress_pct}% done — "
                f"{total_removed} association(s) removed so far).",
                level='warning', event='cancelled')
            return

        if _should_pause(job):
            _save_offset(job, offset)
            db.session.commit()
            log_job(job,
                f"Job paused at offset {offset} ({job.progress_pct}% done — "
                f"{total_removed} association(s) removed so far). "
                f"Click Resume to continue.",
                level='info', event='paused')
            return

        chunk = all_rule_ids[offset:offset + BATCH_SIZE]

        deleted = RuleTagAssociation.query.filter(
            RuleTagAssociation.rule_id.in_(chunk),
            RuleTagAssociation.tag_id.in_(tag_ids),
        ).delete(synchronize_session=False)

        offset        += len(chunk)
        batch_num     += 1
        total_removed += deleted
        job.done       = offset
        _save_offset(job, offset)
        db.session.commit()

        if batch_num % LOG_EVERY == 0:
            log_job(job,
                f"Progress: {job.done}/{job.total} rules ({job.progress_pct}%) — "
                f"{total_removed} association(s) removed so far.",
                level='info', event='progress')

    log_job(job,
        f"Completed — {job.total} rule(s) processed, "
        f"{total_removed} association(s) removed.",
        level='success', event='done')


# ─── delete_github_rules ──────────────────────────────────────────────────────

@register_handler('delete_github_rules')
def handle_delete_github_rules(job, app):
    """
    Payload:
        urls : list[str] — GitHub source URLs to delete

    Progress strategy:
        1. Delete all FK associations in one shot each (fast, no progress change)
        2. Delete rules by batches of DELETE_BATCH — each commit drops the
           Rule.count, so the poll recount sees real progression.
    """
    from app.core.db_class.db import (
        RuleUpdateHistory, Comment, RuleSimilarity, RuleVote,
        BundleRuleAssociation, RuleEditContribution, RuleEditProposal,
        RuleFavoriteUser, RuleTagAssociation, RepportRule,
        ImporterResult, UpdateResult,
    )
    try:
        from app.core.db_class.db import RequestOwnerRule
        _has_request_owner = True
    except ImportError:
        _has_request_owner = False

    DELETE_BATCH = 500   # rules deleted per commit — adjust for granularity

    payload = job.payload or {}
    urls    = payload.get('urls', [])

    if not urls:
        raise ValueError("No URLs provided.")

    def recount():
        db.session.expire_all()
        return Rule.query.filter(Rule.source.in_(urls)).count()

    # ── Initial count ─────────────────────────────────────────────────────────
    initial = recount()
    if job.total == 0:
        job.total = initial
        db.session.commit()
        log_job(job,
            f"Job started — {initial} rule(s) to delete from: {', '.join(urls)}",
            level='info', event='started')

    if job.total == 0:
        log_job(job, "No rules found — nothing to delete.", level='warning', event='done')
        return

    # ── Collect all rule IDs once ─────────────────────────────────────────────
    rule_ids = [r[0] for r in db.session.query(Rule.id).filter(Rule.source.in_(urls)).all()]
    print(f"[delete_github] {len(rule_ids)} rule_ids collected")

    if not rule_ids:
        return

    # ── Step 1: delete all FK tables in one shot — fast, no rule count change ─
    log_job(job, f"Cleaning FK associations for {len(rule_ids)} rule(s)…",
            level='info', event='progress')

    db.session.query(RuleUpdateHistory).filter(RuleUpdateHistory.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(Comment).filter(Comment.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(RuleSimilarity).filter(RuleSimilarity.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(RuleVote).filter(RuleVote.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(BundleRuleAssociation).filter(BundleRuleAssociation.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(RuleEditContribution).filter(RuleEditContribution.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(RuleEditProposal).filter(RuleEditProposal.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(RuleFavoriteUser).filter(RuleFavoriteUser.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(RuleTagAssociation).filter(RuleTagAssociation.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    db.session.query(RepportRule).filter(RepportRule.rule_id.in_(rule_ids)).delete(synchronize_session=False)
    db.session.commit()
    if _has_request_owner:
        db.session.query(RequestOwnerRule).filter(RequestOwnerRule.rule_id.in_(rule_ids)).delete(synchronize_session=False)
        db.session.commit()

    log_job(job, "FK associations cleaned — deleting rules by batch…",
            level='info', event='progress')
    print(f"[delete_github] FK associations cleaned, starting batch rule deletion")

    # ── Step 2: delete rules in batches — each commit drops the count ─────────
    total_deleted = 0
    for i in range(0, len(rule_ids), DELETE_BATCH):
        chunk = rule_ids[i:i + DELETE_BATCH]
        nb    = Rule.query.filter(Rule.id.in_(chunk)).delete(synchronize_session=False)
        db.session.commit()
        total_deleted += nb

        remaining  = recount()
        job.done   = max(0, job.total - remaining)
        db.session.commit()

        print(f"[delete_github] batch deleted {nb} — remaining={remaining} ({job.progress_pct}%)")

        if job.progress_pct % 10 == 0 or remaining == 0:
            log_job(job,
                f"{remaining} rule(s) remaining ({job.progress_pct}% done).",
                level='info', event='progress')

    # ── Clean importers/updaters ───────────────────────────────────────────────
    for url in urls:
        ImporterResult.query.filter(ImporterResult.info.like(f'%{url}%')).delete(synchronize_session=False)
        UpdateResult.query.filter(UpdateResult.repo_sources.like(f'%{url}%')).delete(synchronize_session=False)
    db.session.commit()

    remaining = recount()
    job.done  = job.total - remaining
    db.session.commit()

    log_job(job,
        f"Completed — {total_deleted} rule(s) deleted. {remaining} remaining.",
        level='success', event='done')


# ─── delete_activity_logs ─────────────────────────────────────────────────────

LOG_DELETE_BATCH = 1000


@register_handler('delete_activity_logs')
def handle_delete_activity_logs(job, app):
    """Delete activity log entries in batches.

    Payload keys:
      log_ids      list[int]  — specific IDs to delete (ignored if delete_all=True)
      delete_all   bool       — delete everything (filtered by action_filter if set)
      action_filter str       — optional action prefix to filter when delete_all=True
    """
    payload      = job.payload or {}
    log_ids      = payload.get('log_ids', [])
    delete_all   = payload.get('delete_all', False)
    action_filter = payload.get('action_filter', '')

    log_job(job, "Starting activity log deletion…", level='info', event='started')

    if delete_all:
        q = ActivityLog.query
        if action_filter:
            q = q.filter(ActivityLog.action.ilike(f'{action_filter}%'))
        total = q.count()
    else:
        log_ids = [int(i) for i in log_ids if str(i).isdigit()]
        total = len(log_ids)

    job.total = total
    job.done  = 0
    db.session.commit()

    if total == 0:
        log_job(job, "Nothing to delete.", level='info', event='done')
        return

    deleted = 0

    if delete_all:
        q = ActivityLog.query
        if action_filter:
            q = q.filter(ActivityLog.action.ilike(f'{action_filter}%'))

        offset = payload.get('_resume_offset', 0)

        while True:
            if _is_cancelled(job):
                log_job(job, f"Cancelled — {deleted} deleted so far.", level='warning', event='cancelled')
                return
            if _should_pause(job):
                _save_offset(job, offset)
                db.session.commit()
                log_job(job, f"Paused — {deleted} deleted so far.", level='warning', event='paused')
                while _should_pause(job):
                    import time; time.sleep(1)
                log_job(job, "Resumed.", level='info', event='resumed')

            batch_ids = [r.id for r in ActivityLog.query
                         .filter(ActivityLog.action.ilike(f'{action_filter}%') if action_filter else db.true())
                         .order_by(ActivityLog.id)
                         .offset(offset)
                         .limit(LOG_DELETE_BATCH)
                         .with_entities(ActivityLog.id)
                         .all()]
            if not batch_ids:
                break

            ActivityLog.query.filter(ActivityLog.id.in_(batch_ids)).delete(synchronize_session=False)
            db.session.commit()
            deleted += len(batch_ids)
            job.done = deleted
            db.session.commit()
            log_job(job, f"Deleted {deleted}/{total} log(s).", level='info', event='progress')
    else:
        for i in range(0, len(log_ids), LOG_DELETE_BATCH):
            if _is_cancelled(job):
                log_job(job, f"Cancelled — {deleted} deleted.", level='warning', event='cancelled')
                return

            batch = log_ids[i:i + LOG_DELETE_BATCH]
            ActivityLog.query.filter(ActivityLog.id.in_(batch)).delete(synchronize_session=False)
            db.session.commit()
            deleted += len(batch)
            job.done = deleted
            db.session.commit()

    log_job(job, f"Done — {deleted} activity log(s) deleted.", level='success', event='done')