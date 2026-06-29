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
from app.core.db_class.db import Rule, Tag, RuleTagAssociation, BackgroundJob, BackgroundJobLog, ActivityLog, RequestOwnerRule
from app.features.rule.rule_core import _wipe_rule_children
import json as _json

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
        _wipe_rule_children(chunk)
        Rule.query.filter(Rule.id.in_(chunk), Rule.is_deleted == True).delete(synchronize_session=False)
        db.session.commit()
        deleted  += len(chunk)
        job.done  = deleted
        _save_offset(job, i + TRASH_BATCH)
        db.session.commit()
        log_job(job, f"{deleted}/{total} rule(s) permanently deleted.", level='info', event='progress')

    log_job(job, f"Done — {deleted} rule(s) permanently deleted.", level='success', event='done')


# ─── Connector pull ───────────────────────────────────────────────────────────

@register_handler('connector_pull')
def handle_connector_pull(job, app):
    """
    Pull rules (and optionally bundles) from a remote Rulezet instance.

    Payload:
        connector_id : int — local Connector.id to pull from
    """
    import datetime
    import requests as http_requests
    from concurrent.futures import ThreadPoolExecutor
    from app.core.db_class.db import Connector, Rule, RuleTagAssociation
    from app.features.connector.connector_core import (
        _get_or_create_shadow_user, _upsert_rule, _upsert_bundle,
        _extract_tag_family, build_tag_cache,
        _prepare_new_rule, _import_rule_history_new, _sync_tags, _sync_cve_ids, _sync_attacks,
    )
    from app.core.utils.activity_log import log_activity
    from sqlalchemy import or_

    import time as _time

    payload      = job.payload or {}
    connector_id = payload.get('connector_id')
    job_uuid     = job.uuid
    t_start      = _time.monotonic()

    with app.app_context():
        from app.core.db_class.db import BackgroundJob as BJ
        job = BJ.query.filter_by(uuid=job_uuid).first()
        connector = Connector.query.get(connector_id)
        if not connector or not connector.is_active:
            job.status = 'failed'
            job.error  = 'Connector not found or inactive.'
            db.session.commit()
            return

        if connector.owner_mode == 'self':
            effective_user_id = connector.owner_id
        else:
            shadow = _get_or_create_shadow_user(connector)
            effective_user_id = shadow.id
        headers = {'Accept': 'application/json'}
        if connector.api_key_outbound:
            headers['X-API-KEY'] = connector.api_key_outbound
        # Identify this instance on the remote so it can track pull history
        try:
            from app.core.db_class.db import InstanceConfig as _IC
            import os as _os
            _cfg = _IC.query.first()
            if _cfg:
                headers['X-Rulezet-Instance-UUID'] = str(_cfg.uuid)
            _pub = _os.environ.get('INSTANCE_PUBLIC_URL') or ''
            if _pub:
                headers['X-Rulezet-Instance-URL'] = _pub
        except Exception:
            pass

        # Per-pull content overrides (from trigger payload, fall back to connector flags)
        do_rules   = payload.get('sync_rules',   connector.sync_rules)
        do_bundles = payload.get('sync_bundles', connector.sync_bundles)


        since    = '1970-01-01T00:00:00'
        base     = connector.instance_url.rstrip('/')
        PER_PAGE = 500    # safe page size — remote serialises 500 rules per request

        # ── Build filter query-string params from the pull payload ──────────
        pull_filters = payload.get('filters', {}) or {}

        def _names_from_groups(groups, include_exclude=False):
            """Extract names from [{names, mode, exclude}, ...] filter groups.
            With include_exclude=False (default) only include non-excluded groups."""
            result = []
            for grp in (groups or []):
                if not isinstance(grp, dict):
                    continue
                if include_exclude or not grp.get('exclude', False):
                    result.extend(grp.get('names', []))
            return [n for n in result if n]

        # CVE filter
        cve_names  = _names_from_groups(pull_filters.get('cves', []))
        cve_qs     = ','.join(cve_names) if cve_names else ''

        # Format filter
        fmt_list   = [f for f in (pull_filters.get('formats') or []) if f]
        formats_qs = ','.join(fmt_list) if fmt_list else ''

        # Author filter
        auth_list   = [a for a in (pull_filters.get('authors') or []) if a]
        authors_qs  = ','.join(auth_list) if auth_list else ''

        # License filter (group structure, include only non-excluded)
        lic_names  = _names_from_groups(pull_filters.get('licenses', []))
        license_qs = ','.join(lic_names) if lic_names else ''

        # Tag filter
        tag_groups  = pull_filters.get('tags', []) or []
        tag_names   = _names_from_groups(tag_groups, include_exclude=True)  # include all for building params
        tags_qs     = ','.join(tag_names) if tag_names else ''
        tag_mode_qs = 'OR'
        tag_excl_qs = 'false'
        if tag_groups and isinstance(tag_groups[0], dict):
            tag_mode_qs = (tag_groups[0].get('mode') or 'OR').upper()
            tag_excl_qs = 'true' if tag_groups[0].get('exclude', False) else 'false'

        # Date range
        date_from_qs = (pull_filters.get('date_from') or '').strip()
        date_to_qs   = (pull_filters.get('date_to') or '').strip()

        # ATT&CK filter
        atk_list   = [a for a in (pull_filters.get('attacks') or []) if a]
        attacks_qs = ','.join(atk_list) if atk_list else ''

        def _build_rule_url(p: int) -> str:
            url = f"{base}/api/sync/rules?since={since}&page={p}&per_page={PER_PAGE}"
            if cve_qs:       url += f"&cve={cve_qs}"
            if formats_qs:   url += f"&formats={formats_qs}"
            if authors_qs:   url += f"&author={authors_qs}"
            if license_qs:   url += f"&license={license_qs}"
            if tags_qs:      url += f"&tags={tags_qs}&tag_mode={tag_mode_qs}&tag_exclude={tag_excl_qs}"
            if date_from_qs: url += f"&date_from={date_from_qs}"
            if date_to_qs:   url += f"&date_to={date_to_qs}"
            if attacks_qs:   url += f"&attacks={attacks_qs}"
            return url

        def _build_preflight_url() -> str:
            url = f"{base}/api/sync/rules?since={since}&count_only=true"
            if cve_qs:       url += f"&cve={cve_qs}"
            if formats_qs:   url += f"&formats={formats_qs}"
            if authors_qs:   url += f"&author={authors_qs}"
            if license_qs:   url += f"&license={license_qs}"
            if tags_qs:      url += f"&tags={tags_qs}&tag_mode={tag_mode_qs}&tag_exclude={tag_excl_qs}"
            if date_from_qs: url += f"&date_from={date_from_qs}"
            if date_to_qs:   url += f"&date_to={date_to_qs}"
            if attacks_qs:   url += f"&attacks={attacks_qs}"
            return url

        active_filters = [k for k in [cve_qs, formats_qs, authors_qs, license_qs, tags_qs, date_from_qs, date_to_qs, attacks_qs] if k]

        log_job(job, f"Starting pull from {base}", level='info', event='started')
        if active_filters:
            parts = []
            if cve_qs:       parts.append(f"cve={cve_qs}")
            if formats_qs:   parts.append(f"formats={formats_qs}")
            if authors_qs:   parts.append(f"authors={authors_qs}")
            if license_qs:   parts.append(f"license={license_qs}")
            if tags_qs:      parts.append(f"tags={tags_qs} ({tag_mode_qs}{', exclude' if tag_excl_qs=='true' else ''})")
            if date_from_qs: parts.append(f"from={date_from_qs}")
            if date_to_qs:   parts.append(f"to={date_to_qs}")
            if attacks_qs:   parts.append(f"attacks={attacks_qs}")
            log_job(job, f"Filters active: {' · '.join(parts)}", level='info', event='progress')

        # ── Manifest preflight: verify remote supports sync API ────────────────
        try:
            mf_resp = http_requests.get(f"{base}/api/sync/manifest", headers=headers, timeout=8)
            if mf_resp.status_code == 404:
                msg = ("Remote does not support the sync API — it may be running an older version of "
                       "Rulezet that does not support federation. Ask the remote admin to upgrade.")
                log_job(job, msg, level='error', event='done')
                job.status = 'failed'
                job.error  = msg
                connector.last_error = msg
                db.session.commit()
                return
            elif mf_resp.status_code != 200:
                msg = f"Remote manifest check failed (HTTP {mf_resp.status_code}) — check connectivity."
                log_job(job, msg, level='error', event='done')
                job.status = 'failed'
                job.error  = msg
                connector.last_error = msg
                db.session.commit()
                return
            mf_data    = mf_resp.json()
            remote_ver = mf_data.get('instance', {}).get('version', 'unknown')
            log_job(job, f"Remote version: {remote_ver}", level='info', event='progress')
            caps = mf_data.get('capabilities', {})
            if do_rules and not caps.get('sync_rules', True):
                log_job(job, "Remote reports sync_rules=false — no rules will be fetched.", level='warning', event='progress')
            if do_bundles and not caps.get('sync_bundles', True):
                log_job(job, "Remote reports sync_bundles=false — no bundles will be fetched.", level='warning', event='progress')
        except Exception as mf_exc:
            log_job(job, f"Manifest preflight failed: {mf_exc}", level='warning', event='progress')

        # ── Pre-flight: fetch totals for progress bar ─────────────────────────
        total_rules_remote   = 0
        total_bundles_remote = 0
        try:
            if do_rules:
                r = http_requests.get(_build_preflight_url(), headers=headers, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    total_rules_remote = d.get('count', d.get('total', 0))
            if do_bundles:
                r = http_requests.get(f"{base}/api/sync/bundles?since={since}&page=1&per_page=1",
                                      headers=headers, timeout=10)
                if r.status_code == 200:
                    total_bundles_remote = r.json().get('total', 0)
        except Exception:
            pass

        job.total = max(1, total_rules_remote + total_bundles_remote)
        job.done  = 0
        db.session.commit()
        log_job(job,
                f"Remote: {total_rules_remote} rule(s), {total_bundles_remote} bundle(s) available.",
                level='info', event='progress')

        rules_created  = 0
        rules_updated  = 0
        rules_skipped  = 0
        rules_errors   = 0
        bundles_created = 0
        bundles_updated = 0
        bundles_skipped = 0
        had_error       = False
        all_missing_tags: set = set()
        tag_cache: dict = None   # built once and reused across rules + bundles
        atk_assoc_set: set = set()  # {(rule_id, technique_id)} to avoid duplicate inserts
        attack_install_triggered = False  # only trigger the install job once

        # ── Check if ATT&CK data is installed ─────────────────────────────────
        from app.core.db_class.db import AttackTechnique as _ATK
        if not _ATK.query.first():
            log_job(job,
                    "ATT&CK technique database is empty — queuing an install now. "
                    "Techniques will be available on the next pull.",
                    level='warning', event='progress')
            from app.core.db_class.db import BackgroundJob as _BJ
            atk_job = _BJ(
                type='update_attack_data',
                status='pending',
                payload={},
                created_by=job.created_by,
            )
            db.session.add(atk_job)
            db.session.commit()
            attack_install_triggered = True

        MAX_PAGES = 10_000  # safety guard against infinite pagination loops

        # ── Pull rules ────────────────────────────────────────────────────────
        if do_rules:
            # Build a full tag cache once for the entire pull — reused for bundles too.
            tag_cache = build_tag_cache()
            log_job(job, f"Tag cache built: {len(tag_cache)} tags loaded.", level='info', event='progress')

            PREFETCH  = 4     # sliding window: up to 4 pages fetched in parallel

            def _http_get_rules(p):
                return http_requests.get(_build_rule_url(p), headers=headers, timeout=120)

            page          = 1
            page_futures  = {}   # page_num → Future
            executor      = ThreadPoolExecutor(max_workers=PREFETCH)

            def _enqueue(p):
                if p not in page_futures and p <= MAX_PAGES:
                    page_futures[p] = executor.submit(_http_get_rules, p)

            # Seed the sliding window
            for p in range(1, PREFETCH + 1):
                _enqueue(p)

            try:
                while page <= MAX_PAGES:
                    if _is_cancelled(job):
                        log_job(job, 'Cancelled.', level='warning', event='cancelled')
                        return
                    while _should_pause(job):
                        import time; time.sleep(2)

                    if page not in page_futures:
                        break

                    try:
                        resp = page_futures.pop(page).result(timeout=90)
                    except Exception as exc:
                        msg = f"Error fetching rules page {page}: {exc}"
                        log_job(job, msg, level='error', event='progress')
                        connector.last_error = msg
                        had_error = True
                        db.session.commit()
                        break

                    if resp.status_code != 200:
                        msg = f"Remote returned HTTP {resp.status_code} for rules page {page}."
                        log_job(job, msg, level='error', event='progress')
                        connector.last_error = msg
                        had_error = True
                        break

                    data  = resp.json()
                    items = data.get('rules', [])
                    if not items and page > 1:
                        break

                    # Advance the sliding window
                    _enqueue(page + PREFETCH)

                    # ── Batch UUID lookup: 1 query for the whole page ─────────
                    page_uuids = [item['uuid'] for item in items if item.get('uuid')]
                    existing_rules = Rule.query.filter(
                        or_(Rule.remote_rule_uuid.in_(page_uuids),
                            Rule.uuid.in_(page_uuids))
                    ).order_by(Rule.is_deleted.asc()).all()

                    rule_lookup: dict = {}
                    for r in existing_rules:
                        if r.remote_rule_uuid and r.remote_rule_uuid not in rule_lookup:
                            rule_lookup[r.remote_rule_uuid] = r
                        if r.uuid not in rule_lookup:
                            rule_lookup[r.uuid] = r

                    # ── Batch assoc lookup: 1 query for all matched rules ─────
                    matched_ids = [r.id for r in existing_rules]
                    assoc_set: set = set()
                    if matched_ids:
                        assocs = (RuleTagAssociation.query
                                  .filter(RuleTagAssociation.rule_id.in_(matched_ids))
                                  .with_entities(RuleTagAssociation.rule_id,
                                                 RuleTagAssociation.tag_id)
                                  .all())
                        assoc_set = {(a.rule_id, a.tag_id) for a in assocs}

                    # ── Two-pass page processing ──────────────────────────────
                    # Pass 1: existing rules (already have DB ids — no flush needed).
                    # Pass 2: new rules — batch all INSERTs into a single flush.
                    pg_created = pg_updated = pg_skipped = 0
                    new_rules_pending: list = []   # [(remote_item, Rule)]

                    for item in items:
                        remote_uuid = item.get('uuid')
                        if not remote_uuid:
                            rules_errors += 1
                            continue
                        pre_match = rule_lookup.get(remote_uuid)

                        if pre_match:
                            # Existing rule — handle inline (update or skip)
                            try:
                                result = _upsert_rule(
                                    connector, effective_user_id, item,
                                    triggered_by_id=job.created_by,
                                    missing_tags=all_missing_tags,
                                    local_match=pre_match,
                                    tag_cache=tag_cache,
                                    assoc_set=assoc_set,
                                )
                                if result == 'updated':
                                    rules_updated += 1; pg_updated += 1
                                elif result == 'skipped':
                                    rules_skipped += 1; pg_skipped += 1
                                else:
                                    rules_errors += 1
                            except Exception as item_exc:
                                rules_errors += 1
                                log_job(job, f"Error updating '{item.get('title', '?')}': {item_exc}",
                                        level='warning', event='progress')
                        else:
                            # New rule — stage for batch insert
                            try:
                                rule = _prepare_new_rule(connector, effective_user_id, item)
                                new_rules_pending.append((item, rule))
                            except Exception as item_exc:
                                rules_errors += 1
                                log_job(job, f"Error staging '{item.get('title', '?')}': {item_exc}",
                                        level='warning', event='progress')

                    # Single flush for ALL new rules on this page (1 DB round-trip)
                    if new_rules_pending:
                        try:
                            db.session.flush()
                            for item, rule in new_rules_pending:
                                missed = _sync_tags(rule, item.get('tags', []),
                                                    effective_user_id,
                                                    tag_cache=tag_cache,
                                                    assoc_set=assoc_set)
                                all_missing_tags.update(missed)
                                _sync_cve_ids(rule, item.get('cve_ids', []))
                                unknown_atk = _sync_attacks(rule, item.get('attack_ids', []),
                                                            effective_user_id,
                                                            atk_assoc_set=atk_assoc_set)
                                if '__empty__' in unknown_atk and not attack_install_triggered:
                                    attack_install_triggered = True
                                    log_job(job, "ATT&CK data missing — install job already queued.",
                                            level='warning', event='progress')
                                _import_rule_history_new(rule, item.get('update_history', []),
                                                         effective_user_id)
                            pg_created    = len(new_rules_pending)
                            rules_created += pg_created
                        except Exception as batch_exc:
                            rules_errors += len(new_rules_pending)
                            log_job(job, f"Batch insert error on page {page}: {batch_exc}",
                                    level='error', event='progress')
                            db.session.rollback()

                    db.session.commit()

                    processed = (rules_created + rules_updated + rules_skipped + rules_errors
                                 + bundles_created + bundles_updated + bundles_skipped)
                    job.done = min(processed, job.total)
                    log_job(job,
                            f"Rules p.{page}: +{pg_created} new, ~{pg_updated} updated, ={pg_skipped} skipped.",
                            level='info', event='progress')
                    if not data.get('has_more', False):
                        break
                    page += 1
            finally:
                executor.shutdown(wait=False)

        # ── Pull bundles ──────────────────────────────────────────────────────
        if do_bundles:
            if tag_cache is None:
                tag_cache = build_tag_cache()
                log_job(job, f"Tag cache built: {len(tag_cache)} tags loaded.", level='info', event='progress')

            # Phase 1 — collect all bundle pages and their referenced rule UUIDs
            all_bundle_items: list = []
            bundle_rule_uuids: set = set()
            page = 1
            while page <= MAX_PAGES:
                if _is_cancelled(job):
                    log_job(job, 'Cancelled.', level='warning', event='cancelled')
                    return
                url = f"{base}/api/sync/bundles?since={since}&page={page}&per_page={PER_PAGE}"
                try:
                    resp = http_requests.get(url, headers=headers, timeout=60)
                    if resp.status_code != 200:
                        had_error = True; break
                    data  = resp.json()
                    items = data.get('bundles', [])
                    if not items and page > 1:
                        break
                    all_bundle_items.extend(items)
                    for item in items:
                        bundle_rule_uuids.update(item.get('rules', []))
                    if not data.get('has_more', False):
                        break
                    page += 1
                except Exception as exc:
                    log_job(job, f"Error fetching bundles page {page}: {exc}",
                            level='error', event='progress')
                    had_error = True; break

            # Phase 2 — when not already pulling all rules, import only the rules
            # referenced by the bundles that don't exist locally yet.
            if bundle_rule_uuids and not do_rules:
                existing_local = set(
                    r[0] for r in Rule.query.filter(
                        or_(Rule.uuid.in_(bundle_rule_uuids),
                            Rule.remote_rule_uuid.in_(bundle_rule_uuids))
                    ).with_entities(Rule.uuid).all()
                ) | set(
                    r[0] for r in Rule.query.filter(
                        or_(Rule.uuid.in_(bundle_rule_uuids),
                            Rule.remote_rule_uuid.in_(bundle_rule_uuids))
                    ).with_entities(Rule.remote_rule_uuid).all()
                    if r[0]
                )
                missing_uuids = bundle_rule_uuids - existing_local
                if missing_uuids:
                    log_job(job,
                            f"Fetching {len(missing_uuids)} rule(s) referenced by bundles…",
                            level='info', event='progress')
                    # Chunk to keep URL size reasonable
                    CHUNK = 100
                    missing_list = list(missing_uuids)
                    for i in range(0, len(missing_list), CHUNK):
                        if _is_cancelled(job):
                            log_job(job, 'Cancelled.', level='warning', event='cancelled')
                            return
                        chunk = missing_list[i:i + CHUNK]
                        uuids_qs = ','.join(chunk)
                        try:
                            r = http_requests.get(
                                f"{base}/api/sync/rules?uuids={uuids_qs}",
                                headers=headers, timeout=60,
                            )
                            if r.status_code != 200:
                                log_job(job, f"Failed to fetch bundle rules chunk (HTTP {r.status_code})",
                                        level='warning', event='progress')
                                continue
                            chunk_rules = r.json().get('rules', [])
                            new_rules_pending = []
                            chunk_uuids = [item['uuid'] for item in chunk_rules if item.get('uuid')]
                            existing_chunk = Rule.query.filter(
                                or_(Rule.remote_rule_uuid.in_(chunk_uuids),
                                    Rule.uuid.in_(chunk_uuids))
                            ).all()
                            chunk_lookup = {}
                            for ex in existing_chunk:
                                if ex.remote_rule_uuid:
                                    chunk_lookup[ex.remote_rule_uuid] = ex
                                chunk_lookup[ex.uuid] = ex

                            for item in chunk_rules:
                                pre_match = chunk_lookup.get(item.get('uuid'))
                                if pre_match:
                                    _upsert_rule(connector, effective_user_id, item,
                                                 triggered_by_id=job.created_by,
                                                 missing_tags=all_missing_tags,
                                                 local_match=pre_match,
                                                 tag_cache=tag_cache)
                                    rules_updated += 1
                                else:
                                    rule = _prepare_new_rule(connector, effective_user_id, item)
                                    new_rules_pending.append((item, rule))

                            if new_rules_pending:
                                db.session.flush()
                                for item, rule in new_rules_pending:
                                    missed = _sync_tags(rule, item.get('tags', []),
                                                        effective_user_id,
                                                        tag_cache=tag_cache)
                                    all_missing_tags.update(missed)
                                    _sync_cve_ids(rule, item.get('cve_ids', []))
                                    _import_rule_history_new(rule, item.get('update_history', []),
                                                             effective_user_id)
                                rules_created += len(new_rules_pending)

                            db.session.commit()
                        except Exception as exc:
                            log_job(job, f"Error importing bundle rules chunk: {exc}",
                                    level='warning', event='progress')
                            db.session.rollback()

            # Phase 3 — upsert bundles (rules are now locally available)
            for item in all_bundle_items:
                if _is_cancelled(job):
                    log_job(job, 'Cancelled.', level='warning', event='cancelled')
                    return
                try:
                    result = _upsert_bundle(connector, effective_user_id, item,
                                            triggered_by_id=job.created_by,
                                            tag_cache=tag_cache)
                    if result == 'created':
                        bundles_created += 1
                    elif result == 'updated':
                        bundles_updated += 1
                    elif result == 'skipped':
                        bundles_skipped += 1
                except Exception as bundle_exc:
                    log_job(job, f"Error on bundle '{item.get('name', '?')}': {bundle_exc}",
                            level='warning', event='progress')
                processed = rules_created + rules_updated + rules_skipped + rules_errors + bundles_created + bundles_updated + bundles_skipped
                job.done = min(processed, job.total)
            db.session.commit()

        # ── Finalize ──────────────────────────────────────────────────────────
        now       = datetime.datetime.now(datetime.timezone.utc)
        duration  = round(_time.monotonic() - t_start, 1)

        # Compute unique tag families that had no local match
        missing_families = sorted({
            f for n in all_missing_tags
            for f in [_extract_tag_family(n)] if f
        })

        if not had_error:
            connector.last_sync_at = now
            connector.is_verified  = True
        connector.rules_synced   += rules_created + rules_updated
        connector.bundles_synced += bundles_created + bundles_updated
        job.done   = job.total
        job.status = 'done'
        db.session.commit()

        summary = (
            f"Pull done in {duration}s — "
            f"rules: +{rules_created} new, ~{rules_updated} updated, "
            f"={rules_skipped} skipped, {rules_errors} errors | "
            f"bundles: +{bundles_created} new, ~{bundles_updated} updated, ={bundles_skipped} skipped."
        )
        if missing_families:
            log_job(job,
                    f"Tag families from remote not installed locally: {', '.join(missing_families)}",
                    level='warning', event='progress')

        log_job(job, summary, level='success', event='done')
        log_activity('connector.pull_done',
                     f"Connector '{connector.name}': {summary}",
                     target_type='connector', target_id=connector.id,
                     target_uuid=connector.uuid,
                     extra={
                         'rules_added':         rules_created,
                         'rules_updated':       rules_updated,
                         'rules_skipped':       rules_skipped,
                         'rules_errors':        rules_errors,
                         'bundles_added':       bundles_created,
                         'bundles_updated':     bundles_updated,
                         'bundles_skipped':     bundles_skipped,
                         'remote_rules':        total_rules_remote,
                         'remote_bundles':      total_bundles_remote,
                         'had_error':           had_error,
                         'duration_s':          duration,
                         'missing_tag_families': missing_families,
                     })


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

    job_uuid = job.uuid
    with app.app_context():
        # Re-fetch in this context's session — the worker's `job` object belongs
        # to another session, so commits here would silently drop its changes.
        job = BackgroundJob.query.filter_by(uuid=job_uuid).first()
        if job is None:
            return
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

    job_uuid = job.uuid
    with app.app_context():
        # Re-fetch in this context's session (see handle_update_package).
        job = BackgroundJob.query.filter_by(uuid=job_uuid).first()
        if job is None:
            return
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
    job_uuid = job.uuid
    with app.app_context():
        # Re-fetch in this context's session (see handle_update_package).
        job = BackgroundJob.query.filter_by(uuid=job_uuid).first()
        if job is None:
            return
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
    job_uuid = job.uuid
    with app.app_context():
        # Re-fetch in this context's session (see handle_update_package).
        job = BackgroundJob.query.filter_by(uuid=job_uuid).first()
        if job is None:
            return
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


# ─────────────────────────────────────────────────────────────────────────────
#  bulk_update_decision — accept or reject all pending rule updates for a scan
# ─────────────────────────────────────────────────────────────────────────────

@register_handler('bulk_update_decision')
def handle_bulk_update_decision(job, app):
    with app.app_context():
        try:
            sid    = job.payload.get('sid')
            action = job.payload.get('action')  # 'accept' | 'reject'

            from app.features.rule.rule_core import (
                get_rule_update_list_filtered, accept_all_update, reject_all_update,
            )
            rule_list, count = get_rule_update_list_filtered(
                sid,
                f_found=job.payload.get('f_found'),
                f_error=job.payload.get('f_error'),
                f_syntax_valid=job.payload.get('f_syntax_valid'),
            )

            job.total = max(count, 1)
            if not rule_list or count == 0:
                log_job(job, 'No pending updates found.', level='info', event='done')
                job.status = 'done'
                job.done = job.total
                db.session.commit()
                return

            ok = accept_all_update(rule_list) if action == 'accept' else reject_all_update(rule_list)
            job.done   = job.total
            job.status = 'done' if ok else 'failed'
            verb = 'accepted' if action == 'accept' else 'rejected'
            log_job(job, f'{count} update(s) {verb}.', level='success' if ok else 'error', event='done')
        except Exception as e:
            job.status = 'failed'
            job.error  = str(e)
            log_job(job, str(e), level='error', event='failed')
        db.session.commit()


# ─────────────────────────────────────────────────────────────────────────────
#  bulk_new_rules_decision — add or reject all new rules found in a scan
# ─────────────────────────────────────────────────────────────────────────────

@register_handler('bulk_new_rules_decision')
def handle_bulk_new_rules_decision(job, app):
    with app.app_context():
        try:
            sid     = job.payload.get('sid')
            action  = job.payload.get('action')   # 'add' | 'reject'
            user_id = job.payload.get('user_id')

            from app.features.rule.rule_core import (
                get_valid_new_rules_by_sid, reject_all_new_rules_by_sid,
                get_updater_result_by_id, change_message_new_rule,
            )
            from app.features.rule.rule_format.main_format import parse_rule_by_format
            from app.core.db_class.db import User
            import app.features.account.account_core as AccountModel

            if action == 'reject':
                reject_all_new_rules_by_sid(sid)
                job.done = job.total = 1
                job.status = 'done'
                log_job(job, 'All new rules rejected.', level='success', event='done')
                db.session.commit()
                return

            # action == 'add'
            new_rules = get_valid_new_rules_by_sid(sid)
            job.total = max(len(new_rules), 1)

            if not new_rules:
                log_job(job, 'No valid new rules to add.', level='info', event='done')
                job.status = 'done'
                job.done = job.total
                db.session.commit()
                return

            user   = User.query.get(user_id)
            added  = errors = 0

            for i, nr in enumerate(new_rules):
                source_info = None
                updater = get_updater_result_by_id(nr.update_result_id)
                if updater:
                    try:
                        info = _json.loads(updater.info)
                        source_info = info.get('repo_url')
                    except Exception:
                        pass

                change_message_new_rule(nr.id, 'imported')
                success, message, imported = parse_rule_by_format(
                    nr.rule_content, user, nr.format, source_info, github_path=nr.github_path
                )
                if success and imported:
                    profil = AccountModel.get_or_create_gamification_profile(imported.user_id)
                    if profil:
                        AccountModel.update_rules_owned_gamification(profil.id, imported.user_id)
                    added += 1
                else:
                    change_message_new_rule(nr.id, f'error: {message}')
                    errors += 1

                job.done = i + 1
                db.session.commit()

            job.status = 'done'
            log_job(job, f'{added} rule(s) added, {errors} error(s).', level='success', event='done')
        except Exception as e:
            job.status = 'failed'
            job.error  = str(e)
            log_job(job, str(e), level='error', event='failed')
        db.session.commit()


# ─── ownership_transfer_bulk ───────────────────────────────────────────────────

OWNERSHIP_BATCH = 100

@register_handler('ownership_transfer_bulk')
def handle_ownership_transfer_bulk(job, app):
    """
    Transfer ownership of a large set of rules to a new owner in batches.

    Payload:
        request_id : int        — RequestOwnerRule id
        rule_ids   : list[int]  — rules to transfer
    """
    payload    = job.payload or {}
    request_id = payload.get('request_id')
    rule_ids   = payload.get('rule_ids', [])

    if not request_id or not rule_ids:
        log_job(job, "Missing request_id or rule_ids.", level='error', event='done')
        job.status = 'failed'
        db.session.commit()
        return

    ownership_request = RequestOwnerRule.query.get(request_id)
    if not ownership_request:
        log_job(job, f"RequestOwnerRule #{request_id} not found.", level='error', event='done')
        job.status = 'failed'
        db.session.commit()
        return

    total = len(rule_ids)
    if job.total == 0:
        job.total = total
        db.session.commit()

    # Mark request as approved upfront
    ownership_request.status = 'approved'
    db.session.commit()
    log_job(job, f"Starting transfer of {total} rule(s) to user #{ownership_request.user_id}.",
            level='info', event='started')

    offset    = payload.get('_resume_offset', 0)
    new_owner = ownership_request.user_id
    source    = ownership_request.rule_source
    transferred = 0

    for i in range(offset, total, OWNERSHIP_BATCH):
        if _is_cancelled(job):
            log_job(job, "Cancelled.", level='warning', event='cancelled')
            return
        while _should_pause(job):
            import time; time.sleep(2)

        chunk_ids = rule_ids[i:i + OWNERSHIP_BATCH]

        # Transfer ownership
        Rule.query.filter(Rule.id.in_(chunk_ids)).update(
            {"user_id": new_owner}, synchronize_session=False
        )

        # Auto-reject other pending requests for these rules
        RequestOwnerRule.query.filter(
            RequestOwnerRule.rule_id.in_(chunk_ids),
            RequestOwnerRule.status == 'pending',
            RequestOwnerRule.id != request_id,
        ).update(
            {"status": "rejected", "user_id_to_send": new_owner},
            synchronize_session=False,
        )

        db.session.commit()
        transferred += len(chunk_ids)
        job.done = transferred
        _save_offset(job, i + OWNERSHIP_BATCH)
        db.session.commit()
        log_job(job, f"{transferred}/{total} rule(s) transferred.", level='info', event='progress')

    # Also reject pending source-level requests if applicable
    if source:
        RequestOwnerRule.query.filter(
            RequestOwnerRule.rule_source == source,
            RequestOwnerRule.status == 'pending',
            RequestOwnerRule.id != request_id,
        ).update(
            {"status": "rejected", "user_id_to_send": new_owner},
            synchronize_session=False,
        )
        db.session.commit()

    # Notify the requester
    try:
        from app.features.notification.notification_core import notify_ownership_decision
        notify_ownership_decision(ownership_request, approved=True,
                                  rule_title=f"{transferred} rules from {source or 'source'}")
    except Exception as _e:
        log_job(job, f"Notification error: {_e}", level='warning')

    log_job(job, f"Done — {transferred} rule(s) transferred.", level='success', event='done')


# ─── ATT&CK: update catalogue from MITRE ─────────────────────────────────────

@register_handler('update_attack_data')
def handle_update_attack_data(job, app):
    """Download MITRE ATT&CK STIX bundle and upsert AttackTechnique rows."""
    log_job(job, 'Fetching ATT&CK data from MITRE GitHub…', level='info', event='start')
    try:
        from app.features.attack.attack_core import fetch_and_update_attack_data
        created, updated = fetch_and_update_attack_data()
        job.done = 1
        db.session.commit()
        log_job(job, f'Done — {created} techniques created, {updated} updated.',
                level='success', event='done')
    except Exception as exc:
        log_job(job, f'Error: {exc}', level='error', event='error')
        raise


# ─── ATT&CK: bulk auto-parse rules ───────────────────────────────────────────

ATTACK_PARSE_BATCH = 500

@register_handler('bulk_parse_attack_rules')
def handle_bulk_parse_attack_rules(job, app):
    """
    Scan all (or format-filtered) rules and auto-create RuleAttackAssociation
    entries by parsing rule content for ATT&CK technique IDs.
    """
    payload  = job.payload or {}
    fmt      = payload.get('format')        # optional format filter, e.g. 'sigma'
    offset   = payload.get('_resume_offset', 0)

    from app.features.attack.attack_core import _extract_technique_ids
    from app.core.db_class.db import AttackTechnique, RuleAttackAssociation
    import datetime as _dt

    # Build query
    q = Rule.query.filter(Rule.is_deleted == False)
    if fmt:
        q = q.filter(Rule.format == fmt)

    if job.total == 0:
        job.total = q.count()
        db.session.commit()
        log_job(job, f'Starting — {job.total} rules to parse.', level='info', event='start')

    # Cache all known technique IDs — include deprecated ones so sigma rules
    # that explicitly reference deprecated IDs (e.g. T1068) are still associated.
    known_ids = {
        t.technique_id
        for t in AttackTechnique.query.all()
    }
    if not known_ids:
        log_job(job, 'No ATT&CK techniques in DB — run "Update ATT&CK data" job first.',
                level='warning', event='done')
        job.done = job.total
        db.session.commit()
        return

    total_added = 0
    batch_num   = 0

    while True:
        if _is_cancelled(job): # noqa — defined in local scope via job_worker helpers
            log_job(job, 'Cancelled.', level='warning', event='cancelled')
            return
        while _should_pause(job):
            import time; time.sleep(2)

        rules = (
            q.with_entities(Rule.id, Rule.format, Rule.to_string)
            .offset(offset)
            .limit(ATTACK_PARSE_BATCH)
            .all()
        )
        if not rules:
            break

        new_assocs = []
        # Fetch existing associations for this batch to avoid duplicates
        rule_ids = [r.id for r in rules]
        existing = {
            (a.rule_id, a.technique_id)
            for a in RuleAttackAssociation.query.filter(
                RuleAttackAssociation.rule_id.in_(rule_ids)
            ).all()
        }

        for rule_id, rule_fmt, content in rules:
            ids = _extract_technique_ids(rule_fmt or '', content or '')
            for tid in dict.fromkeys(ids):   # dedup
                if tid not in known_ids:
                    continue
                if (rule_id, tid) in existing:
                    continue
                new_assocs.append({
                    'uuid':         str(uuid_mod.uuid4()),
                    'rule_id':      rule_id,
                    'technique_id': tid,
                    'user_id':      None,
                    'source':       'auto',
                    'added_at':     _dt.datetime.now(tz=_dt.timezone.utc),
                })
                existing.add((rule_id, tid))

        if new_assocs:
            db.session.bulk_insert_mappings(RuleAttackAssociation, new_assocs)
            db.session.commit()
            total_added += len(new_assocs)

        offset   += len(rules)
        job.done  = offset
        _save_offset(job, offset)
        db.session.commit()

        batch_num += 1
        if batch_num % LOG_EVERY == 0:
            log_job(job, f'{offset}/{job.total} rules processed, {total_added} associations created.',
                    level='info', event='progress')

    log_job(job, f'Done — {offset} rules parsed, {total_added} ATT&CK associations created.',
            level='success', event='done')


# ── Bulk Field Parser ────────────────────────────────────────────────────────

FIELD_PARSE_BATCH = 200
FIELD_PARSE_LOG_EVERY = 10

@register_handler('bulk_parse_fields')
def handle_bulk_parse_fields(job, app):
    """
    Parse rule content and update metadata fields (license, author, original_uuid, etc.)
    based on keyword/regex config provided in the job payload.
    """
    from app.features.rule.field_parser_core import parse_field_from_content, PARSEABLE_FIELD_KEYS

    payload       = job.payload or {}
    rule_ids      = payload.get('rule_ids', 'ALL')
    format_filter = payload.get('format_filter') or None
    fields_config = payload.get('fields_config', {})
    offset        = payload.get('_resume_offset', 0)

    enabled_fields = [k for k, v in fields_config.items() if v.get('enabled')]
    if not enabled_fields:
        log_job(job, 'No fields enabled — nothing to do.', level='warning', event='done')
        job.done = job.total or 0
        db.session.commit()
        return

    # with_entities column order: id, to_string, license, author, original_uuid, description, version, title
    FIELD_IDX = {k: i + 2 for i, k in enumerate(PARSEABLE_FIELD_KEYS)}

    q = Rule.query.filter(Rule.is_deleted == False)
    if rule_ids != 'ALL':
        q = q.filter(Rule.id.in_(rule_ids))
    elif format_filter:
        q = q.filter(Rule.format == format_filter)

    if job.total == 0:
        job.total = q.count()
        db.session.commit()
        log_job(job, f'Starting — {job.total} rules to process, fields: {", ".join(enabled_fields)}.',
                level='info', event='start')
    else:
        log_job(job, f'Resuming from offset {offset}.', level='info', event='resume')

    total_updated = 0
    batch_num     = 0

    while True:
        if _is_cancelled(job):
            log_job(job, 'Cancelled.', level='warning', event='cancelled')
            return
        while _should_pause(job):
            import time; time.sleep(2)

        rows = (
            q.with_entities(
                Rule.id, Rule.to_string,
                Rule.license, Rule.author, Rule.original_uuid,
                Rule.description, Rule.version, Rule.title,
            )
            .offset(offset)
            .limit(FIELD_PARSE_BATCH)
            .all()
        )
        if not rows:
            break

        for row in rows:
            rule_id = row[0]
            content = row[1] or ''
            updates = {}

            for field_key in enabled_fields:
                if field_key not in FIELD_IDX:
                    continue
                cfg         = fields_config.get(field_key, {})
                current_val = row[FIELD_IDX[field_key]]

                if current_val and not cfg.get('overwrite', False):
                    continue

                new_val = parse_field_from_content(content, cfg)
                if new_val:
                    updates[field_key] = new_val

            if updates:
                Rule.query.filter(Rule.id == rule_id).update(updates)
                total_updated += 1

        db.session.commit()
        offset    += len(rows)
        job.done   = offset
        _save_offset(job, offset)
        db.session.commit()

        batch_num += 1
        if batch_num % FIELD_PARSE_LOG_EVERY == 0:
            log_job(job, f'{offset}/{job.total} rules processed, {total_updated} rules updated.',
                    level='info', event='progress')

    log_job(job, f'Done — {offset} rules processed, {total_updated} rules updated.',
            level='success', event='done')


# ─────────────────────────────────────────────────────────────────────────────
# blog_from_cve — auto-generate a blog post from vulnerability data
# ─────────────────────────────────────────────────────────────────────────────

def _circl_severity(score):
    try:
        s = float(score)
        if s >= 9.0: return 'Critical'
        if s >= 7.0: return 'High'
        if s >= 4.0: return 'Medium'
        return 'Low'
    except Exception:
        return 'Unknown'



def _render_cve_section(cve_id, data, rule_count=0, bundle_count=0):
    """Return markdown content for one CVE from CIRCL API response data."""
    summary  = data.get('summary') or ''
    cvss     = data.get('cvss3') or data.get('cvss') or ''
    vector   = data.get('cvss3-vector') or data.get('cvss-vector') or ''
    cwe      = data.get('cwe') or ''
    pub      = (data.get('Published') or '')[:10]
    assigner = data.get('assigner') or ''
    vendors  = data.get('vendors') or {}
    credits_ = data.get('credits') or []
    epss     = data.get('epss') or {}

    refs = []
    for r in (data.get('references') or []):
        u = r if isinstance(r, str) else (r.get('url') or r.get('href') or '')
        if u.startswith('http'):
            refs.append(u)
    refs = refs[:6]

    sev = _circl_severity(cvss) if cvss else ''
    lines = []

    if summary:
        lines += ['## Overview\n', f'{summary}\n']

    # Severity table
    rows = []
    if cvss:
        rows.append(('CVSS Score', f'**{cvss}**' + (f' ({sev})' if sev else '')))
    if vector:
        rows.append(('CVSS Vector', f'`{vector}`'))
    if cwe:
        num = cwe.replace('CWE-', '')
        rows.append(('CWE', f'[{cwe}](https://cwe.mitre.org/data/definitions/{num}.html)'))
    if pub:
        rows.append(('Published', pub))
    if epss and isinstance(epss, dict):
        sc = epss.get('score') or epss.get('epss')
        if sc:
            try:
                rows.append(('EPSS Score', f'{float(sc)*100:.2f}%'))
            except Exception:
                pass
    if assigner:
        rows.append(('Assigner', assigner))
    if rows:
        lines += ['\n## Severity & Impact\n', '| Metric | Value |', '|--------|-------|']
        lines += [f'| {k} | {v} |' for k, v in rows]

    # Products
    if vendors:
        lines.append('\n## Affected Products\n')
        for vendor, prods in vendors.items():
            for p in (prods if isinstance(prods, list) else [prods]):
                lines.append(f'- **{vendor}**: {p}')

    # Detection rules
    if rule_count or bundle_count:
        parts = []
        if rule_count:
            parts.append(f'**{rule_count}** detection rule{"s" if rule_count != 1 else ""}')
        if bundle_count:
            parts.append(f'**{bundle_count}** bundle{"s" if bundle_count != 1 else ""}')
        lines += [
            '\n## Detection Rules\n',
            f'Rulezet contains {" and ".join(parts)} for {cve_id}. '
            'They have been automatically attached to this post.',
        ]

    # Remediation
    lines += [
        '\n## Remediation\n',
        f'Apply the latest patches from the vendor. '
        f'Monitor the [{cve_id} entry on Vulnerability Lookup]'
        f'(https://vulnerability.circl.lu/vuln/{cve_id.lower()}) for updates.',
    ]

    # References
    lines += ['\n## References\n',
              f'- [{cve_id} — Vulnerability Lookup](https://vulnerability.circl.lu/vuln/{cve_id.lower()})']
    lines += [f'- {u}' for u in refs]

    # Credits
    if credits_:
        lines.append('\n## Credits\n')
        for c in (credits_ if isinstance(credits_, list) else [credits_]):
            name = c if isinstance(c, str) else (c.get('name') or c.get('value') or str(c))
            lines.append(f'- {name}')

    lines += [
        '\n---',
        f'*Auto-generated from [Vulnerability Lookup](https://vulnerability.circl.lu). '
        f'For up-to-date details visit the [{cve_id} entry]'
        f'(https://vulnerability.circl.lu/vuln/{cve_id.lower()}).*',
    ]
    return '\n'.join(lines)


@register_handler('blog_from_cve')
def handle_blog_from_cve(job, app):
    payload         = job.payload or {}
    post_id         = payload.get('post_id')
    cve_ids         = payload.get('cve_ids') or []
    formats         = payload.get('formats') or []
    include_rules   = payload.get('include_rules', True)
    include_bundles = payload.get('include_bundles', True)

    with app.app_context():
        import requests as _req
        from app.core.db_class.db import BlogPost, Bundle
        from app.features.blog.blog_core import _sync_tags, _sync_rules, _sync_bundles, _make_slug

        post = BlogPost.query.get(post_id)
        if not post:
            log_job(job, f'BlogPost {post_id} not found.', level='error', event='error')
            return

        log_job(job, f'Generating CVE post for: {", ".join(cve_ids)}', event='start')

        # 1. Fetch CVE data
        cve_data = {}
        for cve_id in cve_ids:
            try:
                resp = _req.get(
                    f'https://vulnerability.circl.lu/api/cve/{cve_id.lower()}',
                    timeout=15,
                    headers={'Accept': 'application/json', 'User-Agent': 'Rulezet/1.0'},
                )
                if resp.ok:
                    cve_data[cve_id] = resp.json()
                    log_job(job, f'Fetched {cve_id} from Vulnerability Lookup.', event='progress')
                else:
                    log_job(job, f'CIRCL API {resp.status_code} for {cve_id}.', level='warning', event='warning')
                    cve_data[cve_id] = {}
            except Exception as exc:
                log_job(job, f'Could not fetch {cve_id}: {exc}', level='warning', event='warning')
                cve_data[cve_id] = {}

        # 2. Match rules / bundles
        matched_rule_ids, matched_bundle_ids = [], []
        if include_rules:
            q = Rule.query.filter(Rule.is_deleted == False)
            if formats:
                q = q.filter(Rule.format.in_(formats))
            for cve_id in cve_ids:
                for r in q.filter(Rule.cve_id.ilike(f'%{cve_id}%')).all():
                    if r.id not in matched_rule_ids:
                        matched_rule_ids.append(r.id)
            log_job(job, f'{len(matched_rule_ids)} matching rule(s) found.', event='progress')

        if include_bundles:
            for cve_id in cve_ids:
                for b in Bundle.query.filter(
                    Bundle.vulnerability_identifiers.ilike(f'%{cve_id}%')
                ).all():
                    if b.id not in matched_bundle_ids:
                        matched_bundle_ids.append(b.id)
            log_job(job, f'{len(matched_bundle_ids)} matching bundle(s) found.', event='progress')

        # 3. Cover image — use the bundled Vulnerability Lookup default
        cover_url = '/static/uploads/blog/vendor/Vulnerability-Lookup-default.jpg'

        # 4. Generate content
        nr, nb = len(matched_rule_ids), len(matched_bundle_ids)
        if len(cve_ids) == 1:
            cid = cve_ids[0]
            dat = cve_data.get(cid, {})
            summary = dat.get('summary', '')
            cvss    = dat.get('cvss3') or dat.get('cvss') or ''
            sev     = _circl_severity(cvss) if cvss else ''
            short   = summary[:70].rstrip() + ('…' if len(summary) > 70 else '')
            title   = f'{cid}: {short}' if short else cid
            excerpt = (
                f'Security advisory for {cid}.'
                + (f' CVSS {cvss} ({sev}).' if cvss else '')
                + (f' {summary[:200]}{"…" if len(summary) > 200 else ""}' if summary else '')
            )
            content = _render_cve_section(cid, dat, nr, nb)
        else:
            cids_str = ', '.join(cve_ids)
            title    = f'Security Advisory: {cids_str[:80]}{"…" if len(cids_str) > 80 else ""}'
            excerpt  = f'Combined advisory covering {len(cve_ids)} vulnerabilities: {cids_str[:200]}.'
            content  = '\n\n---\n\n'.join(
                f'# {cid}\n\n' + _render_cve_section(cid, cve_data.get(cid, {}))
                for cid in cve_ids
            )
            if nr or nb:
                parts = []
                if nr: parts.append(f'**{nr}** detection rule{"s" if nr != 1 else ""}')
                if nb: parts.append(f'**{nb}** bundle{"s" if nb != 1 else ""}')
                content += (
                    f'\n\n## Detection Rules\n\n'
                    f'Rulezet contains {" and ".join(parts)} for these vulnerabilities. '
                    'They have been automatically attached to this post.'
                )

        # 5. Update the draft post
        post.title           = title[:500]
        post.slug            = _make_slug(title, exclude_id=post.id)
        post.excerpt         = excerpt
        post.content         = content
        post.cover_image_url = cover_url
        post.cve_ids         = cve_ids
        post.external_links  = [
            {'url': f'https://vulnerability.circl.lu/vuln/{c.lower()}',
             'label': f'{c} — Vulnerability Lookup'}
            for c in cve_ids
        ]
        post.updated_at = datetime.datetime.utcnow()
        db.session.flush()

        _sync_tags(post, ['vulnerability', 'cve'] + [c.lower() for c in cve_ids])
        _sync_rules(post, matched_rule_ids)
        _sync_bundles(post, matched_bundle_ids)
        db.session.commit()

        log_job(job, f'Post "{title[:80]}" ready.', level='success', event='done')
