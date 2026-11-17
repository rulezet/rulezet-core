"""Collections (private folders) — layer 1: who can do what.

Folders are private: logged-in users only, and a user never sees nor touches
another user's folders or items (admins included — it is personal data).
"""
import pytest

from app.core.db_class.collection import UserCollectionItem
from app.features.collection import collection_core as CC
from tests_new.helpers.access import LOGIN, OK, assert_outcome, matrix
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule

TREE = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK}


@pytest.mark.parametrize("role, expected", matrix(TREE))
def test_tree_needs_login(role, expected, clients):
    assert_outcome(clients[role].get("/collection/api/tree"), expected)


@pytest.mark.parametrize("role", ["anonymous", "user", "admin"])
def test_nobody_else_sees_or_changes_my_folder(role, clients, users):
    folder, _ = CC.create_folder(users.owner.id, {"name": "Mine"})
    rule = make_rule(users.owner)
    CC.add_items(users.owner, [folder.id], [rule.id], note="private note")
    item = UserCollectionItem.query.filter_by(collection_id=folder.id).one()
    c = clients[role]

    listed = c.get(f"/collection/api/items?folder={folder.id}")
    c.patch(f"/collection/api/items/{item.id}", json={"note": "hacked"})
    c.patch(f"/collection/api/folders/{folder.id}", json={"name": "hacked"})
    c.post("/collection/api/items/remove", json={"ids": [item.id]})
    c.delete(f"/collection/api/folders/{folder.id}")
    c.delete(f"/collection/api/membership/rule/{rule.id}/{folder.id}")
    c.post("/collection/api/items", json={"folder_ids": [folder.id], "rule_ids": [make_rule(users.user).id]})

    if role != "anonymous":
        assert listed.status_code == 200 and listed.get_json()["total"] == 0
    assert reload(item).note == "private note"
    assert reload(folder).name == "Mine"
    assert count(UserCollectionItem, collection_id=folder.id) == 1


def test_membership_only_shows_my_own_folders(clients, users):
    rule = make_rule(users.owner)
    folder, _ = CC.create_folder(users.owner.id, {"name": "Mine"})
    CC.add_items(users.owner, [folder.id], [rule.id])

    data = clients["user"].get(f"/collection/api/membership/rule/{rule.id}").get_json()

    assert data["membership"] == []
    assert folder.id not in [f["id"] for f in data["folders"]]


def test_private_bundle_of_someone_else_cannot_be_added(users):
    from tests_new.helpers.bundles import make_bundle
    bundle = make_bundle(users.owner, public=False)
    folder, _ = CC.create_folder(users.user.id, {"name": "Spy"})

    added, _ = CC.add_items(users.user, [folder.id], [], [bundle.id])

    assert added == 0


def test_old_collection_url_redirects_to_my_rules_folders_tab(clients):
    response = clients["user"].get("/collection/?folder=3&item=9")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rule/owner_rules?tab=folders&folder=3&item=9")
