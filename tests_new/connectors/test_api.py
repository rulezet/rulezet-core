"""Connectors — layer 3: the sync API (/api/sync/...) that other Rulezet
instances read when they pull from this one.

It is public by design (no API key needed) and must expose only public
content: active rules (never the trash) and public bundles, without any
account data. A key — of any role — unlocks nothing more. The connector
management itself has no REST API: it lives behind the admin-only
/connector routes (layers 1 and 2).
"""
import datetime
import json
import uuid

import pytest

from app import db
from app.core.db_class.db import BundleRuleAssociation, RemotePullLog, RuleTagAssociation, Tag
from tests_new.helpers.attack import link_technique, make_technique, trash
from tests_new.helpers.comments import make_bundle
from tests_new.helpers.connectors import make_connector, no_network  # noqa: F401
from tests_new.helpers.db import count
from tests_new.helpers.rules import make_rule
from tests_new.helpers.users import api_headers

SYNC = "/api/sync"
BAD_KEY = {"X-API-KEY": "no-such-key"}

RULE_FIELDS = {"uuid", "format", "title", "description", "to_string", "author", "version", "license", "source",
               "tags", "cve_ids", "attack_ids", "last_modif", "created_at", "update_history"}
BUNDLE_FIELDS = {"uuid", "name", "description", "rules", "tags", "vulnerability_identifiers", "updated_at",
                 "created_at", "structure"}


def _headers(who, users):
    if who == "nobody":
        return {}
    if who == "bad key":
        return BAD_KEY
    return api_headers(getattr(users, who))


def _get(app, path, headers=None):
    return app.test_client().get(f"{SYNC}{path}", headers=headers or {})


def _uuids(response, key="rules"):
    return {item["uuid"] for item in response.get_json()[key]}


def _tag(rule, name, user):
    tag = Tag.query.filter_by(name=name).first()
    if tag is None:
        tag = Tag(uuid=str(uuid.uuid4()), name=name, is_active=True, created_by=user.id)
        db.session.add(tag)
        db.session.flush()
    db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=rule.id, tag_id=tag.id, user_id=user.id,
                                      added_at=datetime.datetime.now(tz=datetime.timezone.utc)))
    db.session.commit()


def _modified(days_ago):
    return datetime.datetime.now() - datetime.timedelta(days=days_ago)


# ── Public, whoever asks ──────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/manifest", "/stats", "/rules", "/bundles", "/rules?count_only=true"])
@pytest.mark.parametrize("who", ["nobody", "bad key", "user", "admin"])
def test_sync_endpoints_answer_everyone_the_same(path, who, app, users):
    make_rule(users.owner)
    make_bundle(users.owner)
    reference = _get(app, path).get_json()

    response = _get(app, path, _headers(who, users))

    assert response.status_code == 200
    if path != "/rules" and path != "/bundles":
        assert response.get_json() == reference
    else:
        key = path.strip("/")
        assert _uuids(response, key) == {item["uuid"] for item in reference[key]}


def test_manifest_advertises_the_sync_protocol(app):
    data = _get(app, "/manifest").get_json()

    assert data["sync_api_version"] == 2
    assert data["capabilities"]["rule_filters"] is True and data["capabilities"]["bundle_structure"] is True
    assert set(data["instance"]) == {"name", "version", "url"}


# ── Rules: what is exposed ────────────────────────────────────────────────────

def test_rules_serve_the_active_rules_of_every_owner(app, users):
    mine, theirs = make_rule(users.owner), make_rule(users.admin)

    response = _get(app, "/rules")

    assert _uuids(response) == {mine.uuid, theirs.uuid}
    assert response.get_json()["total"] == 2


def test_rules_never_serve_the_trash(app, users):
    kept = make_rule(users.owner)
    trashed = trash(make_rule(users.owner), users.admin)

    listed = _get(app, "/rules")
    by_uuid = _get(app, f"/rules?uuids={kept.uuid},{trashed.uuid}")
    counted = _get(app, "/rules?count_only=true")

    assert _uuids(listed) == {kept.uuid}
    assert _uuids(by_uuid) == {kept.uuid}
    assert counted.get_json()["count"] == 1


def test_rule_payload_holds_the_rule_and_no_account_data(app, users):
    rule = make_rule(users.owner, cve_id=json.dumps(["CVE-2024-1234"]))
    _tag(rule, "tlp:clear", users.owner)
    link_technique(rule, make_technique("T1059"), users.owner)

    item = _get(app, "/rules").get_json()["rules"][0]

    assert set(item) == RULE_FIELDS
    assert (item["title"], item["to_string"]) == (rule.title, rule.to_string)
    assert item["tags"] == ["tlp:clear"] and item["cve_ids"] == ["CVE-2024-1234"] and item["attack_ids"] == ["T1059"]
    raw = json.dumps(item)
    assert users.owner.email not in raw and users.owner.api_key not in raw


def test_rule_pulled_from_elsewhere_is_served_under_its_origin_uuid(app, users):
    """A rule travels between instances under one uuid, so a third instance matches it."""
    connector = make_connector(users.admin)
    origin_uuid = str(uuid.uuid4())
    make_rule(users.owner, remote_rule_uuid=origin_uuid, connector_id=connector.id)

    response = _get(app, f"/rules?uuids={origin_uuid}")

    assert _uuids(response) == {origin_uuid}


def test_rules_never_expose_the_connectors_remote_key(app, users):
    connector = make_connector(users.admin, api_key_outbound="remote-secret-key")
    make_rule(users.owner, connector_id=connector.id)

    responses = [_get(app, path) for path in ("/rules", "/bundles", "/stats", "/manifest")]

    assert all(b"remote-secret-key" not in r.data for r in responses)


