"""
notification_core.py
Business logic for the notification system.

Public surface:
  create_notification(user_id, notif_type, title, body, link, icon, ...)
  create_job_notification(job, user_id)
  update_job_notification(job)
  notify_followers_new_rule(rule, author_user_id)
  notify_rule_update_found(user_id, count, update_result_id)

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
    'new_rule':           'fa-solid fa-shield-halved',
    'rule_update_found':  'fa-solid fa-rotate',
    'job_created':        'fa-solid fa-clock',
    'job_finished':       'fa-solid fa-circle-check',
    'job_failed':         'fa-solid fa-circle-xmark',
}


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
    """Create a job_created notification for the job owner."""
    return create_notification(
        user_id    = user_id,
        notif_type = 'job_created',
        title      = f'Job started: {job.label or job.job_type}',
        body       = 'Your background job has been queued.',
        link       = '/jobs/list',
        icon       = 'fa-solid fa-clock',
        job_uuid   = job.uuid,
        job_status = 'pending',
        job_progress = 0,
    )


def update_job_notification(job):
    """
    Called when a job reaches a terminal state (done / failed / cancelled).
    Finds the matching notification and updates it in place so the bell shows
    the final result without creating a duplicate row.
    """
    try:
        notif = Notification.query.filter_by(job_uuid=job.uuid).first()
        if not notif:
            return

        final_type  = 'job_finished' if job.status == 'done' else 'job_failed'
        progress    = 100 if job.status == 'done' else (job.progress_pct or 0)

        notif.notif_type    = final_type
        notif.title         = f'Job finished: {job.label or job.job_type}'
        notif.body          = (f'Completed with status: {job.status} — {progress}%'
                               if job.status == 'done'
                               else f'Failed: {job.error or "unknown error"}')
        notif.icon          = _TYPE_ICON.get(final_type)
        notif.job_status    = job.status
        notif.job_progress  = progress
        notif.is_read       = False   # force unread so it surfaces in the bell
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[notification_core] update_job_notification error: {e}")


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

    # Active jobs (running / pending / paused) that may already be read
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

    # Merge, deduplicate by id
    seen = set()
    merged = []
    for n in (unread + active_job_notifs):
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
