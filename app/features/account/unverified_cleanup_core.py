"""
unverified_cleanup_core.py — delete accounts that never verified their email and never used Rulezet
(sign-up bots, typos, abandoned sign-ups). Run daily by the workflow task "Unverified accounts — clean-up"
(task type purge_unverified_users, template unverified_accounts_cleanup).

Never a real user — an account is deleted only when ALL of these hold:
  1. local sign-up (an OIDC / SSO account is vouched for by its identity provider, never touched);
  2. email never verified (a local unverified account can't log in to the site at all);
  3. not an admin, no role, identity never checked by an admin, not a system account;
  4. older than the grace period (default 24 h: someone who signs up at 23:50 has time to verify);
  5. no trace of use: no row in ANY table that points to a user (rules, bundles, comments, votes,
     favorites, proposals, workspaces, API-made objects…, found from the database schema itself, so a
     table added later is covered too) — except the few filled in automatically at sign-up — and no
     activity log entry of their own other than signing up / verification attempts;
  6. at most `max_per_run` per run (default 200): more candidates than that means something is off —
     nothing is deleted, the admins are told.
Before deletion, the activity log entries about the account (its sign-up) become private.
"""
from __future__ import annotations

import datetime

from sqlalchemy import or_

from app import db
from app.core.db_class.activity_log import ActivityLog
from app.core.db_class.user import User

# Filled in automatically for every new account — no sign of use
AUTO_TABLES = {'user', 'activity_log', 'notification', 'notification_preference', 'gamification', 'user_config',
               'user_follow'}
# The account's own log entries that are not "use": signing up and trying to verify
SIGNUP_ACTIONS = {'user.register'}


def _points_to_a_user(col) -> bool:
    """A column holding a user id: a foreign key to user.id, or — several tables store it without one
    (Rule.user_id…) — an integer column named like one."""
    if any(fk.column.table.name == 'user' and fk.column.name == 'id' for fk in col.foreign_keys):
        return True
    name = col.name.lower()
    try:
        is_int = col.type.python_type is int
    except (NotImplementedError, AttributeError):
        is_int = False
    return is_int and not col.primary_key and (
        name in ('user_id', 'owner_id', 'author_id', 'created_by', 'creator_id', 'editor_id', 'uploaded_by')
        or name.endswith('_by_id') or name.endswith('_user_id'))


def _user_fk_columns():
    """(table, column) of every column holding a user id, from the SQLAlchemy metadata."""
    out = []
    for table in db.metadata.sorted_tables:
        if table.name in AUTO_TABLES:
            continue
        out += [(table, col) for col in table.columns if _points_to_a_user(col)]
    return out


def _used_ids(ids: list[int]) -> set[int]:
    """Candidates that left a trace somewhere."""
    used = set()
    if not ids:
        return used
    for table, col in _user_fk_columns():
        rows = db.session.execute(db.select(col).where(col.in_(ids)).distinct()).all()
        used.update(r[0] for r in rows if r[0] is not None)
    acted = (db.session.query(ActivityLog.user_id).filter(ActivityLog.user_id.in_(ids),
                                                           ActivityLog.action.notin_(SIGNUP_ACTIONS)).distinct())
    used.update(r[0] for r in acted)
    return used


def find_candidates(grace_hours: int = 24) -> dict:
    """{'delete': [User], 'kept_used': n, 'kept_other': n} — nothing is changed."""
    from app.core.db_class.role import UserRole
    from app.features.account.account_core import is_protected_system_user
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=max(int(grace_hours), 1))
    q = (User.query.filter(User.is_verified.isnot(True),
                           or_(User.auth_provider == 'local', User.auth_provider.is_(None)),
                           User.admin.isnot(True), User.identity_verified.isnot(True),
                           User.created_at.isnot(None), User.created_at < cutoff))
    with_role = {uid for (uid,) in db.session.query(UserRole.user_id).distinct()}
    users = [u for u in q.all() if u.id not in with_role and not is_protected_system_user(u)]
    used = _used_ids([u.id for u in users])
    return {'delete': [u for u in users if u.id not in used], 'kept_used': len([u for u in users if u.id in used])}


def make_logs_private(user_ids: list[int]) -> int:
    """The activity log entries about these accounts (their sign-up) — not shown publicly anymore."""
    if not user_ids:
        return 0
    n = (ActivityLog.query.filter(or_(ActivityLog.user_id.in_(user_ids),
                                      (ActivityLog.target_type == 'user') & ActivityLog.target_id.in_(user_ids)))
         .update({ActivityLog.is_public: False}, synchronize_session=False))
    db.session.commit()
    return n


def purge(grace_hours: int = 24, max_per_run: int = 200, dry_run: bool = True, log=lambda m: None) -> dict:
    from app.features.account.account_core import delete_user_core
    found = find_candidates(grace_hours)
    users = found['delete']
    report = {'candidates': len(users), 'kept_used': found['kept_used'], 'deleted': 0, 'logs_private': 0,
              'aborted': False, 'examples': [f'#{u.id} {u.email} (signed up {u.created_at:%Y-%m-%d %H:%M})' for u in users[:15]]}
    log(f"{len(users)} unverified, unused account(s) older than {grace_hours} h; "
        f"{found['kept_used']} unverified account(s) kept because they were used.")
    if len(users) > max_per_run:
        report['aborted'] = True
        log(f"More than {max_per_run} — nothing deleted (too many at once looks wrong). Check them, then raise "
            f"the limit or run it by hand.")
        return report
    if dry_run or not users:
        return report
    ids = [u.id for u in users]
    report['logs_private'] = make_logs_private(ids)
    for uid in ids:
        if delete_user_core(uid):
            report['deleted'] += 1
    return report
