"""_log_api_request (app/api/api.py's after_request audit hook) must only
write a category='api' ActivityLog row for a genuine X-API-KEY request.
Several /api/* namespaces (comments, ...) are dual-purpose: the website's
own frontend calls them directly over the logged-in session with no API
key at all, and that must NOT show up as "API Activity" — it's just the
site using its own route, and where it matters (e.g. comment hard-delete)
the route already writes its own correctly-categorized log_activity() call."""

import uuid as uuid_mod

from app import db
from app.core.db_class.db import ActivityLog, UnifiedComment, User


def _login(client, email):
    user = User.query.filter_by(email=email).first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    return user


def _make_comment(app):
    with app.app_context():
        admin = User.query.filter_by(email="admin@admin.admin").first()
        comment = UnifiedComment(
            uuid=str(uuid_mod.uuid4()), content="hi", object_type="rule", object_id=1,
            created_by=admin.id,
        )
        db.session.add(comment)
        db.session.commit()
        return comment.uuid


def test_session_only_request_does_not_create_api_activity_log(app, client):
    comment_uuid = _make_comment(app)
    with app.app_context():
        _login(client, "admin@admin.admin")

    with app.app_context():
        before = ActivityLog.query.filter_by(category="api").count()

    res = client.delete(f"/api/comments/{comment_uuid}/hard_delete")
    assert res.status_code == 200

    with app.app_context():
        after_api = ActivityLog.query.filter_by(category="api").count()
        hard_delete_logged = ActivityLog.query.filter_by(action="comment.hard_delete").first()

    # No new 'api' category row from the after_request hook...
    assert after_api == before
    # ...but the route's own specific log_activity() call still fired.
    assert hard_delete_logged is not None


def test_api_key_request_creates_api_activity_log(app, client):
    """comment_api.py's own moderation check is session-only (_can_moderate
    checks flask-login's current_user, not the API key), so an API-key-only
    call with no session still 403s here — that's a separate, pre-existing
    gap in that endpoint's own auth, not this test's concern. What this
    guards is the audit hook itself: presenting a real API key must still
    produce a category='api' log row regardless of what the endpoint
    itself decides to do with the request."""
    comment_uuid = _make_comment(app)

    with app.app_context():
        before = ActivityLog.query.filter_by(category="api").count()

    res = client.delete(
        f"/api/comments/{comment_uuid}/hard_delete",
        headers={"X-API-KEY": "admin_api_key"},
    )
    assert res.status_code == 403

    with app.app_context():
        after = ActivityLog.query.filter_by(category="api").count()
        entry = (ActivityLog.query.filter_by(category="api", method="DELETE")
                 .order_by(ActivityLog.id.desc()).first())

    assert after == before + 1
    assert entry is not None
    assert f"/api/comments/{comment_uuid}/hard_delete" in entry.url
