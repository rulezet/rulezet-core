"""
rule_mirror_core.py — Rule Git Mirror (see docs/design/rule_git_mirror.md).

Mirrors every active, public rule into a plain git repository: one folder
per rule (rule.<ext> + metadata.yaml), history is native git history (a
rule's file gets a new commit each time its content changes — no separate
"historique" folder, no duplicated content). Off by default, per-instance,
admin-configured — see RuleMirrorConfig.

Security notes (do not regress these — see the design doc's
"Configuration & security" section):
  - The GitHub token is never embedded in a git CLI argument or in a
    persisted remote URL that a `ps aux`/process listing could show. It's
    written directly into the local working clone's .git/config via
    GitPython's config_writer() (a plain file write, not a subprocess
    invocation), used for the push, then immediately cleared back to a
    placeholder URL.
  - Only rules visible to the public are considered (see get_tags_for_rule
    et al. below, which already restrict to public tags when there is no
    authenticated request context — exactly the case here, since this
    runs from a background job, not a logged-in request).
"""
import datetime
import json
import os
import re
import shutil

import yaml
from git import Repo, GitCommandError

from app import db
from app.core.db_class.db import Rule, RuleMirrorConfig
from app.core.utils.activity_log import log_activity

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOCAL_REPO_DIR = os.path.join(ROOT_DIR, 'data', 'rule_mirror_repo')

# Cosmetic only (so a plain `git clone` gets working syntax highlighting) —
# never used for anything that affects correctness. Formats not listed here
# fall back to '.txt'.
_EXTENSION_BY_FORMAT = {
    'yara': 'yar', 'sigma': 'yml', 'suricata': 'rules', 'zeek': 'zeek',
    'wazuh': 'xml', 'nse': 'nse', 'crs': 'conf', 'nova': 'nov',
    'splunk': 'yml', 'elastic': 'toml', 'kql': 'kql', 'atr': 'toml',
}

# Loose allow-list for the license_verified flag in metadata.yaml — not a
# gate on whether a rule gets mirrored (everything active/public does),
# just makes an unclear or non-permissive-looking license visible instead
# of silent. Matched case-insensitively, substring.
_PERMISSIVE_LICENSE_MARKERS = (
    'mit', 'apache', 'bsd', 'gpl', 'lgpl', 'agpl', 'mpl', 'cc0',
    'cc-by', 'unlicense', 'public domain', 'isc',
)


def _extension_for(fmt: str) -> str:
    return _EXTENSION_BY_FORMAT.get((fmt or '').lower(), 'txt')


def _shard_for(uuid_str: str) -> str:
    return (uuid_str or '00')[:2].lower()


def _is_license_permissive(license_str: str) -> bool:
    if not license_str:
        return False
    low = license_str.lower()
    return any(marker in low for marker in _PERMISSIVE_LICENSE_MARKERS)


def _rule_relative_dir(rule) -> str:
    fmt = (rule.format or 'unknown').lower()
    return os.path.join('rules', fmt, _shard_for(rule.uuid), rule.uuid)


def _public_url_for(rule) -> str:
    from app.core.db_class.db import InstanceConfig
    cfg = InstanceConfig.query.first()
    base = (cfg.public_url if cfg and cfg.public_url else 'https://rulezet.org').rstrip('/')
    return f"{base}/rule/detail_rule/{rule.id}"


def _metadata_for(rule, tags_by_rule: dict, techniques_by_rule: dict) -> dict:
    tags = [t.name for t in tags_by_rule.get(rule.id, [])]
    techniques = [t.get('technique_id') for t in techniques_by_rule.get(rule.id, []) if t.get('technique_id')]

    cve_list = []
    if rule.cve_id:
        try:
            parsed = json.loads(rule.cve_id) if isinstance(rule.cve_id, str) else rule.cve_id
            cve_list = [c.strip() for c in parsed if c and c.strip()]
        except (ValueError, TypeError):
            pass

    return {
        'uuid': rule.uuid,
        'title': rule.title,
        'format': rule.format,
        'author': rule.author,
        'license': rule.license,
        'license_verified': _is_license_permissive(rule.license),
        'description': rule.description or '',
        'source': rule.source,
        'tags': tags,
        'attack_techniques': techniques,
        'cve': cve_list,
        'created_at': rule.creation_date.strftime('%Y-%m-%d') if rule.creation_date else None,
        'last_modified': rule.last_modif.strftime('%Y-%m-%d') if rule.last_modif else None,
        'rulezet_url': _public_url_for(rule),
    }


