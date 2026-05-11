"""
job_handlers_rulecast.py
Background job handler for GitHub import using RuleCast (experimental).

Registered job_type: 'import_github_rulecast'

Payload:
    repo_url   : str   — GitHub URL to clone/access
    repo_dir   : str   — local path to already-cloned repo
    license    : str   — license string
    user_id    : int   — injected server-side by the route
    info       : dict  — metadata dict (author, source, repo_url, etc.)
"""

import os
import sys
import re

from app.features.jobs.job_worker import register_handler
from app.features.jobs.job_handlers import log_job, _is_cancelled, _should_pause, _save_offset
from app import db
from app.core.db_class.db import Rule
from app.features.rule import rule_core as RuleModel
from app.features.rule.rules_core import bad_rule_core as BadRuleModel


BATCH_SIZE = 200   # rules committed per batch


def _get_rulecast_engine():
    from parsers.engine import RuleCastEngine
    return RuleCastEngine()



def _walk_rule_files(repo_dir, engine):
    """
    Walk the repo directory and yield results for every candidate file.

    Strategy:
    - For unambiguous extensions (.yar, .yara, .rules, etc.) — use can_handle()
      to confirm format, skip if no match.
    - For ambiguous extensions (.yml, .yaml) — try every parser that claims
      those extensions; use the first one whose can_handle() returns True.
      If none match, log and skip.

    Yields tuples:
        ('match', fname, None, filepath, content, parser)
        ('skip',  fname, reason, None, None, None)
    """
    # Build extension → [parsers] map
    ext_to_parsers = {}
    for p in engine.parsers:
        for ext in p.extensions:
            ext_to_parsers.setdefault(ext.lower(), []).append(p)

    # Extensions claimed by more than one parser = ambiguous
    ambiguous_exts = {ext for ext, parsers in ext_to_parsers.items() if len(parsers) > 1}
    # Also treat .yml/.yaml as always ambiguous (many tools use them)
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
                yield 'skip', fname, f"extension '{ext}' not supported (known: {sorted(known_extensions)})", None, None, None
                continue

            filepath = os.path.join(root, fname)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                yield 'skip', fname, f"could not read file: {e}", None, None, None
                continue

            if ext in ambiguous_exts:
                # Try all parsers that handle this extension
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
                # Unambiguous extension — use the single parser for it
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


def _build_metadata_from_normalized(normalized, info, filepath):
    """
    Map RuleCast normalize() output to the dict expected by add_rule_core().
    Mirrors what parse_metadata() returns in rulezet-core's format classes.
    """
    from app.core.utils.utils import detect_cve

    description = normalized.get('description') or ''
    _, cves = detect_cve(description)

    return {
        'format':        normalized.get('format', 'unknown'),
        'title':         normalized.get('title') or 'Untitled',
        'license':       normalized.get('license') or info.get('license', 'unknown'),
        'description':   description,
        'version':       normalized.get('version', '1.0'),
        'author':        normalized.get('author') or info.get('author', 'Unknown'),
        'original_uuid': normalized.get('original_uuid') or 'Unknown',
        'source':        info.get('repo_url', 'Unknown'),
        'to_string':     normalized.get('content', ''),
        'cve_id':        cves,
        'vulnerabilities': normalized.get('vulnerabilities', []),
        'github_path':   filepath,
    }


