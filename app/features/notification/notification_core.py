"""
notification_core.py
Business logic for the notification system.

Public surface:
  create_notification(user_id, notif_type, title, body, link, icon, ...)
  create_job_notification(job, user_id)       — creator + all admins
  update_job_notification(job)                — updates ALL matching notifs (creator + admins)
  notify_similarity_done(user_id, ...)        — creator done notif for similarity
  notify_followers_new_rule(rule, author_user_id)
  notify_rule_update_found(user_id, count, update_result_id)
  notify_github_import_done(user_id, imported, skipped, bad_rules, result_uuid)
  notify_github_update_done(user_id, updated, found, result_id)

  get_notifications(user_id, page, per_page, unread_only)
  get_unread_count(user_id)
  get_bell_items(user_id)   — recent unread + active job notifs for dropdown

  mark_read(notif_id, user_id)
  mark_all_read(user_id)
  delete_notification(notif_id, user_id)

  follow_user(follower_id, followed_id)
  unfollow_user(follower_id, followed_id)
  is_following(follower_id, followed_id)
  get_following(user_id)
  get_followers(user_id)
"""

import datetime

from app import db
from app.core.db_class.db import Notification, UserFollow, BackgroundJob

# ── Icons per notification type ────────────────────────────────────────────────

_TYPE_ICON = {
    'new_rule':              'fa-solid fa-shield-halved',
    'rule_update_found':     'fa-solid fa-rotate',
    'job_created':           'fa-solid fa-clock',
    'job_finished':          'fa-solid fa-circle-check',
    'job_failed':            'fa-solid fa-circle-xmark',
    'github_import_done':    'fa-brands fa-github',
    'github_update_done':    'fa-solid fa-code-branch',
    'proposal_submitted':    'fa-solid fa-code-pull-request',
    'session_running':       'fa-solid fa-spinner',
    'session_done':          'fa-solid fa-circle-check',
    'report_submitted':      'fa-solid fa-triangle-exclamation',
}


# ── Admin helpers ──────────────────────────────────────────────────────────────

def _get_all_admin_ids():
    """Return IDs of all admin users."""
    from app.core.db_class.db import User
    return [u.id for u in User.query.filter_by(admin=True).all()]


# ── Core create / update ───────────────────────────────────────────────────────

def create_notification(user_id, notif_type, title, body=None, link=None,
                        icon=None, job_uuid=None, job_status=None, job_progress=None):
    """Insert one Notification row and return it (or None on failure)."""
    try:
        notif = Notification(
            user_id      = user_id,
            notif_type   = notif_type,
            title        = title,
            body         = body,
            link         = link,
            icon         = icon or _TYPE_ICON.get(notif_type),
            job_uuid     = job_uuid,
            job_status   = job_status,
            job_progress = job_progress,
            is_read      = False,
            created_at   = datetime.datetime.utcnow(),
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] create_notification error: {e}")
        return None


def create_job_notification(job, user_id):
    """Create a job_created notification for the job owner and all admins."""
    # Notify the job creator
    create_notification(
        user_id      = user_id,
        notif_type   = 'job_created',
        title        = f'Job started: {job.label or job.job_type}',
        body         = 'Your background job has been queued.',
        link         = '/jobs/list',
        icon         = 'fa-solid fa-clock',
        job_uuid     = job.uuid,
        job_status   = 'pending',
        job_progress = 0,
    )
    # Also notify all admins (skip creator to avoid duplicate)
    try:
        admin_ids = [uid for uid in _get_all_admin_ids() if uid != user_id]
        if admin_ids:
            notifs = [
                Notification(
                    user_id      = uid,
                    notif_type   = 'job_created',
                    title        = f'Job started: {job.label or job.job_type}',
                    body         = f'Queued by user #{user_id}',
                    link         = '/jobs/list',
                    icon         = 'fa-solid fa-clock',
                    job_uuid     = job.uuid,
                    job_status   = 'pending',
                    job_progress = 0,
                    is_read      = False,
                    created_at   = datetime.datetime.utcnow(),
                )
                for uid in admin_ids
            ]
            db.session.add_all(notifs)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] create_job_notification (admins) error: {e}")


