"""
nav_state.py — the figures the navbar shows on every page (admin "to check" counters, unread
notifications, whether the user has a background job running), rendered into the page instead of
fetched by it: no request after the page loads, reload the page to see them change.

Cached per user for NAV_TTL seconds (one page load after another doesn't recount); anything that
must show at once (a notification just read, a job just started) still updates in the page itself.
"""
NAV_TTL = 20


def _count(fn):
    try:
        return int(fn() or 0)
    except Exception:
        return 0


def compute(user):
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.notification import Notification
    from app.features.account import account_core as AccountModel
    from app.features.messages.messages_core import unread_total
    from app.features.rule import rule_core as RuleModel
    admin = user.is_admin()
    state = {
        'unread': _count(lambda: Notification.query.filter_by(user_id=user.id, is_read=False).count()),
        'active_jobs': _count(lambda: BackgroundJob.query.filter(
            BackgroundJob.created_by == user.id,
            BackgroundJob.status.in_(['pending', 'running', 'paused'])).count()),
        'requests_to_check': _count(AccountModel.get_total_requests_to_check_admin if admin
                                    else AccountModel.get_total_requests_to_check),
        'changes_to_check': _count(RuleModel.get_total_change_to_check_admin if admin
                                   else RuleModel.get_total_change_to_check),
        'updates_to_check': _count(RuleModel.get_update_pending),
        'reports_to_check': 0,
        'messages_unread': _count(lambda: unread_total(user)),
    }
    if admin:
        from app.features.report.report_core import count_pending
        state['reports_to_check'] = _count(count_pending)
    return state


def nav_state(user):
    """{} for a visitor; the user's figures (cached NAV_TTL s) otherwise."""
    if not user.is_authenticated:
        return {}
    from app import cache as memory_cache   # shared (Redis in prod): every worker sees a forget()
    key = f'nav_state:{user.id}'
    try:
        cached = memory_cache.get(key)
    except Exception:
        cached = None
    if cached is not None:
        return cached
    state = compute(user)
    try:
        memory_cache.set(key, state, timeout=NAV_TTL)
    except Exception:
        pass
    return state


def forget(user_id):
    """Drop a user's cached figures (e.g. they just read their notifications)."""
    from app import cache as memory_cache   # shared (Redis in prod): every worker sees a forget()
    try:
        memory_cache.delete(f'nav_state:{user_id}')
    except Exception:
        pass
