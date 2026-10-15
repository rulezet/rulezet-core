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

_map_cache = {'built_at': 0.0, 'imports': {}}


def file_version(filename):
    """Modification time of a static file as an int, or None if it doesn't exist."""
    try:
        return int(os.path.getmtime(os.path.join(STATIC_DIR, filename)))
    except (OSError, ValueError):
        return None


def import_map():
    """{"imports": {"/static/js/x.js": "/static/js/x.js?v=…", …}} for every module in static/js."""
    now = time.monotonic()
    if now - _map_cache['built_at'] < REFRESH_SECONDS:
        return _map_cache['imports']
    imports = {}
    for root, _dirs, files in os.walk(MODULES_DIR):
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
    return _map_cache['imports']