def update_job_notification(job):
    """
    Called when a job reaches a terminal state (done / failed / cancelled).
    Updates ALL matching notifications (creator + any admins) so the bell shows
    the final result without creating duplicate rows.
    """
    try:
        notifs = Notification.query.filter_by(job_uuid=job.uuid).all()
        if not notifs:
            return

        final_type = 'job_finished' if job.status == 'done' else 'job_failed'
        progress   = 100 if job.status == 'done' else (job.progress_pct or 0)
        title      = f'Job finished: {job.label or job.job_type}'
        body       = (f'Completed — {progress}%'
                      if job.status == 'done'
                      else f'Failed: {job.error or "unknown error"}')

        for notif in notifs:
            notif.notif_type    = final_type
            notif.title         = title
            notif.body          = body
            notif.icon          = _TYPE_ICON.get(final_type)
            notif.job_status    = job.status
            notif.job_progress  = progress
            notif.is_read       = False   # resurface in the bell as done
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] update_job_notification error: {e}")


def notify_similarity_done(user_id, session_uuid, total, pairs_found):
    """Notify the user who triggered a similarity analysis that it finished."""
    return create_notification(
        user_id    = user_id,
        notif_type = 'session_done',
        title      = 'Similarity analysis finished',
        body       = f'{total} rules processed · {pairs_found} similar pairs found',
        link       = f'/rule/similar_loading/{session_uuid}',
        icon       = 'fa-solid fa-code-compare',
    )


def notify_proposal_submitted(proposal, rule):
    """
    Notify the rule owner + all admins when a new edit proposal is submitted.
    Skips the submitter (they don't need to notify themselves).
    """
    try:
        from app.core.db_class.db import User
        submitter = User.query.get(proposal.user_id)
        submitter_name = submitter.get_username() if submitter else 'Someone'

        recipients = set(_get_all_admin_ids())
        if rule.user_id:
            recipients.add(rule.user_id)
        recipients.discard(proposal.user_id)  # don't notify the submitter

        if not recipients:
            return

        notifs = []
        for uid in recipients:
            notifs.append(Notification(
                user_id    = uid,
                notif_type = 'proposal_submitted',
                title      = f'New proposal on "{rule.title}"',
                body       = f'{submitter_name} suggested an edit — review it now.',
                link       = f'/rule/proposal_content_discuss?id={proposal.id}',
                icon       = _TYPE_ICON['proposal_submitted'],
                is_read    = False,
                created_at = datetime.datetime.utcnow(),
            ))
        db.session.add_all(notifs)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] notify_proposal_submitted error: {e}")


def notify_admins_report_created(report, rule, reporter):
    """
    Notify all admins when a new rule report is submitted (first report only,
    de-duplicated at the callsite with is_new=True).
    """
    try:
        admin_ids = _get_all_admin_ids()
        if not admin_ids:
            return

        reporter_name = reporter.get_username() if reporter else 'Someone'
        rule_title = rule.title if rule else f'rule #{report.rule_id}'

        notifs = []
        for uid in admin_ids:
            notifs.append(Notification(
                user_id    = uid,
                notif_type = 'report_submitted',
                title      = f'Rule reported: "{rule_title}"',
                body       = f'{reporter_name} submitted a report — reason: {report.reason or "unspecified"}',
                link       = '/rule/admin/rules_reported',
                icon       = _TYPE_ICON['report_submitted'],
                is_read    = False,
                created_at = datetime.datetime.utcnow(),
            ))
        db.session.add_all(notifs)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] notify_admins_report_created error: {e}")


