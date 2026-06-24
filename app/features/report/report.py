from flask import Blueprint, jsonify, request, render_template, abort
from flask_login import current_user, login_required

from app.features.report.report_core import (
    create_report, get_combined_page, get_report_by_id,
    delete_report, delete_legacy_report, resolve_report, dismiss_report,
    check_report, uncheck_report, bulk_check_reports, bulk_uncheck_reports,
    delete_target_object, bulk_delete_reports, bulk_resolve_reports,
    bulk_dismiss_reports, count_pending, notify_admins, VALID_REASONS,
)
from app.core.utils.activity_log import log_activity

report_blueprint = Blueprint('report', __name__)


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin():
        abort(403)


# ── Submit a report (any authenticated user) ──────────────────────────────────

@report_blueprint.post('/submit')
@login_required
def api_submit():
    data        = request.get_json(silent=True) or {}
    object_type = (data.get('object_type') or '').strip()
    object_id   = data.get('object_id')
    reason      = (data.get('reason') or '').strip()
    message     = (data.get('message') or '').strip()

    if not object_type or not object_id or not reason:
        return jsonify({'message': 'object_type, object_id and reason are required',
                        'toast_class': 'danger', 'success': False}), 400
    if reason not in VALID_REASONS:
        return jsonify({'message': 'Invalid reason', 'toast_class': 'danger', 'success': False}), 400

    try:
        report, is_new = create_report(current_user.id, object_type, int(object_id), reason, message)
    except (ValueError, Exception) as e:
        return jsonify({'message': str(e), 'toast_class': 'danger', 'success': False}), 400

    if not is_new:
        return jsonify({'message': 'You already submitted this report.',
                        'toast_class': 'warning-subtle', 'success': False}), 200

    log_activity(
        f'report.{object_type}',
        f'Reported {object_type} id={object_id} — reason: {reason}',
        target_type=object_type, target_id=int(object_id),
        is_public=False,
    )
    notify_admins(report, current_user)

    return jsonify({'message': 'Report submitted. Thank you.',
                    'toast_class': 'success', 'success': True}), 201


# ── Count of pending reports (sidebar badge) ──────────────────────────────────

@report_blueprint.get('/count')
def api_count():
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'count': 0})
    return jsonify({'count': count_pending()})


# ── Admin: list page ──────────────────────────────────────────────────────────

@report_blueprint.get('/admin')
@login_required
def page_admin():
    _require_admin()
    return render_template('report/admin_reports.html')


# ── Admin: DataTable JSON feed ────────────────────────────────────────────────

@report_blueprint.get('/admin/data')
@login_required
def api_admin_data():
    _require_admin()
    page        = request.args.get('page', 1, type=int)
    per_page    = min(request.args.get('per_page', 20, type=int), 100)
    search      = request.args.get('search', '').strip() or None
    object_type = request.args.get('object_type', '').strip() or None
    status      = request.args.get('status', '').strip() or None
    sort        = request.args.get('sort', 'created_at')
    direction   = request.args.get('dir', 'desc')

    paginated = get_combined_page(page, per_page, object_type, status, search, sort, direction)
    return jsonify({
        'items':    paginated.items,   # already dicts
        'total':    paginated.total,
        'page':     page,
        'per_page': per_page,
        'pages':    paginated.pages,
    })


# ── Admin: single report actions ──────────────────────────────────────────────

@report_blueprint.post('/admin/<report_id>/resolve')
@login_required
def api_resolve(report_id):
    _require_admin()
    if str(report_id).startswith('legacy-'):
        return jsonify({'message': 'Legacy reports cannot be resolved (delete only)',
                        'toast_class': 'warning', 'success': False}), 400
    ok = resolve_report(int(report_id))
    if not ok:
        return jsonify({'message': 'Report not found', 'toast_class': 'danger', 'success': False}), 404
    return jsonify({'message': 'Report marked as resolved', 'toast_class': 'success', 'success': True})


@report_blueprint.post('/admin/<report_id>/dismiss')
@login_required
def api_dismiss(report_id):
    _require_admin()
    if str(report_id).startswith('legacy-'):
        return jsonify({'message': 'Legacy reports cannot be dismissed (delete only)',
                        'toast_class': 'warning', 'success': False}), 400
    ok = dismiss_report(int(report_id))
    if not ok:
        return jsonify({'message': 'Report not found', 'toast_class': 'danger', 'success': False}), 404
    return jsonify({'message': 'Report dismissed', 'toast_class': 'success-subtle', 'success': True})


@report_blueprint.post('/admin/<report_id>/delete')
@login_required
def api_delete(report_id):
    _require_admin()
    rid = str(report_id)
    if rid.startswith('legacy-'):
        ok = delete_legacy_report(int(rid[7:]))
    else:
        ok = delete_report(int(rid))
    if not ok:
        return jsonify({'message': 'Report not found', 'toast_class': 'danger', 'success': False}), 404
    return jsonify({'message': 'Report deleted', 'toast_class': 'success', 'success': True})


# ── Admin: check / uncheck ────────────────────────────────────────────────────

