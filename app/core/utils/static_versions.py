"""Versioned static URLs, so the browser can cache CSS/JS for good.

Every `url_for('static', filename=…)` gets `?v=<file modification time>`
(see the url_defaults hook in app/__init__.py), and a request carrying `v`
is answered with a one-year immutable cache — the browser stops asking.
Change a file and its URL changes, so it is fetched again: nothing to bump
by hand, in development as in production.

ES modules import each other by plain path (`import X from
'/static/js/toaster.js'`); the import map from import_map() — rendered in
base.html before any module — points each of those paths at its
versioned URL, so modules are cached the same way.
"""
import os
import time

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'static')
MODULES_DIR = os.path.join(STATIC_DIR, 'js')
REFRESH_SECONDS = 2   # how often the import map is rebuilt (cheap: one stat per file)
# Never listed in the import map, which is in every page's source: the hidden
# games must stay hidden. Its modules still load (unversioned) on its own page.
HIDDEN_DIRS = (os.path.join(MODULES_DIR, 'starfield'), os.path.join(MODULES_DIR, 'nightshift'))

_map_cache = {'built_at': 0.0, 'imports': {}}


def file_version(filename):
    """Modification time of a static file as an int, or None if it doesn't exist."""
    try:
        return int(os.path.getmtime(os.path.join(STATIC_DIR, filename)))
    except (OSError, ValueError):
        return None


def _module_entries(directory):
    imports = {}
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if name.endswith('.js'):
                path = os.path.join(root, name)
                url = '/static/' + os.path.relpath(path, STATIC_DIR).replace(os.sep, '/')
                try:
                    imports[url] = f'{url}?v={int(os.path.getmtime(path))}'
                except OSError:
                    continue
    return imports


def import_map(hidden=None):
    """{"imports": {"/static/js/x.js": "/static/js/x.js?v=…", …}} for every module in static/js.

    hidden: name of a hidden game dir ('starfield', 'nightshift') whose modules are added —
    only on that game's own page, so its modules are versioned too (otherwise a stale
    cached copy of one of them breaks the game after an update)."""
    hidden_dir = os.path.join(MODULES_DIR, hidden) if hidden else None
    if hidden_dir not in HIDDEN_DIRS:
        hidden_dir = None
    now = time.monotonic()
    if now - _map_cache['built_at'] >= REFRESH_SECONDS:
        _build_map(now)
    if not hidden_dir:
        return _map_cache['imports']
    return {'imports': {**_map_cache['imports']['imports'], **_module_entries(hidden_dir)}}


def _build_map(now):
    imports = {}
    for root, _dirs, files in os.walk(MODULES_DIR):
        if root.startswith(HIDDEN_DIRS):
            continue
        for name in files:
            if not name.endswith('.js'):
                continue
            path = os.path.join(root, name)
            url = '/static/' + os.path.relpath(path, STATIC_DIR).replace(os.sep, '/')
            try:
                imports[url] = f'{url}?v={int(os.path.getmtime(path))}'
            except OSError:
                continue
    _map_cache.update(built_at=now, imports={'imports': imports})