def notify_admins_session_started(user, session_type, session_uuid, label, link):
    """
    Notify all admins (and the triggering user) that a long-running session
    (import / update / similarity) has started.
    The notification stays visible in the bell while job_status='running',
    which keeps the bell polling so the completion toast always fires.
    """
    try:
        admin_ids = set(_get_all_admin_ids())
        # Always include the triggering user so their bell keeps polling
        # even if they are not an admin — this is the key invariant that
        # allows update_admin_session_notifications() to later fire a toast
        # for the session owner regardless of their role.
        if user and getattr(user, 'id', None):
            admin_ids.add(user.id)
        if not admin_ids:
            return

        _icons = {
            'github_import': 'fa-brands fa-github',
            'github_update': 'fa-solid fa-code-branch',
            'similarity':    'fa-solid fa-code-compare',
        }
        icon = _icons.get(session_type, _TYPE_ICON['session_running'])
        username = user.get_username() if user else 'Someone'

        notifs = []
        for uid in admin_ids:
            notifs.append(Notification(
                user_id      = uid,
                notif_type   = 'session_running',
                title        = label,
                body         = f'Started by {username}',
                link         = link,
                icon         = icon,
                job_uuid     = session_uuid,
                job_status   = 'running',
                job_progress = 0,
                is_read      = False,
                created_at   = datetime.datetime.utcnow(),
            ))
        db.session.add_all(notifs)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] notify_admins_session_started error: {e}")


def update_admin_session_notifications(session_uuid, summary, link=None):
    """
    Called when a session finishes. Finds all session_running notifications
    for this session UUID and marks them done with the final summary.
    Pass `link` to redirect the user to the specific results page.
    """
    try:
        notifs = Notification.query.filter_by(job_uuid=session_uuid, notif_type='session_running').all()
        for n in notifs:
            n.notif_type   = 'session_done'
            n.title        = n.title.replace(' running', ' done').replace('Running', 'Done')
            n.body         = summary
            n.job_status   = 'done'
            n.job_progress = 100
            n.is_read      = False   # resurface in the bell as "done"
            n.icon         = _TYPE_ICON['session_done']
            if link:
                n.link = link
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] update_admin_session_notifications error: {e}")


def notify_followers_new_rule(rule, author_user_id):
    """Notify every follower of author_user_id that a new rule was created."""
    try:
        follows = UserFollow.query.filter_by(followed_id=author_user_id).all()
        if not follows:
            return

        from app.core.db_class.db import User
        author = User.query.get(author_user_id)
        author_name = author.get_username() if author else 'Someone'

        notifs = []
        for follow in follows:
            notifs.append(Notification(
                user_id    = follow.follower_id,
                notif_type = 'new_rule',
                title      = f'New rule by {author_name}',
                body       = rule.title,
                link       = f'/rule/detail_rule/{rule.id}',
                icon       = _TYPE_ICON['new_rule'],
                is_read    = False,
                created_at = datetime.datetime.utcnow(),
            ))
        db.session.add_all(notifs)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] notify_followers_new_rule error: {e}")


def notify_rule_update_found(user_id, count, update_result_id=None):
    """Create a rule_update_found notification for a user."""
    link = '/rule/github/update_github/update_rules_from_github'
    if update_result_id:
        link += f'?result_id={update_result_id}'
    return create_notification(
        user_id    = user_id,
        notif_type = 'rule_update_found',
        title      = f'{count} rule update{"s" if count > 1 else ""} available',
        body       = 'New versions detected for your imported GitHub rules.',
        link       = link,
        icon       = _TYPE_ICON['rule_update_found'],
    )


def notify_github_import_done(user_id, imported, skipped, bad_rules, result_uuid=None):
    """Notification sent when a GitHub / ZIP import session finishes."""
    total = imported + skipped + bad_rules
    link = f'/rule/import_history?uuid={result_uuid}' if result_uuid else '/rule/import_history'
    return create_notification(
        user_id    = user_id,
        notif_type = 'github_import_done',
        title      = f'Import finished — {imported} rule{"s" if imported != 1 else ""} imported',
        body       = f'{imported} imported · {skipped} skipped · {bad_rules} invalid (total {total})',
        link       = link,
        icon       = _TYPE_ICON['github_import_done'],
    )


def notify_github_update_done(user_id, updated, found, result_id=None):
    """Notification sent when a GitHub update check session finishes."""
    link = '/rule/github/update_github/update_rules_from_github'
    if result_id:
        link += f'?result_id={result_id}'
    if updated:
        title = f'{updated} rule update{"s" if updated != 1 else ""} available'
    else:
        title = 'Update check finished — rules are up to date'
    return create_notification(
        user_id    = user_id,
        notif_type = 'github_update_done',
        title      = title,
        body       = f'{found} rule{"s" if found != 1 else ""} checked · {updated} update{"s" if updated != 1 else ""} found',
        link       = link,
        icon       = _TYPE_ICON['github_update_done'],
    )


