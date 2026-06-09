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
import os
import subprocess
import sys
import uuid as uuid_mod
from pathlib import Path

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
    Soft-delete all rules from the given GitHub source URLs.
    Rules are moved to the trash (is_deleted=True) and can be restored by an admin.

    Payload:
        urls : list[str] — GitHub source URLs
    """
    import uuid as _uuid
    import datetime

    payload = job.payload or {}
    urls    = payload.get('urls', [])
    if not urls:
        raise ValueError("No URLs provided.")

    # Count active rules for these sources
    initial = Rule.query.filter(Rule.source.in_(urls), Rule.is_deleted == False).count()
    if job.total == 0:
        job.total = initial
        db.session.commit()
        log_job(job, f"Job started — {initial} rule(s) to move to trash from: {', '.join(urls)}",
                level='info', event='started')

    if initial == 0:
        log_job(job, "No active rules found — nothing to delete.", level='warning', event='done')
        return

    batch_uuid = payload.get('batch_uuid') or str(_uuid.uuid4())
    now        = datetime.datetime.now(tz=datetime.timezone.utc)
    created_by = job.created_by

    # Soft-delete in one bulk update
    updated = Rule.query.filter(Rule.source.in_(urls), Rule.is_deleted == False).update(
        {"is_deleted": True, "deleted_at": now, "deleted_by_id": created_by, "delete_batch_uuid": batch_uuid},
        synchronize_session=False,
    )
    db.session.commit()

    job.done = updated
    db.session.commit()

    log_job(job, f"Completed — {updated} rule(s) moved to trash (batch: {batch_uuid[:8]}).",
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


# ─── update_misp_data ─────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parents[3]   # rulezet-core/
TAX_PATH = ROOT_DIR / "app" / "modules" / "misp-taxonomies"
GAL_PATH = ROOT_DIR / "app" / "modules" / "misp-galaxy"


def _git_submodule_update(submodule_path: Path) -> tuple[bool, str]:
    """Update a git submodule to its latest upstream commit.

    Submodules are always in detached-HEAD state, so `git pull` inside them
    fails. The correct command is `git submodule update --remote` run from
    the project root, passing the relative submodule path.
    """
    try:
        rel = submodule_path.relative_to(ROOT_DIR)
        r = subprocess.run(
            ["git", "submodule", "update", "--remote", "--merge", str(rel)],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (r.stdout + r.stderr).strip()
        return r.returncode == 0, output or "Already up to date."
    except Exception as e:
        return False, str(e)


@register_handler('update_misp_data')
def handle_update_misp_data(job, app):
    """3-step MISP data update:
      Step 1 — git pull both submodules
      Step 2 — update ALREADY-IMPORTED taxonomies only (add new tags, skip existing)
      Step 3 — update ALREADY-IMPORTED galaxies only (add new clusters, skip existing)
    """
    from app.core.db_class.db import User
    from app.features.tags import tags_core

    user = User.query.get(job.created_by)
    if not user:
        log_job(job, "User not found — aborting.", level='error', event='error')
        return

    # ── Step 1: git pull ──────────────────────────────────────────────────────
    log_job(job, "Step 1 — Pulling latest MISP data from GitHub…",
            level='info', event='step1_start')
    job.total = 3
    job.done  = 0
    db.session.commit()

    tax_ok, tax_out = _git_submodule_update(TAX_PATH)
    log_job(job,
            f"misp-taxonomies: {tax_out}",
            level='success' if tax_ok else 'warning',
            event='step1_tax_pull')

    gal_ok, gal_out = _git_submodule_update(GAL_PATH)
    log_job(job,
            f"misp-galaxy: {gal_out}",
            level='success' if gal_ok else 'warning',
            event='step1_gal_pull')

    job.done = 1
    db.session.commit()
    log_job(job, "Step 1 done.", level='success', event='step1_done')

    # ── Step 2: update already-imported taxonomies only ───────────────────────
    tax_list = tags_core.get_imported_taxonomy_uuids_from_disk()
    log_job(job,
            f"Step 2 — Updating {len(tax_list)} imported taxonomy(ies)…",
            level='info', event='step2_start')

    updated_t = 0
    uptodate_t = 0
    error_t = 0

    for uid, ns in tax_list:
        if _is_cancelled(job):
            log_job(job, "Cancelled during taxonomy update.", level='warning', event='cancelled')
            return

        ok, msg = tags_core.update_tags_from_misp_taxonomy(uid, user)
        if ok is True and "up to date" in msg:
            uptodate_t += 1
        elif ok is True:
            updated_t += 1
            log_job(job, f"[taxonomy] {msg}", level='success', event='step2_progress')
        else:
            error_t += 1
            log_job(job, f"[taxonomy] {msg}", level='warning', event='step2_progress')

    job.done = 2
    db.session.commit()
    log_job(job,
            f"Step 2 done — {updated_t} updated, {uptodate_t} already up to date, {error_t} errors.",
            level='success', event='step2_done')

    # ── Step 3: update already-imported galaxies only ────────────────────────
    gal_list = tags_core.get_imported_galaxy_uuids_from_disk()
    log_job(job,
            f"Step 3 — Updating {len(gal_list)} imported galaxy(ies)…",
            level='info', event='step3_start')

    updated_g  = 0
    uptodate_g = 0
    error_g    = 0

    for uid, gtype in gal_list:
        if _is_cancelled(job):
            log_job(job, "Cancelled during galaxy update.", level='warning', event='cancelled')
            return

        ok, msg = tags_core.update_tags_from_misp_galaxy(uid, user)
        if ok is True and "up to date" in msg:
            uptodate_g += 1
        elif ok is True:
            updated_g += 1
            log_job(job, f"[galaxy] {msg}", level='success', event='step3_progress')
        else:
            error_g += 1
            log_job(job, f"[galaxy] {msg}", level='warning', event='step3_progress')

    job.done = 3
    db.session.commit()
    log_job(job,
            f"Step 3 done — {updated_g} updated, {uptodate_g} already up to date, {error_g} errors.",
            level='success', event='step3_done')

    log_job(job, "All done. Your imported MISP data is up to date.", level='success', event='done')

# ─── trash_restore_bulk ───────────────────────────────────────────────────────

TRASH_BATCH = 200


@register_handler('trash_restore_bulk')
def handle_trash_restore_bulk(job, app):
    """
    Restore soft-deleted rules in batches.

    Payload:
        ids          : list[int]  — specific rule IDs to restore (optional)
        restore_all  : bool       — restore every rule in the trash
        batch_uuid   : str        — restore all rules sharing this batch UUID
    """
    import datetime as _dt
    payload    = job.payload or {}
    restore_all = payload.get('restore_all', False)
    batch_uuid  = payload.get('batch_uuid')
    ids         = payload.get('ids', [])

    # Build the target query
    query = Rule.query.filter(Rule.is_deleted == True)
    if restore_all:
        pass  # all deleted rules
    elif batch_uuid:
        query = query.filter(Rule.delete_batch_uuid == batch_uuid)
    elif ids:
        query = query.filter(Rule.id.in_(ids))
    else:
        log_job(job, "No target specified.", level='warning', event='done')
        return

    total = query.count()
    if job.total == 0:
        job.total = total
        db.session.commit()
        log_job(job, f"Job started — {total} rule(s) to restore.", level='info', event='started')

    if total == 0:
        log_job(job, "No deleted rules found.", level='warning', event='done')
        return

    offset = payload.get('_resume_offset', 0)
    restored = 0
    all_ids  = [r[0] for r in query.with_entities(Rule.id).all()]

    for i in range(offset, len(all_ids), TRASH_BATCH):
        if _is_cancelled(job):
            log_job(job, "Cancelled.", level='warning', event='cancelled')
            return
        while _should_pause(job):
            import time; time.sleep(2)
        chunk = all_ids[i:i + TRASH_BATCH]
        now   = _dt.datetime.now(tz=_dt.timezone.utc)
        Rule.query.filter(Rule.id.in_(chunk), Rule.is_deleted == True).update(
            {"is_deleted": False, "deleted_at": None, "deleted_by_id": None, "delete_batch_uuid": None},
            synchronize_session=False,
        )
        db.session.commit()
        restored  += len(chunk)
        job.done   = restored
        _save_offset(job, i + TRASH_BATCH)
        db.session.commit()
        log_job(job, f"{restored}/{total} rule(s) restored.", level='info', event='progress')

    log_job(job, f"Done — {restored} rule(s) restored.", level='success', event='done')


# ─── trash_permanent_delete_bulk ──────────────────────────────────────────────

@register_handler('trash_permanent_delete_bulk')
def handle_trash_permanent_delete_bulk(job, app):
    """
    Permanently delete soft-deleted rules in batches (irreversible).

    Payload:
        ids          : list[int]  — specific rule IDs
        delete_all   : bool       — delete every rule in the trash
        batch_uuid   : str        — delete all rules sharing this batch UUID
    """
    payload    = job.payload or {}
    delete_all = payload.get('delete_all', False)
    batch_uuid = payload.get('batch_uuid')
    ids        = payload.get('ids', [])

    query = Rule.query.filter(Rule.is_deleted == True)
    if delete_all:
        pass
    elif batch_uuid:
        query = query.filter(Rule.delete_batch_uuid == batch_uuid)
    elif ids:
        query = query.filter(Rule.id.in_(ids))
    else:
        log_job(job, "No target specified.", level='warning', event='done')
        return

    total = query.count()
    if job.total == 0:
        job.total = total
        db.session.commit()
        log_job(job, f"Job started — {total} rule(s) to permanently delete.", level='info', event='started')

    if total == 0:
        log_job(job, "No rules found.", level='warning', event='done')
        return

    offset  = payload.get('_resume_offset', 0)
    deleted = 0
    all_ids = [r[0] for r in query.with_entities(Rule.id).all()]

    for i in range(offset, len(all_ids), TRASH_BATCH):
        if _is_cancelled(job):
            log_job(job, "Cancelled.", level='warning', event='cancelled')
            return
        while _should_pause(job):
            import time; time.sleep(2)
        chunk = all_ids[i:i + TRASH_BATCH]
        Rule.query.filter(Rule.id.in_(chunk), Rule.is_deleted == True).delete(synchronize_session=False)
        db.session.commit()
        deleted  += len(chunk)
        job.done  = deleted
        _save_offset(job, i + TRASH_BATCH)
        db.session.commit()
        log_job(job, f"{deleted}/{total} rule(s) permanently deleted.", level='info', event='progress')

    log_job(job, f"Done — {deleted} rule(s) permanently deleted.", level='success', event='done')


# ─── Package management ───────────────────────────────────────────────────────

@register_handler('update_package')
def handle_update_package(job, app):
    payload = job.payload or {}
    name = payload.get('name', '').strip()
    if not name:
        job.status = 'failed'
        job.error = 'No package name provided.'
        db.session.commit()
        return

    with app.app_context():
        job.total = 1
        job.done = 0
        db.session.commit()
        log_job(job, f"Upgrading: {name}", level='info', event='started')
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '--upgrade', name],
                capture_output=True, text=True, timeout=180,
            )
            output = (result.stdout + result.stderr).strip()
            # Emit output lines as log entries
            for line in output.splitlines()[-30:]:
                if line.strip():
                    log_job(job, line, level='info', event='progress')
            if result.returncode == 0:
                log_job(job, f"Successfully upgraded {name}.", level='success', event='done')
                job.status = 'done'
                job.done = 1
            else:
                job.status = 'failed'
                job.error = output[-500:]
                log_job(job, f"pip returned code {result.returncode}.", level='error', event='failed')
        except Exception as e:
            job.status = 'failed'
            job.error = str(e)
            log_job(job, str(e), level='error', event='failed')
        db.session.commit()


@register_handler('uninstall_package')
def handle_uninstall_package(job, app):
    payload = job.payload or {}
    name = payload.get('name', '').strip()
    if not name:
        job.status = 'failed'
        job.error = 'No package name provided.'
        db.session.commit()
        return

    with app.app_context():
        job.total = 1
        job.done = 0
        db.session.commit()
        log_job(job, f"Uninstalling: {name}", level='warning', event='started')
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'uninstall', '-y', name],
                capture_output=True, text=True, timeout=60,
            )
            output = (result.stdout + result.stderr).strip()
            for line in output.splitlines()[-20:]:
                if line.strip():
                    log_job(job, line, level='info', event='progress')
            if result.returncode == 0:
                log_job(job, f"Successfully uninstalled {name}.", level='success', event='done')
                job.status = 'done'
                job.done = 1
            else:
                job.status = 'failed'
                job.error = output[-500:]
                log_job(job, f"pip returned code {result.returncode}.", level='error', event='failed')
        except Exception as e:
            job.status = 'failed'
            job.error = str(e)
            log_job(job, str(e), level='error', event='failed')
        db.session.commit()


# ─── Git submodule management ─────────────────────────────────────────────────

@register_handler('update_submodule_bg')
def handle_update_submodule_bg(job, app):
    payload = job.payload or {}
    path = payload.get('path', '').strip()
    if not path:
        job.status = 'failed'
        job.error = 'No submodule path provided.'
        db.session.commit()
        return

    cwd = os.getcwd()
    with app.app_context():
        job.total = 1
        job.done = 0
        db.session.commit()
        log_job(job, f"Updating submodule: {path}", level='info', event='started')
        try:
            result = subprocess.run(
                ['git', 'submodule', 'update', '--remote', '--merge', '--', path],
                capture_output=True, text=True, timeout=300, cwd=cwd,
            )
            output = (result.stdout + result.stderr).strip()
            for line in output.splitlines()[-30:]:
                if line.strip():
                    log_job(job, line, level='info', event='progress')
            if result.returncode == 0:
                log_job(job, f"Submodule '{path}' updated successfully.", level='success', event='done')
                job.status = 'done'
                job.done = 1
            else:
                job.status = 'failed'
                job.error = output[-500:]
                log_job(job, f"git returned code {result.returncode}.", level='error', event='failed')
        except Exception as e:
            job.status = 'failed'
            job.error = str(e)
            log_job(job, str(e), level='error', event='failed')
        db.session.commit()


@register_handler('remove_submodule')
def handle_remove_submodule(job, app):
    payload = job.payload or {}
    path = payload.get('path', '').strip()
    if not path:
        job.status = 'failed'
        job.error = 'No submodule path provided.'
        db.session.commit()
        return

    cwd = os.getcwd()
    with app.app_context():
        job.total = 3
        job.done = 0
        db.session.commit()
        log_job(job, f"Removing submodule: {path}", level='warning', event='started')
        try:
            # Step 1: deinit
            r1 = subprocess.run(
                ['git', 'submodule', 'deinit', '--force', '--', path],
                capture_output=True, text=True, timeout=30, cwd=cwd,
            )
            log_job(job, (r1.stdout + r1.stderr).strip() or 'deinit done', level='info', event='progress')
            job.done = 1
            db.session.commit()

            # Step 2: git rm
            r2 = subprocess.run(
                ['git', 'rm', '-f', path],
                capture_output=True, text=True, timeout=30, cwd=cwd,
            )
            log_job(job, (r2.stdout + r2.stderr).strip() or 'git rm done', level='info', event='progress')
            job.done = 2
            db.session.commit()

            # Step 3: remove .git/modules entry
            modules_dir = os.path.join(cwd, '.git', 'modules', path)
            if os.path.isdir(modules_dir):
                import shutil
                shutil.rmtree(modules_dir, ignore_errors=True)
                log_job(job, f"Cleaned .git/modules/{path}", level='info', event='progress')

            if r1.returncode == 0 and r2.returncode == 0:
                log_job(job, f"Submodule '{path}' removed successfully.", level='success', event='done')
                job.status = 'done'
                job.done = 3
            else:
                err = (r1.stderr + r2.stderr).strip()
                job.status = 'failed'
                job.error = err[-500:]
                log_job(job, f"Removal may be incomplete: {err[:300]}", level='warning', event='failed')
        except Exception as e:
            job.status = 'failed'
            job.error = str(e)
            log_job(job, str(e), level='error', event='failed')
        db.session.commit()
