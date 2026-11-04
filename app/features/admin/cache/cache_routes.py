"""Admin → Settings → Cache (expert tab, /admin/settings?tab=cache): status, hit ratio, settings and actions. Admins only."""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.core.utils import page_cache
from app.core.utils.activity_log import log_activity
from app.features.admin.cache import cache_core

cache_admin_blueprint = Blueprint('cache_admin', __name__)


@cache_admin_blueprint.before_request
def _require_admin():
    if not current_user.is_authenticated:
        return redirect(url_for('account.login'))
    if not current_user.is_admin():
        abort(403)


@cache_admin_blueprint.route('/admin/cache', methods=['GET'])
def cache_page():
    """The cache is an expert tab of Admin → Settings."""
    return redirect('/admin/settings?tab=cache')


@cache_admin_blueprint.route('/admin/cache/status', methods=['GET'])
def cache_status():
    return jsonify(cache_core.status())


@cache_admin_blueprint.route('/admin/cache/action', methods=['POST'])
def cache_action():
    data = request.get_json(silent=True) or request.form
    action = (data.get('action') or '').strip()
    if action == 'refresh_rules':
        cache_core.refresh_all_rules()
        msg = 'Every rule page, list and API answer will be computed again.'
    elif action == 'refresh_rule':
        try:
            rid = int(data.get('rule_id'))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'Give a rule id.'}), 400
        if not cache_core.refresh_rule(rid):
            return jsonify({'success': False, 'message': f'No rule #{rid}.'}), 404
        msg = f'Rule #{rid} will be computed again.'
    elif action == 'clear_all':
        cache_core.clear_all()
        msg = 'Both caches emptied.'
    elif action == 'reset_stats':
        page_cache.reset_stats()
        msg = 'Hit / miss counters reset.'
    else:
        return jsonify({'success': False, 'message': 'Unknown action.'}), 400
    log_activity(f'cache.{action}', msg)
    return jsonify({'success': True, 'message': msg, 'status': cache_core.status()})
