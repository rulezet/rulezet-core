import datetime

from app import db
from app.core.db_class.db import Report, User

VALID_TYPES   = {'rule', 'bundle', 'comment'}
VALID_REASONS = [
    'Plagiarism',
    'Malicious content',
    'Incorrect or misleading',
    'Inappropriate content',
    'Spam',
    'Other',
]


def create_report(user_id, object_type, object_id, reason, message=''):
    """Create a new report. Returns (report, is_new).
    is_new=False when an identical report from the same user already exists."""
    if object_type not in VALID_TYPES:
        raise ValueError(f'Invalid object_type: {object_type}')

    existing = Report.query.filter_by(
        user_id=user_id,
        object_type=object_type,
        object_id=object_id,
        reason=reason,
        message=message,
    ).first()

    if existing:
        return existing, False

    report = Report(
        user_id=user_id,
        object_type=object_type,
        object_id=object_id,
        reason=reason,
        message=message or None,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        status='pending',
    )
    db.session.add(report)
    db.session.commit()
    return report, True


def _legacy_to_dict(r):
    """Convert a RepportRule row to the same dict shape as Report.to_json()."""
    reporter  = r.user
    rule      = r.rule
    rule_url  = f'/rule/detail_rule/{r.rule_id}' if rule else None
    return {
        'id':            f'legacy-{r.id}',
        'user_id':       r.user_id,
        'reporter_name': reporter.get_username() if reporter else '?',
        'user_avatar':   reporter.get_avatar_url() if reporter else None,
        'object_type':   'rule',
        'object_id':     r.rule_id,
        'object_label':  rule.title if rule else f'Rule #{r.rule_id}',
        'object_url':    rule_url,
        'reason':        r.reason or '',
        'message':       r.message,
        'created_at':    r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else None,
        'status':            'pending',   # RepportRule has no status field
        'checked_by_id':     None,
        'checked_by_name':   None,
        'checked_by_avatar': None,
        'checked_at':        None,
        'is_legacy':         True,
    }


