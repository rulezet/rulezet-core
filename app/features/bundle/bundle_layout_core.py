"""Per-user layout of the bundle structure editor (/bundle/edit/<id>, Structure tab).

The editor's panels (Bundle Explorer, Rule Library, Preview & Editor,
Overview) are each shown one way, chosen by the user:
  - 'grid'   — docked on a 12-column grid, arranged like the dashboard widgets;
  - 'window' — a floating window over the page (position + size in pixels);
  - 'drawer' — the Rule Library only: a panel sliding in from the right.
`minimized` folds a window to its title bar / closes the drawer. The layout belongs to the user, not to a bundle: it is stored in
their UserConfig.meta under 'bundle_editor_layout', next to the dashboard's
'dashboard_layout', so it follows them across bundles and devices.
"""
from flask_login import current_user

from app import db
from app.features.config.config_core import get_user_config, create_default_config_core

META_KEY = 'bundle_editor_layout'
GRID_COLUMNS = 12
MAX_ROWS = 60

PANEL_IDS = ('explorer', 'library', 'preview', 'overview')
MODES = ('grid', 'window', 'drawer')
DRAWER_PANELS = ('library',)
MAX_PIXELS = 20000
MIN_WINDOW = 200

DEFAULT_LAYOUT = {
    'panels': [
        {'id': 'explorer', 'x': 0, 'y': 0,  'w': 5,  'h': 9, 'hidden': False, 'mode': 'grid', 'minimized': False},
        {'id': 'library',  'x': 5, 'y': 0,  'w': 7,  'h': 9, 'hidden': False, 'mode': 'grid', 'minimized': False},
        {'id': 'preview',  'x': 0, 'y': 9,  'w': 12, 'h': 7, 'hidden': False, 'mode': 'grid', 'minimized': False},
        {'id': 'overview', 'x': 0, 'y': 16, 'w': 12, 'h': 3, 'hidden': True,  'mode': 'grid', 'minimized': False},
    ],
}


def _get_or_create_config():
    config = get_user_config(current_user.id)
    if not config:
        config, _msg = create_default_config_core(current_user.id)
    return config


def _is_int(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def validate_layout(layout):
    """(clean_layout, None) or (None, error message).

    Every known panel must appear exactly once, with integer grid
    coordinates that fit the 12-column grid; unknown keys are dropped."""
    panels = layout.get('panels') if isinstance(layout, dict) else None
    if not isinstance(panels, list):
        return None, 'Invalid layout: expected {"panels": [...]}'
    clean, seen = [], set()
    for p in panels:
        if not isinstance(p, dict) or p.get('id') not in PANEL_IDS:
            return None, 'Invalid layout: unknown panel'
        if p['id'] in seen:
            return None, f"Invalid layout: panel '{p['id']}' appears twice"
        seen.add(p['id'])
        x, y, w, h = p.get('x'), p.get('y'), p.get('w'), p.get('h')
        if not (_is_int(w, 1, GRID_COLUMNS) and _is_int(x, 0, GRID_COLUMNS - 1)
                and x + w <= GRID_COLUMNS and _is_int(y, 0, MAX_ROWS) and _is_int(h, 1, MAX_ROWS)):
            return None, f"Invalid layout: bad position or size for panel '{p['id']}'"
        hidden, minimized = p.get('hidden', False), p.get('minimized', False)
        if not isinstance(hidden, bool) or not isinstance(minimized, bool):
            return None, f"Invalid layout: 'hidden' and 'minimized' must be true or false for panel '{p['id']}'"
        mode = p.get('mode', 'grid')
        if mode not in MODES or (mode == 'drawer' and p['id'] not in DRAWER_PANELS):
            return None, f"Invalid layout: bad display mode for panel '{p['id']}'"
        panel = {'id': p['id'], 'x': x, 'y': y, 'w': w, 'h': h, 'hidden': hidden, 'mode': mode, 'minimized': minimized}
        win = p.get('win')
        if win is not None:
            if not (isinstance(win, dict) and _is_int(win.get('x'), 0, MAX_PIXELS) and _is_int(win.get('y'), 0, MAX_PIXELS)
                    and _is_int(win.get('w'), MIN_WINDOW, MAX_PIXELS) and _is_int(win.get('h'), MIN_WINDOW, MAX_PIXELS)):
                return None, f"Invalid layout: bad window position or size for panel '{p['id']}'"
            panel['win'] = {k: win[k] for k in ('x', 'y', 'w', 'h')}
        clean.append(panel)
    if seen != set(PANEL_IDS):
        return None, 'Invalid layout: every panel must be listed'
    if all(p['hidden'] for p in clean):
        return None, 'Invalid layout: at least one panel must stay visible'
    return {'panels': clean}, None


def get_layout() -> dict:
    """This user's saved layout, or DEFAULT_LAYOUT. A stored layout that no
    longer validates (e.g. saved before a panel was added) falls back to
    the default instead of breaking the editor."""
    config = _get_or_create_config()
    stored = (config.meta or {}).get(META_KEY) if config else None
    if stored:
        clean, _err = validate_layout(stored)
        if clean:
            return clean
    return DEFAULT_LAYOUT


def save_layout(layout) -> tuple:
    clean, err = validate_layout(layout)
    if err:
        return False, err
    config = _get_or_create_config()
    if not config:
        return False, 'Could not load or create your settings'
    meta = dict(config.meta or {})
    meta[META_KEY] = clean
    config.meta = meta
    db.session.commit()
    return True, 'Layout saved'


def reset_layout() -> dict:
    """Forget this user's layout and return the default one."""
    config = _get_or_create_config()
    if config and config.meta and META_KEY in config.meta:
        meta = dict(config.meta)
        del meta[META_KEY]
        config.meta = meta
        db.session.commit()
    return DEFAULT_LAYOUT
