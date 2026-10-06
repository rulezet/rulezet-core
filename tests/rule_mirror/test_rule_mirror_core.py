"""
Covers the hardening added for the ~600k-rule initial sync:
  - _write_rule(skip_rename_check=True) really skips the rename lookup
  - _run_initial_sync paginates by keyset (not OFFSET) and processes
    every rule exactly once across several batches
  - a pause mid-run saves a resume cursor, and a second call picks up
    from exactly there without missing or duplicating any rule
  - a cancel mid-run behaves the same way (stops, saves cursor)

These exercise the git plumbing against a real local repo (git.Repo.init
in a tmp dir) — no network, no real GitHub remote — so _maybe_push is a
no-op stand-in here; that part is unrelated to what's under test.
"""
import datetime as _dt
import uuid as _uuid

import git
import pytest

from app import db
from app.core.db_class.db import Rule
from app.features.admin.rule_mirror import rule_mirror_core as mirror


class FakeJob:
    """Minimal stand-in for a BackgroundJob — only the attributes
    _run_initial_sync actually reads/writes. Not a persisted ORM row, so
    job_handlers._reload()'s db.session.refresh() call on it silently
    no-ops (caught by that function's own broad except), which is exactly
    why a plain object works here instead of a real BackgroundJob."""
    def __init__(self, payload=None, total=0):
        self.payload = payload or {}
        self.total = total
        self.done = 0
        self.status = 'running'


def _clear_seed_rules():
    """The shared `app` fixture (conftest.py) seeds one active Rule via
    create_rule_test() — soft-delete it so _active() counts in this
    module's tests reflect only the rules each test creates itself."""
    Rule.query.update({'is_deleted': True})
    db.session.commit()


def _make_rule(title, fmt='yara', creation_date=None):
    rule = Rule(
        title=title, format=fmt, to_string=f'rule {title.replace(" ", "_")} {{ condition: true }}',
        is_deleted=False, vote_up=0, vote_down=0, source=None, author='tester',
        creation_date=creation_date or _dt.datetime.now(tz=_dt.timezone.utc),
        uuid=str(_uuid.uuid4()),
    )
    db.session.add(rule)
    db.session.commit()
    return rule


def _make_removed_rule(title, deleted_at, fmt='yara'):
    """A rule that's already soft-deleted as of creation — for exercising
    _run_incremental_sync's "removed since cutoff" phase, which looks at
    Rule.is_deleted/deleted_at directly (not _active())."""
    rule = Rule(
        title=title, format=fmt, to_string=f'rule {title.replace(" ", "_")} {{ condition: true }}',
        is_deleted=True, deleted_at=deleted_at, vote_up=0, vote_down=0, source=None, author='tester',
        creation_date=_dt.datetime.now(tz=_dt.timezone.utc),
        uuid=str(_uuid.uuid4()),
    )
    db.session.add(rule)
    db.session.commit()
    return rule


def _make_repo_env(tmp_path):
    local_dir = str(tmp_path / 'repo')
    repo = git.Repo.init(local_dir, initial_branch='main')
    # Mirrors _ensure_local_repo's repo-local identity (rule_mirror_core.py)
    # — needed since _commit below now shells out to the native `git commit`
    # CLI, which (unlike GitPython's repo.index.commit()) hard-fails with no
    # identity configured anywhere.
    with repo.config_writer() as cw:
        cw.set_value('user', 'name', 'Rulezet Mirror Sync')
        cw.set_value('user', 'email', 'noreply@rulezet-mirror.local')
    logs = []

    def _log(level, message):
        logs.append((level, message))

    def _commit(message):
        # Exact same logic as rule_mirror_core.py's real _commit closure —
        # native `git commit` (CLI), not GitPython's repo.index.commit(),
        # which rebuilds/sorts the whole index in pure Python on every call
        # (measured ~1.85s/commit at 180k tracked files vs ~240ms for the
        # CLI, at production scale that gap is what turned the incremental
        # sync's one-commit-per-rule design into a days-long run).
        if repo.head.is_valid() and not repo.index.diff(repo.head.commit):
            return
        repo.git.commit('-m', message, '--quiet')

    def _maybe_push():
        pass  # no remote configured in these tests — nothing to push to

    return repo, local_dir, logs, _log, _commit, _maybe_push


