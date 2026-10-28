"""Tutorial: the full tour's data and the demo pages it shows on a Rulezet with no rule or bundle.
The per-page tour is embedded by base.html (context processor below) — see tour_core.py."""
from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from app.core.utils.activity_log import log_activity

from . import tour_core as TourModel

tour_blueprint = Blueprint('tour', __name__, url_prefix='/tour')


@tour_blueprint.app_context_processor
def _tour_context():
    try:
        return {'tour_ctx': TourModel.context()}
    except Exception:                 # never break a page for the tutorial
        return {'tour_ctx': None}


@tour_blueprint.route('/full')
def full_tour_data():
    """The full tour for the current visitor (steps already filtered by role). ?onboarding=1: the
    first run of an empty instance (keeps the welcome pages after the starter rule was created)."""
    roles = TourModel.user_roles()
    onboarding = request.args.get('onboarding') == '1'
    return jsonify({'intro': TourModel.role_step(roles), 'pages': TourModel.full_tour(roles, onboarding),
                    'demo': {'rule': TourModel.demo('rule'), 'bundle': TourModel.demo('bundle')}})


@tour_blueprint.route('/starter', methods=['POST'])
@login_required
def starter():
    """First run of an empty Rulezet: a real first rule and bundle for the tour (see create_starter)."""
    created = TourModel.create_starter(current_user)
    if created:
        log_activity('tour.starter', 'Tutorial created a first rule and bundle', is_public=False)
    return jsonify({'created': bool(created), **(created or {})})


@tour_blueprint.route('/welcome')
def welcome():
    """First page of the full tour on an empty Rulezet: what it is and how to fill it."""
    return render_template('tour/welcome.html', empty=TourModel.instance_empty(),
                           starter=TourModel.starter_links(current_user),
                           is_admin=current_user.is_authenticated and current_user.is_admin())


@tour_blueprint.route('/demo/<string:kind>')
def demo(kind):
    """An example rule or bundle (setting tour.demo), never saved: what the tour shows when the
    instance has none yet."""
    data = TourModel.demo(kind)
    if kind not in ('rule', 'bundle') or not data:
        abort(404)
    return render_template(f'tour/demo_{kind}.html', demo=data)
