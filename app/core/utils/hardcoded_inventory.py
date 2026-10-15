"""Inventory of the values written in the code: every module-level constant
that is a list, dict, tuple or set (3 items or more), plus the data files
(JSON / TXT) shipped next to the code.

Read straight from the source files on each call, so the admin
Configuration page always lists what is really in the code — nothing to
keep up to date by hand. Constants read with app_settings.setting('<key>')
are reported as editable (their value lives in app/config/<key>.json).
"""
import ast
import functools
import os

APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_DIR = os.path.dirname(APP_DIR)

# Third-party code vendored into the tree, cloned rule repositories, uploads.
_SKIP_PARTS = ('Rules_Github', 'rule_from_github/Rules', '/modules/', '/static/', '/uploads/',
               '/media_overrides/', '__pycache__', '/templates/')
CONFIG_DIR = os.path.join(APP_DIR, 'config')
_DATA_EXTENSIONS = ('.json', '.txt')
MIN_ITEMS = 3


def _python_files():
    for root, _dirs, files in os.walk(APP_DIR):
        if any(part in root + '/' for part in _SKIP_PARTS):
            continue
        for name in files:
            if name.endswith('.py'):
                yield os.path.join(root, name)


def _module_name(path):
    rel = os.path.relpath(path, REPO_DIR)[:-3].replace(os.sep, '.')
    return rel[:-len('.__init__')] if rel.endswith('.__init__') else rel


def _size(node):
    if isinstance(node, ast.Dict):
        return len(node.keys)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return len(node.elts)
    return None


def _setting_call(node):
    """The setting key when *node* is `setting('key')`, else None."""
    if isinstance(node, ast.Call) and getattr(node.func, 'id', getattr(node.func, 'attr', None)) == 'setting':
        if node.args and isinstance(node.args[0], ast.Constant):
            return node.args[0].value
    return None


@functools.lru_cache(maxsize=1)
def _scan(_mtime_key):
    entries = []
    for path in _python_files():
        try:
            source = open(path, encoding='utf-8').read()
            tree = ast.parse(source)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if not isinstance(target, ast.Name) or not target.id.lstrip('_').isupper():
                continue
            setting_key = _setting_call(node.value)
            value_node = node.value
            size = _size(value_node)
            if setting_key is None and (size is None or size < MIN_ITEMS):
                continue
            entries.append({
                'name': target.id,
                'file': os.path.relpath(path, REPO_DIR),
                'module': _module_name(path),
                'line': node.lineno,
                'lines': node.end_lineno - node.lineno + 1,
                'type': 'json file' if setting_key else type(value_node).__name__.lower(),
                'items': size,
                'setting_key': setting_key,
                'preview': ast.get_source_segment(source, node)[:4000],
            })
    return entries


def _tree_mtime():
    """Changes whenever a source file changes — invalidates the scan cache."""
    latest = 0.0
    for path in _python_files():
        try:
            latest = max(latest, os.path.getmtime(path))
        except OSError:
            pass
    return latest


def list_constants():
    return sorted(_scan(_tree_mtime()), key=lambda e: (e['setting_key'] is None, e['file'], e['line']))


def list_data_files():
    out = []
    for root, _dirs, files in os.walk(APP_DIR):
        if any(part in root + '/' for part in _SKIP_PARTS) or root.startswith(CONFIG_DIR):
            continue
        for name in files:
            if name.endswith(_DATA_EXTENSIONS):
                path = os.path.join(root, name)
                out.append({'file': os.path.relpath(path, REPO_DIR), 'bytes': os.path.getsize(path)})
    return sorted(out, key=lambda f: f['file'])
