"""Admin-editable settings — the lists, tables and labels that used to be
written in the code.

Each setting is one JSON file in app/config/, named after its key
(`app/config/gamification.points.json`):

    {
      "label": "Points per contribution",
      "category": "Gamification",
      "description": "…",
      "public": false,            # readable by anyone at /api/config/settings/<key>
      "python_type": "tuple",     # optional: tuple | set | dict_int_keys (JSON has none of these)
      "value": { … }
    }

Adding a file is enough: it shows up on Admin → Configuration and the code
can read it with get_setting('<key>'). The file holds the default; a value
changed from the admin page is stored in the `app_setting` table (never
written back to the file, so `git pull` keeps working on a server), and
"Reset" deletes it to go back to the file.

Updates without conflicts: the row keeps the file value the admin started
from (base_value). When an update changes the file, the current value is a
three-way merge — the new file value with the admin's own changes applied
on top (see merge_values) — so a new entry shipped by the update shows up
and the admin's edits are kept. The page flags it ("file updated") and lets
the admin accept the merge or go back to the file. Every change is kept in
app_setting_history and can be restored.

In the code, `setting('<key>')` returns a live value: it behaves like the
dict / list / tuple (`X['a']`, `x in X`, `for … in X`, `X.items()`…) and
reads the current value on every access. Use `.value` where a real object is
required (`str.startswith(X.value)`, `|tojson`).
"""
import copy
import datetime
import json
import os
import time

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config')
CACHE_SECONDS = 30

_files_cache = {'signature': None, 'definitions': {}}
_db_cache = {'loaded_at': 0.0, 'values': {}}


# ── The JSON files ───────────────────────────────────────────────────────────

def _files_signature():
    try:
        names = sorted(n for n in os.listdir(CONFIG_DIR) if n.endswith('.json'))
    except FileNotFoundError:
        return ()
    return tuple((n, os.path.getmtime(os.path.join(CONFIG_DIR, n))) for n in names)


def _definitions():
    """{key: definition} read from app/config/*.json — re-read as soon as a
    file is added, removed or changed."""
    signature = _files_signature()
    if signature == _files_cache['signature']:
        return _files_cache['definitions']
    definitions = {}
    for name, _mtime in signature:
        key = name[:-len('.json')]
        path = os.path.join(CONFIG_DIR, name)
        try:
            with open(path, encoding='utf-8') as f:
                doc = json.load(f)
        except (OSError, ValueError) as e:
            definitions[key] = {'key': key, 'error': f'{name}: {e}', 'value': None, 'label': key,
                                'category': 'Invalid files', 'description': '', 'public': False, 'python_type': None}
            continue
        definitions[key] = {
            'key': key,
            'label': doc.get('label') or key,
            'category': doc.get('category') or 'Other',
            'description': doc.get('description') or '',
            'public': bool(doc.get('public')),
            'python_type': doc.get('python_type'),
            'value': doc.get('value'),
            'error': None if 'value' in doc else f'{name}: no "value" field',
        }
    _files_cache.update(signature=signature, definitions=definitions)
    return definitions


def _default(key):
    definitions = _definitions()
    if key not in definitions:
        raise KeyError(f"No setting '{key}' — add app/config/{key}.json")
    return definitions[key]


# ── Reading ──────────────────────────────────────────────────────────────────

_MISSING = object()