@report_blueprint.post('/admin/<report_id>/check')
@login_required
def api_check(report_id):
    _require_admin()
    rid = str(report_id)
    if rid.startswith('legacy-'):
        return jsonify({'message': 'Legacy reports cannot be checked this way',
                        'toast_class': 'warning', 'success': False}), 400
    ok = check_report(int(rid), current_user.id)
    if not ok:
        return jsonify({'message': 'Report not found', 'toast_class': 'danger', 'success': False}), 404
    from app.core.db_class.db import Report as ReportModel
    r = ReportModel.query.get(int(rid))
    return jsonify({'message': 'Report marked as checked', 'toast_class': 'success', 'success': True,
                    'checked_by_name': r.checked_by.get_username() if r.checked_by else None,
                    'checked_at': r.checked_at.strftime('%Y-%m-%d %H:%M') if r.checked_at else None})


@report_blueprint.post('/admin/<report_id>/uncheck')
@login_required
def api_uncheck(report_id):
    _require_admin()
    rid = str(report_id)
    if rid.startswith('legacy-'):
        return jsonify({'message': 'Legacy reports cannot be unchecked',
                        'toast_class': 'warning', 'success': False}), 400
    ok = uncheck_report(int(rid))
    if not ok:
        return jsonify({'message': 'Report not found', 'toast_class': 'danger', 'success': False}), 404
    return jsonify({'message': 'Report reverted to pending', 'toast_class': 'success', 'success': True})


# ── Admin: delete the reported object ────────────────────────────────────────

@report_blueprint.post('/admin/<report_id>/delete_target')
@login_required
def api_delete_target(report_id):
    _require_admin()
    rid = str(report_id)
    if rid.startswith('legacy-'):
        from app.core.db_class.db import RepportRule
        r = RepportRule.query.get(int(rid[7:]))
        if not r:
            return jsonify({'message': 'Not found', 'toast_class': 'danger', 'success': False}), 404
        obj_type, obj_id = 'rule', r.rule_id
    else:
        from app.core.db_class.db import Report as ReportModel
        r = ReportModel.query.get(int(rid))
        if not r:
            return jsonify({'message': 'Not found', 'toast_class': 'danger', 'success': False}), 404
        obj_type, obj_id = r.object_type, r.object_id

    ok = delete_target_object(obj_type, obj_id, current_user.id)
    if not ok:
        return jsonify({'message': f'Failed to delete {obj_type}',
                        'toast_class': 'danger', 'success': False}), 500
    return jsonify({'message': f'{obj_type.capitalize()} deleted successfully',
                    'toast_class': 'success', 'success': True})


# ── Admin: stats ──────────────────────────────────────────────────────────────

@report_blueprint.get('/admin/stats')
@login_required
def api_stats():
    _require_admin()
    from app.core.db_class.db import Report as ReportModel, RepportRule
    from sqlalchemy import func
    from app import db
    stats = db.session.query(ReportModel.status, func.count(ReportModel.id)).group_by(ReportModel.status).all()
    result = {s: c for s, c in stats}
    result['pending'] = result.get('pending', 0) + RepportRule.query.count()
    return jsonify(result)


# ── Admin: bulk actions ───────────────────────────────────────────────────────

@report_blueprint.post('/admin/bulk')
@login_required
def api_bulk():
    _require_admin()
    data    = request.get_json(silent=True) or {}
    action  = data.get('action')
    ids     = data.get('ids', [])

    if not action or not isinstance(ids, list) or not ids:
        return jsonify({'message': 'action and ids are required',
                        'toast_class': 'danger', 'success': False}), 400

    if action == 'delete':
        bulk_delete_reports(ids)
        return jsonify({'message': f'{len(ids)} report(s) deleted',
                        'toast_class': 'success', 'success': True})
    if action == 'resolve':
        bulk_resolve_reports(ids)
        return jsonify({'message': f'{len(ids)} report(s) resolved',
                        'toast_class': 'success', 'success': True})
    if action == 'dismiss':
        bulk_dismiss_reports(ids)
        return jsonify({'message': f'{len(ids)} report(s) dismissed',
                        'toast_class': 'success-subtle', 'success': True})
    if action == 'check':
        bulk_check_reports(ids, current_user.id)
        return jsonify({'message': f'{len(ids)} report(s) checked',
                        'toast_class': 'success', 'success': True})
    if action == 'uncheck':
        bulk_uncheck_reports(ids)
        return jsonify({'message': f'{len(ids)} report(s) reverted to pending',
                        'toast_class': 'success', 'success': True})
    if action == 'delete_target':
        errors = 0
        for rid in ids:
            s = str(rid)
            if s.startswith('legacy-'):
                from app.core.db_class.db import RepportRule
                r = RepportRule.query.get(int(s[7:]))
                if r:
                    ok = delete_target_object('rule', r.rule_id, current_user.id)
                    if not ok:
                        errors += 1
            else:
                from app.core.db_class.db import Report as ReportModel
                r = ReportModel.query.get(int(rid))
                if r:
                    ok = delete_target_object(r.object_type, r.object_id, current_user.id)
                    if not ok:
                        errors += 1
        msg = f'{len(ids) - errors} target(s) deleted'
        if errors:
            msg += f', {errors} failed'
        return jsonify({'message': msg,
                        'toast_class': 'success' if not errors else 'warning',
                        'success': True})

    return jsonify({'message': 'Unknown action', 'toast_class': 'danger', 'success': False}), 400
