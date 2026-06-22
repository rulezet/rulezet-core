import os
import re
from datetime import datetime
from flask import current_app
from flask_login import current_user
from ... import db
from ...core.db_class.db import UserConfig, CustomTheme, THEME_CHOICES, _slugify


# CSS variable keys that admins can customise per-theme.
THEME_VAR_KEYS = [
    '--bg-color', '--card-bg-color', '--light-bg-color', '--code-bg-color',
    '--card-header-bg-color', '--navbar-bg-color', '--bar-bg-color',
    '--text-color', '--subtle-text-color', '--navbar-text-color',
    '--border-color', '--selected-color', '--page-selected-color',
    '--sidebar-color', '--rule-name-color',
]

BUILTIN_STATIC_THEMES = set(THEME_CHOICES)
BUILTIN_OVERRIDABLE   = {'dark'}
_BUILTIN_META = {
    'dark': ('Dark', 'fa-moon', True),
}

# Named themes shipped with the app (CSS defined in themes/theme.css).
# These are always available regardless of the DB.
_OCEAN_VARS = {
    '--bg-color': '#0d1b2a', '--card-bg-color': '#1a2d42', '--light-bg-color': '#1e3550',
    '--code-bg-color': '#0a1520', '--card-header-bg-color': '#1e3550',
    '--navbar-bg-color': '#0d1b2a', '--bar-bg-color': '#1a2d42',
    '--text-color': '#cfe2f3', '--subtle-text-color': '#7aaec8', '--navbar-text-color': '#cfe2f3',
    '--border-color': 'rgba(79, 195, 247, 0.15)', '--selected-color': 'rgba(79, 195, 247, 0.20)',
    '--page-selected-color': '#4fc3f7', '--sidebar-color': '#060f1a', '--rule-name-color': '#4fc3f7',
}
_FOREST_VARS = {
    '--bg-color': '#0d1f0e', '--card-bg-color': '#142715', '--light-bg-color': '#1a3020',
    '--code-bg-color': '#0a1a0b', '--card-header-bg-color': '#1a3020',
    '--navbar-bg-color': '#0d1f0e', '--bar-bg-color': '#142715',
    '--text-color': '#c8e6c9', '--subtle-text-color': '#81c784', '--navbar-text-color': '#c8e6c9',
    '--border-color': 'rgba(102, 187, 106, 0.15)', '--selected-color': 'rgba(102, 187, 106, 0.20)',
    '--page-selected-color': '#66bb6a', '--sidebar-color': '#061008', '--rule-name-color': '#66bb6a',
}
_MIDNIGHT_VARS = {
    '--bg-color': '#0a0a0f', '--card-bg-color': '#12121e', '--light-bg-color': '#1a1a2e',
    '--code-bg-color': '#07070f', '--card-header-bg-color': '#1a1a2e',
    '--navbar-bg-color': '#0a0a0f', '--bar-bg-color': '#12121e',
    '--text-color': '#d4d4f0', '--subtle-text-color': '#7878a8', '--navbar-text-color': '#d4d4f0',
    '--border-color': 'rgba(138, 99, 210, 0.15)', '--selected-color': 'rgba(138, 99, 210, 0.20)',
    '--page-selected-color': '#8a63d2', '--sidebar-color': '#050510', '--rule-name-color': '#a78bfa',
}
_SUNSET_VARS = {
    '--bg-color': '#1a0f0a', '--card-bg-color': '#2a1810', '--light-bg-color': '#351f14',
    '--code-bg-color': '#120a06', '--card-header-bg-color': '#351f14',
    '--navbar-bg-color': '#1a0f0a', '--bar-bg-color': '#2a1810',
    '--text-color': '#f0d4b8', '--subtle-text-color': '#c89060', '--navbar-text-color': '#f0d4b8',
    '--border-color': 'rgba(251, 146, 60, 0.15)', '--selected-color': 'rgba(251, 146, 60, 0.20)',
    '--page-selected-color': '#fb923c', '--sidebar-color': '#0d0703', '--rule-name-color': '#fb923c',
}

