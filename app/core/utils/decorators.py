from functools import wraps
from flask import abort, request, g
from app.core.utils.utils import verif_api_key


_NO_USER = object()


def _run_as_api_user(user, f, *args, **kwargs):
    """Run `f` with `user` as Flask-Login's current_user for this call only.

    An X-API-KEY request has no session, so current_user used to stay
    anonymous inside API routes: log_activity() recorded no author ("System"
    in the logs), bundle history had no author and every current_user-based
    permission check (can_view_bundle…) treated the key owner as a visitor.
    No login_user(): no session cookie is ever issued to an API client.
    The previous value is restored afterwards (tests run several requests
    inside one app context, where `g` outlives the request)."""
    prev_user = g.get('_login_user', _NO_USER)
    prev_flag = g.get('_api_key_user', _NO_USER)
    g._login_user = user
    g._api_key_user = True
    try:
        return f(*args, **kwargs)
    finally:
        for key, prev in (('_login_user', prev_user), ('_api_key_user', prev_flag)):
            if prev is _NO_USER:
                g.pop(key, None)
            else:
                setattr(g, key, prev)


def verification_required():
    """Restrict API access to users without a valid key"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.path.startswith("/api/"):
                if not verif_api_key(request.headers):
                    abort(403)
                from app.core.utils.utils import get_user_from_api
                return _run_as_api_user(get_user_from_api(request.headers), f, *args, **kwargs)

            return f(*args, **kwargs)

        return decorated_function

    return decorator





def api_required(f):
    return verification_required()(f)


def api_optional(f):
    """Public API route that also honours an X-API-KEY when one is sent:
    with a valid key the call runs as that user (e.g. an owner reading their
    own private bundle); without one — or with an unknown key — it runs
    anonymously, exactly like a plain public call."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.core.utils.utils import get_user_from_api
        user = get_user_from_api(request.headers) if request.headers.get("X-API-KEY") else None
        if user is not None:
            return _run_as_api_user(user, f, *args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function
