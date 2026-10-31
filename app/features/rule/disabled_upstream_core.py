"""
disabled_upstream_core.py — Suricata / Sagan rules that are commented out ("# alert …") where they come
from, but were imported as active rules (issue #62).

Rulesets such as ET Open ship thousands of rules disabled on purpose (expensive, policy-specific, false
positive prone) — consumers enable them knowingly. Since 2026-10-06 the importers skip them; this finds
the ones imported before, so they can go to the trash (restorable, one batch):

  - rules from a git repository: their file is read again in the local clone (Rules_Github cache);
    a rule is disabled upstream when its sid appears there only commented out;
  - rules from an upload (ZIP, file — no file to read again): compared with reference rulesets
    (default: ET Open's emerging-all.rules); a rule matches when its sid AND its msg appear there only
    commented out — the msg as well, so a community rule reusing a sid number is never touched.

find_disabled_upstream() only reads; the job (job_handlers.disabled_upstream_rules) trashes on request.
"""
from __future__ import annotations

import os
import re

from sqlalchemy import func

from app.core.db_class.rule import Rule
from app.features.rule.rule_core import _active

FORMATS = ('suricata', 'sagan')
ET_OPEN_URL = 'https://rules.emergingthreats.net/open/suricata-7.0/emerging-all.rules'
_SID = re.compile(r'\bsid\s*:\s*(\d+)')
_MSG = re.compile(r'\bmsg\s*:\s*"((?:[^"\\]|\\.)*)"')
MAX_REFERENCE_BYTES = 120 * 1024 * 1024


def _sid(text):
    m = _SID.search(text or '')
    return int(m.group(1)) if m else None


def _norm_msg(msg):
    """A msg without its ruleset category: ET moves rules between categories over time
    ("ET INFO SSN Detected…" became "ET POLICY SSN Detected…") — the rest of the msg stays."""
    msg = (msg or '').strip()
    m = re.match(r'^(ET|ETPRO|GPL)\s+[A-Z_\-]+\s+(.*)$', msg)
    return (m.group(2) if m else msg).strip().lower()


def _msg(text):
    m = _MSG.search(text or '')
    return _norm_msg(m.group(1)) if m else None


def _states(content: str) -> dict:
    """{sid: {'enabled': bool, 'disabled': bool, 'msgs': set}} of one rules file."""
    from suricataparser import parse_rules
    out = {}
    for r in parse_rules(content or ''):
        if r.sid is None:
            continue
        s = out.setdefault(int(r.sid), {'enabled': False, 'disabled': False, 'msgs': set()})
        s['enabled' if r.enabled else 'disabled'] = True
        if r.msg:
            s['msgs'].add(_norm_msg(r.msg))
    return out


def _only_disabled(state) -> bool:
    return bool(state and state['disabled'] and not state['enabled'])


def load_reference(url: str, timeout: int = 120) -> dict:
    """Disabled sids of a reference ruleset: {sid: {msgs}} (only the sids never enabled there)."""
    import requests
    resp = requests.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()
    chunks, size = [], 0
    for chunk in resp.iter_content(1 << 20):
        size += len(chunk)
        if size > MAX_REFERENCE_BYTES:
            raise ValueError(f'{url} is larger than {MAX_REFERENCE_BYTES // (1 << 20)} MB')
        chunks.append(chunk)
    states = _states(b''.join(chunks).decode('utf-8', 'replace'))
    return {sid: s['msgs'] for sid, s in states.items() if _only_disabled(s)}


def _repo_file(source: str, branch: str | None, path: str) -> str | None:
    """Text of a rule's file in the local clone (cloned if missing), or None."""
    from app.features.rule.rule_format.utils_format.utils_import_update import clone_or_access_repo
    try:
        repo_dir = clone_or_access_repo(source, branch=branch, refresh=False)
        repo_dir = repo_dir[0] if isinstance(repo_dir, tuple) else repo_dir
    except Exception:
        return None
    full = os.path.realpath(os.path.join(repo_dir, path))
    if not full.startswith(os.path.realpath(repo_dir) + os.sep) or not os.path.isfile(full) or os.path.islink(full):
        return None
    try:
        with open(full, encoding='utf-8', errors='replace') as f:
            return f.read()
    except OSError:
        return None


def find_disabled_upstream(formats=FORMATS, source: str | None = None, reference_urls=(ET_OPEN_URL,),
                           log=lambda msg: None) -> dict:
    """{'git': [rule ids], 'reference': [rule ids], 'checked': n, 'unreadable_files': n, 'examples': [...]}."""
    base = _active().filter(func.lower(Rule.format).in_([f.lower() for f in formats]))
    if source:
        base = base.filter(Rule.source == source)
    found_git, found_ref, examples = [], [], []
    checked = unreadable = 0

    # 1. rules from a git repository: read their file again
    git_rules = (base.filter(Rule.github_path.isnot(None), Rule.source.ilike('http%'))
                 .with_entities(Rule.id, Rule.source, Rule.branch, Rule.github_path, Rule.to_string, Rule.title).all())
    by_file = {}
    for row in git_rules:
        by_file.setdefault((row.source, row.branch, row.github_path), []).append(row)
    log(f'{len(git_rules)} rule(s) from {len(by_file)} file(s) of git repositories')
    for (src, branch, path), rows in by_file.items():
        content = _repo_file(src, branch, path)
        if content is None:
            unreadable += 1
            continue
        states = _states(content)
        for row in rows:
            checked += 1
            if _only_disabled(states.get(_sid(row.to_string))):
                found_git.append(row.id)
                if len(examples) < 20:
                    examples.append(f'{row.title} — {src} {path}')

    # 2. uploaded rules (no file to read again): reference rulesets, sid + msg
    refs = {}
    for url in [u for u in (reference_urls or []) if u]:
        try:
            ref = load_reference(url)
            log(f'Reference {url}: {len(ref)} rule(s) commented out')
            for sid, msgs in ref.items():
                refs.setdefault(sid, set()).update(msgs)
        except Exception as e:
            log(f'Reference {url} could not be read: {e}')
    if refs:
        uploaded = (base.filter((Rule.github_path.is_(None)) | (~Rule.source.ilike('http%')) | Rule.source.is_(None))
                    .with_entities(Rule.id, Rule.to_string, Rule.title, Rule.source))
        for row in uploaded.yield_per(2000):
            checked += 1
            sid = _sid(row.to_string)
            if sid in refs and _msg(row.to_string) in refs[sid]:
                found_ref.append(row.id)
                if len(examples) < 20:
                    examples.append(f'{row.title} — {row.source or "upload"} (sid {sid})')
    return {'git': found_git, 'reference': found_ref, 'checked': checked,
            'unreadable_files': unreadable, 'examples': examples}
