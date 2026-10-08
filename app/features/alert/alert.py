"""
alert.py — "tell me when..." alerts: the pages (/alert/...) and the JSON
endpoints behind them. Business logic lives in alert_core.py.

Permissions: every route needs a logged-in user; an alert can only be read
or changed by its owner or an admin. The email-unsubscribe link is the one
exception — it works without a session, authorised by its signed token.
"""

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.core.db_class.db import Alert, AttackTechnique, Tag, User
from app.core.utils.activity_log import log_activity
from app.core.utils.mail_status import is_email_available

from . import alert_core as AlertModel

alert_blueprint = Blueprint('alert', __name__, template_folder='templates')


def _get_owned_alert_or_404(alert_uuid):
    alert = AlertModel.get_alert_by_uuid(alert_uuid)
    if not alert:
        abort(404)
    if alert.user_id != current_user.id and not current_user.is_admin():
        abort(403)
    return alert


def _criteria_display(criteria: dict) -> dict:
    """Objects the form's pickers need to show a stored/prefilled criteria:
    TagInput wants tag objects, AttackInput technique objects, the user
    picker id + username."""
    criteria = criteria or {}
    tag_names = [t.lower() for t in criteria.get('tags') or []]
    tags = (Tag.query.filter(func.lower(Tag.name).in_(tag_names)).all() if tag_names else [])
    attack_ids = criteria.get('attacks') or []
    techniques = (AttackTechnique.query.filter(AttackTechnique.technique_id.in_(attack_ids)).all()
                  if attack_ids else [])
    user_ids = [int(u) for u in criteria.get('users') or [] if str(u).isdigit()]
    users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    known_tags = {t.name.lower() for t in tags}
    known_techniques = {t.technique_id: t for t in techniques}
    return {
        'tags': [t.to_json() for t in tags],
        # A prefilled tag name with no Tag row still shows, as a plain chip.
        'unknown_tags': [n for n in tag_names if n not in known_tags],
        # Same for a technique id missing from the local ATT&CK data.
        'attacks': [
            {'technique_id': tid, 'name': known_techniques[tid].name if tid in known_techniques else tid,
             'tactic_keys': (known_techniques[tid].tactic_keys or []) if tid in known_techniques else []}
            for tid in attack_ids
        ],
        'users': [{'id': u.id, 'username': u.get_username(), 'avatar': u.get_avatar_url()} for u in users],
    }


def _prefill_from_args(args) -> dict:
    """/alert/new?cves=...&tags=...&attacks=...&keywords=...&formats=...
    &users=...&github_repos=...&cve_any=true...&target=rule|bundle|both — what the "Watch" buttons and
    "Alert me for this search" link to. Values are only a starting point:
    everything is validated again on save."""
    def csv(key):
        return [v.strip() for v in (args.get(key) or '').split(',') if v.strip()]

    criteria = {
        'cves': [c.upper() for c in csv('cves')],
        'tags': [t.lower() for t in csv('tags')],
        'attacks': [a.upper() for a in csv('attacks')],
        'keywords': [k.lower() for k in csv('keywords')],
        'formats': [f.lower() for f in csv('formats')],
        'users': [int(u) for u in csv('users') if u.isdigit()],
        'github_repos': csv('github_repos'),
        'cve_any': args.get('cve_any') == 'true',
        'tag_any': args.get('tag_any') == 'true',
        'attack_any': args.get('attack_any') == 'true',
        'github_any': args.get('github_any') == 'true',
    }
    target = args.get('target')
    targets = {'rule': ['rule'], 'bundle': ['bundle'], 'both': ['rule', 'bundle']}.get(target, ['rule'])
    return {
        'name': (args.get('name') or '')[:AlertModel.NAME_MAX_LEN],
        'targets': targets,
        'events': ['created'],
        'match_mode': 'any',
        'criteria': criteria,
        'notify_in_app': True,
        'email_mode': 'off',
    }


# ─── Pages ───────────────────────────────────────────────────────────────────

@alert_blueprint.route('/', methods=['GET'])
@login_required
def list_alerts():
    return render_template('alert/list_alert.html')


