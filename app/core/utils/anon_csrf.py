"""CSRF without a session for anonymous visitors, so their pages can be cached (docs/future/caching.md).

Every page calls csrf_token() (base.html), which used to create a server-side session for every
cookieless visitor: one `flask_sessions` row + a Set-Cookie per crawler hit, and a page nginx can
never cache. Now an anonymous visitor without a session gets a token derived from a raw value
shared by all anonymous visitors (HMAC of SECRET_KEY + the day), and no session at all.
On their first POST the session is created with that raw value, so Flask-WTF validates as usual.

Kept as before (a session of its own): signed-in users, visitors who already have a session,
and the account pages (login, register, password reset…) — a shared token there would allow
login CSRF. Those pages set a cookie, so they are never cached. A session that got the shared
value (an anonymous POST, a flash message) swaps it for its own random one on sign-in or on an account page.
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from flask import current_app, request, session

FIELD = 'csrf_token'                       # Flask-WTF's session key (WTF_CSRF_FIELD_NAME default)
OWN_SESSION_ENDPOINTS = {
    'account.login', 'account.add_user', 'account.verify', 'account.forgot_password',
    'account.reset_password', 'account.oidc_login',
}


def shared_raw(day=None):
    day = day or datetime.now(timezone.utc).date()
    key = (current_app.config.get('SECRET_KEY') or '').encode()
    return hmac.new(key, f'rz-anon-csrf:{day.isoformat()}'.encode(), hashlib.sha256).hexdigest()


def _raws():
    today = datetime.now(timezone.utc).date()
    return {shared_raw(today), shared_raw(today - timedelta(days=1))}


def _anonymous():
    from flask_login import current_user
    try:
        return not current_user.is_authenticated
    except Exception:
        return False


def _same_origin():
    """A browser always sends Origin on a cross-site POST: the shared token is never accepted from another site."""
    from urllib.parse import urlsplit
    origin = request.headers.get('Origin')
    if origin is None:
        ref = request.headers.get('Referer')
        if not ref:
            return True                    # not a browser form / fetch (no cross-site risk)
        origin = ref
    if origin == 'null':
        return False
    o = urlsplit(origin)
    return (o.netloc or '').lower() == request.host.lower()


def _applies():
    if not current_app.config.get('SECRET_KEY'):
        return False                       # no secret: the shared value would be guessable, keep sessions
    return (request.endpoint not in OWN_SESSION_ENDPOINTS and request.endpoint != 'static'
            and FIELD not in session and _anonymous())


def _posted_raw():
    """The raw value inside the posted token, when it is one of the shared ones."""
    from itsdangerous import BadData, URLSafeTimedSerializer
    token = request.headers.get('X-CSRFToken') or request.headers.get('X-CSRF-Token') or request.form.get(FIELD)
    if not token:
        return None
    try:
        raw = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='wtf-csrf-token').loads(token)
    except BadData:
        return None
    return raw if raw in _raws() else None


def before_request():
    # A session that still holds the shared value must get its own as soon as it matters:
    # signed in (a known token would be a real CSRF hole) or on an account page (login CSRF)
    if session.get(FIELD) in _raws() and (request.endpoint in OWN_SESSION_ENDPOINTS or not _anonymous()):
        session.pop(FIELD)                 # Flask-WTF draws a fresh random one
        return
    if not _applies():
        return
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        session[FIELD] = shared_raw()      # csrf_token() signs this value; dropped again in after_request
    else:
        raw = _posted_raw() if _same_origin() else None
        if raw:
            session[FIELD] = raw           # a real session from now on: Flask-WTF validates as usual


def after_request(response):
    """Anonymous GET whose session holds nothing but the shared value: no session, no cookie."""
    # ('_permanent' is Flask-Session's own flag, SESSION_PERMANENT)
    if (request.method in ('GET', 'HEAD', 'OPTIONS') and session.get(FIELD) in _raws()
            and set(session.keys()) <= {FIELD, '_permanent'}):
        session.clear()
        session.modified = False
    return response


def init_app(app):
    # Before Flask-WTF's own check (registered earlier by csrf.init_app): insert first
    app.before_request_funcs.setdefault(None, []).insert(0, before_request)
    app.after_request(after_request)
