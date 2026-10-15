from flask import request
from flask_restx import Namespace, Resource
from flask_login import current_user

from ...core.utils.decorators import api_required
from ...features.config.config_core import (
    get_user_config, update_config_core,
    get_all_custom_themes, create_custom_theme_core, update_custom_theme_core,
    delete_custom_theme_core, upsert_builtin_theme_override_core,
    reset_builtin_theme_core, get_valid_theme_keys, THEME_VAR_KEYS, BUILTIN_OVERRIDABLE,
)

config_ns = Namespace('config', description='User interface preferences, public settings and the format list')


@config_ns.route('/settings')
class PublicSettingsResource(Resource):
    def get(self):
        """Several public settings in one call: ?keys=a,b,c → {key: value}
        (unknown or non-public keys are left out)."""
        from ...core.utils.app_settings import get_public_setting
        keys = [k.strip() for k in (request.args.get('keys') or '').split(',') if k.strip()][:50]
        values = {k: get_public_setting(k) for k in keys}
        return {'values': {k: v for k, v in values.items() if v is not None}}, 200


@config_ns.route('/settings/<string:key>')
class PublicSettingResource(Resource):
    def get(self, key):
        """Current value of a public setting (e.g. report.reasons, git.provider_icons)."""
        from ...core.utils.app_settings import get_public_setting
        value = get_public_setting(key)
        if value is None:
            return {'message': f"No public setting '{key}'"}, 404
        return {'key': key, 'value': value}, 200


@config_ns.route('/formats')
class FormatListResource(Resource):
    def get(self):
        """Every rule format this instance knows — registered formats plus any
        format a rule uses — with its description, links, file extensions,
        whether it can be executed, and its number of active rules.
        Always the current list: read from the database on each call."""
        from ...features.rule.rule_core import get_formats_overview
        formats = get_formats_overview()
        return {'formats': formats, 'total': len(formats)}, 200


@config_ns.route('/')
class ConfigResource(Resource):
    method_decorators = [api_required]

    def get(self):
        config = get_user_config()
        if not config:
            return {'message': 'No config found'}, 404
        return config.to_json(), 200

    def patch(self):
        data = request.json or {}
        if 'theme' not in data:
            return {'message': 'theme field required'}, 400
        is_admin = current_user.is_authenticated and current_user.is_admin()
        if data['theme'] not in get_valid_theme_keys(admin=is_admin):
            return {'message': 'Invalid theme'}, 400
        config, msg = update_config_core({'theme': data['theme']})
        if not config:
            return {'message': msg}, 400
        return {'message': msg, 'config': config.to_json()}, 200


@config_ns.route('/themes')
class ThemeListResource(Resource):
    method_decorators = [api_required]

    def get(self):
        themes = get_all_custom_themes(admin_view=current_user.is_admin())
        return {'themes': [t.to_json() for t in themes]}, 200

    def post(self):
        if not current_user.is_admin():
            return {'message': 'Admin only'}, 403
        data = request.json or {}
        theme, msg = create_custom_theme_core(data, current_user.id)
        if not theme:
            return {'message': msg}, 400
        return {'message': msg, 'theme': theme.to_json()}, 201


@config_ns.route('/themes/vars')
class ThemeVarsResource(Resource):
    method_decorators = [api_required]

    def get(self):
        return {'vars': THEME_VAR_KEYS}, 200


@config_ns.route('/themes/builtin/<string:css_key>')
class BuiltinThemeResource(Resource):
    method_decorators = [api_required]

    def put(self, css_key):
        if not current_user.is_admin():
            return {'message': 'Admin only'}, 403
        data = request.json or {}
        theme, msg = upsert_builtin_theme_override_core(css_key, data, current_user.id)
        if not theme:
            return {'message': msg}, 400
        return {'message': msg, 'theme': theme.to_json()}, 200

    def delete(self, css_key):
        if not current_user.is_admin():
            return {'message': 'Admin only'}, 403
        ok, msg = reset_builtin_theme_core(css_key, current_user.id)
        if not ok:
            return {'message': msg}, 400
        return {'message': msg}, 200


@config_ns.route('/themes/<string:uuid>')
class ThemeResource(Resource):
    method_decorators = [api_required]

    def put(self, uuid):
        if not current_user.is_admin():
            return {'message': 'Admin only'}, 403
        data = request.json or {}
        theme, msg = update_custom_theme_core(uuid, data, current_user.id)
        if not theme:
            return {'message': msg}, 400
        return {'message': msg, 'theme': theme.to_json()}, 200

    def delete(self, uuid):
        if not current_user.is_admin():
            return {'message': 'Admin only'}, 403
        ok, msg = delete_custom_theme_core(uuid, current_user.id)
        if not ok:
            return {'message': msg}, 400
        return {'message': msg}, 200


@config_ns.route('/themes/<string:uuid>/visibility')
class ThemeVisibilityResource(Resource):
    method_decorators = [api_required]

    def patch(self, uuid):
        if not current_user.is_admin():
            return {'message': 'Admin only'}, 403
        data = request.json or {}
        if 'is_public' not in data:
            return {'message': 'is_public required'}, 400
        theme, msg = update_custom_theme_core(uuid, {'is_public': data['is_public']}, current_user.id)
        if not theme:
            return {'message': msg}, 400
        return {'message': msg, 'theme': theme.to_json()}, 200
