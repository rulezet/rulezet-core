"""
rule_mirror_core.py — Rulesets / Rule Git Mirror (see docs/design/rule_git_mirror.md).

Mirrors every active, public rule into one or more plain git repositories:
one folder per rule (<rule-name>.<ext> + metadata.json), history is native
git history (a rule's file gets a new commit each time its content changes
— no separate "historique" folder, no duplicated content). A generated
README.md at the repo root lists every source currently mirrored (with a
link back to it) and the Rulezet version, refreshed on every sync. Off by
default, per-instance, admin-configured — an instance can run several
independent mirror targets (RuleMirrorConfig rows), each with its own
repo/branch/token.

Security notes (do not regress these — see the design doc's
"Configuration & security" section):
  - The GitHub token is never embedded in a git CLI argument or in a
    persisted remote URL that a `ps aux`/process listing could show. It's
    written directly into the local working clone's .git/config via
    GitPython's config_writer() (a plain file write, not a subprocess
    invocation), used for the push, then immediately cleared back to a
    placeholder URL.
  - Only rules visible to the public are considered. get_tags_for_rules_batch
    restricts to public tags when flask_login's current_user isn't
    authenticated — but a background job has no request context at all, so
    current_user resolves to None rather than an anonymous user. Fixed by
    calling it inside a throwaway current_app.test_request_context(), which
    is what actually makes current_user resolve to a logged-out user
    instead of crashing (see the sync loop below).
"""
import datetime
import json
import os
import re
import shutil
import uuid as uuid_mod

import requests
from git import Repo, GitCommandError

from app import db
from app.core.db_class.db import ActivityLog, Rule, RuleMirrorConfig
from app.core.utils.activity_log import log_activity

# One dirname() short of the repo root would land this under app/data/
# instead of the top-level data/ used by every other regenerable-mirror
# feature (see RULE_VALIDATION_MIRROR_DIR in job_handlers.py) — this file
# is 4 levels under app/ (features/admin/rule_mirror/rule_mirror_core.py),
# so it takes 5 dirname() calls to reach rulezet-core/, not 4.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
LOCAL_REPO_ROOT = os.path.join(ROOT_DIR, 'data', 'rule_mirror_repo')

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


def _source_slug_for(source: str) -> str:
    """Turns a rule's `source` (a GitHub repo URL for imported rules — see
    the GitHub Sources feature — or empty for hand-authored ones) into a
    safe top-level directory name, e.g. 'https://github.com/org/repo' ->
    'github.com_org_repo'. Rules with no source land under 'manual'."""
    if not source or not source.strip():
        return 'manual'
    slug = re.sub(r'^https?://', '', source.strip())
    slug = re.sub(r'[^A-Za-z0-9._-]+', '_', slug).strip('_')
    return slug.lower() or 'manual'


def _slugify(text: str, fallback: str = 'rule') -> str:
    """Filesystem-safe slug for a rule's content filename, e.g. 'Detect F5
    TMUI RCE (CVE-2020-5902)!' -> 'detect-f5-tmui-rce-cve-2020-5902'. Always
    used inside that rule's own uuid-named folder, so a collision between
    two rules sharing a title is impossible — no uniqueness suffix needed."""
    slug = re.sub(r"[^\w\s-]", '', text or '', flags=re.UNICODE).strip().lower()
    slug = re.sub(r'[\s_-]+', '-', slug).strip('-')
    return slug[:80].strip('-') or fallback


def _is_license_permissive(license_str: str) -> bool:
    if not license_str:
        return False
    low = license_str.lower()
    return any(marker in low for marker in _PERMISSIVE_LICENSE_MARKERS)