@alert_blueprint.route('/new', methods=['GET'])
@login_required
def new_alert():
    alert_data = _prefill_from_args(request.args)
    return render_template('alert/edit_alert.html', is_edit=False, alert=None, alert_data=alert_data,
                           criteria_display=_criteria_display(alert_data['criteria']))


@alert_blueprint.route('/<string:alert_uuid>/edit', methods=['GET'])
@login_required
def edit_alert(alert_uuid):
    alert = _get_owned_alert_or_404(alert_uuid)
    return render_template('alert/edit_alert.html', is_edit=True, alert=alert, alert_data=alert.to_json(),
                           criteria_display=_criteria_display(alert.criteria))


@alert_blueprint.route('/<string:alert_uuid>', methods=['GET'])
@login_required
def detail_alert(alert_uuid):
    alert = _get_owned_alert_or_404(alert_uuid)
    unseen = AlertModel.unseen_counts(alert.user_id).get(alert.id, 0)
    alert_data = alert.to_json(unseen_count=unseen)
    return render_template('alert/detail_alert.html', alert=alert, alert_data=alert_data,
                           criteria_display=_criteria_display(alert.criteria))


@alert_blueprint.route('/unsubscribe/<string:token>', methods=['GET'])
def unsubscribe(token):
    """One-click "stop emails for this alert" from an alert email — no login
    needed, the signed token is the authorisation. Only ever turns emails
    OFF, never on, so a leaked link can't be used for anything harmful."""
    alert_uuid = AlertModel.read_unsubscribe_token(token)
    alert = AlertModel.get_alert_by_uuid(alert_uuid) if alert_uuid else None
    if alert:
        AlertModel.disable_alert_emails(alert)
        log_activity('alert.email_unsubscribe', f'Emails turned off for alert "{alert.name}" from an email link',
                     target_type='alert', target_id=alert.id, is_public=False, actor_id=alert.user_id)
    return render_template('alert/unsubscribe_alert.html', alert=alert)


# ─── JSON: list / KPIs ───────────────────────────────────────────────────────

@alert_blueprint.route('/data', methods=['GET'])
@login_required
def alerts_data():
    """One page of the user's alerts (search / filters / sort) plus the
    KPIs, which always cover every alert regardless of the filters."""
    args = request.args
    pagination = AlertModel.search_user_alerts(
        current_user.id,
        q=(args.get('q') or '').strip() or None,
        status=args.get('status'), email=args.get('email'), target=args.get('target'),
        unseen_only=args.get('unseen') == 'true',
        sort=args.get('sort', 'recent'),
        page=args.get('page', 1, type=int),
        per_page=min(max(args.get('per_page', 12, type=int), 1), 60),
    )
    unseen = AlertModel.unseen_counts(current_user.id)
    alerts = pagination.items
    watched_user_ids = {int(u) for a in alerts for u in (a.criteria or {}).get('users') or []}
    watched_users = User.query.filter(User.id.in_(watched_user_ids)).all() if watched_user_ids else []
    total = Alert.query.filter_by(user_id=current_user.id).count()
    return jsonify({
        'items': [a.to_json(unseen_count=unseen.get(a.id, 0)) for a in alerts],
        'total': pagination.total,
        'total_pages': pagination.pages or 1,
        'page': pagination.page,
        'users': [{'id': u.id, 'username': u.get_username()} for u in watched_users],
        'kpis': {
            'total': total,
            'active': Alert.query.filter_by(user_id=current_user.id, is_active=True).count(),
            'unseen': sum(unseen.values()),
            'matches_7d': AlertModel.matches_since(current_user.id, days=7),
            'emailed': Alert.query.filter(Alert.user_id == current_user.id, Alert.email_mode != 'off').count(),
        },
        'limit': AlertModel.max_alerts_per_user(),
        'email_available': is_email_available(),
    })


@alert_blueprint.route('/unseen_count', methods=['GET'])
@login_required
def unseen_count():
    return jsonify({'unseen': AlertModel.total_unseen(current_user.id)})


# ─── JSON: create / update / toggle / delete ────────────────────────────────

