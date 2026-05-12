"""
job_handlers_rulecast.py
"""

import os
import multiprocessing as mp
from functools import partial

from app.features.jobs.job_worker import register_handler
from app.features.jobs.job_handlers import log_job, _is_cancelled, _should_pause, _save_offset
from app import db
from app.features.rule import rule_core as RuleModel
from app.features.rule.rules_core import bad_rule_core as BadRuleModel


PARSE_WORKERS     = max(2, mp.cpu_count() - 1)  # all CPUs minus 1 for the main process
BATCH_SIZE        = 500                           # larger batch = better multiprocessing efficiency
PROGRESS_INTERVAL = 20


def _get_rulecast_engine():
    from parsers.engine import RuleCastEngine
    return RuleCastEngine()


def _walk_rule_files(repo_dir, engine):
    ext_to_parsers = {}
    for p in engine.parsers:
        for ext in p.extensions:
            ext_to_parsers.setdefault(ext.lower(), []).append(p)

    ambiguous_exts = {ext for ext, parsers in ext_to_parsers.items() if len(parsers) > 1}
    ambiguous_exts.update({'.yml', '.yaml'})
    known_extensions = set(ext_to_parsers.keys())

    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if not d.startswith(('.', '_'))]
        for fname in files:
            if fname.startswith(('.', '_')):
                continue
            _, ext = os.path.splitext(fname)
            ext = ext.lower()
            if ext not in known_extensions:
                yield 'skip', fname, f"extension '{ext}' not supported", None, None, None
                continue

            filepath = os.path.join(root, fname)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                yield 'skip', fname, f"could not read file: {e}", None, None, None
                continue

            if ext in ambiguous_exts:
                matched_parser = None
                for p in ext_to_parsers.get(ext, engine.parsers):
                    if p.can_handle(content):
                        matched_parser = p
                        break
                if matched_parser is None:
                    preview = ' | '.join(content.strip().splitlines()[:3])[:120]
                    yield 'skip', fname, f"no parser matched .{ext} content (preview: {preview!r})", None, None, None
                else:
                    yield 'match', fname, None, filepath, content, matched_parser
            else:
                candidates = ext_to_parsers.get(ext, [])
                if not candidates:
                    yield 'skip', fname, f"no parser for extension '{ext}'", None, None, None
                    continue
                parser = candidates[0]
                if not parser.can_handle(content):
                    preview = ' | '.join(content.strip().splitlines()[:3])[:120]
                    yield 'skip', fname, f"parser '{parser.format}' rejected content (preview: {preview!r})", None, None, None
                else:
                    yield 'match', fname, None, filepath, content, parser


def _build_metadata_from_normalized(normalized, parsed, info, filepath):
    from app.core.utils.utils import detect_cve

    description = (
        normalized.get('description')
        or parsed.get('metadata', {}).get('description')
        or parsed.get('metadata', {}).get('details')
        or parsed.get('metadata', {}).get('reference')
        or 'No description provided'
    )
    _, cves = detect_cve(description)

    return {
        'format':          normalized.get('format', 'unknown'),
        'title':           normalized.get('title') or parsed.get('identity', {}).get('name') or 'Untitled',
        'license':         normalized.get('license') or parsed.get('metadata', {}).get('license') or info.get('license', 'unknown'),
        'description':     description,
        'version':         parsed.get('metadata', {}).get('version', '1.0'),
        'author':          normalized.get('author') or parsed.get('metadata', {}).get('author') or info.get('author', 'Unknown'),
        'original_uuid':   normalized.get('original_uuid') or parsed.get('original_uuid') or 'Unknown',
        'source':          info.get('repo_url', 'Unknown'),
        'to_string':       normalized.get('content', ''),
        'cve_id':          cves,
        'vulnerabilities': parsed.get('vulnerabilities', []),
        'github_path':     filepath,
    }


# ── Worker function — runs in a separate process, no Flask/SQLAlchemy ─────────