# ── Rules: filters and paging ─────────────────────────────────────────────────

@pytest.mark.parametrize("query, expected", [
    ("formats=sigma", {"sigma"}),
    ("formats=SIGMA,yara", {"sigma", "yara"}),
    ("author=alice", {"yara"}),
    ("license=GPL", {"sigma"}),
    ("cve=CVE-2024-1234", {"yara"}),
    ("attacks=t1059", {"sigma"}),
])
def test_rules_filters_select_the_matching_rules(query, expected, app, users):
    make_rule(users.owner, format="yara", author="Alice", license="MIT", cve_id=json.dumps(["CVE-2024-1234"]))
    sigma = make_rule(users.owner, format="sigma", author="Bob", license="GPL-3.0", to_string="title: x")
    link_technique(sigma, make_technique("T1059"), users.owner)

    response = _get(app, f"/rules?{query}")

    assert {item["format"] for item in response.get_json()["rules"]} == expected


@pytest.mark.parametrize("query, expected", [
    ("tags=red", {"red only", "red and blue"}),
    ("tags=red,blue&tag_mode=AND", {"red and blue"}),
    ("tags=red&tag_exclude=true", {"untagged"}),
    ("tags=no-such-tag", set()),
    ("tags=no-such-tag&tag_exclude=true", {"red only", "red and blue", "untagged"}),
])
def test_rules_tag_filters(query, expected, app, users):
    red = make_rule(users.owner, title="red only")
    both = make_rule(users.owner, title="red and blue")
    make_rule(users.owner, title="untagged")
    _tag(red, "red", users.owner)
    _tag(both, "red", users.owner)
    _tag(both, "blue", users.owner)

    response = _get(app, f"/rules?{query}")

    assert {item["title"] for item in response.get_json()["rules"]} == expected


def test_rules_since_and_date_range_select_by_last_modification(app, users):
    make_rule(users.owner, title="old", last_modif=_modified(30))
    make_rule(users.owner, title="recent", last_modif=_modified(1))
    week_ago = _modified(7).date().isoformat()

    since = _get(app, f"/rules?since={week_ago}T00:00:00")
    until = _get(app, f"/rules?date_to={week_ago}")

    assert {i["title"] for i in since.get_json()["rules"]} == {"recent"}
    assert {i["title"] for i in until.get_json()["rules"]} == {"old"}


def test_rules_are_paginated(app, users):
    for _ in range(5):
        make_rule(users.owner)

    first = _get(app, "/rules?per_page=2&page=1").get_json()
    last = _get(app, "/rules?per_page=2&page=3").get_json()

    assert (len(first["rules"]), first["total"], first["has_more"]) == (2, 5, True)
    assert (len(last["rules"]), last["has_more"]) == (1, False)


@pytest.mark.parametrize("per_page, served", [("0", 1), ("-5", 1), ("100000", 2000)])
def test_rules_page_size_is_kept_within_bounds(per_page, served, app):
    data = _get(app, f"/rules?per_page={per_page}").get_json()

    assert data["per_page"] == served


def test_count_only_returns_just_the_count(app, users):
    make_rule(users.owner, cve_id=json.dumps(["CVE-2024-1234"]))
    make_rule(users.owner)

    data = _get(app, "/rules?count_only=true&cve=CVE-2024-1234").get_json()

    assert data == {"count": 1, "cve": "CVE-2024-1234"}


def test_a_pull_session_is_logged_once_on_its_first_page(app, users):
    for _ in range(3):
        make_rule(users.owner)
    headers = {"X-Rulezet-Instance-UUID": str(uuid.uuid4()), "X-Rulezet-Instance-URL": "https://puller.test"}

    _get(app, "/rules?per_page=2&page=1", headers)
    _get(app, "/rules?per_page=2&page=2", headers)
    _get(app, "/rules?count_only=true", headers)

    entry = RemotePullLog.query.one()
    assert (entry.instance_url, entry.rules_total) == ("https://puller.test", 3)


# ── Stats and bundles ─────────────────────────────────────────────────────────

def test_stats_count_only_active_rules_and_public_bundles(app, users):
    make_rule(users.owner)
    trash(make_rule(users.owner), users.admin)
    make_bundle(users.owner)
    make_bundle(users.owner, public=False)

    assert _get(app, "/stats").get_json() == {"rules": 1, "bundles": 1}


def test_bundles_serve_only_public_bundles(app, users):
    public = make_bundle(users.owner)
    make_bundle(users.owner, public=False)

    response = _get(app, "/bundles")

    assert _uuids(response, "bundles") == {public.uuid}


def test_bundle_payload_lists_its_active_rules_only(app, users):
    bundle = make_bundle(users.owner)
    kept, trashed = make_rule(users.owner), make_rule(users.owner)
    db.session.add_all([BundleRuleAssociation(bundle_id=bundle.id, rule_id=kept.id),
                        BundleRuleAssociation(bundle_id=bundle.id, rule_id=trashed.id)])
    db.session.commit()
    trash(trashed, users.admin)

    item = _get(app, "/bundles").get_json()["bundles"][0]

    assert set(item) == BUNDLE_FIELDS
    assert item["rules"] == [kept.uuid]
    assert users.owner.email not in json.dumps(item)


def test_bundles_are_paginated(app, users):
    for _ in range(3):
        make_bundle(users.owner)

    data = _get(app, "/bundles?per_page=2&page=1").get_json()

    assert (len(data["bundles"]), data["total"], data["has_more"]) == (2, 3, True)
    assert count(RemotePullLog) == 0
