"""Database backup + rotation (job db_backup_rotate, backup_rotation.py).

Runs in a temporary folder: a fake backup script writes the new dump, so no real database dump is
made and the real backup/dumps is never touched.
"""
import os
import uuid

import pytest

from app import db
from app.core.db_class.job import BackgroundJob
from app.core.db_class.notification import Notification
from app.features.admin.task_scheduler import backup_rotation as BR
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix

ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}


@pytest.fixture
def backup_root(tmp_path, monkeypatch):
    """A project-like folder: backup/scripts/backup_rulezet.sh (fake) + backup/dumps with old dumps."""
    dumps = tmp_path / "backup" / "dumps"
    scripts = tmp_path / "backup" / "scripts"
    dumps.mkdir(parents=True)
    scripts.mkdir(parents=True)
    for day in range(1, 13):                                   # 12 automatic backups
        (dumps / f"rulezet_2026-01-{day:02d}_01-00.dump").write_bytes(b"x" * 2048)
    (dumps / "old.dump").write_bytes(b"x" * 2048)              # named by hand: never rotated
    (dumps / "before-upgrade.dump").write_bytes(b"x" * 2048)
    (scripts / "backup_rulezet.sh").write_text(
        '#!/bin/bash\nf="$(dirname "$0")/../dumps/rulezet_2026-12-31_23-59.dump"\n'
        'head -c 4096 /dev/zero > "$f"\necho "Backup saved to $(realpath "$f")"\n')
    monkeypatch.chdir(tmp_path)
    return dumps


def _run(app, admin, keep="10"):
    from app.features.jobs.job_handlers import handle_db_backup_rotate
    job = BackgroundJob(uuid=uuid.uuid4().hex, created_by=admin.id, job_type="db_backup_rotate",
                        status="running", payload={"keep": keep})
    db.session.add(job)
    db.session.commit()
    handle_db_backup_rotate(job, app)
    return job


def _auto(dumps):
    return sorted(p.name for p in dumps.iterdir() if BR.ROTATED.match(p.name))


def test_keeps_the_newest_and_never_touches_hand_named_dumps(app, users, backup_root, monkeypatch):
    monkeypatch.setattr(BR, "check_dump", lambda path: None)

    job = _run(app, users.admin, keep="10")

    names = _auto(backup_root)
    assert job.status != "failed"
    assert len(names) == 10
    assert "rulezet_2026-12-31_23-59.dump" in names                  # the new one stays
    assert "rulezet_2026-01-01_01-00.dump" not in names              # the oldest went
    assert (backup_root / "old.dump").exists() and (backup_root / "before-upgrade.dump").exists()


def test_never_fewer_than_three(app, users, backup_root, monkeypatch):
    monkeypatch.setattr(BR, "check_dump", lambda path: None)

    _run(app, users.admin, keep="1")

    assert len(_auto(backup_root)) == BR.MIN_KEEP


def test_a_bad_new_backup_deletes_nothing_and_alerts_admins(app, users, backup_root, monkeypatch):
    monkeypatch.setattr(BR, "check_dump", lambda path: "pg_restore cannot read it")
    before = _auto(backup_root)

    job = _run(app, users.admin, keep="3")

    assert job.status == "failed"
    assert _auto(backup_root) == [n for n in before]                  # nothing deleted, bad file set aside
    assert (backup_root / "rulezet_2026-12-31_23-59.dump.failed").exists()
    assert Notification.query.filter_by(user_id=users.admin.id, notif_type="backup_failed").count() == 1


def test_a_failing_script_deletes_nothing(app, users, backup_root):
    (backup_root.parent / "scripts" / "backup_rulezet.sh").write_text("#!/bin/bash\necho boom >&2\nexit 3\n")
    before = _auto(backup_root)

    job = _run(app, users.admin, keep="3")

    assert job.status == "failed" and "exit 3" in job.error
    assert _auto(backup_root) == before


def test_keep_must_be_three_or_more_at_save(app):
    from app.features.admin.task_scheduler.task_scheduler_core import _validate_target_payload
    assert _validate_target_payload("db_backup_rotate", {"keep": "2"})
    assert _validate_target_payload("db_backup_rotate", {"keep": "abc"})
    assert _validate_target_payload("db_backup_rotate", {"keep": "10"}) is None


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_backup_folder_listing_is_admin_only(role, expected, clients):
    assert_outcome(clients[role].get("/admin/tasks/backups"), expected)