def merge_values(base, mine, theirs):
    """Three-way merge of JSON values: `base` is the file value the admin
    edited, `mine` the admin's value, `theirs` the file value now.

    dict: start from `theirs`; keys the admin changed or added keep the
    admin's value (merged recursively when both sides are dicts), keys the
    admin removed stay removed. list: the admin's list plus the items the
    update added. Anything else: the admin's value wins."""
    if base == theirs:
        return mine
    if isinstance(mine, dict) and isinstance(theirs, dict):
        base = base if isinstance(base, dict) else {}
        out = dict(theirs)
        for k, v in mine.items():
            b = base.get(k, _MISSING)
            if b is _MISSING or v != b:
                t = theirs.get(k, _MISSING)
                out[k] = merge_values(b if b is not _MISSING else None, v, t) if isinstance(v, dict) and isinstance(t, dict) else v
        for k in base:
            if k not in mine:
                out.pop(k, None)
        return out
    if isinstance(mine, list) and isinstance(theirs, list):
        base = base if isinstance(base, list) else []
        return list(mine) + [x for x in theirs if x not in base and x not in mine]
    return mine


def _stored_values():
    """{key: value} changed from the admin page, cached for CACHE_SECONDS.
    Empty outside an app context (module import time, scripts)."""
    now = time.monotonic()
    if now - _db_cache['loaded_at'] < CACHE_SECONDS:
        return _db_cache['values']
    try:
        from app import db
        from app.core.db_class.setting import AppSetting
        # In a savepoint: if the table doesn't exist yet (before its
        # migration), the failed query must not abort the caller's transaction.
        with db.session.begin_nested():
            rows = AppSetting.query.all()
            values = {row.key: row.value for row in rows}
            bases = {row.key: row.base_value for row in rows}
    except Exception:
        # No app context yet, or the table doesn't exist.
        return {}
    _db_cache.update(values=values, bases=bases, loaded_at=now)
    return values


def _stored_base(key):
    """File value the admin's value was made from (None for rows saved
    before base_value existed)."""
    _stored_values()
    return _db_cache.get('bases', {}).get(key)


def current_json_value(key):
    """Current value as JSON: file value, admin value, or their merge when
    the file changed since the admin's edit."""
    definition = _default(key)
    stored = _stored_values()
    if key not in stored:
        return definition['value']
    base = _stored_base(key)
    if base is None:
        return stored[key]
    return merge_values(base, stored[key], definition['value'])


def clear_cache():
    _db_cache['loaded_at'] = 0.0


def get_setting(key):
    """Current value: the admin's one if set, else the file's — with the
    Python type the file declares (python_type)."""
    definition = _default(key)
    return _as_python(current_json_value(key), definition['python_type'])


def _as_python(value, python_type):
    if python_type == 'tuple':
        return tuple(value)
    if python_type == 'set':
        return set(value)
    if python_type == 'dict_int_keys':
        return {int(k): v for k, v in value.items()}
    return value


def setting(key):
    """Live value of a setting, to assign to a module constant:
    `POINTS = setting('gamification.points')`."""
    return LiveSetting(key)


def get_public_setting(key):
    """JSON value of a public setting, or None if *key* isn't one."""
    definition = _definitions().get(key)
    if not definition or not definition['public'] or definition['error']:
        return None
    return current_json_value(key)


# ── Writing ──────────────────────────────────────────────────────────────────

def validate(key, value):
    """Error message, or None when *value* can replace the file's value."""
    default = _default(key)['value']
    if isinstance(default, dict):
        if not isinstance(value, dict):
            return 'Expected a JSON object { … }.'
        if _default(key)['python_type'] == 'dict_int_keys':
            try:
                [int(k) for k in value]
            except ValueError:
                return 'Every key must be a whole number.'
        sample = next(iter(default.values()), None)
        if isinstance(sample, (int, float)) and not isinstance(sample, bool):
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value.values()):
                return 'Every value must be a number.'
        if isinstance(sample, str) and not all(isinstance(v, str) for v in value.values()):
            return 'Every value must be a text.'
    elif isinstance(default, list):
        if not isinstance(value, list):
            return 'Expected a JSON list [ … ].'
        sample = next(iter(default), None)
        if isinstance(sample, str) and not all(isinstance(v, str) for v in value):
            return 'Every item must be a text.'
    return None


