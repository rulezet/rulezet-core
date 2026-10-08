"""The shared fixtures do what the rest of the suite relies on."""
import pytest

from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome
from tests_new.helpers.users import make_user_with_permission


@pytest.mark.parametrize("role, logged_in", [("anonymous", False), ("user", True), ("owner", True), ("admin", True)])
def test_clients_are_logged_in_as_their_role(role, logged_in, clients):
    response = clients[role].get("/account/")

    assert_outcome(response, OK if logged_in else LOGIN)


def test_admin_is_admin_and_others_are_not(users):
    assert users.admin.is_admin()
    assert not users.owner.is_admin()
    assert not users.user.is_admin()


def test_user_with_permission_has_only_that_permission(app):
    tagger = make_user_with_permission("rule.tag_any")

    assert tagger.has_permission("rule.tag_any")
    assert not tagger.has_permission("ai.manage")
    assert not tagger.is_admin()


def test_assert_outcome_rejects_a_login_redirect_as_ok(clients):
    response = clients["anonymous"].get("/account/")

    with pytest.raises(AssertionError):
        assert_outcome(response, OK)
    with pytest.raises(AssertionError):
        assert_outcome(response, FORBIDDEN)


def test_each_client_stays_its_own_user_across_requests(clients, users):
    """Several clients in one test must not share the logged-in user (Flask's
    `g` is reset per request — see conftest._app)."""
    whoami = {}
    for role in ("owner", "user", "admin", "owner"):
        response = clients[role].get("/account/")
        whoami.setdefault(role, set()).add(response.status_code)

    assert_outcome(clients["anonymous"].get("/account/"), LOGIN)
    assert all(codes == {200} for codes in whoami.values())


def test_api_key_user_does_not_leak_into_the_next_request(app, users):
    from tests_new.helpers.users import api_headers
    client = app.test_client()

    client.get("/api/rule/private/me", headers=api_headers(users.owner))
    response = client.get("/account/")

    assert_outcome(response, LOGIN)
