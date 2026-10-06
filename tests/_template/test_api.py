"""<Feature> — layer 3: the REST API, authenticated with X-API-KEY.

Same expectations as the web routes: a user's API key never allows what the
user can't do in the UI.
"""
# import pytest
#
# from tests.helpers.users import api_headers
#
#
# @pytest.mark.parametrize("who, expected_status", [("nobody", 403), ("user", 403), ("owner", 200), ("admin", 200)])
# def test_api_delete_thing(who, expected_status, app, users):
#     thing = make_thing(users.owner)
#     key_of = None if who == "nobody" else getattr(users, who)
#
#     response = app.test_client().delete(f"/api/thing/private/{thing.id}", headers=api_headers(key_of))
#
#     assert response.status_code == expected_status