def _worker_parse_item(args):
    """
    Executed in a worker process via multiprocessing.Pool.
    Must be a top-level function (picklable).
    Returns a serialisable result dict — no SQLAlchemy objects.
    """
    item, info = args
    filepath  = item['filepath']
    raw_chunk = item['chunk']
    fmt       = item['format']

    try:
        from parsers.engine import RuleCastEngine
        from app.core.utils.utils import detect_cve

        engine = RuleCastEngine()
        parser = engine.get_parser(fmt)

        if parser is None:
            return {'status': 'skip', 'fmt': fmt, 'filepath': filepath,
                    'raw_chunk': raw_chunk, 'reason': 'no parser found'}

        validation = parser.validate(raw_chunk)
        parsed     = parser.parse(raw_chunk)
        normalized = parser.normalize(parsed)

        description = (
            normalized.get('description')
            or parsed.get('metadata', {}).get('description')
            or parsed.get('metadata', {}).get('details')
            or parsed.get('metadata', {}).get('reference')
            or 'No description provided'
        )
        _, cves = detect_cve(description)

        metadata = {
            'format':          normalized.get('format', 'unknown'),
            'title':           normalized.get('title') or parsed.get('identity', {}).get('name') or 'Untitled',
            'license':         normalized.get('license') or parsed.get('metadata', {}).get('license') or info.get('license', 'unknown'),
            'description':     description,
            'version':         parsed.get('metadata', {}).get('version', '1.0'),
            'author':          normalized.get('author') or parsed.get('metadata', {}).get('author') or info.get('author', 'Unknown'),
            'original_uuid':   normalized.get('original_uuid') or parsed.get('original_uuid')  or 'Unknown',
            'source':          info.get('repo_url', 'Unknown'),
            'to_string':       normalized.get('content', ''),
            'cve_id':          cves,
            'vulnerabilities': parsed.get('vulnerabilities', []),
            'github_path':     filepath,
        }

        return {
            'status':     'parsed',
            'fmt':        fmt,
            'filepath':   filepath,
            'raw_chunk':  raw_chunk,
            'validation_ok':     validation.ok,
            'validation_errors': validation.errors,
            'metadata':   metadata,
            'rule_name':  normalized.get('title') or 'unknown',
        }

    except Exception as e:
        return {'status': 'error', 'fmt': fmt, 'filepath': filepath,
                'raw_chunk': raw_chunk, 'error': str(e)}


def _parse_batch_mp(batch, info):
    """Parse a batch using a multiprocessing Pool. Returns results in order."""
    args = [(item, info) for item in batch]
    # 'spawn' context avoids fork issues with Flask/SQLAlchemy
    ctx  = mp.get_context('fork')
    with ctx.Pool(processes=PARSE_WORKERS) as pool:
        results = pool.map(_worker_parse_item, args)
    return results


def _write_results(results, user, job, start_idx, by_format):
    """Sequential DB writes. Returns (imported, bad_rules, skipped)."""
    imported  = 0
    bad_rules = 0
    skipped   = 0

    for local_idx, result in enumerate(results):
        fmt = result['fmt']
        if fmt not in by_format:
            by_format[fmt] = {'imported': 0, 'bad': 0, 'skipped': 0}

        if result['status'] == 'skip':
            skipped += 1
            by_format[fmt]['skipped'] += 1

        elif result['status'] == 'error':
            skipped += 1
            by_format[fmt]['skipped'] += 1
            log_job(job,
                f"[{fmt}] Parse error in {os.path.basename(result['filepath'])}: {result['error']}",
                level='warning', event='error')

        else:
            metadata  = result['metadata']
            rule_name = result['rule_name']
            raw_chunk = result['raw_chunk']

            if result['validation_ok']:
                try:
                    success, msg = RuleModel.add_rule_core(metadata, user)
                    if success:
                        imported += 1
                        by_format[fmt]['imported'] += 1
                        log_job(job, f"[{fmt}] Imported: {rule_name!r}", level='info', event='rule_imported')
                    else:
                        skipped += 1
                        by_format[fmt]['skipped'] += 1
                        log_job(job, f"[{fmt}] Skipped (duplicate?): {rule_name!r} — {msg}", level='info', event='rule_skipped')
                except Exception as e:
                    skipped += 1
                    by_format[fmt]['skipped'] += 1
                    log_job(job, f"[{fmt}] DB error for {rule_name!r}: {e}", level='warning', event='error')
            else:
                errors = result['validation_errors']
                log_job(job,
                    f"[{fmt}] Invalid: {rule_name!r} — {'; '.join(errors[:2])}",
                    level='warning', event='bad_rule')
                try:
                    BadRuleModel.save_invalid_rule(
                        form_dict=metadata,
                        to_string=raw_chunk,
                        rule_type=fmt,
                        error=errors,
                        user=user,
                    )
                except Exception as e:
                    log_job(job, f"[{fmt}] Failed to save bad rule: {e}", level='warning', event='error')
                bad_rules += 1
                by_format[fmt]['bad'] += 1

        job.done = start_idx + local_idx + 1
        if (local_idx + 1) % PROGRESS_INTERVAL == 0:
            db.session.commit()

    return imported, bad_rules, skipped


def _flush_batch(batch, info, user, job, batch_start, imported, bad_rules, skipped, by_format):
    results = _parse_batch_mp(batch, info)
    i_b, b_b, s_b = _write_results(results, user, job, batch_start, by_format)
    return imported + i_b, bad_rules + b_b, skipped + s_b