def _rule_relative_dir(rule) -> str:
    """Layout: rules/<source>/<format>/<shard>/<uuid>/ — grouped by where a
    rule came from first (there can be many different GitHub sources),
    then by format within each source."""
    source_slug = _source_slug_for(rule.source)
    fmt = (rule.format or 'unknown').lower()
    return os.path.join('rules', source_slug, fmt, _shard_for(rule.uuid), rule.uuid)


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
    """Writes <rule-name>.<ext> + metadata.json for one rule, removing any
    other file in that same folder first (an old rule.yar/metadata.yaml
    from before this layout, or a previous title's slug after a rename) —
    the folder always holds exactly one content file + metadata.json.
    Returns the rule's directory, relative to the repo root, for the
    caller to stage with `repo.git.add(rel_dir)`.

    NOTE: staging must be the `git add <path>` CLI form (repo.git.add), not
    GitPython's index.add()/index.remove() pair — index.add() on a
    directory does not pick up a file that disappeared from it, silently
    leaving a stale entry staged as an unstaged working-tree deletion (this
    is what caused the diverged-history incident on 2026-09-11: a whole
    incremental sync's renames landed in the working tree but not in any
    commit). `repo.git.add(rel_dir)` stages adds/modifies/deletes under
    that path in one atomic call."""
    rel_dir = _rule_relative_dir(rule)
    abs_dir = os.path.join(base_path, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    ext = _extension_for(rule.format)
    filename = f'{_slugify(rule.title, fallback=rule.uuid or "rule")}.{ext}'

    for existing in os.listdir(abs_dir):
        if existing not in (filename, 'metadata.json'):
            os.remove(os.path.join(abs_dir, existing))

    with open(os.path.join(abs_dir, filename), 'w', encoding='utf-8') as f:
        f.write(rule.to_string or '')

    metadata = _metadata_for(rule, tags_by_rule, techniques_by_rule)
    with open(os.path.join(abs_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        f.write('\n')

    return rel_dir


def _remove_rule_dir(base_path: str, rule) -> str:
    rel_dir = _rule_relative_dir(rule)
    abs_dir = os.path.join(base_path, rel_dir)
    if os.path.isdir(abs_dir):
        shutil.rmtree(abs_dir)
    return rel_dir


def _readme_for(config: RuleMirrorConfig) -> str:
    """Regenerated on every sync — a plain-text manifest for anyone who
    just `git clone`d this repo: what Rulezet version produced it, when it
    was last synced, and every source currently mirrored (each one linking
    straight back to it), so a browsing human doesn't need the app at all."""
    from sqlalchemy import func
    from flask import current_app

    rows = (
        db.session.query(Rule.source, func.count(Rule.id))
        .filter(Rule.is_deleted == False)
        .group_by(Rule.source)
        .order_by(func.count(Rule.id).desc())
        .all()
    )
    total = sum(count for _, count in rows)
    version = current_app.config.get('APP_VERSION', 'unknown')
    now = datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    lines = [
        f"# {config.name}",
        "",
        f"A [Rulezet](https://rulezet.org) Rulesets mirror — auto-generated by "
        f"Rulezet v{version}, do not edit by hand, this file is overwritten on every sync.",
        "",
        f"- **Rules mirrored:** {total}",
        f"- **Last synced:** {now}",
        "- **Layout:** `rules/<source>/<format>/<shard>/<rule-uuid>/<rule-name>.<ext>` "
        "+ `metadata.json` per rule",
        "",
        "## Sources",
        "",
        "| Source | Rules |",
        "|---|---:|",
    ]
    for source, count in rows:
        source = (source or '').strip()
        if source:
            label = source.rstrip('/')
            lines.append(f"| [{label}]({label}) | {count} |")
        else:
            lines.append(f"| Manual / hand-authored on Rulezet | {count} |")
    lines.append("")
    return "\n".join(lines)


# ─── Config (multiple mirror targets per instance) ─────────────────────────

def list_configs() -> list:
    return RuleMirrorConfig.query.order_by(RuleMirrorConfig.id).all()


def get_config_by_uuid(config_uuid: str):
    return RuleMirrorConfig.query.filter_by(uuid=config_uuid).first()


def create_config(user_id: int, name: str = None, enabled: bool = False, repo_url: str = None,
                   github_token: str = None, branch: str = None) -> RuleMirrorConfig:
    config = RuleMirrorConfig(
        uuid=str(uuid_mod.uuid4()),
        name=(name or '').strip() or 'Rulesets mirror',
        enabled=bool(enabled),
        repo_url=(repo_url or '').strip() or None,
        github_token=(github_token or '').strip() or None,
        branch=(branch or '').strip() or 'main',
        updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
        updated_by_id=user_id,
    )
    db.session.add(config)
    db.session.commit()

    log_activity(
        'admin.rule_mirror_config_created',
        f"Rulesets mirror config '{config.name}' created",
        target_type='rule_mirror_config',
        target_id=config.id,
        is_public=False,
    )
    return config


def update_config(config: RuleMirrorConfig, user_id: int, name: str = None, enabled: bool = None,
                   repo_url: str = None, github_token: str = None, branch: str = None) -> RuleMirrorConfig:
    """github_token is only changed when a non-empty value is given — the
    admin UI never re-sends the existing token back (it's never displayed
    to begin with), so an empty submission means 'leave it as-is', not
    'clear it'."""
    connection_changed = False

    if name is not None and name.strip():
        config.name = name.strip()
    if enabled is not None:
        config.enabled = enabled
    if repo_url is not None:
        new_repo_url = repo_url.strip() or None
        if new_repo_url != config.repo_url:
            config.repo_url = new_repo_url
            connection_changed = True
    if github_token:
        config.github_token = github_token.strip()
        connection_changed = True
    if branch and branch.strip() != config.branch:
        config.branch = branch.strip()
        connection_changed = True

    # The repo/branch/token changed — the last "Test connection" result no
    # longer reflects reality, so it must be re-tested before "Run now"
    # is allowed again (see RuleMirrorConfig.is_verified).
    if connection_changed:
        config.is_verified = False
        config.last_error = None

    config.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    config.updated_by_id = user_id
    db.session.commit()

    log_activity(
        'admin.rule_mirror_config_changed',
        f"Rulesets mirror config '{config.name}' updated (enabled={config.enabled}, repo={config.repo_url})",
        target_type='rule_mirror_config',
        target_id=config.id,
        is_public=False,
    )
    return config


def get_config_history(config: RuleMirrorConfig) -> list:
    """Last 30 activity log entries for this one config (created/updated/
    deleted, connection tests, sync triggered/done/failed) — same shape and
    source as MispServer's get_server_history, for the same per-row
    expandable timeline in the admin UI."""
    entries = (ActivityLog.query
               .filter(
                   ActivityLog.target_type == 'rule_mirror_config',
                   ActivityLog.target_id == config.id,
               )
               .order_by(ActivityLog.created_at.desc())
               .limit(30)
               .all())
    return [
        {
            'action':      e.action,
            'description': e.description,
            'timestamp':   e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else None,
            'extra':       e.extra or {},
        }
        for e in entries
    ]


def delete_config(config: RuleMirrorConfig):
    """Removes the config row and its local working clone. Never touches
    the remote GitHub repo itself — only this instance's own settings and
    local checkout of it."""
    config_id, name = config.id, config.name
    local_dir = _local_repo_dir(config)
    db.session.delete(config)
    db.session.commit()
    shutil.rmtree(local_dir, ignore_errors=True)

    log_activity(
        'admin.rule_mirror_config_deleted',
        f"Rulesets mirror config '{name}' deleted",
        target_type='rule_mirror_config',
        target_id=config_id,
        is_public=False,
    )


# ─── Git plumbing ──────────────────────────────────────────────────────────

def _local_repo_dir(config: RuleMirrorConfig) -> str:
    return os.path.join(LOCAL_REPO_ROOT, str(config.id))


def _repo_slug(repo_url: str) -> str:
    """'https://github.com/org/repo(.git)' -> 'org/repo'."""
    m = re.search(r'github\.com[:/]+([^/]+/[^/.]+)', repo_url or '')
    return m.group(1) if m else repo_url


def _ensure_local_repo(config: RuleMirrorConfig) -> Repo:
    """Ensures the local working clone exists. Deliberately does NOT clone
    anonymously (that used to be the only path here) — an anonymous clone
    silently looks "empty" for a private repo, which made this treat an
    already-populated private mirror as brand new and build a disconnected
    local history that a later push would then be rejected for. Instead:
    init once if needed, then _align_with_remote() (using the configured
    token) does the real "is there anything already there" check."""
    local_dir = _local_repo_dir(config)
    os.makedirs(os.path.dirname(local_dir), exist_ok=True)
    if os.path.isdir(os.path.join(local_dir, '.git')):
        repo = Repo(local_dir)
    else:
        plain_url = f"https://github.com/{_repo_slug(config.repo_url)}.git"
        repo = Repo.init(local_dir, initial_branch=config.branch)
        repo.create_remote('origin', plain_url)
    _align_with_remote(repo, config)
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


def _align_with_remote(repo: Repo, config: RuleMirrorConfig):
    """Fetches and merges in whatever's already on the remote branch
    before this sync writes/commits anything — the "git pull first"
    every push needs, so a remote that already has commits we don't (a
    repo GitHub itself initialized with a README, a push from elsewhere,
    or just a local clone that's fallen behind) doesn't get a rejected,
    non-fast-forward push later. A real, unresolvable conflict is raised
    rather than silently discarded either side's content."""
    _set_authenticated_remote(repo, config)
    try:
        try:
            repo.git.fetch('origin', config.branch)
        except GitCommandError:
            return  # brand-new/empty remote — nothing to align with yet

        remote_ref = f'origin/{config.branch}'
        if remote_ref not in [str(r) for r in repo.remotes.origin.refs]:
            return

        if not repo.head.is_valid():
            # Fresh local init, no commits yet — just adopt the remote branch.
            repo.git.checkout('-B', config.branch, remote_ref)
            return

        try:
            repo.git.merge(remote_ref, '--allow-unrelated-histories', '-m', 'Merge remote changes')
        except GitCommandError as e:
            raise RuntimeError(
                f"'{config.name}': remote and local mirror history diverged and "
                f"couldn't be merged automatically — resolve manually in "
                f"{_local_repo_dir(config)}: {e}"
            )
    finally:
        _clear_authenticated_remote(repo, config)


# ─── Test connection ────────────────────────────────────────────────────────

def test_config(config: RuleMirrorConfig) -> tuple:
    """Confirms the stored repo URL + token can actually authenticate and
    push to that one repository — without cloning or writing anything —
    by reading the repo's own metadata from the GitHub API and checking
    the token's reported permissions on it. Mandatory before "Run now" is
    allowed (see RuleMirrorConfig.is_verified, enforced both here and by
    the run_now route). Returns (success, message)."""
    def _fail(message: str):
        config.is_verified = False
        config.last_error = message
        config.last_tested_at = datetime.datetime.now(tz=datetime.timezone.utc)
        db.session.commit()
        log_activity(
            'admin.rule_mirror_test_failed',
            f"Rulesets connection test failed for '{config.name}': {message}",
            target_type='rule_mirror_config', target_id=config.id, is_public=False,
        )
        return False, message

    if not config.repo_url or not config.github_token:
        return _fail("Set a repository URL and token first.")

    slug = _repo_slug(config.repo_url)
    if not slug or '/' not in slug:
        return _fail("Repository URL doesn't look like a GitHub repo (expected https://github.com/org/repo).")

    try:
        resp = requests.get(
            f'https://api.github.com/repos/{slug}',
            headers={
                'Authorization': f'Bearer {config.github_token}',
                'Accept': 'application/vnd.github+json',
            },
            timeout=10,
        )
    except requests.RequestException as e:
        return _fail(f"Network error reaching GitHub: {e}")

    if resp.status_code == 401:
        return _fail("GitHub rejected the token (401 Bad credentials).")
    if resp.status_code == 404:
        return _fail(f"Repository '{slug}' not found, or the token can't see it.")
    if resp.status_code != 200:
        return _fail(f"GitHub API returned {resp.status_code}.")

    data = resp.json()
    if not (data.get('permissions') or {}).get('push'):
        return _fail("Token can see the repository but doesn't have write (push) access to it.")

    config.is_verified = True
    config.last_error = None
    config.last_tested_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    log_activity(
        'admin.rule_mirror_test_ok',
        f"Rulesets connection test passed for '{config.name}' ({slug})",
        target_type='rule_mirror_config', target_id=config.id, is_public=False,
    )
    return True, f"Connected to '{slug}' with push access."


# ─── Sync ──────────────────────────────────────────────────────────────────

INITIAL_LOAD_BATCH_SIZE = 500   # rules per commit on the very first sync
PUSH_EVERY_N_COMMITS    = 1000  # during the (large) initial load only


def sync_mirror(config_id: int = None, job=None, log_fn=None) -> dict:
    """Runs a sync pass for one config (config_id given — used by that
    config's own "Run now"/schedule) or, when config_id is omitted, for
    every currently enabled config in turn (used by a generic recurring
    Task Scheduler entry that isn't targeting one config in particular).

    Returns a small summary dict. Raises on failure (the caller — the
    'rule_git_mirror_sync' job handler — is responsible for turning that
    into a failed BackgroundJob with the error recorded)."""
    def _log(level, message):
        if log_fn:
            log_fn(level, message)

    if config_id is not None:
        config = RuleMirrorConfig.query.get(config_id)
        if not config:
            raise RuntimeError("Rulesets mirror config not found.")
        # A single explicitly-targeted config (one config's own "Run now") —
        # let a failure raise straight through, same as before.
        return _sync_one_config(config, job=job, log_fn=log_fn)

    configs = RuleMirrorConfig.query.filter_by(enabled=True).order_by(RuleMirrorConfig.id).all()
    if not configs:
        raise RuntimeError("No enabled Rulesets mirror config to sync — enable at least one first.")

    # A generic recurring sweep (no config targeted) — one config being
    # unverified/broken shouldn't stop the others from syncing.
    summaries = []
    failed = []
    for config in configs:
        _log('info', f"── {config.name} ──")
        try:
            summaries.append(_sync_one_config(config, job=job, log_fn=log_fn))
        except Exception as e:
            failed.append(config.name)
            _log('error', f"'{config.name}' skipped: {e}")
            log_activity(
                'admin.rule_mirror_sync_failed',
                f"Rulesets sync failed for '{config.name}': {e}",
                target_type='rule_mirror_config', target_id=config.id, is_public=False,
            )

    if not summaries:
        raise RuntimeError(f"All {len(configs)} enabled config(s) failed to sync — see log above.")

    return {
        'configs_synced': len(summaries),
        'configs_failed': failed,
        'written': sum(s['written'] for s in summaries),
        'deleted': sum(s['deleted'] for s in summaries),
    }


def _sync_one_config(config: RuleMirrorConfig, job=None, log_fn=None) -> dict:
    def _log(level, message):
        if log_fn:
            log_fn(level, message)

    if not config.enabled:
        raise RuntimeError(f"'{config.name}' is not enabled — enable it in the admin settings first.")
    if not config.repo_url or not config.github_token:
        raise RuntimeError(f"'{config.name}' is enabled but missing a repo URL or token.")
    if not config.is_verified:
        raise RuntimeError(f"'{config.name}' hasn't passed a connection test yet — click 'Test connection' first.")

    local_dir = _local_repo_dir(config)
    is_first_sync = config.last_synced_at is None
    cutoff = config.last_synced_at
    # now(tz=utc), not the naive utcnow() this used to be — Rule.creation_date/
    # last_modif are set with now(tz=utc) too, and psycopg2 converts an aware
    # datetime to the DB session's local timezone before storing it in this
    # timezone-less column. A naive utcnow() bypasses that conversion, so it
    # landed ~2h off from Rule's timestamps here (Europe/Luxembourg) — cutoff
    # comparisons below need the same storage convention to mean anything.
    started_at = datetime.datetime.now(tz=datetime.timezone.utc)

    _log('info', f"Starting {'initial' if is_first_sync else 'incremental'} sync for '{config.name}'…")
    repo = _ensure_local_repo(config)

    from sqlalchemy import or_
    from app.features.rule.rule_core import _active
    query = _active()
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
    # get_tags_for_rules_batch checks flask_login's current_user to decide
    # public-only vs. full visibility — outside any request (a background
    # job), that proxy resolves to None rather than an anonymous user, and
    # None.is_authenticated crashes the whole sync. A throwaway request
    # context gives flask_login a real (logged-out) current_user to check,
    # which is what actually makes this "public tags only" instead of just
    # broken.
    from flask import current_app
    with current_app.test_request_context():
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
        # Re-align with the remote right before pushing, not just once at
        # the start of the sync — covers a remote that changed *during*
        # this run (e.g. a concurrent push from elsewhere), same as the
        # alignment _ensure_local_repo already does up front.
        _align_with_remote(repo, config)
        _set_authenticated_remote(repo, config)
        try:
            repo.git.push('origin', config.branch)
        finally:
            _clear_authenticated_remote(repo, config)
        commits_since_push = 0

    def _stage_rule(rule):
        """Writes the rule and stages it — see _write_rule's docstring for
        why this must be repo.git.add (the CLI form), not index.add()."""
        rel_dir = _write_rule(local_dir, rule, tags_by_rule, techniques_by_rule)
        repo.git.add(rel_dir)

    if is_first_sync:
        batch = []
        for rule in changed:
            _stage_rule(rule)
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
            _stage_rule(rule)
            _commit(f"update: {rule.format}/{rule.uuid} - {rule.title}")
            written += 1
            if job:
                job.done += 1
        for rule in removed:
            rel_dir = _remove_rule_dir(local_dir, rule)
            try:
                repo.index.remove([rel_dir], r=True)
            except Exception:
                pass  # already gone from the index/working tree — fine
            _commit(f"remove: {rule.format}/{rule.uuid} - {rule.title}")
            deleted += 1
            if job:
                job.done += 1

    readme_path = os.path.join(local_dir, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(_readme_for(config))
    repo.git.add('README.md')
    _commit("Update README.md")

    _maybe_push()

    config.last_synced_at = started_at
    db.session.commit()

    log_activity(
        'admin.rule_mirror_sync',
        f"Rulesets mirror sync ('{config.name}'): {written} written, {deleted} removed",
        target_type='rule_mirror_config',
        target_id=config.id,
        is_public=False,
    )
    _log('success', f"'{config.name}' sync complete — {written} written, {deleted} removed.")

    return {'written': written, 'deleted': deleted, 'first_sync': is_first_sync}
