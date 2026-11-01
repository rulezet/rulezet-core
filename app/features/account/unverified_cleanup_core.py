"""
unverified_cleanup_core.py — delete the accounts whose email was never verified (sign-up bots, typos, abandoned
sign-ups). Run daily by the workflow task "Unverified accounts — clean-up" (task type purge_unverified_users,
template unverified_accounts_cleanup).

An account is deleted when:
  1. its email is not verified (User.is_verified — the email check; an admin's identity check is something else);
  2. it is a local sign-up (an OIDC / SSO account is verified by its identity provider);
  3. it is older than the grace period (default 24 h: someone who signs up at 23:50 has time to verify);
  4. at most `max_per_run` per run (default 200): more than that means something is off — nothing is deleted,
     the admins are told.
Never deleted, verified or not: admins, the system accounts (Rulezet Official, which owns the imported rules)
and the account that runs the clean-up. What a deleted account made goes to the admin (delete_user_core).
Before deletion, the activity log entries about the account (its sign-up) become private.
"""
from __future__ import annotations

import datetime

from sqlalchemy import or_

from app import db
from app.core.db_class.activity_log import ActivityLog
from app.core.db_class.user import User

def find_candidates(grace_hours: int = 24, protect_ids=()) -> dict:
    """{'delete': [User], 'kept_protected': n} — nothing is changed."""
    from app.features.account.account_core import is_protected_system_user
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=max(int(grace_hours), 1))
    q = User.query.filter(User.is_verified.isnot(True),
                          or_(User.auth_provider == 'local', User.auth_provider.is_(None)),
                          User.created_at.isnot(None), User.created_at < cutoff)
    protect = {int(i) for i in protect_ids if i}
    users, kept = [], 0
    for u in q.all():
        if u.admin or u.id in protect or is_protected_system_user(u):
            kept += 1
        else:
            users.append(u)
    return {'delete': users, 'kept_protected': kept}


def make_logs_private(user_ids: list[int]) -> int:
    """The activity log entries about these accounts (their sign-up) — not shown publicly anymore."""
    if not user_ids:
        return 0
    n = (ActivityLog.query.filter(or_(ActivityLog.user_id.in_(user_ids),
                                      (ActivityLog.target_type == 'user') & ActivityLog.target_id.in_(user_ids)))
         .update({ActivityLog.is_public: False}, synchronize_session=False))
    db.session.commit()
    return n


def purge(grace_hours: int = 24, max_per_run: int = 200, dry_run: bool = True, log=lambda m: None,
          protect_ids=()) -> dict:
    from app.features.account.account_core import delete_user_core
    found = find_candidates(grace_hours, protect_ids)
    users = found['delete']
    report = {'candidates': len(users), 'kept_protected': found['kept_protected'], 'deleted': 0, 'logs_private': 0,
              'aborted': False, 'examples': [f'#{u.id} {u.email} (signed up {u.created_at:%Y-%m-%d %H:%M})' for u in users[:15]]}
    log(f"{len(users)} account(s) with an unverified email, older than {grace_hours} h; "
        f"{found['kept_protected']} kept (admin, system account or the account running this).")
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
