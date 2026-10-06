"""MISP — layer 3: the REST API exports, authenticated with X-API-KEY.

- GET /api/rule/public/Convert_MISP — search active rules and get each one
  as a MISP object; public, a key changes nothing.
- GET /api/bundle/public/<ref>/download?part=misp — a bundle as a MISP
  event; a private bundle only for its owner's or an admin's key.

The MISP server connections have no API (admin web routes only).
"""
import json

import pytest

from tests_new.helpers.attack import trash
from tests_new.helpers.comments import make_bundle
from tests_new.helpers.misp import add_to_bundle, objects_named, values
from tests_new.helpers.rules import make_rule
from tests_new.helpers.users import api_headers

CONVERT = "/api/rule/public/Convert_MISP"
BAD_KEY = {"X-API-KEY": "no-such-key"}
KEYS = ["nobody", "bad key", "user", "owner", "admin"]


def _headers(who, users):
    if who == "nobody":
        return {}
    if who == "bad key":
        return BAD_KEY
    return api_headers(getattr(users, who))


def _bundle_url(bundle, **params):
    query = "&".join(f"{k}={v}" for k, v in {"part": "misp", **params}.items())
    return f"/api/bundle/public/{bundle.id}/download?{query}"


# ── Convert_MISP ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who", KEYS)
def test_convert_misp_is_public(who, app, users):
    rule = make_rule(users.owner)

    response = app.test_client().get(CONVERT, headers=_headers(who, users))

    assert response.status_code == 200
    assert [r["uuid"] for r in response.get_json()["results"]] == [rule.uuid]


def test_convert_misp_returns_each_rule_as_a_misp_object(app, users):
    rule = make_rule(users.owner)

    result = app.test_client().get(CONVERT).get_json()["results"][0]

    assert result["misp_object"] is not None
    [metadata] = objects_named(result["misp_object"], "rulezet-metadata")
    [content] = objects_named(result["misp_object"], "yara")
    assert values(metadata, "uuid") == [rule.uuid]
    assert values(content, "yara") == [rule.to_string]


def test_convert_misp_leaves_out_trashed_rules(app, users):
    kept = make_rule(users.owner)
    trashed = trash(make_rule(users.owner), users.admin)

    response = app.test_client().get(CONVERT, headers=api_headers(users.admin))

    assert response.get_json()["total_rules_found"] == 1
    assert kept.uuid.encode() in response.data and trashed.uuid.encode() not in response.data


def test_convert_misp_filters_by_search(app, users):
    make_rule(users.owner, title="Log4Shell detection")
    make_rule(users.owner, title="Something else")

    results = app.test_client().get(f"{CONVERT}?search=log4shell").get_json()["results"]

    assert [r["title"] for r in results] == ["Log4Shell detection"]


def test_convert_misp_filters_by_author(app, users):
    make_rule(users.owner, author="Jane Analyst")
    make_rule(users.owner, author="Someone Else")

    results = app.test_client().get(f"{CONVERT}?author=Jane").get_json()["results"]

    assert [r["author"] for r in results] == ["Jane Analyst"]


def test_convert_misp_never_contains_account_secrets(app, users):
    make_rule(users.owner)

    body = app.test_client().get(CONVERT, headers=api_headers(users.admin)).get_data(as_text=True)

    for secret in (users.owner.email, users.owner.api_key, users.admin.api_key):
        assert secret not in body


# ── Bundle as a MISP event ────────────────────────────────────────────────────

@pytest.mark.parametrize("who", KEYS)
def test_public_bundle_misp_event_for_every_key(who, app, users):
    bundle = add_to_bundle(make_bundle(users.owner, public=True), make_rule(users.owner))

    response = app.test_client().get(_bundle_url(bundle), headers=_headers(who, users))

    assert response.status_code == 200 and response.mimetype == "application/json"
    assert values(objects_named(json.loads(response.data), "rulezet-bundle")[0], "uuid") == [bundle.uuid]


@pytest.mark.parametrize("who, status", [("nobody", 403), ("bad key", 403), ("user", 403),
                                         ("owner", 200), ("admin", 200)])
def test_private_bundle_misp_event_only_for_owner_and_admin(who, status, app, users):
    rule = make_rule(users.owner)
    bundle = add_to_bundle(make_bundle(users.owner, public=False), rule)

    response = app.test_client().get(_bundle_url(bundle), headers=_headers(who, users))

    assert response.status_code == status
    assert (rule.uuid.encode() in response.data) is (status == 200)


def test_bundle_misp_event_leaves_out_trashed_rules(app, users):
    trashed = make_rule(users.owner)
    bundle = add_to_bundle(make_bundle(users.owner), make_rule(users.owner), trashed)
    trash(trashed, users.admin)

    response = app.test_client().get(_bundle_url(bundle))

    assert response.status_code == 200
    assert trashed.uuid.encode() not in response.data


def test_bundle_release_cannot_be_downloaded_as_misp(app, users):
    bundle = add_to_bundle(make_bundle(users.owner), make_rule(users.owner))

    response = app.test_client().get(_bundle_url(bundle, release="v1.0"))

    assert response.status_code == 400