class _Page:
    """Simple pagination container (duck-types Flask-SQLAlchemy Pagination)."""
    def __init__(self, items, total, page, per_page):
        self.items    = items
        self.total    = total
        self.page     = page
        self.per_page = per_page
        self.pages    = max(1, -(-total // per_page))  # ceiling division


def get_combined_page(page, per_page=20, object_type=None, status=None, search=None,
                      sort='created_at', direction='desc'):
    """Query both Report and RepportRule, merge, sort and paginate."""
    from app.core.db_class.db import RepportRule, Rule

    # ── Report rows ──────────────────────────────────────────────────────────
    q = Report.query
    if object_type:
        q = q.filter(Report.object_type == object_type)
    if status:
        q = q.filter(Report.status == status)
    if search:
        q = q.join(Report.user).filter(
            db.or_(
                User.first_name.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%'),
                Report.reason.ilike(f'%{search}%'),
                Report.message.ilike(f'%{search}%'),
            )
        )
    new_rows = [r.to_json() for r in q.all()]

    # ── Legacy RepportRule rows (only when type filter is 'rule' or unset) ───
    legacy_rows = []
    if not object_type or object_type == 'rule':
        # RepportRule has no status; only include when not filtering by a
        # specific status OR when filtering for 'pending' (they're all pending).
        if not status or status == 'pending':
            lq = RepportRule.query
            if search:
                lq = lq.join(RepportRule.rule, isouter=True) \
                        .join(RepportRule.user, isouter=True)
                lq = lq.filter(
                    db.or_(
                        User.first_name.ilike(f'%{search}%'),
                        Rule.title.ilike(f'%{search}%'),
                        RepportRule.reason.ilike(f'%{search}%'),
                        RepportRule.message.ilike(f'%{search}%'),
                    )
                )
            # Exclude rule IDs already present in Report to avoid duplicates
            existing_rule_ids = {
                r['object_id'] for r in new_rows if r['object_type'] == 'rule'
            }
            legacy_rows = [
                _legacy_to_dict(r) for r in lq.all()
                if r.rule_id not in existing_rule_ids
            ]

    # ── Merge, sort, paginate ─────────────────────────────────────────────────
    all_rows = new_rows + legacy_rows
    reverse  = (direction == 'desc')

    def _sort_key(item):
        v = item.get(sort) or item.get('created_at') or ''
        return v

    all_rows.sort(key=_sort_key, reverse=reverse)

    total  = len(all_rows)
    start  = (page - 1) * per_page
    items  = all_rows[start: start + per_page]

    return _Page(items, total, page, per_page)


def get_report_by_id(report_id):
    return Report.query.get(report_id)


def delete_report(report_id):
    r = get_report_by_id(report_id)
    if not r:
        return False
    db.session.delete(r)
    db.session.commit()
    return True


def delete_legacy_report(legacy_id):
    from app.core.db_class.db import RepportRule
    r = RepportRule.query.get(legacy_id)
    if not r:
        return False
    db.session.delete(r)
    db.session.commit()
    return True


def resolve_report(report_id):
    r = get_report_by_id(report_id)
    if not r:
        return False
    r.status = 'resolved'
    db.session.commit()
    return True


def dismiss_report(report_id):
    r = get_report_by_id(report_id)
    if not r:
        return False
    r.status = 'dismissed'
    db.session.commit()
    return True


def bulk_delete_reports(report_ids):
    """Accept a mix of plain int IDs (Report) and 'legacy-<n>' IDs (RepportRule)."""
    from app.core.db_class.db import RepportRule
    new_ids    = []
    legacy_ids = []
    for rid in report_ids:
        s = str(rid)
        if s.startswith('legacy-'):
            legacy_ids.append(int(s[7:]))
        else:
            new_ids.append(int(rid))
    if new_ids:
        Report.query.filter(Report.id.in_(new_ids)).delete(synchronize_session=False)
    if legacy_ids:
        RepportRule.query.filter(RepportRule.id.in_(legacy_ids)).delete(synchronize_session=False)
    db.session.commit()


def bulk_resolve_reports(report_ids):
    new_ids = [int(r) for r in report_ids if not str(r).startswith('legacy-')]
    if new_ids:
        Report.query.filter(Report.id.in_(new_ids)).update(
            {'status': 'resolved'}, synchronize_session=False
        )
        db.session.commit()


def bulk_dismiss_reports(report_ids):
    new_ids = [int(r) for r in report_ids if not str(r).startswith('legacy-')]
    if new_ids:
        Report.query.filter(Report.id.in_(new_ids)).update(
            {'status': 'dismissed'}, synchronize_session=False
        )
        db.session.commit()


def count_pending():
    from app.core.db_class.db import RepportRule
    new_count    = Report.query.filter_by(status='pending').count()
    legacy_count = RepportRule.query.count()
    return new_count + legacy_count


def notify_admins(report, reporter):
    """Send an in-app notification to all admins for a new report."""
    try:
        import datetime as _dt
        from app.core.db_class.db import Notification
        from app.features.notification.notification_core import _get_all_admin_ids
        admin_ids = _get_all_admin_ids()
        if not admin_ids:
            return
        reporter_name = reporter.get_username() if reporter else 'Someone'
        label = report.get_object_label()
        notifs = [
            Notification(
                user_id    = uid,
                notif_type = 'report_submitted',
                title      = f'{report.object_type.capitalize()} reported: "{label}"',
                body       = f'{reporter_name} — reason: {report.reason}',
                link       = '/report/admin',
                icon       = 'fa-solid fa-triangle-exclamation',
                is_read    = False,
                created_at = _dt.datetime.utcnow(),
            )
            for uid in admin_ids
        ]
        db.session.add_all(notifs)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'[report] notify_admins error: {e}')


def check_report(report_id, user_id):
    import datetime as _dt
    r = get_report_by_id(report_id)
    if not r:
        return False
    r.status = 'checked'
    r.checked_by_id = user_id
    r.checked_at = _dt.datetime.now(_dt.timezone.utc)
    db.session.commit()
    return True


def uncheck_report(report_id):
    """Revert a checked report back to pending."""
    r = get_report_by_id(report_id)
    if not r:
        return False
    r.status = 'pending'
    r.checked_by_id = None
    r.checked_at = None
    db.session.commit()
    return True


def bulk_uncheck_reports(report_ids):
    new_ids = [int(r) for r in report_ids if not str(r).startswith('legacy-')]
    if new_ids:
        for r in Report.query.filter(Report.id.in_(new_ids)).all():
            r.status = 'pending'
            r.checked_by_id = None
            r.checked_at = None
        db.session.commit()


def bulk_check_reports(report_ids, user_id):
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)
    new_ids = [int(r) for r in report_ids if not str(r).startswith('legacy-')]
    if new_ids:
        for r in Report.query.filter(Report.id.in_(new_ids)).all():
            r.status = 'checked'
            r.checked_by_id = user_id
            r.checked_at = now
        db.session.commit()


def delete_target_object(object_type, object_id, admin_user_id):
    """Delete the object being reported, then clean up all associated reports."""
    try:
        if object_type == 'rule':
            from app.features.rule.rule_core import soft_delete_rule
            soft_delete_rule(object_id, admin_user_id)
        elif object_type == 'bundle':
            from app.features.bundle.bundle_core import delete_bundle
            delete_bundle(object_id)
        elif object_type == 'comment':
            from app.core.db_class.db import UnifiedComment
            c = UnifiedComment.query.get(object_id)
            if c:
                c.is_active = False
                db.session.commit()

        # Remove all reports pointing to this object so they don't show as orphans
        Report.query.filter_by(
            object_type=object_type, object_id=object_id
        ).delete(synchronize_session=False)
        if object_type == 'rule':
            from app.core.db_class.db import RepportRule
            RepportRule.query.filter_by(rule_id=object_id).delete(synchronize_session=False)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f'[report] delete_target_object error: {e}')
        return False
