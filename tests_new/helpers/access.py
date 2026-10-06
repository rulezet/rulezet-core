"""Access-matrix helpers — layer 1 of every feature.

A feature declares, once, what each role gets for an action:

    DELETE_RULE = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}

and one parametrized test runs it for every role:

    @pytest.mark.parametrize("role, expected", matrix(DELETE_RULE))
    def test_delete_rule(role, expected, clients, users):
        rule = make_rule(users.owner)

        response = clients[role].post(f"/rule/delete_rule/{rule.id}")

        assert_outcome(response, expected)
        assert reload(rule).is_deleted is (expected is OK)

Changing a permission is then a one-line diff in the table, and reading the
table tells you the feature's permission model.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Outcome:
    name: str
    statuses: tuple            # accepted HTTP statuses
    login_redirect: bool = False

    def __repr__(self):
        return self.name


OK = Outcome("OK", (200, 201, 204, 302))
LOGIN = Outcome("LOGIN", (302, 401), login_redirect=True)
FORBIDDEN = Outcome("FORBIDDEN", (403,))
NOT_FOUND = Outcome("NOT_FOUND", (404,))


def matrix(table):
    """`table` ({role: Outcome}) → pytest.parametrize values, one per role, id = role."""
    import pytest
    return [pytest.param(role, expected, id=role) for role, expected in table.items()]


def _is_login_redirect(response):
    return response.status_code == 302 and "/account/login" in (response.headers.get("Location") or "")


def assert_outcome(response, expected):
    """The response matches `expected`. OK never accepts a redirect to the
    login page, and LOGIN accepts either 401 or that redirect."""
    status = response.status_code
    detail = f"expected {expected!r}, got {status} {response.headers.get('Location') or ''}".strip()
    assert status in expected.statuses, detail
    if expected.login_redirect:
        assert status == 401 or _is_login_redirect(response), detail
    elif status == 302:
        assert not _is_login_redirect(response), detail