def _rule_dirs_on_disk(local_dir):
    """Every rule folder actually written under rules/manual/yara/<shard>/."""
    import os
    found = []
    rules_root = os.path.join(local_dir, 'rules')
    for root, dirs, files in os.walk(rules_root):
        if 'metadata.json' in files:
            found.append(root)
    return found


def test_write_rule_skip_rename_check_skips_the_lookup(app, monkeypatch, tmp_path):
    with app.app_context():
        _clear_seed_rules()
        rule = _make_rule('Skip Rename Check')

        def _boom(*a, **kw):
            raise AssertionError("_find_existing_rule_dir should not be called when skip_rename_check=True")
        monkeypatch.setattr(mirror, '_find_existing_rule_dir', _boom)

        # Should NOT raise — the lookup is skipped entirely.
        touched = mirror._write_rule(str(tmp_path), rule, {}, {}, skip_rename_check=True)
        assert len(touched) == 1

        # Default (skip_rename_check=False) DOES call it — proves the flag
        # is actually wired, not just a no-op parameter.
        with pytest.raises(AssertionError):
            mirror._write_rule(str(tmp_path), rule, {}, {})


def test_run_initial_sync_processes_every_rule_across_batches(app, monkeypatch, tmp_path):
    with app.app_context():
        _clear_seed_rules()
        rules = [_make_rule(f'Batch Rule {i}') for i in range(7)]
        monkeypatch.setattr(mirror, 'INITIAL_LOAD_BATCH_SIZE', 2)   # forces 4 batches for 7 rules
        monkeypatch.setattr(mirror, 'PUSH_EVERY_N_COMMITS', 1)      # push after every batch (no-op remote here)

        repo, local_dir, logs, _log, _commit, _maybe_push = _make_repo_env(tmp_path)
        job = FakeJob()

        written, interrupted = mirror._run_initial_sync(repo, local_dir, job, _log, _commit, _maybe_push)

        assert interrupted is False
        assert written == 7
        assert job.done == 7
        assert job.total == 7
        assert len(_rule_dirs_on_disk(local_dir)) == 7
        # 4 batches -> 4 "initial import" commits + no README commit here
        # (README is written by _sync_one_config, not _run_initial_sync).
        assert repo.head.is_valid()


def test_run_initial_sync_pause_then_resume_covers_every_rule_exactly_once(app, monkeypatch, tmp_path):
    with app.app_context():
        _clear_seed_rules()
        rules = [_make_rule(f'Resume Rule {i}') for i in range(6)]
        monkeypatch.setattr(mirror, 'INITIAL_LOAD_BATCH_SIZE', 2)   # 3 batches for 6 rules
        monkeypatch.setattr(mirror, 'PUSH_EVERY_N_COMMITS', 1)

        repo, local_dir, logs, _log, base_commit, _maybe_push = _make_repo_env(tmp_path)

        job = FakeJob()
        paused_after_first_batch = {'done': False}

        def _commit_then_pause(message):
            base_commit(message)
            if not paused_after_first_batch['done']:
                paused_after_first_batch['done'] = True
                job.status = 'paused'   # simulates an admin clicking Pause mid-run

        written1, interrupted1 = mirror._run_initial_sync(repo, local_dir, job, _log, _commit_then_pause, _maybe_push)

        assert interrupted1 is True
        assert written1 == 2                      # exactly one batch got through before the pause was seen
        assert job.payload.get('_resume_after_id') is not None
        assert job.payload.get('_resume_done_count') == 2
        assert len(_rule_dirs_on_disk(local_dir)) == 2

        # Resume: fresh FakeJob carrying over the saved cursor, same repo/local_dir.
        job2 = FakeJob(payload=dict(job.payload), total=job.total)
        written2, interrupted2 = mirror._run_initial_sync(repo, local_dir, job2, _log, base_commit, _maybe_push)

        assert interrupted2 is False
        assert written2 == 6                       # cumulative total returned on completion
        assert job2.done == 6
        # No duplicates, nothing skipped — exactly one folder per rule.
        assert len(_rule_dirs_on_disk(local_dir)) == 6


