"""Collections — layer 2: folders, items, reminders, and what happens to them
when a rule / bundle / user is deleted."""
import datetime

from app import db
from app.core.db_class.collection import UserCollection, UserCollectionItem
from app.core.db_class.notification import Notification
from app.features.collection import collection_core as CC
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule


def _folder(user, name="F", **kw):
    folder, msg = CC.create_folder(user.id, {"name": name, **kw})
    assert folder, msg
    return folder


def test_first_visit_creates_the_default_folders(clients, users):
    data = clients["owner"].get("/collection/api/tree").get_json()

    names = [f["name"] for f in data["folders"]]
    assert "To fix" in names and len(names) == len(CC._cfg("default_folders"))
    clients["owner"].get("/collection/api/tree")      # only once
    assert count(UserCollection, user_id=users.owner.id) == len(names)


def test_add_a_rule_with_note_status_and_reminder(clients, users):
    folder = _folder(users.owner)
    rule = make_rule(users.user)

    response = clients["owner"].post("/collection/api/items", json={
        "folder_ids": [folder.id], "rule_ids": [rule.id], "note": "change request pending",
        "status": "doing", "remind_at": "2030-01-02T09:00:00Z"})

    assert response.status_code == 200 and response.get_json()["added"] == 1
    item = UserCollectionItem.query.filter_by(collection_id=folder.id).one()
    assert (item.rule_id, item.note, item.status) == (rule.id, "change request pending", "doing")
    assert item.remind_at == datetime.datetime(2030, 1, 2, 9, 0)


def test_adding_twice_updates_instead_of_duplicating(users):
    folder = _folder(users.owner)
    rule = make_rule(users.owner)
    CC.add_items(users.owner, [folder.id], [rule.id], note="first")

    added, _ = CC.add_items(users.owner, [folder.id], [rule.id], note="second")

    assert added == 0
    assert UserCollectionItem.query.filter_by(collection_id=folder.id).one().note == "second"


def test_move_an_item_and_refuse_a_folder_inside_itself(clients, users):
    parent = _folder(users.owner, "Parent")
    child = _folder(users.owner, "Child", parent_id=parent.id)
    CC.add_items(users.owner, [parent.id], [make_rule(users.owner).id])
    item = UserCollectionItem.query.filter_by(collection_id=parent.id).one()

    moved = clients["owner"].patch(f"/collection/api/items/{item.id}", json={"collection_id": child.id})
    cycle = clients["owner"].patch(f"/collection/api/folders/{parent.id}", json={"parent_id": child.id})

    assert moved.status_code == 200 and reload(item).collection_id == child.id
    assert cycle.status_code == 400 and reload(parent).parent_id is None


def test_deleting_a_folder_removes_sub_folders_and_items_not_rules(clients, users):
    parent = _folder(users.owner, "Parent")
    child = _folder(users.owner, "Child", parent_id=parent.id)
    rule = make_rule(users.owner)
    CC.add_items(users.owner, [child.id], [rule.id])

    assert clients["owner"].delete(f"/collection/api/folders/{parent.id}").status_code == 200

    assert count(UserCollection, user_id=users.owner.id) == 0
    assert count(UserCollectionItem, user_id=users.owner.id) == 0
    assert reload(rule) is not None


def test_due_reminder_notifies_once_and_skips_done_items(users):
    folder = _folder(users.owner)
    r1, r2 = make_rule(users.owner), make_rule(users.owner)
    past = "2020-01-01T09:00:00Z"
    CC.add_items(users.owner, [folder.id], [r1.id], note="look again", remind_at=past)
    CC.add_items(users.owner, [folder.id], [r2.id], remind_at=past, status="done")

    CC.fire_due_reminders()
    CC.fire_due_reminders()

    notes = Notification.query.filter_by(user_id=users.owner.id, notif_type="collection_reminder").all()
    assert len(notes) == 1
    assert r1.title in notes[0].title and "look again" in notes[0].body
    assert notes[0].link.startswith("/rule/owner_rules?tab=folders")


def test_soft_deleted_rule_stays_listed_with_its_note(users):
    folder = _folder(users.owner)
    rule = make_rule(users.owner)
    CC.add_items(users.owner, [folder.id], [rule.id], note="keep")
    rule.is_deleted = True
    db.session.commit()

    item = CC.list_items(users.owner.id, folder_id=folder.id)["items"][0]

    assert item["object"]["deleted"] is True and item["note"] == "keep"
    assert CC.add_items(users.owner, [folder.id], [make_rule(users.owner, is_deleted=True).id])[0] == 0


def test_permanent_rule_delete_removes_its_folder_items(users):
    from app.features.rule.rule_core import permanent_delete_rule
    folder = _folder(users.owner)
    rule = make_rule(users.owner)
    CC.add_items(users.owner, [folder.id], [rule.id])
    rule.is_deleted = True
    db.session.commit()

    assert permanent_delete_rule(rule.id)

    assert count(UserCollectionItem, collection_id=folder.id) == 0
    assert CC.list_items(users.owner.id, folder_id=folder.id)["total"] == 0


def test_bundle_delete_removes_its_folder_items(users):
    from app.features.bundle.bundle_core import delete_bundle
    from tests_new.helpers.bundles import make_bundle
    folder = _folder(users.owner)
    bundle = make_bundle(users.owner)
    CC.add_items(users.owner, [folder.id], [], [bundle.id])

    assert delete_bundle(bundle.id)

    assert count(UserCollectionItem, collection_id=folder.id) == 0


def test_user_delete_removes_their_folders(users):
    from app.features.account.account_core import delete_user_core
    parent = _folder(users.user, "Parent")
    _folder(users.user, "Child", parent_id=parent.id)
    CC.add_items(users.user, [parent.id], [make_rule(users.owner).id])
    uid = users.user.id

    assert delete_user_core(uid)

    assert count(UserCollection, user_id=uid) == 0
    assert count(UserCollectionItem, user_id=uid) == 0