BUILTIN_NAMED_THEMES = {
    'ocean':    {'label': 'Ocean',    'icon': 'fa-water',      'is_dark': True, 'css_vars': _OCEAN_VARS},
    'forest':   {'label': 'Forest',   'icon': 'fa-tree',       'is_dark': True, 'css_vars': _FOREST_VARS},
    'midnight': {'label': 'Midnight', 'icon': 'fa-moon',       'is_dark': True, 'css_vars': _MIDNIGHT_VARS},
    'sunset':   {'label': 'Sunset',   'icon': 'fa-cloud-sun',  'is_dark': True, 'css_vars': _SUNSET_VARS},
}


def seed_default_themes():
    """Create/backfill built-in named themes in the DB and regenerate CSS."""
    try:
        changed = False
        for css_key, meta in BUILTIN_NAMED_THEMES.items():
            theme = CustomTheme.query.filter_by(css_key=css_key).first()
            if not theme:
                theme = CustomTheme(
                    name=meta['label'], css_key=css_key,
                    icon=meta['icon'], is_dark=meta['is_dark'],
                    is_builtin=False, is_public=True,
                    css_vars=meta.get('css_vars'), created_by=None,
                )
                db.session.add(theme)
                changed = True
            elif theme.css_vars is None and meta.get('css_vars'):
                theme.css_vars = meta['css_vars']
                changed = True
        if changed:
            db.session.commit()
            regenerate_custom_themes_css()
    except Exception:
        db.session.rollback()


def get_valid_theme_keys(admin=False):
    """Return the set of theme identifiers a user may select."""
    q = CustomTheme.query.filter_by(is_active=True, is_builtin=False)
    if not admin:
        q = q.filter_by(is_public=True)
    custom_keys = {t.css_key for t in q.all()}
    return BUILTIN_STATIC_THEMES | set(BUILTIN_NAMED_THEMES.keys()) | custom_keys


def get_all_custom_themes(admin_view=True):
    q = CustomTheme.query.filter_by(is_active=True)
    if not admin_view:
        q = q.filter_by(is_public=True)
    return q.order_by(CustomTheme.id).all()


def regenerate_custom_themes_css():
    """Rewrite app/static/css/themes/custom-themes.css from the DB.

    Each theme uses dual selectors to beat body.dark-mode specificity:
      html[data-theme="X"]       (0,1,1) beats [data-bs-theme="dark"] (0,1,0)
      html[data-theme="X"] body  (0,1,2) beats body.dark-mode          (0,1,1)
    """
    themes = CustomTheme.query.filter_by(is_active=True).order_by(CustomTheme.id).all()
    lines = ['/* Auto-generated custom themes — do not edit manually */']
    for t in themes:
        if not t.css_vars:
            continue
        var_lines = [
            f'    {var}: {value};'
            for var, value in t.css_vars.items()
            if var in THEME_VAR_KEYS and value
        ]
        if not var_lines:
            continue
        lines.append(f'\nhtml[data-theme="{t.css_key}"],')
        lines.append(f'html[data-theme="{t.css_key}"] body {{')
        lines.extend(var_lines)
        lines.append('}')
    css = '\n'.join(lines) + '\n'
    path = os.path.join(current_app.root_path, 'static', 'css', 'themes', 'custom-themes.css')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(css)


# ── UserConfig CRUD ──────────────────────────────────────────────────────────

def get_user_config(user_id=None):
    uid = user_id or (current_user.id if current_user.is_authenticated else None)
    if not uid:
        return None
    return UserConfig.query.filter_by(user_id=uid, is_active=True).first()


def create_default_config_core(user_id) -> tuple:
    try:
        existing = UserConfig.query.filter_by(user_id=user_id).first()
        if existing:
            return existing, 'Config already exists'
        config = UserConfig(user_id=user_id, created_by=user_id)
        db.session.add(config)
        db.session.commit()
        return config, 'Config created'
    except Exception:
        db.session.rollback()
        return None, 'Error creating config'


def update_config_core(form_dict) -> tuple:
    try:
        uid = current_user.id if current_user.is_authenticated else None
        if not uid:
            return None, 'Not authenticated'
        config = get_user_config(uid)
        if not config:
            config, msg = create_default_config_core(uid)
            if not config:
                return None, msg

        if 'theme' in form_dict:
            is_admin = current_user.is_admin() if current_user.is_authenticated else False
            if form_dict['theme'] not in get_valid_theme_keys(admin=is_admin):
                return None, 'Invalid theme'
            config.theme = form_dict['theme']

        db.session.commit()
        return config, 'Settings saved'
    except Exception:
        db.session.rollback()
        return None, 'Error saving settings'