@alert_blueprint.route('/create', methods=['POST'])
@login_required
def create_alert():
    data = request.get_json(silent=True) or {}
    try:
        fields = AlertModel.validate_alert_payload(data, email_available=is_email_available())
        alert = AlertModel.create_alert(current_user.id, fields)
    except AlertModel.AlertError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    log_activity('alert.create', f'Created alert "{alert.name}"',
                 target_type='alert', target_id=alert.id, is_public=False)
    return jsonify({'success': True, 'alert': alert.to_json(), 'message': 'Alert created.'})


@alert_blueprint.route('/<string:alert_uuid>/update', methods=['POST'])
@login_required
def update_alert(alert_uuid):
    alert = _get_owned_alert_or_404(alert_uuid)
    data = request.get_json(silent=True) or {}
    try:
        fields = AlertModel.validate_alert_payload(data, email_available=is_email_available(),
                                                   current_email_mode=alert.email_mode)
    except AlertModel.AlertError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    AlertModel.update_alert(alert, fields)
    log_activity('alert.update', f'Updated alert "{alert.name}"',
                 target_type='alert', target_id=alert.id, is_public=False)
    return jsonify({'success': True, 'alert': alert.to_json(), 'message': 'Alert saved.'})


@alert_blueprint.route('/<string:alert_uuid>/toggle', methods=['POST'])
@login_required
def toggle_alert(alert_uuid):
    alert = _get_owned_alert_or_404(alert_uuid)
    data = request.get_json(silent=True) or {}
    AlertModel.set_alert_active(alert, data.get('is_active', not alert.is_active))
    log_activity('alert.toggle', f'{"Resumed" if alert.is_active else "Paused"} alert "{alert.name}"',
                 target_type='alert', target_id=alert.id, is_public=False)
    return jsonify({'success': True, 'is_active': alert.is_active})


@alert_blueprint.route('/<string:alert_uuid>/delete', methods=['POST'])
@login_required
def delete_alert(alert_uuid):
    alert = _get_owned_alert_or_404(alert_uuid)
    name, alert_id = alert.name, alert.id
    AlertModel.delete_alert(alert)
    log_activity('alert.delete', f'Deleted alert "{name}"',
                 target_type='alert', target_id=alert_id, is_public=False)
    return jsonify({'success': True, 'message': 'Alert deleted.'})


# ─── JSON: preview / matches / activity ─────────────────────────────────────

@alert_blueprint.route('/preview', methods=['POST'])
@login_required
def preview_alert():
    """What these criteria would have caught over the last 30 days — shown
    live in the form while the user builds the alert."""
    data = request.get_json(silent=True) or {}
    try:
        criteria = AlertModel.normalize_criteria(data.get('criteria'))
    except AlertModel.AlertError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    if not AlertModel.has_any_criterion(criteria):
        return jsonify({'success': True, 'preview': None})
    targets = [t for t in (data.get('targets') or ['rule']) if t in ('rule', 'bundle')]
    match_mode = data.get('match_mode') if data.get('match_mode') in ('any', 'all') else 'any'
    return jsonify({'success': True,
                    'preview': AlertModel.preview(criteria, match_mode, targets, user_id=current_user.id)})


@alert_blueprint.route('/<string:alert_uuid>/seen', methods=['POST'])
@login_required
def mark_alert_seen(alert_uuid):
    """Called by the detail page once it has shown the matches, so the
    "new" markers are visible on that first view and cleared for the next.
    An admin looking at someone else's alert doesn't clear anything."""
    alert = _get_owned_alert_or_404(alert_uuid)
    if alert.user_id == current_user.id:
        AlertModel.mark_matches_seen(alert)
    return jsonify({'success': True})


@alert_blueprint.route('/<string:alert_uuid>/matches', methods=['GET'])
@login_required
def alert_matches(alert_uuid):
    alert = _get_owned_alert_or_404(alert_uuid)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    return jsonify(AlertModel.get_alert_matches(alert, page=page, per_page=per_page))


@alert_blueprint.route('/<string:alert_uuid>/activity', methods=['GET'])
@login_required
def alert_activity(alert_uuid):
    alert = _get_owned_alert_or_404(alert_uuid)
    return jsonify(AlertModel.get_alert_activity(alert))