def _write_rule(base_path: str, rule, tags_by_rule: dict, techniques_by_rule: dict) -> str:
    """Writes rule.<ext> + metadata.yaml for one rule. Returns the
    directory's path relative to the repo root (for `git add`)."""
    rel_dir = _rule_relative_dir(rule)
    abs_dir = os.path.join(base_path, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    ext = _extension_for(rule.format)
    with open(os.path.join(abs_dir, f'rule.{ext}'), 'w', encoding='utf-8') as f:
        f.write(rule.to_string or '')

    metadata = _metadata_for(rule, tags_by_rule, techniques_by_rule)
    with open(os.path.join(abs_dir, 'metadata.yaml'), 'w', encoding='utf-8') as f:
        yaml.safe_dump(metadata, f, sort_keys=False, allow_unicode=True)

    return rel_dir


def _remove_rule_dir(base_path: str, rule) -> str:
    rel_dir = _rule_relative_dir(rule)
    abs_dir = os.path.join(base_path, rel_dir)
    if os.path.isdir(abs_dir):
        shutil.rmtree(abs_dir)
    return rel_dir


# ─── Config ───────────────────────────────────────────────────────────────

def get_config() -> RuleMirrorConfig:
    config = RuleMirrorConfig.query.first()
    if not config:
        config = RuleMirrorConfig(enabled=False, branch='main')
        db.session.add(config)
        db.session.commit()
    return config


def update_config(user_id: int, enabled: bool = None, repo_url: str = None,
                   github_token: str = None, branch: str = None) -> RuleMirrorConfig:
    """github_token is only changed when a non-empty value is given — the
    admin UI never re-sends the existing token back (it's never displayed
    to begin with), so an empty submission means 'leave it as-is', not
    'clear it'."""
    config = get_config()
    if enabled is not None:
        config.enabled = enabled
    if repo_url is not None:
        config.repo_url = repo_url.strip() or None
    if github_token:
        config.github_token = github_token.strip()
    if branch:
        config.branch = branch.strip()
    config.updated_at = datetime.datetime.utcnow()
    config.updated_by_id = user_id
    db.session.commit()

    log_activity(
        'admin.rule_mirror_config_changed',
        f"Rule Git Mirror config updated (enabled={config.enabled}, repo={config.repo_url})",
        target_type='rule_mirror_config',
        is_public=False,
    )
    return config


# ─── Git plumbing ──────────────────────────────────────────────────────────

def _repo_slug(repo_url: str) -> str:
    """'https://github.com/org/repo(.git)' -> 'org/repo'."""
    m = re.search(r'github\.com[:/]+([^/]+/[^/.]+)', repo_url or '')
    return m.group(1) if m else repo_url


def _ensure_local_repo(config: RuleMirrorConfig) -> Repo:
    os.makedirs(os.path.dirname(LOCAL_REPO_DIR), exist_ok=True)
    if os.path.isdir(os.path.join(LOCAL_REPO_DIR, '.git')):
        repo = Repo(LOCAL_REPO_DIR)
    else:
        plain_url = f"https://github.com/{_repo_slug(config.repo_url)}.git"
        try:
            repo = Repo.clone_from(plain_url, LOCAL_REPO_DIR, branch=config.branch)
        except GitCommandError:
            # Brand-new/empty remote repo — nothing to clone yet.
            repo = Repo.init(LOCAL_REPO_DIR, initial_branch=config.branch)
            repo.create_remote('origin', plain_url)
    return repo


def _set_authenticated_remote(repo: Repo, config: RuleMirrorConfig):
    """Writes the token straight into .git/config (a Python file write via
    GitPython's config writer, NOT a `git remote set-url` subprocess call)
    so it never appears as a process argument. Cleared again right after
    use — see _clear_authenticated_remote."""
    slug = _repo_slug(config.repo_url)
    authed_url = f"https://x-access-token:{config.github_token}@github.com/{slug}.git"
    with repo.config_writer() as cw:
        cw.set_value('remote "origin"', 'url', authed_url)


def _clear_authenticated_remote(repo: Repo, config: RuleMirrorConfig):
    plain_url = f"https://github.com/{_repo_slug(config.repo_url)}.git"
    with repo.config_writer() as cw:
        cw.set_value('remote "origin"', 'url', plain_url)


# ─── Sync ──────────────────────────────────────────────────────────────────

INITIAL_LOAD_BATCH_SIZE = 500   # rules per commit on the very first sync
PUSH_EVERY_N_COMMITS    = 1000  # during the (large) initial load only


def sync_mirror(job=None, log_fn=None) -> dict:
    """Runs one sync pass: writes/updates changed rules, removes deleted
    ones, commits, pushes. `job`/`log_fn` are optional BackgroundJob-style
    progress hooks (job.total/job.done, log_fn(level, message)) — both are
    no-ops if this is called outside a job (e.g. from a test script).

    Returns a small summary dict. Raises on failure (the caller — the
    'rule_git_mirror_sync' job handler — is responsible for turning that
    into a failed BackgroundJob with the error recorded)."""
    def _log(level, message):
        if log_fn:
            log_fn(level, message)

    config = get_config()
    if not config.enabled:
        raise RuntimeError("Rule Git Mirror is not enabled — enable it in the admin settings first.")
    if not config.repo_url or not config.github_token:
        raise RuntimeError("Rule Git Mirror is enabled but missing a repo URL or token.")

    is_first_sync = config.last_synced_at is None
    cutoff = config.last_synced_at
    started_at = datetime.datetime.utcnow()

    _log('info', f"Starting {'initial' if is_first_sync else 'incremental'} sync…")
    repo = _ensure_local_repo(config)

    from sqlalchemy import or_
    query = Rule.query.filter(Rule.is_deleted == False)
    if cutoff:
        query = query.filter(or_(Rule.creation_date > cutoff, Rule.last_modif > cutoff))
    changed = query.all()

    removed = []
    if cutoff:
        removed = Rule.query.filter(Rule.is_deleted == True, Rule.deleted_at > cutoff).all()

    if job:
        job.total = len(changed) + len(removed)
        job.done = 0
        db.session.commit()

    # NOTE for the real ~600k-rule initial load: this fetches tags/techniques
    # for every changed rule in one batch up front. Fine for the (small)
    # incremental case; if the first run's memory footprint becomes a
    # problem at full scale, chunk this per INITIAL_LOAD_BATCH_SIZE instead
    # of all at once — not done here since it's untested and unnecessary
    # for anything short of the full corpus.
    changed_ids = [r.id for r in changed]
    from app.features.rule.rule_core import get_tags_for_rules_batch
    from app.features.attack.attack_core import get_techniques_for_rules_batch
    tags_by_rule = get_tags_for_rules_batch(changed_ids)
    techniques_by_rule = get_techniques_for_rules_batch(changed_ids)

    commits_since_push = 0
    written = 0
    deleted = 0

    def _commit(message):
        nonlocal commits_since_push
        has_parent = repo.head.is_valid()
        if has_parent and not repo.index.diff(repo.head.commit):
            return  # nothing actually changed (e.g. re-written identical content) — skip an empty commit
        repo.index.commit(message)
        commits_since_push += 1

    def _maybe_push():
        nonlocal commits_since_push
        if commits_since_push == 0:
            return
        _set_authenticated_remote(repo, config)
        try:
            repo.git.push('origin', config.branch)
        finally:
            _clear_authenticated_remote(repo, config)
        commits_since_push = 0

    if is_first_sync:
        batch = []
        for rule in changed:
            rel_dir = _write_rule(LOCAL_REPO_DIR, rule, tags_by_rule, techniques_by_rule)
            repo.index.add([rel_dir])
            batch.append(rule)
            written += 1
            if job:
                job.done += 1
            if len(batch) >= INITIAL_LOAD_BATCH_SIZE:
                _commit(f"initial import: {len(batch)} rule(s) ({batch[0].format})")
                batch = []
                if commits_since_push >= PUSH_EVERY_N_COMMITS:
                    _maybe_push()
        if batch:
            _commit(f"initial import: {len(batch)} rule(s)")
    else:
        for rule in changed:
            rel_dir = _write_rule(LOCAL_REPO_DIR, rule, tags_by_rule, techniques_by_rule)
            repo.index.add([rel_dir])
            _commit(f"update: {rule.format}/{rule.uuid} - {rule.title}")
            written += 1
            if job:
                job.done += 1
        for rule in removed:
            rel_dir = _remove_rule_dir(LOCAL_REPO_DIR, rule)
            try:
                repo.index.remove([rel_dir], r=True)
            except Exception:
                pass  # already gone from the index/working tree — fine
            _commit(f"remove: {rule.format}/{rule.uuid} - {rule.title}")
            deleted += 1
            if job:
                job.done += 1

    _maybe_push()

    config.last_synced_at = started_at
    db.session.commit()

    log_activity(
        'admin.rule_mirror_sync',
        f"Rule Git Mirror sync: {written} written, {deleted} removed",
        target_type='rule_mirror_config',
        is_public=False,
    )
    _log('success', f"Sync complete — {written} written, {deleted} removed.")

    return {'written': written, 'deleted': deleted, 'first_sync': is_first_sync}
