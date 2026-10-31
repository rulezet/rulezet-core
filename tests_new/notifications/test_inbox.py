"""Notifications inbox (inbox_core.py, /notifications/inbox, /bulk, /labels): folders, bulk actions, labels,
muted kinds, auto-archive — always only the user's own notifications."""
import datetime

from app import db
from app.core.db_class.notification import Notification
from app.features.notification.notification_core import create_notification, update_preference


def _notifs(user, n=3, notif_type="rule_comment"):
    return [create_notification(user.id, notif_type, f"Comment {i}", body="hello") for i in range(n)]


def _ids(resp):
    return [n["id"] for n in resp.get_json()["notifications"]]


def test_page_and_menu(clients):
    assert clients["anonymous"].get("/notifications/").status_code in (302, 401)
    html = clients["user"].get("/notifications/?tab=prefs").get_data(as_text=True)
    assert 'data-mailbox-tab="prefs"' in html and "/alert/" in html          # shared menu: inbox · alerts · prefs
    assert 'href="/notifications/"' in clients["user"].get("/alert/").get_data(as_text=True)


def test_folders_and_bulk(clients, users):
    a, b, c = _notifs(users.user)
    other = _notifs(users.owner, 1)[0]
    cl = clients["user"]
    assert sorted(_ids(cl.get("/notifications/inbox"))) == sorted([a.id, b.id, c.id])
    r = cl.post("/notifications/bulk", json={"ids": [a.id, other.id], "action": "archive"})
    assert r.get_json()["changed"] == 1                                      # someone else's id is ignored
    assert db.session.get(Notification, other.id).is_archived is False
    cl.post("/notifications/bulk", json={"ids": [b.id], "action": "star"})
    assert _ids(cl.get("/notifications/inbox?folder=archived")) == [a.id]
    assert _ids(cl.get("/notifications/inbox?folder=starred")) == [b.id]
    data = cl.get("/notifications/inbox?folder=unread&with_ids=1").get_json()
    assert sorted(data["matching_ids"]) == sorted([b.id, c.id]) and data["counts"]["unread"] == 2
    cl.post("/notifications/bulk", json={"ids": [c.id], "action": "delete"})
    assert db.session.get(Notification, c.id) is None
    assert cl.post("/notifications/bulk", json={"ids": [b.id], "action": "nope"}).status_code == 400


def test_search_and_types(clients, users):
    create_notification(users.user.id, "rule_comment", "About YARA")
    create_notification(users.user.id, "bundle_fork", "Merge request")
    cl = clients["user"]
    assert len(_ids(cl.get("/notifications/inbox?search=yara"))) == 1
    assert len(_ids(cl.get("/notifications/inbox?types=bundle_fork"))) == 1


def test_labels(clients, users):
    a, = _notifs(users.user, 1)
    cl = clients["user"]
    lab = cl.post("/notifications/labels", json={"name": "To review", "color": "#198754"}).get_json()["label"]
    assert cl.post("/notifications/labels", json={"name": "to REVIEW"}).status_code == 400   # same name
    assert cl.post("/notifications/labels", json={"name": "x", "color": "red"}).status_code == 400
    cl.post("/notifications/bulk", json={"ids": [a.id], "action": "label_add", "label_id": lab["id"]})
    assert _ids(cl.get(f"/notifications/inbox?label={lab['id']}")) == [a.id]
    # someone else can't use, rename or delete it
    assert clients["owner"].post(f"/notifications/labels/{lab['id']}", json={"name": "mine"}).status_code == 404
    assert clients["owner"].delete(f"/notifications/labels/{lab['id']}").status_code == 404
    assert cl.post(f"/notifications/labels/{lab['id']}", json={"name": "Later"}).status_code == 200
    assert cl.delete(f"/notifications/labels/{lab['id']}").status_code == 200
    assert db.session.get(Notification, a.id) is not None and db.session.get(Notification, a.id).labels == []


def test_muted_kind_never_arrives(app, users):
    update_preference(users.user.id, {"muted_types": ["bundle_fork"]})
    assert create_notification(users.user.id, "bundle_fork", "x") is None or \
        Notification.query.filter_by(user_id=users.user.id, notif_type="bundle_fork").count() == 0
    create_notification(users.user.id, "rule_comment", "y")
    assert Notification.query.filter_by(user_id=users.user.id).count() == 1


def test_auto_archive(clients, users):
    old, new = _notifs(users.user, 2)
    old.is_read, old.created_at = True, datetime.datetime.utcnow() - datetime.timedelta(days=40)
    db.session.commit()
    update_preference(users.user.id, {"auto_archive_days": 30})
    assert _ids(clients["user"].get("/notifications/inbox")) == [new.id]
    assert db.session.get(Notification, old.id).is_archived is True