@register_handler('import_github_rulecast')
def handle_import_github_rulecast(job, app):
    """
    Import rules from a cloned GitHub repo using RuleCast parsers.

    Uses can_handle() to detect format per-file — so .yml files that are NOT
    Sigma are silently skipped instead of causing false imports.

    Progress:
        job.total  = total number of individual rules found across all files
        job.done   = rules processed so far
    Each batch commits so the UI sees live progress.
    """
    payload  = job.payload or {}
    repo_dir = payload.get('repo_dir')
    info     = payload.get('info', {})
    user_id  = payload.get('user_id')
    offset   = payload.get('_resume_offset', 0)

    if not repo_dir or not os.path.exists(repo_dir):
        raise ValueError(f"repo_dir not found: {repo_dir!r}")

    # ── Load user ─────────────────────────────────────────────────────────────
    from app.core.db_class.db import User
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found.")

    # ── Load RuleCast engine ──────────────────────────────────────────────────
    try:
        engine = _get_rulecast_engine()
    except Exception as e:
        raise RuntimeError(f"Could not load RuleCast engine: {e}")

    log_job(job,
        f"RuleCast engine loaded — parsers: "
        f"{', '.join(p['format'] for p in engine.list_parsers())}",
        level='info', event='started')

    # ── Phase 1: discover all rule chunks across all files ────────────────────
    # We need the total count before we start so the progress bar makes sense.
    if job.total == 0:
        log_job(job, f"Scanning {repo_dir} for rule files…", level='info', event='progress')

        file_count = 0
        skip_count = 0
        total_chunks = 0

        # Phase 1: count only — don't store chunks in payload (too large for DB)
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

    # ── Phase 2: process rules in order, skip already-processed by offset ────
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
            # Skip already-processed chunks (resume support)
            if global_idx < offset:
                global_idx += 1
                continue

            batch.append({'filepath': filepath, 'chunk': chunk, 'format': parser.format})
            global_idx += 1

            if len(batch) >= BATCH_SIZE:
                # Cancel / pause check
                if _is_cancelled(job):
                    log_job(job, f"Job cancelled at {global_idx}/{job.total} — {imported} imported · {bad_rules} bad · {skipped} skipped.", level='warning', event='cancelled')
                    return
                if _should_pause(job):
                    _save_offset(job, global_idx - len(batch))
                    db.session.commit()
                    log_job(job, f"Job paused at {global_idx}/{job.total}.", level='info', event='paused')
                    return

                i_b, b_b, s_b, fmt_b = _process_batch(batch, engine, info, user, job)
                imported += i_b; bad_rules += b_b; skipped += s_b
                for fmt, c in fmt_b.items():
                    by_format.setdefault(fmt, {'imported': 0, 'bad': 0, 'skipped': 0})
                    by_format[fmt]['imported'] += c['imported']
                    by_format[fmt]['bad']      += c['bad']
                    by_format[fmt]['skipped']  += c['skipped']

                job.done = global_idx
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
        i_b, b_b, s_b, fmt_b = _process_batch(batch, engine, info, user, job)
        imported += i_b; bad_rules += b_b; skipped += s_b
        job.done = global_idx
        db.session.commit()

    # ── Summary log ──────────────────────────────────────────────────────────
    fmt_summary = '  ·  '.join(
        f"{fmt}: {c['imported']} imported / {c['bad']} bad / {c['skipped']} skipped"
        for fmt, c in by_format.items()
    ) or 'none'

    log_job(job,
        f"Import complete — {job.total} rules processed. "
        f"{imported} imported · {bad_rules} bad rules saved · {skipped} skipped. "
        f"By format: {fmt_summary}",
        level='success', event='done')


def _process_batch(batch, engine, info, user, job):
    """Process a batch of rule chunks. Returns (imported, bad, skipped, by_format)."""
    imported  = 0
    bad_rules = 0
    skipped   = 0
    by_format = {}

    for item in batch:
        filepath   = item['filepath']
        raw_chunk  = item['chunk']
        fmt        = item['format']

        if fmt not in by_format:
            by_format[fmt] = {'imported': 0, 'bad': 0, 'skipped': 0}

        parser = engine.get_parser(fmt)
        if parser is None:
            skipped += 1
            by_format[fmt]['skipped'] += 1
            continue

        try:
            validation = parser.validate(raw_chunk)
            parsed     = parser.parse(raw_chunk)
            normalized = parser.normalize(parsed)
            metadata   = _build_metadata_from_normalized(normalized, info, filepath)

            if validation.ok:
                success, msg = RuleModel.add_rule_core(metadata, user)
                if success:
                    imported += 1
                    by_format[fmt]['imported'] += 1
                else:
                    # Duplicate or other skip reason
                    skipped += 1
                    by_format[fmt]['skipped'] += 1
            else:
                # Log one line per bad rule for visibility
                rule_name = normalized.get('title') or 'unknown'
                log_job(job,
                    f"Bad rule [{fmt}] {rule_name!r} — {'; '.join(validation.errors[:2])}",
                    level='warning', event='bad_rule')

                BadRuleModel.save_invalid_rule(
                    form_dict=metadata,
                    to_string=raw_chunk,
                    rule_type=fmt,
                    error=validation.errors,
                    user=user,
                )
                bad_rules += 1
                by_format[fmt]['bad'] += 1

        except Exception as e:
            skipped += 1
            by_format[fmt]['skipped'] += 1
            log_job(job,
                f"Error processing rule in {os.path.basename(filepath)}: {e}",
                level='warning', event='error')

    return imported, bad_rules, skipped, by_format