"""Whole-page cache for anonymous visitors (docs/future/caching.md, step 2).

    return anonymous_page(rule_key('page', rule.id, request.host_url, request.full_path),
                          lambda: render_template(...), timeout=1800)

Served from / stored in the shared `cache` only when the page is the same for every anonymous
visitor: a GET, nobody signed in, no API key, and a session holding nothing but the shared anonymous
CSRF value (app/core/utils/anon_csrf.py) — so no flash message, no per-visitor token, nothing of
anyone in the HTML. Everybody else gets the page rendered live, as before.
The key must be a versioned one (cache_versions.rule_key / rules_key): no invalidation to write.
"""
from flask import current_app, make_response, request, session

from app.core.utils import anon_csrf

HEADER = 'X-App-Cache'


def _cache():
    from app import cache
    return cache


def enabled():
    """Admin switch (setting cache.enabled, Admin → Cache)."""
    from app.core.utils.app_settings import get_setting
    try:
        return bool(get_setting('cache.enabled'))
    except Exception:
        return True


def seconds(key, default):
    """A duration setting (cache.rule_page_seconds…), never below 0."""
    from app.core.utils.app_settings import get_setting
    try:
        return max(0, int(get_setting(key)))
    except Exception:
        return default


STATS_KINDS = ('page', 'value')


def count(kind, hit):
    """Hit / miss counters shown on Admin → Cache (rz:stats:<kind>:<hit|miss>, shared by every process)."""
    try:
        _cache().cache.inc(f'rz:stats:{kind}:{"hit" if hit else "miss"}')
    except Exception:
        pass


def stats():
    out = {}
    for k in STATS_KINDS:
        try:
            h = int(_cache().get(f'rz:stats:{k}:hit') or 0)
            m = int(_cache().get(f'rz:stats:{k}:miss') or 0)
        except Exception:
            h = m = 0
        out[k] = {'hit': h, 'miss': m, 'ratio': round(100 * h / (h + m)) if h + m else None}
    return out


def reset_stats():
    for k in STATS_KINDS:
        for w in ('hit', 'miss'):
            try:
                _cache().delete(f'rz:stats:{k}:{w}')
            except Exception:
                pass


def eligible():
    from flask_login import current_user
    if not enabled():
        return False
    if request.method not in ('GET', 'HEAD'):
        return False
    if request.headers.get('X-API-KEY') or request.headers.get('Authorization'):
        return False
    try:
        if current_user.is_authenticated:
            return False
    except Exception:
        return False
    if not set(session.keys()) <= {anon_csrf.FIELD, '_permanent'}:
        return False                       # flash messages, a cart, a 'next'… : not a shared page
    token = session.get(anon_csrf.FIELD)
    return token is None or token in anon_csrf._raws()


def _max_timeout(timeout):
    # The page holds a timed CSRF token: never keep it longer than the token is accepted
    limit = current_app.config.get('WTF_CSRF_TIME_LIMIT', 3600)
    return timeout if not limit else max(60, min(timeout, int(limit) - 600))


def anonymous_page(key, render, timeout=1800):
    if not eligible() or timeout <= 0:
        return render()
    c = _cache()
    try:
        html = c.get(key)
    except Exception:
        html = None
    count('page', html is not None)
    if html is not None:
        resp = make_response(html)
        resp.headers[HEADER] = 'HIT'
        return resp
    resp = make_response(render())
    if resp.status_code == 200 and resp.mimetype == 'text/html' and eligible():   # rendering may have flashed
        try:
            c.set(key, resp.get_data(as_text=True), timeout=_max_timeout(timeout))
        except Exception:
            pass
    resp.headers[HEADER] = 'MISS'
    return resp


def cached_value(key, compute, timeout=600):
    """A value the same for every viewer (MISP export, counts…), from the shared cache."""
    if not enabled() or timeout <= 0:
        return compute()
    c = _cache()
    try:
        v = c.get(key)
    except Exception:
        v = None
    count('value', v is not None)
    if v is None:
        v = compute()
        try:
            c.set(key, v, timeout=timeout)
        except Exception:
            pass
    return v


# ── Public API (step 3) ──────────────────────────────────────────────────────

def api_eligible():
    """A public API answer is the same for every caller only without an API key / session."""
    from flask_login import current_user
    if not enabled() or request.method not in ('GET', 'HEAD'):
        return False
    if request.headers.get('X-API-KEY') or request.headers.get('Authorization'):
        return False
    try:
        return not current_user.is_authenticated
    except Exception:
        return False


def _json_response(body, status):
    from flask import json as fjson
    resp = current_app.response_class(fjson.dumps(body) + '\n', status=status, mimetype='application/json')
    if status == 200:
        resp.add_etag()                    # strong ETag of the body: If-None-Match → 304, nothing sent
        resp.make_conditional(request)
    return resp


def api_cached(kind, rule_arg=None):
    """Decorator for a flask-restx Resource.get returning (dict, status).
    rule_arg: name of the URL argument holding a rule id (the key then follows that rule's version);
    without it the key follows every rule change (rules_key). The answer gets an ETag either way."""
    import functools
    from app.core.utils.cache_versions import rule_key, rules_key

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            if not api_eligible():
                return fn(self, *args, **kwargs)
            timeout = seconds('cache.api_seconds', 300)
            parts = (request.host_url, request.full_path)
            key = (rule_key(f'api:{kind}', kwargs[rule_arg], *parts) if rule_arg
                   else rules_key(f'api:{kind}', *parts))
            hit = None
            if timeout > 0:
                try:
                    hit = _cache().get(key)
                except Exception:
                    hit = None
                count('value', hit is not None)
            if hit is not None:
                body, status = hit
                resp = _json_response(body, status)
                resp.headers[HEADER] = 'HIT'
                return resp
            out = fn(self, *args, **kwargs)
            body, status = (out if isinstance(out, tuple) else (out, 200))[:2]
            if status == 200 and timeout > 0:
                try:
                    _cache().set(key, (body, status), timeout=timeout)
                except Exception:
                    pass
            resp = _json_response(body, status)
            resp.headers[HEADER] = 'MISS'
            return resp
        return wrapper
    return deco
