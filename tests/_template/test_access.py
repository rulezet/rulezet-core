"""<Feature> — layer 1: who can do what.

One table per action: role → expected outcome (OK / LOGIN / FORBIDDEN /
NOT_FOUND). The test runs once per role and also checks the effect in the DB.
"""
# import pytest
#
# from tests.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
# from tests.helpers.db import reload
# from tests.helpers.thing_factory import make_thing
#
# DELETE_THING = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
#
#
# @pytest.mark.parametrize("role, expected", matrix(DELETE_THING))
# def test_delete_thing(role, expected, clients, users):
#     thing = make_thing(users.owner)
#
#     response = clients[role].post(f"/thing/delete/{thing.id}")
#
#     assert_outcome(response, expected)
#     assert (reload(thing) is None) is (expected is OK)
