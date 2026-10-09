"""
ai_request_core.py — requests for an AI analysis of a rule or a bundle.

A logged-in user who can't launch an analysis (rule: not an admin / ai.use
holder; bundle: not an admin / ai.manage holder) asks for one from the AI
Analysis section; the AI managers (admins + ai.manage) are notified and
review the requests on the Rule / Bundle Analysis admin pages. Accepting
queues the analysis — one `ai_generate` job per script for the selected
rules, one `ai_bundle_analysis` job per bundle — and tells the requesters.
"""

import datetime

from sqlalchemy import or_
from sqlalchemy.orm import aliased

from app import db
from app.core.db_class.db import (AIAnalysisRequest, Bundle, Notification, Permission, RolePermission,
                                  Rule, User, UserRole)

TARGET_TYPES = ('rule', 'bundle')
SCRIPTS = {'rule': ('standard', 'deep'), 'bundle': ('full',)}
SCRIPT_LABELS = {'standard': 'Standard analysis', 'deep': 'In-depth report', 'full': 'Full bundle review'}
STATUSES = ('pending', 'accepted', 'rejected')
MESSAGE_MAX = 1000
NOTE_MAX = 2000


def can_launch(user, target_type):
    """Who may launch the analysis directly — the others may request it."""
    if not user or not user.is_authenticated:
        return False
    if user.is_admin():
        return True
    return user.has_permission('ai.use' if target_type == 'rule' else 'ai.manage')


def _ai_manager_ids():
    """Admins and holders of ai.manage — the people who review requests."""
    ids = {u.id for u in User.query.filter_by(admin=True).all()}
    rows = (db.session.query(UserRole.user_id)
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .filter(Permission.key == 'ai.manage').all())
    ids.update(r[0] for r in rows)
    return ids


def _target(target_type, target_id):
    if target_type == 'rule':
        return Rule.query.filter(Rule.id == target_id, Rule.is_deleted == False).first()
    return db.session.get(Bundle, target_id)


def _target_filter(query, target_type, target_id):
    col = AIAnalysisRequest.rule_id if target_type == 'rule' else AIAnalysisRequest.bundle_id
    return query.filter(AIAnalysisRequest.target_type == target_type, col == target_id)


def pending_for(target_type, target_id):
    """The open requests on a rule / bundle (oldest first)."""
    q = _target_filter(AIAnalysisRequest.query, target_type, target_id).filter_by(status='pending')
    return q.order_by(AIAnalysisRequest.created_at.asc()).all()


def create_request(target_type, target_id, user, script=None, message=None):
    """Returns (ok, request or error message, created). A request for the
    same target and script already waiting is returned instead of a
    duplicate (created=False)."""
    if target_type not in TARGET_TYPES:
        return False, "Unknown target.", False
    script = script or SCRIPTS[target_type][0]
    if script not in SCRIPTS[target_type]:
        return False, f"script must be one of {', '.join(SCRIPTS[target_type])}.", False
    if message is not None and not isinstance(message, str):
        return False, "The message must be a text.", False
    message = (message or '').strip()
    if len(message) > MESSAGE_MAX:
        return False, f"The message is limited to {MESSAGE_MAX} characters.", False
    target = _target(target_type, target_id)
    if not target:
        return False, "Not found.", False

    existing = next((r for r in pending_for(target_type, target_id) if r.script == script), None)
    if existing:
        return True, existing, False

    req = AIAnalysisRequest(
        target_type=target_type, script=script, message=message or None, user_id=user.id,
        rule_id=target_id if target_type == 'rule' else None,
        bundle_id=target_id if target_type == 'bundle' else None,
    )
    db.session.add(req)
    db.session.commit()
    _notify_managers(req, target, user)
    return True, req, True


def _notify_managers(req, target, user):
    try:
        title_of = target.title if req.target_type == 'rule' else target.name
        link = f"/ai/admin/{'rule' if req.target_type == 'rule' else 'bundle'}-analysis#requests"
        body = f"{user.get_username()} asks for a {SCRIPT_LABELS[req.script].lower()}"
        if req.message:
            body += f" — {req.message[:200]}"
        now = datetime.datetime.utcnow()
        db.session.add_all([Notification(
            user_id=uid, notif_type='ai_analysis_requested',
            title=f'This {req.target_type} needs an AI analysis: "{title_of[:120]}"',
            body=body, link=link, icon='fa-solid fa-robot', is_read=False, created_at=now,
        ) for uid in _ai_manager_ids() if uid != user.id])
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ai_request_core] notify managers error: {e}")


