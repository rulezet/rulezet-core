from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from .config_core import (
    get_user_config, update_config_core,
    get_all_custom_themes, get_valid_theme_keys,
)

config_blueprint = Blueprint('config', __name__)


@config_blueprint.route('/settings')
@login_required
def settings():
    config        = get_user_config()
    is_admin      = current_user.is_admin()
    custom_themes = get_all_custom_themes() if is_admin else []
    return render_template(
        'config/settings.html',
        config=config,
        is_admin=is_admin,
        custom_themes=custom_themes,
    )


@config_blueprint.route('/config/themes-data')
@login_required
def themes_data():
    themes = get_all_custom_themes(admin_view=current_user.is_admin())
    return jsonify({'themes': [t.to_json() for t in themes]})


@config_blueprint.route('/config/update', methods=['POST'])
@login_required
def update():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    if 'theme' not in data:
        return jsonify({'message': 'No valid field provided'}), 400

    config, msg = update_config_core({'theme': data['theme']})
    if not config:
        return jsonify({'message': msg}), 400
    return jsonify({'message': msg, 'config': config.to_json()}), 200