def test_run_initial_sync_cancel_mid_run_stops_and_saves_cursor(app, monkeypatch, tmp_path):
    with app.app_context():
        _clear_seed_rules()
        rules = [_make_rule(f'Cancel Rule {i}') for i in range(4)]
        monkeypatch.setattr(mirror, 'INITIAL_LOAD_BATCH_SIZE', 1)
        monkeypatch.setattr(mirror, 'PUSH_EVERY_N_COMMITS', 1)

        repo, local_dir, logs, _log, base_commit, _maybe_push = _make_repo_env(tmp_path)
        job = FakeJob()

        cancel_after = {'count': 0}

        def _commit_then_cancel(message):
            base_commit(message)
            cancel_after['count'] += 1
            if cancel_after['count'] == 2:
                job.status = 'cancelled'

        written, interrupted = mirror._run_initial_sync(repo, local_dir, job, _log, _commit_then_cancel, _maybe_push)

        assert interrupted is True
        assert written == 2
        assert len(_rule_dirs_on_disk(local_dir)) == 2
        assert job.payload.get('_resume_after_id') is not None


# ── _run_incremental_sync ──────────────────────────────────────────────────
# Same hardening as _run_initial_sync (keyset pagination, DB-persisted
# progress, pause/cancel/resume) but for the "delta since last sync" path,
# added after a bulk operation touching ~20k rules' last_modif at once
# turned out to break that path's old "deltas are always small" assumption —
# see rule_mirror_core.py's module-level notes. Two phases in one run
# (changed rules, then removed rules), each keyset-paginated and each rule
# still getting its own isolated git commit (unlike the initial sync, which
# batches commits — see the module docstring for why incremental can't).

def test_run_incremental_sync_processes_changed_and_removed_across_batches(app, monkeypatch, tmp_path):
    with app.app_context():
        _clear_seed_rules()
        cutoff = _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(hours=1)
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        changed = [_make_rule(f'Incr Changed {i}', creation_date=now) for i in range(5)]
        removed = [_make_removed_rule(f'Incr Removed {i}', deleted_at=now) for i in range(3)]
        monkeypatch.setattr(mirror, 'INITIAL_LOAD_BATCH_SIZE', 2)   # forces multiple batches in both phases

        repo, local_dir, logs, _log, _commit, _maybe_push = _make_repo_env(tmp_path)
        job = FakeJob()

        written, deleted, interrupted = mirror._run_incremental_sync(
            repo, local_dir, cutoff, job, _log, _commit, _maybe_push
        )

        assert interrupted is False
        assert written == 5
        assert deleted == 3
        assert job.done == 8
        assert job.total == 8
        assert len(_rule_dirs_on_disk(local_dir)) == 5
        # Commits are batched now (one per INITIAL_LOAD_BATCH_SIZE=2 batch),
        # not one per rule: 5 changed rules -> 3 batches (2+2+1) -> 3 commits.
        # The "removed" phase produces zero commits — those rules were never
        # actually mirrored in this fresh test repo, so removing them is a
        # real no-op _commit() correctly skips: nothing to un-stage.
        assert sum(1 for _ in repo.iter_commits()) == 3


