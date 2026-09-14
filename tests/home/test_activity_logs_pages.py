"""/admin/logs/connections and /admin/logs/api — dedicated, pre-filtered
views split out of the main /admin/logs page so login/logout and API
traffic don't bury everything else. Same ActivityLog table, just scoped
server-side (fixed_actions / fixed_category in _build_logs_query) —
these tests mainly guard that scoping, plus that the general endpoint's
own action/category filters still work after the refactor."""

from app.core.db_class.db import User
from app.core.utils.activity_log import log_activity


def _login(client, email):
    user = User.query.filter_by(email=email).first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    return user


def _login_admin(app, client):
    with app.app_context():
        return _login(client, "admin@admin.admin")


def _login_plain_user(app, client):
    with app.app_context():
        return _login(client, "t@t.t")


_LOG_PAGE_URLS = ("/admin/logs", "/admin/logs/connections", "/admin/logs/api", "/admin/logs/definitions")


def test_pages_require_admin(client):
    for url in _LOG_PAGE_URLS:
        res = client.get(url)
        assert res.status_code == 302  # not logged in -> redirected to login


def test_pages_deny_non_admin(app, client):
    _login_plain_user(app, client)
    for url in _LOG_PAGE_URLS:
        res = client.get(url)
        assert res.status_code == 200
        assert b"Access denied" in res.data


def test_pages_render_for_admin(app, client):
    _login_admin(app, client)
    for url, needle in (
        ("/admin/logs", b"Activity Logs"),
        ("/admin/logs/connections", b"User Connections"),
        ("/admin/logs/api", b"API Activity"),
        ("/admin/logs/definitions", b"Log Definitions"),
    ):
        res = client.get(url)
        assert res.status_code == 200
        assert needle in res.data


def test_all_four_log_pages_link_to_each_other(app, client):
    """Every log page's nav row must carry links to all three sibling
    pages (the fourth being itself) — the whole point of the shared
    logs_nav_items macro."""
    _login_admin(app, client)
    for url in _LOG_PAGE_URLS:
        res = client.get(url)
        for other in _LOG_PAGE_URLS:
            assert other.encode() in res.data, f"{url} is missing a link to {other}"


def test_connection_logs_endpoint_only_returns_login_logout(app, client):
    with app.app_context():
        admin = User.query.filter_by(email="admin@admin.admin").first()
        log_activity("user.login", "logged in", actor_id=admin.id)
        log_activity("user.logout", "logged out", actor_id=admin.id)
        log_activity("rule.create", "unrelated rule action", actor_id=admin.id)

    _login_admin(app, client)
    data = client.get("/admin/get_connection_logs_page?per_page=100").get_json()
    actions = {item["action"] for item in data["items"]}
    assert actions <= {"user.login", "user.logout"}
    assert "user.login" in actions
    assert "user.logout" in actions


def test_connection_logs_endpoint_ignores_client_category_override(app, client):
    """fixed_actions must win even if a caller tries to widen the filter
    with a category param — this is what hideCategoryFilter's LogTable
    prop exists to avoid confusing the user about in the first place."""
    with app.app_context():
        admin = User.query.filter_by(email="admin@admin.admin").first()
        log_activity("user.login", "logged in", actor_id=admin.id)
        log_activity("rule.create", "unrelated rule action", actor_id=admin.id)

    _login_admin(app, client)
    data = client.get("/admin/get_connection_logs_page?category=rule&per_page=100").get_json()
    actions = {item["action"] for item in data["items"]}
    assert "rule.create" not in actions


def test_api_logs_endpoint_only_returns_api_category(app, client):
    with app.app_context():
        admin = User.query.filter_by(email="admin@admin.admin").first()
        log_activity("api.request", "GET /api/rule/public/all", actor_id=admin.id,
                     category="api", icon="fa-solid fa-code")
        log_activity("rule.create", "unrelated rule action", actor_id=admin.id)

    _login_admin(app, client)
    data = client.get("/admin/get_api_logs_page?per_page=100").get_json()
    categories = {item["category"] for item in data["items"]}
    assert categories <= {"api"}
    assert len(data["items"]) >= 1


def test_general_logs_endpoint_still_supports_action_and_category_filters(app, client):
    """Regression check for the _build_logs_query refactor — the
    general /admin/get_logs_page endpoint's own free-form action/category
    params (unlike the two pinned endpoints above) must keep working."""
    with app.app_context():
        admin = User.query.filter_by(email="admin@admin.admin").first()
        log_activity("user.login", "logged in", actor_id=admin.id)
        log_activity("rule.create", "unrelated rule action", actor_id=admin.id)

    _login_admin(app, client)
    by_action = client.get("/admin/get_logs_page?action=user.login&per_page=100").get_json()
    assert all(item["action"] == "user.login" for item in by_action["items"])

    by_category = client.get("/admin/get_logs_page?category=rule&per_page=100").get_json()
    assert all(item["category"] == "rule" for item in by_category["items"])
