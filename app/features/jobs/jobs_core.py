"""
jobs_core.py — Business logic and DB queries for background jobs.
"""

import uuid
import datetime

from app import db
from app.core.db_class.db import BackgroundJob, BackgroundJobLog


# ─── Internal log helper ──────────────────────────────────────────────────────

def _log(job, message, level='info', event=None):
    """Write one log line for a job. Called from core actions (pause/cancel/etc.)."""
    try:
        db.session.add(BackgroundJobLog(
            job_id=job.id,
            level=level,
            event=event,
            message=message,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[jobs_core] failed to write log: {e}")


# ─── CRUD ─────────────────────────────────────────────────────────────────────

def create_job(job_type, payload, label, created_by):
    """Create a new pending job and return it."""
    try:
        job = BackgroundJob(
            uuid=str(uuid.uuid4()),
            job_type=job_type,
            status='pending',
            payload=payload,
            label=label,
            created_by=created_by,
            total=0,
            done=0,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.session.add(job)
        db.session.commit()

        _log(job,
             f"Job created and queued — waiting for worker.",
             level='info', event='queued')

        return job
    except Exception as e:
        db.session.rollback()
        print(f"[jobs_core] create_job error: {e}")
        return None


def get_job_by_uuid(job_uuid):
    """Always expire cache before reading — avoids stale 0% progress."""
    db.session.expire_all()
    return BackgroundJob.query.filter_by(uuid=job_uuid).first()


def get_jobs_for_user(user_id, args):
    query = BackgroundJob.query.filter_by(created_by=user_id)
    if args.get('status'):
        query = query.filter_by(status=args['status'])
    if args.get('job_type'):
        query = query.filter_by(job_type=args['job_type'])
    return query.order_by(BackgroundJob.created_at.desc()).limit(50).all()


def get_job_logs(job_uuid, since_id=0):
    """Return log lines for a job, optionally only those after since_id."""
    db.session.expire_all()
    job = BackgroundJob.query.filter_by(uuid=job_uuid).first()
    if not job:
        return []
    query = BackgroundJobLog.query.filter_by(job_id=job.id)
    if since_id:
        query = query.filter(BackgroundJobLog.id > since_id)
    return query.order_by(BackgroundJobLog.created_at.asc()).all()


def cancel_job(job):
    """Cancel a pending, running, or paused job."""
    if job.status not in ('pending', 'running', 'paused'):
        return False, f"Cannot cancel a job with status '{job.status}'."
    try:
        job.status      = 'cancelled'
        job.finished_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.commit()
        _log(job,
             f"Job cancelled by user at {job.progress_pct}% "
             f"({job.done}/{job.total} processed).",
             level='warning', event='cancelled')
        return True, "Job cancelled."
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def pause_job(job):
    """Pause a running or pending job."""
    if job.status not in ('pending', 'running'):
        return False, f"Cannot pause a job with status '{job.status}'."
    try:
        job.status = 'paused'
        db.session.commit()
        _log(job,
             f"Job pause requested by user at {job.progress_pct}% "
             f"({job.done}/{job.total}) — worker will stop at next batch boundary.",
             level='info', event='pause_requested')
        return True, "Job paused."
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def resume_job(job):
    """Resume a paused job."""
    if job.status != 'paused':
        return False, f"Cannot resume a job with status '{job.status}'."
    try:
        job.status     = 'pending'
        job.started_at = None
        db.session.commit()
        _log(job,
             f"Job resume requested by user — queued from offset "
             f"{job.payload.get('_resume_offset', 0) if job.payload else 0} "
             f"({job.progress_pct}% already done).",
             level='info', event='resume_requested')
        return True, "Job resumed."
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def delete_job(job):
    """Permanently delete a job and all its logs."""
    if job.status in ('pending', 'running'):
        return False, "Cannot delete a running or pending job. Cancel it first."
    try:
        db.session.delete(job)
        db.session.commit()
        return True, "Job deleted."
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def get_jobs_for_user(user_id, args):
    query = BackgroundJob.query.filter_by(created_by=user_id)
    if args.get('status'):
        query = query.filter_by(status=args['status'])
    if args.get('job_type'):
        query = query.filter_by(job_type=args['job_type'])
    if args.get('search'):
        s = f"%{args['search']}%"
        query = query.filter(BackgroundJob.label.ilike(s) | BackgroundJob.job_type.ilike(s))

    page     = int(args.get('page', 1))
    per_page = int(args.get('per_page', 20))
    total    = query.count()
    items    = query.order_by(BackgroundJob.created_at.desc())\
                    .offset((page - 1) * per_page).limit(per_page).all()
    return items, total, page, per_page


def get_zombie_jobs():
    """
    Detect jobs that are stuck and no longer being processed.
 
    A zombie is:
    - status='running' AND started more than 2 hours ago
    - status='pending' AND created more than 6 hours ago
    """
    now               = datetime.datetime.now(datetime.timezone.utc)
    threshold_running = now - datetime.timedelta(hours=2)
    threshold_pending = now - datetime.timedelta(hours=6)
    zombies           = []
 
    stuck_running = BackgroundJob.query.filter(
        BackgroundJob.status == 'running',
        BackgroundJob.started_at < threshold_running,
    ).all()
    for job in stuck_running:
        d = job.to_json()
        d['zombie_reason'] = f"Running for over 2h (started {job.started_at.strftime('%Y-%m-%d %H:%M')})"
        zombies.append(d)
 
    stuck_pending = BackgroundJob.query.filter(
        BackgroundJob.status == 'pending',
        BackgroundJob.created_at < threshold_pending,
    ).all()
    for job in stuck_pending:
        d = job.to_json()
        d['zombie_reason'] = f"Pending for over 6h (created {job.created_at.strftime('%Y-%m-%d %H:%M')})"
        zombies.append(d)
 
    return zombies
 
 
def kill_all_zombies():
    """Force all zombie jobs (stuck running >2h or pending >6h) to failed."""
    try:
        now               = datetime.datetime.now(datetime.timezone.utc)
        threshold_running = now - datetime.timedelta(hours=2)
        threshold_pending = now - datetime.timedelta(hours=6)
 
        stuck = BackgroundJob.query.filter(
            db.or_(
                db.and_(BackgroundJob.status == 'running',
                        BackgroundJob.started_at < threshold_running),
                db.and_(BackgroundJob.status == 'pending',
                        BackgroundJob.created_at < threshold_pending),
            )
        ).all()
 
        count = len(stuck)
        for job in stuck:
            reason          = 'stuck running >2h' if job.status == 'running' else 'stuck pending >6h'
            job.status      = 'failed'
            job.error       = f'Killed by admin — job was {reason}.'
            job.finished_at = now
            _log(job,
                 f"Job killed by admin ({reason}) — marked as failed.",
                 level='error', event='killed')
 
        db.session.commit()
        return True, count, f"{count} zombie job(s) killed."
    except Exception as e:
        db.session.rollback()
        return False, 0, str(e)