def test_run_incremental_sync_pause_then_resume_covers_every_rule_once(app, monkeypatch, tmp_path):
    with app.app_context():
        _clear_seed_rules()
        cutoff = _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(hours=1)
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        changed = [_make_rule(f'Incr Resume {i}', creation_date=now) for i in range(4)]
        removed = [_make_removed_rule(f'Incr Resume Removed {i}', deleted_at=now) for i in range(2)]
        monkeypatch.setattr(mirror, 'INITIAL_LOAD_BATCH_SIZE', 1)   # pause after the very first rule

        repo, local_dir, logs, _log, base_commit, _maybe_push = _make_repo_env(tmp_path)
        job = FakeJob()
        paused = {'done': False}

        def _commit_then_pause(message):
            base_commit(message)
            if not paused['done']:
                paused['done'] = True
                job.status = 'paused'

        written1, deleted1, interrupted1 = mirror._run_incremental_sync(
            repo, local_dir, cutoff, job, _log, _commit_then_pause, _maybe_push
        )

        assert interrupted1 is True
        assert written1 == 1
        assert deleted1 == 0
        assert job.payload.get('_resume_incr_phase') == 'changed'
        assert job.payload.get('_resume_incr_after_id') is not None

        # Resume: fresh FakeJob carrying over the saved cursor, same repo/local_dir.
        job2 = FakeJob(payload=dict(job.payload), total=job.total)
        written2, deleted2, interrupted2 = mirror._run_incremental_sync(
            repo, local_dir, cutoff, job2, _log, base_commit, _maybe_push
        )

        assert interrupted2 is False
        assert written2 == 4                        # cumulative, not just this run's slice
        assert deleted2 == 2
        assert job2.done == 6
        assert len(_rule_dirs_on_disk(local_dir)) == 4
        # 4 real commits (the "removed" rules were never actually mirrored in
        # this fresh test repo, so removing them is a genuine no-op _commit()
        # correctly skips — see the batches test above for the same point).
        assert sum(1 for _ in repo.iter_commits()) == 4


def test_run_incremental_sync_cancel_mid_run_stops_and_saves_cursor(app, monkeypatch, tmp_path):
    with app.app_context():
        _clear_seed_rules()
        cutoff = _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(hours=1)
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        changed = [_make_rule(f'Incr Cancel {i}', creation_date=now) for i in range(4)]
        monkeypatch.setattr(mirror, 'INITIAL_LOAD_BATCH_SIZE', 1)

        repo, local_dir, logs, _log, base_commit, _maybe_push = _make_repo_env(tmp_path)
        job = FakeJob()
        cancel_after = {'count': 0}

        def _commit_then_cancel(message):
            base_commit(message)
            cancel_after['count'] += 1
            if cancel_after['count'] == 2:
                job.status = 'cancelled'

        written, deleted, interrupted = mirror._run_incremental_sync(
            repo, local_dir, cutoff, job, _log, _commit_then_cancel, _maybe_push
        )

        assert interrupted is True
        assert written == 2
        assert deleted == 0
        assert len(_rule_dirs_on_disk(local_dir)) == 2
        assert job.payload.get('_resume_incr_after_id') is not None


def test_commit_works_with_no_global_git_identity(app, monkeypatch, tmp_path):
    """Regression test for the native-`git commit`-CLI switch in _commit
    (see its docstring in rule_mirror_core.py): unlike GitPython's
    repo.index.commit() — which silently synthesizes an author from the OS
    user when nothing is configured — the CLI hard-fails with "Please tell
    me who you are" if no identity is set anywhere. _ensure_local_repo now
    sets a repo-local user.name/user.email specifically to cover a server
    with no global git config at all; this proves that's sufficient by
    pointing HOME at an empty directory so ~/.gitconfig can't exist."""
    empty_home = tmp_path / 'empty_home'
    empty_home.mkdir()
    monkeypatch.setenv('HOME', str(empty_home))
    for var in ('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL'):
        monkeypatch.delenv(var, raising=False)

    with app.app_context():
        _clear_seed_rules()
        rules = [_make_rule(f'NoIdentity Rule {i}') for i in range(3)]

        # _make_repo_env sets the same repo-local identity _ensure_local_repo
        # does — with HOME now pointing at an empty dir, that local config is
        # the ONLY identity available anywhere, exactly like a fresh server.
        repo, local_dir, logs, _log, _commit, _maybe_push = _make_repo_env(tmp_path)
        job = FakeJob()

        written, interrupted = mirror._run_initial_sync(repo, local_dir, job, _log, _commit, _maybe_push)

        assert interrupted is False
        assert written == 3
        assert len(_rule_dirs_on_disk(local_dir)) == 3
        assert repo.head.commit.author.email == 'noreply@rulezet-mirror.local'