@register_handler('import_github_rulecast')
def handle_import_github_rulecast(job, app):
    payload  = job.payload or {}
    repo_dir = payload.get('repo_dir')
    info     = payload.get('info', {})
    user_id  = payload.get('user_id')
    offset   = payload.get('_resume_offset', 0)

    if not repo_dir or not os.path.exists(repo_dir):
        raise ValueError(f"repo_dir not found: {repo_dir!r}")

    from app.core.db_class.db import User
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found.")

    try:
        engine = _get_rulecast_engine()
    except Exception as e:
        raise RuntimeError(f"Could not load RuleCast engine: {e}")

    log_job(job,
        f"RuleCast engine loaded — parsers: "
        f"{', '.join(p['format'] for p in engine.list_parsers())} "
        f"— {PARSE_WORKERS} worker processes — batch size: {BATCH_SIZE}",
        level='info', event='started')

    # ── Phase 1: discovery ────────────────────────────────────────────────────
    if job.total == 0:
        log_job(job, f"Scanning {repo_dir} for rule files…", level='info', event='progress')

        file_count   = 0
        skip_count   = 0
        total_chunks = 0

        for status, fname, reason, filepath, content, parser in _walk_rule_files(repo_dir, engine):
            if status == 'skip':
                skip_count += 1
                log_job(job, f"Skipped {fname} — {reason}", level='warning', event='skip')
                continue
            file_count += 1
            try:
                chunks = [c for c in parser.split_rules(content) if c.strip()]
            except Exception as e:
                skip_count += 1
                log_job(job, f"Skipped {fname} [{parser.format}] — split_rules() failed: {e}", level='warning', event='skip')
                continue
            if not chunks:
                skip_count += 1
                log_job(job, f"Skipped {fname} [{parser.format}] — no rule chunks extracted", level='warning', event='skip')
                continue
            log_job(job, f"Found {fname} [{parser.format}] — {len(chunks)} rule(s)", level='info', event='progress')
            total_chunks += len(chunks)

        job.total = total_chunks
        db.session.commit()

        log_job(job,
            f"Discovery complete — {file_count} file(s) matched, "
            f"{skip_count} skipped, {job.total} rule(s) to process.",
            level='info', event='progress')

        if job.total == 0:
            log_job(job, "No rules found — nothing to import.", level='warning', event='done')
            return

    # ── Phase 2: process ──────────────────────────────────────────────────────
    global_idx = 0
    imported   = 0
    bad_rules  = 0
    skipped    = 0
    by_format  = {}
    batch      = []

    for status, fname, reason, filepath, content, parser in _walk_rule_files(repo_dir, engine):
        if status == 'skip':
            continue
        try:
            chunks = [c for c in parser.split_rules(content) if c.strip()]
        except Exception:
            continue

        for chunk in chunks:
            if global_idx < offset:
                global_idx += 1
                continue

            batch.append({'filepath': filepath, 'chunk': chunk, 'format': parser.format})
            global_idx += 1

            if len(batch) >= BATCH_SIZE:
                if _is_cancelled(job):
                    log_job(job, f"Job cancelled at {global_idx}/{job.total} — {imported} imported · {bad_rules} bad · {skipped} skipped.", level='warning', event='cancelled')
                    return
                if _should_pause(job):
                    _save_offset(job, global_idx - len(batch))
                    db.session.commit()
                    log_job(job, f"Job paused at {global_idx}/{job.total}.", level='info', event='paused')
                    return

                batch_start = global_idx - len(batch)
                imported, bad_rules, skipped = _flush_batch(
                    batch, info, user, job, batch_start,
                    imported, bad_rules, skipped, by_format
                )
                _save_offset(job, global_idx)
                db.session.commit()
                log_job(job,
                    f"Progress: {job.done}/{job.total} ({job.progress_pct}%) — "
                    f"{imported} imported · {bad_rules} bad · {skipped} skipped.",
                    level='info', event='progress')
                batch = []

    # ── Last partial batch ────────────────────────────────────────────────────
    if batch:
        if _is_cancelled(job):
            log_job(job, f"Job cancelled — {imported} imported.", level='warning', event='cancelled')
            return
        batch_start = global_idx - len(batch)
        imported, bad_rules, skipped = _flush_batch(
            batch, info, user, job, batch_start,
            imported, bad_rules, skipped, by_format
        )
        db.session.commit()

    fmt_summary = '  ·  '.join(
        f"{fmt}: {c['imported']} imported / {c['bad']} bad / {c['skipped']} skipped"
        for fmt, c in by_format.items()
    ) or 'none'

    log_job(job,
        f"Import complete — {job.total} rules processed. "
        f"{imported} imported · {bad_rules} bad rules saved · {skipped} skipped. "
        f"By format: {fmt_summary}",
        level='success', event='done')