def _notify_requester(req, accepted):
    if not req.user_id:
        return
    try:
        target = req.rule if req.target_type == 'rule' else req.bundle
        title_of = (target.title if req.target_type == 'rule' else target.name) if target else 'deleted'
        body = (f"{SCRIPT_LABELS[req.script]} queued — the report appears in the AI Analysis section once it is written."
                if accepted else "Your request was declined.")
        if req.decision_note:
            body += f" — {req.decision_note[:300]}"
        db.session.add(Notification(
            user_id=req.user_id,
            notif_type='ai_analysis_accepted' if accepted else 'ai_analysis_rejected',
            title=f'AI analysis {"accepted" if accepted else "declined"}: "{title_of[:120]}"',
            body=body, link=req.to_json()['target_url'],
            icon='fa-solid fa-wand-magic-sparkles' if accepted else 'fa-solid fa-circle-xmark',
            is_read=False, created_at=datetime.datetime.utcnow(),
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ai_request_core] notify requester error: {e}")


def _list_query(target_type, status='', q=''):
    query = AIAnalysisRequest.query.filter(AIAnalysisRequest.target_type == target_type)
    if status in STATUSES:
        query = query.filter(AIAnalysisRequest.status == status)
    if q:
        needle = f"%{q.strip()}%"
        author = aliased(User)
        query = query.outerjoin(author, AIAnalysisRequest.user_id == author.id)
        if target_type == 'rule':
            query = query.outerjoin(Rule, AIAnalysisRequest.rule_id == Rule.id)
            title_col = Rule.title
        else:
            query = query.outerjoin(Bundle, AIAnalysisRequest.bundle_id == Bundle.id)
            title_col = Bundle.name
        query = query.filter(or_(title_col.ilike(needle), AIAnalysisRequest.message.ilike(needle),
                                 (author.first_name + ' ' + author.last_name).ilike(needle)))
    return query


def list_requests(target_type, page=1, per_page=20, status='', q=''):
    per_page = min(max(per_page or 20, 1), 100)
    query = _list_query(target_type, status, q)
    counts = dict(db.session.query(AIAnalysisRequest.status, db.func.count(AIAnalysisRequest.id))
                  .filter(AIAnalysisRequest.target_type == target_type)
                  .group_by(AIAnalysisRequest.status).all())
    return (query.order_by(AIAnalysisRequest.status != 'pending', AIAnalysisRequest.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False),
            {s: counts.get(s, 0) for s in STATUSES})


def decide(target_type, action, decider, *, ids=None, all_pending=False, q='',
           model=None, default_public=True, note=None):
    """Accept or reject pending requests — the given ids, or every pending
    one matching `q`. Accepting queues the analyses. Returns (ok, message,
    {"count", "jobs": [uuid]})."""
    from app.features.jobs import jobs_core as JobsModel

    if action not in ('accept', 'reject'):
        return False, "action must be accept or reject.", {}
    note = (note or '').strip()[:NOTE_MAX] or None
    query = _list_query(target_type, 'pending', q if all_pending else '')
    if not all_pending:
        ids = [i for i in (ids or []) if isinstance(i, int)]
        if not ids:
            return False, "No request selected.", {}
        query = query.filter(AIAnalysisRequest.id.in_(ids))
    requests = query.order_by(AIAnalysisRequest.created_at.asc()).all()
    if not requests:
        return False, "No pending request found.", {}

    now = datetime.datetime.now(datetime.timezone.utc)
    jobs = []
    if action == 'accept':
        if target_type == 'rule':
            by_script = {}
            for r in requests:
                if r.rule and not r.rule.is_deleted:
                    by_script.setdefault(r.script, []).append(r)
            for script, reqs in by_script.items():
                rule_ids = sorted({r.rule_id for r in reqs})
                job = JobsModel.create_job(
                    job_type='ai_generate',
                    payload={'agent_key': 'rule_analysis', 'script': script, 'rule_ids': rule_ids,
                             'regenerate_existing': True, 'default_public': bool(default_public),
                             'model': model or None, 'batch_size': len(rule_ids),
                             'max_seconds': 300 * len(rule_ids)},
                    label=f"AI Rule Analysis{' (in-depth)' if script == 'deep' else ''} — "
                          f"{len(rule_ids)} requested rule{'s' if len(rule_ids) > 1 else ''}",
                    created_by=decider.id,
                )
                if job:
                    jobs.append(job.uuid)
                    for r in reqs:
                        r.job_uuid = job.uuid
        else:
            for bundle_id in sorted({r.bundle_id for r in requests if r.bundle}):
                bundle = db.session.get(Bundle, bundle_id)
                job = JobsModel.create_job(
                    job_type='ai_bundle_analysis',
                    payload={'bundle_id': bundle_id, 'model': model or None,
                             'default_public': bool(default_public), 'user_id': decider.id},
                    label=f"AI Bundle Analysis — {bundle.name[:60]} (requested)",
                    created_by=decider.id,
                )
                if job:
                    jobs.append(job.uuid)
                    for r in requests:
                        if r.bundle_id == bundle_id:
                            r.job_uuid = job.uuid

    decided = []
    for r in requests:
        if action == 'accept' and not r.job_uuid:
            continue          # its rule / bundle is gone, or the job could not be queued
        r.status = 'accepted' if action == 'accept' else 'rejected'
        r.decided_by_id, r.decided_at, r.decision_note = decider.id, now, note
        decided.append(r)
    db.session.commit()
    for r in decided:
        _notify_requester(r, action == 'accept')

    n = len(decided)
    if action == 'accept':
        msg = f"{n} request{'s' if n != 1 else ''} accepted — {len(jobs)} analysis job{'s' if len(jobs) != 1 else ''} queued."
    else:
        msg = f"{n} request{'s' if n != 1 else ''} rejected."
    return True, msg, {"count": n, "jobs": jobs}
