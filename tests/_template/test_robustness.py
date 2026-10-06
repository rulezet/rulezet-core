"""<Feature> — layer 4: inputs meant to break Rulezet.

Expected: a clean 4xx with a message, never a 500, and nothing half-written.
Reuse the shared bad-input catalogue in tests/helpers/inputs.py.
"""
# import pytest
#
# from tests.helpers.inputs import TOO_LONG, INJECTIONS
#
#
# @pytest.mark.parametrize("title", [TOO_LONG, *INJECTIONS])
# def test_create_thing_with_bad_title_is_refused_cleanly(title, clients):
#     response = clients["owner"].post("/thing/create", data={"title": title})
#
#     assert response.status_code < 500
