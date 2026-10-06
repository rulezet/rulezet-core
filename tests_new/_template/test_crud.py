"""<Feature> — layer 2: create / read / edit / delete, checked in the DB."""
# from tests_new.helpers.db import count, reload
#
#
# def test_create_thing_stores_it_owned_by_the_creator(clients, users):
#     response = clients["owner"].post("/thing/create", data={"title": "My thing"})
#
#     assert response.status_code in (200, 302)
#     thing = Thing.query.filter_by(title="My thing").one()
#     assert thing.user_id == users.owner.id
