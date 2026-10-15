"""nightshift.py — the hidden investigation game (/nightshift, linked from
nowhere). The page, then a small JSON API the game calls: open a case, pin
evidence, ask Rulezy for a hint, test the rule, deploy it."""
from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user

from app.features.nightshift import nightshift_core as NightshiftModel

nightshift_blueprint = Blueprint('nightshift', __name__)

MAX_PAYLOAD = 10_000


def _user_id():
    return current_user.id if current_user.is_authenticated else None


def _payload():
    if request.content_length and request.content_length > MAX_PAYLOAD:
        abort(413)
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _player(data):
    player_id = data.get('player')
    if not NightshiftModel.valid_player_id(player_id):
        abort(400)
    return player_id


def _run(data):
    run = NightshiftModel.get_run(data.get('run'), _player(data), _user_id())
    if run is None:
        abort(404)
    return run


@nightshift_blueprint.route('/nightshift')
def nightshift():
    return render_template('nightshift/nightshift.html')


@nightshift_blueprint.route('/nightshift/cases')
def cases():
    return jsonify({'cases': [{'id': c['id'], 'number': c['number'], 'time': c['time'], 'title': c['title']}
                              for c in NightshiftModel.list_cases()]})


@nightshift_blueprint.route('/nightshift/case/start', methods=['POST'])
def start_case():
    data = _payload()
    case = NightshiftModel.get_case(str(data.get('case', '')))
    if case is None:
        abort(404)
    run = NightshiftModel.start_run(case['id'], _player(data), _user_id())
    return jsonify({'case': NightshiftModel.public_case(case), 'run': NightshiftModel.run_state(run)})


@nightshift_blueprint.route('/nightshift/case/pin', methods=['POST'])
def pin():
    data = _payload()
    run = _run(data)
    error = NightshiftModel.pin(run, data.get('key'))
    if error:
        return jsonify({'success': False, 'message': error}), 400
    return jsonify({'success': True, 'run': NightshiftModel.run_state(run)})


@nightshift_blueprint.route('/nightshift/case/hint', methods=['POST'])
def hint():
    data = _payload()
    run = _run(data)
    error = NightshiftModel.take_hint(run)
    if error:
        return jsonify({'success': False, 'message': error}), 400
    return jsonify({'success': True, 'run': NightshiftModel.run_state(run)})


@nightshift_blueprint.route('/nightshift/case/test', methods=['POST'])
def test_rule():
    return _check(deploy=False)


@nightshift_blueprint.route('/nightshift/case/deploy', methods=['POST'])
def deploy_rule():
    return _check(deploy=True)


def _check(deploy):
    data = _payload()
    run = _run(data)
    result, error = NightshiftModel.check_rule(run, data.get('blanks'), deploy=deploy)
    if error:
        return jsonify({'success': False, 'message': error}), 400
    return jsonify({'success': True, **result, 'run': NightshiftModel.run_state(run)})
