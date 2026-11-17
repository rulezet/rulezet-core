"""Collections — layer 4: inputs meant to break it. Clean 4xx, never a 500."""
import pytest

from app.core.db_class.collection import UserCollection
from tests_new.helpers.db import count
from tests_new.helpers.inputs import BAD_IDS, INJECTIONS, TOO_LONG, WRONG_TYPES


@pytest.mark.parametrize("name", [TOO_LONG, *INJECTIONS, *WRONG_TYPES])
def test_create_folder_with_bad_name(name, clients):
    response = clients["owner"].post("/collection/api/folders", json={"name": name, "icon": name, "color": name})

    assert response.status_code < 500


@pytest.mark.parametrize("value", [*BAD_IDS, *WRONG_TYPES, "not-a-date", "9999-99-99"])
def test_add_items_with_bad_values(value, clients):
    response = clients["owner"].post("/collection/api/items", json={
        "folder_ids": value, "rule_ids": value, "bundle_ids": [value], "note": value,
        "status": value, "remind_at": value})

    assert response.status_code < 500


@pytest.mark.parametrize("body", [[], "text", 12, None, {"ids": "x"}, {"ids": [None, "a", -1]}])
def test_non_object_bodies(body, clients):
    c = clients["owner"]
    for method, url in [(c.post, "/collection/api/folders"), (c.post, "/collection/api/items"),
                        (c.post, "/collection/api/items/remove"), (c.post, "/collection/api/folders/reorder")]:
        assert method(url, json=body).status_code < 500


@pytest.mark.parametrize("query", ["folder=abc", "folder=-1", "page=0", "per_page=99999", "status=<x>",
                                   "view=../etc", "search=%25%27%3B--", "kind=everything"])
def test_list_items_with_odd_query(query, clients):
    assert clients["owner"].get(f"/collection/api/items?{query}").status_code < 500


def test_patch_with_wrong_types_keeps_the_item_working(clients, users):
    from app.features.collection import collection_core as CC
    from tests_new.helpers.rules import make_rule
    folder, _ = CC.create_folder(users.owner.id, {"name": "F"})
    CC.add_items(users.owner, [folder.id], [make_rule(users.owner).id])
    item_id = CC.list_items(users.owner.id, folder_id=folder.id)["items"][0]["id"]

    for bad in WRONG_TYPES:
        response = clients["owner"].patch(f"/collection/api/items/{item_id}",
                                          json={"note": bad, "status": bad, "remind_at": bad, "collection_id": bad})
        assert response.status_code < 500
    assert count(UserCollection, user_id=users.owner.id) == 1
