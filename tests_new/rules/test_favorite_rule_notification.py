"""Issue #84 — users who favorited a rule are notified when its content changes; the API exposes it."""
from app import db
from app.core.db_class.notification import Notification
from app.features.account import account_core as AccountModel
from app.features.notification.notification_core import update_preference
from app.features.rule import rule_core as RuleModel
from tests_new.helpers.rules import make_rule
from tests_new.helpers.users import api_headers


def _change(rule, by, content, change_type="content"):
    return RuleModel.create_rule_history({"id": rule.id, "title": rule.title, "success": True, "message": "edit",
                                          "old_content": rule.to_string, "new_content": content,
                                          "analyzed_by_user_id": by.id, "change_type": change_type})


def _notifs(user):
    return Notification.query.filter_by(user_id=user.id, notif_type="favorite_rule_update").all()


def test_content_change_notifies_favoriters_once(clients, users):
    rule = make_rule(users.owner)
    AccountModel.add_favorite(rule_id=rule.id, user_id=users.user.id)
    AccountModel.add_favorite(rule_id=rule.id, user_id=users.owner.id)
    _change(rule, users.owner, rule.to_string + "\n// v2")
    _change(rule, users.owner, rule.to_string + "\n// v3")
    got = _notifs(users.user)
    assert len(got) == 1                                   # second change updates the unread one
    assert f"/rule/detail_rule/{rule.id}/history" in got[0].link
    assert _notifs(users.owner) == []                      # the author of the change is not notified


def test_metadata_only_or_opted_out_does_not_notify(clients, users):
    rule = make_rule(users.owner)
    AccountModel.add_favorite(rule_id=rule.id, user_id=users.user.id)
    _change(rule, users.owner, rule.to_string, change_type="metadata")
    assert _notifs(users.user) == []
    update_preference(users.user.id, {"favorite_rule_update": False})
    _change(rule, users.owner, rule.to_string + "\n// v2")
    assert _notifs(users.user) == []


def test_api_favorite_status_and_preferences(clients, users):
    rule = make_rule(users.owner)
    h = api_headers(users.user)
    assert clients["anonymous"].get(f"/api/rule/private/favorite_status/{rule.id}").status_code in (401, 403)
    assert clients["anonymous"].get(f"/api/rule/private/favorite_status/{rule.id}", headers=h).get_json()["is_favorited"] is False
    assert clients["anonymous"].get(f"/api/rule/private/favorite/{rule.id}", headers=h).get_json()["is_favorited"] is True
    assert clients["anonymous"].get(f"/api/rule/private/favorite_status/{rule.id}", headers=h).get_json()["is_favorited"] is True
    assert clients["anonymous"].get("/api/rule/private/favorite_status/999999", headers=h).status_code == 404
    prefs = clients["anonymous"].get("/api/account/private/notification_preferences", headers=h).get_json()["preferences"]
    assert prefs["favorite_rule_update"] is True
    r = clients["anonymous"].post("/api/account/private/notification_preferences", headers=h, json={"favorite_rule_update": False})
    assert r.get_json()["preferences"]["favorite_rule_update"] is False
    assert clients["anonymous"].get("/api/account/private/notification_preferences").status_code in (401, 403)
    db.session.expire_all()