# ── CustomTheme CRUD ─────────────────────────────────────────────────────────

def create_custom_theme_core(data, user_id):
    try:
        name = (data.get('name') or '').strip()
        if not name or len(name) > 64:
            return None, 'Theme name is required (max 64 chars)'
        css_key = _slugify(name)
        if not css_key:
            return None, 'Invalid theme name'
        if css_key in BUILTIN_STATIC_THEMES:
            return None, 'Cannot use a built-in theme name'
        if CustomTheme.query.filter_by(css_key=css_key).first():
            return None, 'A theme with this name already exists'
        icon    = (data.get('icon') or 'fa-palette').strip()
        is_dark = bool(data.get('is_dark', False))
        css_vars = {k: v for k, v in (data.get('css_vars') or {}).items()
                    if k in THEME_VAR_KEYS and v}
        theme = CustomTheme(
            name=name, css_key=css_key, icon=icon,
            is_dark=is_dark, is_builtin=False,
            css_vars=css_vars or None, created_by=user_id,
        )
        db.session.add(theme)
        db.session.commit()
        regenerate_custom_themes_css()
        return theme, 'Theme created'
    except Exception as e:
        db.session.rollback()
        return None, f'Error creating theme: {e}'


def update_custom_theme_core(uuid, data, user_id):
    try:
        theme = CustomTheme.query.filter_by(uuid=uuid, is_active=True).first()
        if not theme:
            return None, 'Theme not found'
        if not theme.is_builtin:
            name = (data.get('name') or '').strip()
            if name and len(name) <= 64:
                theme.name = name
            icon = data.get('icon')
            if icon:
                theme.icon = icon.strip()
            if 'is_dark' in data:
                theme.is_dark = bool(data['is_dark'])
        if 'is_public' in data:
            theme.is_public = bool(data['is_public'])
        if 'css_vars' in data:
            css_vars = {k: v for k, v in (data['css_vars'] or {}).items()
                        if k in THEME_VAR_KEYS and v}
            theme.css_vars = css_vars or None
        db.session.commit()
        regenerate_custom_themes_css()
        return theme, 'Theme updated'
    except Exception as e:
        db.session.rollback()
        return None, f'Error updating theme: {e}'


def upsert_builtin_theme_override_core(css_key, data, user_id):
    if css_key not in BUILTIN_OVERRIDABLE:
        return None, 'Not a valid built-in theme'
    try:
        theme = CustomTheme.query.filter_by(css_key=css_key, is_builtin=True).first()
        bname, bicon, bdark = _BUILTIN_META[css_key]
        if not theme:
            theme = CustomTheme(
                name=bname, css_key=css_key, icon=bicon,
                is_dark=bdark, is_builtin=True, created_by=user_id,
            )
            db.session.add(theme)
        css_vars = {k: v for k, v in (data.get('css_vars') or {}).items()
                    if k in THEME_VAR_KEYS and v}
        theme.css_vars  = css_vars or None
        theme.is_active = bool(css_vars)
        db.session.commit()
        regenerate_custom_themes_css()
        return theme, 'Theme vars saved'
    except Exception as e:
        db.session.rollback()
        return None, f'Error saving theme: {e}'


def reset_builtin_theme_core(css_key, user_id):
    if css_key not in BUILTIN_OVERRIDABLE:
        return False, 'Not a valid built-in theme'
    try:
        theme = CustomTheme.query.filter_by(css_key=css_key, is_builtin=True).first()
        if theme:
            theme.is_active = False
            theme.css_vars  = None
            db.session.commit()
            regenerate_custom_themes_css()
        return True, 'Built-in theme reset to defaults'
    except Exception as e:
        db.session.rollback()
        return False, f'Error resetting theme: {e}'


def delete_custom_theme_core(uuid, user_id):
    try:
        theme = CustomTheme.query.filter_by(uuid=uuid, is_active=True).first()
        if not theme:
            return False, 'Theme not found'
        if theme.is_builtin:
            return False, 'Cannot delete a built-in theme override'
        theme.is_active  = False
        theme.deleted_at = datetime.utcnow()
        theme.deleted_by = user_id
        db.session.commit()
        regenerate_custom_themes_css()
        return True, 'Theme deleted'
    except Exception as e:
        db.session.rollback()
        return False, f'Error deleting theme: {e}'
