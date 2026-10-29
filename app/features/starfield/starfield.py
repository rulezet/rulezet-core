"""starfield.py — the hidden Starfield game (/starfield, linked from nowhere)
and its score tracking: the game reports each finished run, admins see every
player's runs in detail on the same page."""
from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user

from app.features.starfield import starfield_core as StarfieldModel

starfield_blueprint = Blueprint('starfield', __name__)


def _require_admin():
    if not (current_user.is_authenticated and current_user.is_admin()):
        abort(403)


@starfield_blueprint.route('/starfield')
def starfield():
    """Hidden easter egg — a small space game. Not linked from any nav/sitemap."""
    is_admin = current_user.is_authenticated and current_user.is_admin()
    return render_template('starfield.html', is_admin=is_admin)


@starfield_blueprint.route('/starfield/run', methods=['POST'])
def record_run():
    """Called by the game at the end of each run — anonymous players too."""
    if request.content_length and request.content_length > 20_000:
        return jsonify({'success': False, 'message': 'Payload too large.'}), 413
    user_id = current_user.id if current_user.is_authenticated else None
    run, error = StarfieldModel.record_run(request.get_json(silent=True), user_id=user_id)
    if error:
        return jsonify({'success': False, 'message': error}), 400
    if user_id:                     # secret badges come from runs: check on the next page
        from app.core.db_class.gamification import mark_badge_check
        mark_badge_check(user_id)
    return jsonify({'success': True, 'uuid': run.uuid}), 201


@starfield_blueprint.route('/starfield/admin/players')
def admin_players():
    _require_admin()
    return jsonify({'players': StarfieldModel.list_players(), **StarfieldModel.overview()})


@starfield_blueprint.route('/starfield/admin/runs')
def admin_player_runs():
    _require_admin()
    runs = StarfieldModel.player_runs(request.args.get('player', ''))
    if runs is None:
        return jsonify({'success': False, 'message': 'Unknown player.'}), 404
    return jsonify({'success': True, 'runs': runs})
