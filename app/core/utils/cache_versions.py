"""Versioned cache keys for rules (docs/future/caching.md, step 4).

Instead of deleting cache entries when something changes (easy to forget one), every cached
value that depends on rules has a *generation* in its key:

    rule_key('page', rule_id)      -> "rz:rule:page:<id>:<gen of the rule>:<bulk gen>"
    rules_key('list', <args>)      -> "rz:rules:list:<global gen>:<hash of args>"

A commit that touches a rule (the Rule row, or any row with a rule_id: votes, comments, tags,
history, bundles, proposals…) bumps that rule's generation and the global one, automatically
(SQLAlchemy session events, see init_app). A bulk UPDATE / DELETE (query.update(), soft-delete
batches…) bumps the "bulk" generation, which every rule key contains. Old entries are never read
again and expire on their own timeout.

A generation is a unique value (time in ns), never a counter: if it is evicted from the cache it
comes back as a new value, so an old entry can never become valid again.
Counters live in the shared `cache` (Redis in production) — every process (site, API, worker) sees them.
"""
import hashlib
import json
import time

from sqlalchemy import event

GLOBAL = 'rz:gen:rules'
BULK = 'rz:gen:bulk'


def _cache():
    from app import cache
    return cache


def _now():
    return str(time.time_ns())


def _get(key):
    c = _cache()
    try:
        v = c.get(key)
    except Exception:
        v = None
    if v is None:
        v = _now()
        try:
            c.set(key, v, timeout=0)       # never expires on its own
        except Exception:
            pass
    return v


def _bump(key):
    try:
        _cache().set(key, _now(), timeout=0)
    except Exception:
        pass                               # a cache is an optimisation, it never breaks a commit


def rule_gen(rule_id):
    return _get(f'rz:gen:rule:{int(rule_id)}')


def global_gen():
    return _get(GLOBAL)


def bulk_gen():
    return _get(BULK)


def bump_rule(rule_id):
    _bump(f'rz:gen:rule:{int(rule_id)}')
    _bump(GLOBAL)


def bump_all():
    _bump(BULK)
    _bump(GLOBAL)


def _digest(parts):
    raw = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def rule_key(kind, rule_id, *parts):
    """Key of a value about one rule: changes whenever that rule (or anything with its rule_id) changes."""
    extra = f':{_digest(parts)}' if parts else ''
    return f'rz:rule:{kind}:{int(rule_id)}:{rule_gen(rule_id)}:{bulk_gen()}{extra}'


def rules_key(kind, *parts):
    """Key of a value about many rules (lists, searches, stats): changes on any rule change."""
    return f'rz:rules:{kind}:{global_gen()}:{_digest(parts)}'


# ── Automatic bumps ─────────────────────────────────────────────────────────

def _touched_rule_ids(session):
    from app.core.db_class.rule import Rule
    ids, other = set(), False
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        if isinstance(obj, Rule):
            if obj.id is not None:
                ids.add(obj.id)
            else:
                other = True               # a new rule: lists change, no page cached yet
        else:
            rid = getattr(obj, 'rule_id', None)
            if isinstance(rid, int):
                ids.add(rid)
    return ids, other


def _after_flush(session, flush_context):
    ids, other = _touched_rule_ids(session)
    pending = session.info.setdefault('rz_touched_rules', set())
    pending.update(ids)
    if other:
        session.info['rz_touched_any'] = True


def _after_commit(session):
    ids = session.info.pop('rz_touched_rules', set())
    anything = session.info.pop('rz_touched_any', False)
    bulk = session.info.pop('rz_touched_bulk', False)
    if bulk:
        bump_all()
    for rid in ids:
        bump_rule(rid)
    if anything and not ids and not bulk:
        _bump(GLOBAL)


def _after_rollback(session):
    for k in ('rz_touched_rules', 'rz_touched_any', 'rz_touched_bulk'):
        session.info.pop(k, None)


def _rule_tables():
    """Tables whose rows are about rules: rule itself + every table with a rule_id column."""
    from app import db
    return {t.name for t in db.metadata.tables.values() if t.name == 'rule' or 'rule_id' in t.c}


def _do_orm_execute(state):
    if not (state.is_update or state.is_delete):
        return
    try:
        table = state.statement.table.name
    except Exception:
        table = None
    if table is None or table in _rule_tables():
        state.session.info['rz_touched_bulk'] = True


_installed = False


def init_app(app):
    global _installed
    if _installed:
        return
    from sqlalchemy.orm import Session
    event.listen(Session, 'after_flush', _after_flush)
    event.listen(Session, 'after_commit', _after_commit)
    event.listen(Session, 'after_rollback', _after_rollback)
    event.listen(Session, 'do_orm_execute', _do_orm_execute)
    _installed = True