# ── Read / fetch ───────────────────────────────────────────────────────────────

def get_notifications(user_id, page=1, per_page=20, unread_only=False, notif_type=None):
    q = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        q = q.filter_by(is_read=False)
    if notif_type:
        q = q.filter_by(notif_type=notif_type)
    return q.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)


def get_unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def get_bell_items(user_id, limit=15):
    """
    Items to show in the bell dropdown:
      - Unread notifications (all types)
      - Active job notifications (job still running) even if read
    Deduplicated and sorted newest first, capped at `limit`.
    """
    # Unread
    unread = (Notification.query
              .filter_by(user_id=user_id, is_read=False)
              .order_by(Notification.created_at.desc())
              .limit(limit)
              .all())

    # Active BackgroundJobs (running / pending / paused) that may already be read
    active_job_uuids = [
        j.uuid for j in BackgroundJob.query
        .filter(BackgroundJob.status.in_(['pending', 'running', 'paused']))
        .filter_by(created_by=user_id)
        .all()
    ]
    active_job_notifs = []
    if active_job_uuids:
        active_job_notifs = (Notification.query
                             .filter(Notification.user_id == user_id,
                                     Notification.is_read == True,
                                     Notification.job_uuid.in_(active_job_uuids))
                             .order_by(Notification.created_at.desc())
                             .all())

    # Active thread-based sessions (import/update/similarity) that may already be read
    active_session_notifs = (Notification.query
                             .filter(Notification.user_id == user_id,
                                     Notification.is_read == True,
                                     Notification.notif_type == 'session_running',
                                     Notification.job_status.in_(['running', 'pending']))
                             .order_by(Notification.created_at.desc())
                             .all())

    # Merge, deduplicate by id
    seen = set()
    merged = []
    for n in (unread + active_job_notifs + active_session_notifs):
        if n.id not in seen:
            seen.add(n.id)
            merged.append(n)

    merged.sort(key=lambda n: n.created_at, reverse=True)
    return merged[:limit]


# ── Mutations ──────────────────────────────────────────────────────────────────

def mark_read(notif_id, user_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if not notif:
        return False
    try:
        notif.is_read = True
        notif.read_at = datetime.datetime.utcnow()
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] mark_read error: {e}")
        return False


def mark_all_read(user_id):
    try:
        Notification.query.filter_by(user_id=user_id, is_read=False).update({
            'is_read': True,
            'read_at': datetime.datetime.utcnow(),
        })
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] mark_all_read error: {e}")
        return False


def delete_notification(notif_id, user_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if not notif:
        return False
    try:
        db.session.delete(notif)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] delete_notification error: {e}")
        return False


# ── Follow / Unfollow ──────────────────────────────────────────────────────────

def follow_user(follower_id, followed_id):
    if follower_id == followed_id:
        return False, 'Cannot follow yourself'
    existing = UserFollow.query.filter_by(follower_id=follower_id, followed_id=followed_id).first()
    if existing:
        return True, 'Already following'
    try:
        db.session.add(UserFollow(follower_id=follower_id, followed_id=followed_id))
        db.session.commit()
        return True, 'Following'
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] follow_user error: {e}")
        return False, str(e)


def unfollow_user(follower_id, followed_id):
    follow = UserFollow.query.filter_by(follower_id=follower_id, followed_id=followed_id).first()
    if not follow:
        return True, 'Not following'
    try:
        db.session.delete(follow)
        db.session.commit()
        return True, 'Unfollowed'
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] unfollow_user error: {e}")
        return False, str(e)


def is_following(follower_id, followed_id):
    return UserFollow.query.filter_by(follower_id=follower_id, followed_id=followed_id).first() is not None


def get_following(user_id):
    follows = UserFollow.query.filter_by(follower_id=user_id).all()
    return [f.followed_id for f in follows]


def get_followers(user_id):
    follows = UserFollow.query.filter_by(followed_id=user_id).all()
    return [f.follower_id for f in follows]


def get_follower_count(user_id):
    return UserFollow.query.filter_by(followed_id=user_id).count()


def get_following_count(user_id):
    return UserFollow.query.filter_by(follower_id=user_id).count()