def _log(key, action, value, base_value, user_id):
    from app import db
    from app.core.db_class.setting import AppSettingHistory
    db.session.add(AppSettingHistory(key=key, action=action, value=value, base_value=base_value, user_id=user_id))


def set_setting(key, value, user_id=None, action='saved', base_value=None):
    """Store the admin's value, based on the file value as it is now (or on
    *base_value*: the file value an older version was made from)."""
    from app import db
    from app.core.db_class.setting import AppSetting
    file_value = _default(key)['value'] if base_value is None else base_value
    row = db.session.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key)
        db.session.add(row)
    row.value = value
    row.base_value = file_value
    row.updated_by_id = user_id
    row.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    _log(key, action, value, file_value, user_id)
    db.session.commit()
    clear_cache()


def accept_merge(key, user_id=None):
    """Keep the merged value (file update + admin changes) as the new admin
    value, based on the current file — the "file updated" flag goes away."""
    set_setting(key, current_json_value(key), user_id=user_id, action='merged')


def reset_setting(key, user_id=None):
    """Back to the value of the JSON file."""
    from app import db
    from app.core.db_class.setting import AppSetting
    file_value = _default(key)['value']
    AppSetting.query.filter_by(key=key).delete()
    _log(key, 'reset', file_value, file_value, user_id)
    db.session.commit()
    clear_cache()


def setting_history(key, limit=50):
    from app.core.db_class.setting import AppSettingHistory
    rows = (AppSettingHistory.query.filter_by(key=key)
            .order_by(AppSettingHistory.created_at.desc(), AppSettingHistory.id.desc()).limit(limit).all())
    return [r.to_json() for r in rows]


def restore_version(key, history_id, user_id=None):
    """Make an earlier version the current value again. Returns False if the
    entry doesn't belong to *key*."""
    from app import db
    from app.core.db_class.setting import AppSettingHistory
    entry = db.session.get(AppSettingHistory, history_id)
    if entry is None or entry.key != key:
        return False
    if entry.action == 'reset':
        reset_setting(key, user_id=user_id)
    else:
        # Keep the version's own base: if the file changed since, the merge
        # re-applies the update on top of the restored value.
        set_setting(key, entry.value, user_id=user_id, action='restored', base_value=entry.base_value)
    return True


def list_settings():
    """Every setting of app/config/ with its file value and current value."""
    stored = _stored_values()
    out = []
    for key, d in sorted(_definitions().items(), key=lambda kv: (kv[1]['category'], kv[1]['label'])):
        base = _stored_base(key) if key in stored else None
        file_changed = key in stored and base is not None and base != d['value']
        out.append({
            'key': key,
            'file': f'app/config/{key}.json',
            'label': d['label'],
            'category': d['category'],
            'description': d['description'],
            'public': d['public'],
            'kind': type(d['value']).__name__ if d['value'] is not None else None,
            'default': d['value'],
            'value': current_json_value(key) if not d['error'] else None,
            'admin_value': stored.get(key),
            'base_value': base,
            'overridden': key in stored,
            'file_changed': file_changed,
            'error': d['error'],
        })
    return out


# ── Live value ───────────────────────────────────────────────────────────────

class LiveSetting:
    """Stands in for the setting's value and reads the current one on every
    access."""

    __slots__ = ('key',)

    def __init__(self, key):
        self.key = key

    @property
    def value(self):
        return get_setting(self.key)

    def __getitem__(self, item):
        return self.value[item]

    def __contains__(self, item):
        return item in self.value

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __bool__(self):
        return bool(self.value)

    def __eq__(self, other):
        return self.value == (other.value if isinstance(other, LiveSetting) else other)

    __hash__ = None

    def __repr__(self):
        return f'LiveSetting({self.key!r})'

    def __getattr__(self, name):
        # dict/list methods: get, keys, values, items, index, count, copy…
        return getattr(self.value, name)

    def __deepcopy__(self, memo):
        return copy.deepcopy(self.value, memo)
