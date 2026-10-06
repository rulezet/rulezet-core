"""Bundles — layer 3: the REST API (/api/bundle/...), authenticated with X-API-KEY.

Same rights as the web routes: the public namespace reads public bundles for
anyone, and a private bundle only for its owner / an admin (their key) or a
user holding its share key (their key + X-Share-Key). The private namespace
needs a key, and changing a bundle needs the owner's or an admin's key.
"nobody" = no key at all, "bad key" = a key that matches no account.
"""
import io
import zipfile

import pytest

from app import db
from app.core.db_class.db import Bundle, BundleNode, BundleRuleAssociation, BundleTagAssociation
from app.features.bundle import bundle_core as BundleModel
from tests_new.helpers.bundles import add_rules, file, folder, make_bundle, make_release, make_tag, rule_node, share
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule
from tests_new.helpers.users import api_headers

PRIVATE = "/api/bundle/private"
PUBLIC = "/api/bundle/public"
BAD_KEY = {"X-API-KEY": "no-such-key"}

OWNER_OR_ADMIN = [("nobody", 403), ("bad key", 403), ("user", 403), ("owner", 200), ("admin", 200)]
ANY_KEY = [("nobody", 403), ("bad key", 403), ("user", 200), ("admin", 200)]


def _headers(who, users):
    if who == "nobody":
        return {}
    if who == "bad key":
        return BAD_KEY
    return api_headers(getattr(users, who))


def _call(app, method, url, who, users, **kwargs):
    return app.test_client().open(url, method=method, headers=_headers(who, users), **kwargs)


# ── Public namespace: reading ─────────────────────────────────────────────────

READ_ENDPOINTS = ["/detail/{ref}", "/{ref}/rules", "/{ref}/structure", "/{ref}/releases", "/{ref}/download"]


@pytest.mark.parametrize("endpoint", READ_ENDPOINTS)
@pytest.mark.parametrize("who, status", OWNER_OR_ADMIN)
def test_read_private_bundle(who, status, endpoint, app, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner, public=False), rule)

    response = _call(app, "GET", PUBLIC + endpoint.format(ref=bundle.id), who, users)

    assert response.status_code == status
    if status != 200:
        assert bundle.name.encode() not in response.data and rule.to_string.encode() not in response.data


@pytest.mark.parametrize("endpoint", READ_ENDPOINTS)
@pytest.mark.parametrize("who", ["nobody", "bad key", "user"])
def test_read_public_bundle(who, endpoint, app, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))

    response = _call(app, "GET", PUBLIC + endpoint.format(ref=bundle.uuid), who, users)

    assert response.status_code == 200


@pytest.mark.parametrize("endpoint", READ_ENDPOINTS)
def test_share_key_opens_a_private_bundle_to_a_user(endpoint, app, users):
    bundle = add_rules(make_bundle(users.owner, public=False), make_rule(users.owner))
    key = share(bundle)

    response = app.test_client().get(PUBLIC + endpoint.format(ref=bundle.id),
                                     headers={**api_headers(users.user), "X-Share-Key": key})

    assert response.status_code == 200


def test_share_key_without_an_api_key_is_refused(app, users):
    bundle = make_bundle(users.owner, public=False)
    key = share(bundle)

    response = app.test_client().get(f"{PUBLIC}/detail/{bundle.id}", headers={"X-Share-Key": key})

    assert response.status_code == 403


def test_old_share_key_is_refused_after_regenerating(app, users):
    bundle = make_bundle(users.owner, public=False)
    old_key = share(bundle)
    share(bundle)

    response = app.test_client().get(f"{PUBLIC}/detail/{bundle.id}?share_key={old_key}", headers=api_headers(users.user))

    assert response.status_code == 403


def test_detail_shape(app, users):
    kept, trashed = make_rule(users.owner), make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), kept, trashed)
    BundleModel.save_workspace(bundle.id, [folder("Main", rule_node(kept), rule_node(trashed), file("README.md", "hi"))])
    BundleModel.update_bundle_tags(bundle.id, [make_tag("workflow:todo", users.admin).id], users.owner)
    trashed.is_deleted = True
    db.session.commit()
    make_release(bundle, users.owner)

    data = app.test_client().get(f"{PUBLIC}/detail/{bundle.uuid}").get_json()["bundle"]

    assert (data["id"], data["uuid"], data["name"]) == (bundle.id, bundle.uuid, bundle.name)
    assert data["tags"] == ["workflow:todo"]
    assert [r["id"] for r in data["rules"]] == [kept.id]
    assert data["structure"] == [{"type": "folder", "name": "Main", "children": [
        {"type": "rule", "name": kept.title, "rule_id": kept.id, "rule_uuid": kept.uuid, "format": "yara"},
        {"type": "file", "name": "README.md", "content": "hi"},
    ]}]
    assert data["release_count"] == 1


def test_detail_of_an_unknown_bundle_is_not_found(app, users):
    response = app.test_client().get(f"{PUBLIC}/detail/424242")

    assert response.status_code == 404


def test_rules_are_paginated_and_active_only(app, users):
    rules = [make_rule(users.owner) for _ in range(3)]
    bundle = add_rules(make_bundle(users.owner), *rules)
    rules[0].is_deleted = True
    db.session.commit()

    data = app.test_client().get(f"{PUBLIC}/{bundle.id}/rules?per_page=1&page=2").get_json()

    assert (data["total"], data["total_pages"], data["page"]) == (2, 2, 2)
    assert [r["id"] for r in data["rules"]] == [rules[2].id]


def test_download_parts(app, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    BundleModel.save_workspace(bundle.id, BundleModel.build_tree_json(bundle.id) + [file("README.md", "hi")])
    client = app.test_client()

    full = client.get(f"{PUBLIC}/{bundle.id}/download")
    files = client.get(f"{PUBLIC}/{bundle.id}/download?part=files")
    misp = client.get(f"{PUBLIC}/{bundle.id}/download?part=misp")

    assert "bundle.json" in zipfile.ZipFile(io.BytesIO(full.data)).namelist()
    assert zipfile.ZipFile(io.BytesIO(files.data)).namelist() == ["README.md"]
    assert misp.mimetype == "application/json"


@pytest.mark.parametrize("query, status", [("part=nope", 400), ("part=misp&release=v1.0.0", 400), ("release=v9.9.9", 404)])
def test_download_with_bad_parameters_is_refused(query, status, app, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    make_release(bundle, users.owner)

    response = app.test_client().get(f"{PUBLIC}/{bundle.id}/download?{query}")

    assert response.status_code == status


def test_releases_are_listed(app, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    make_release(bundle, users.owner, "v1.0.0")

    data = app.test_client().get(f"{PUBLIC}/{bundle.id}/releases").get_json()

    assert [r["version"] for r in data["releases"]] == ["v1.0.0"]


# ── Public namespace: search ──────────────────────────────────────────────────

@pytest.mark.parametrize("who", ["nobody", "user", "owner", "admin"])
def test_search_returns_public_bundles_only(who, app, users):
    public = make_bundle(users.owner, name="Phishing kit")
    private = make_bundle(users.owner, name="Phishing drafts", public=False)

    data = _call(app, "GET", f"{PUBLIC}/search?search=phishing", who, users).get_json()

    assert [b["name"] for b in data["bundle_list"]] == [public.name]
    assert private.name not in str(data)


def test_search_paginated(app, users):
    for _ in range(3):
        make_bundle(users.owner)

    data = app.test_client().get(f"{PUBLIC}/search?page=2&per_page=2&sort=name").get_json()

    assert (data["total"], data["total_pages"], len(data["bundle_list"])) == (3, 2, 1)


def test_search_with_an_unknown_sort_is_refused(app, users):
    response = app.test_client().get(f"{PUBLIC}/search?sort=nope")

    assert response.status_code == 400


# ── Private namespace: create ─────────────────────────────────────────────────

@pytest.mark.parametrize("who, status", ANY_KEY)
def test_create_bundle_needs_a_valid_key(who, status, app, users):
    response = _call(app, "POST", f"{PRIVATE}/create", who, users, json={"name": "API bundle"})

    assert response.status_code == status
    assert count(Bundle, name="API bundle") == (1 if status == 200 else 0)


def test_create_bundle_with_a_name_you_already_use_is_a_conflict(app, users):
    existing = make_bundle(users.owner)

    response = app.test_client().post(f"{PRIVATE}/create", json={"name": existing.name},
                                      headers=api_headers(users.owner))

    assert response.status_code == 409 and count(Bundle, name=existing.name) == 1


def test_create_bundle_with_a_name_another_user_uses_is_allowed(app, users):
    existing = make_bundle(users.user)

    response = app.test_client().post(f"{PRIVATE}/create", json={"name": existing.name},
                                      headers=api_headers(users.owner))

    assert response.status_code == 200 and count(Bundle, name=existing.name) == 2


def test_rename_bundle_to_a_name_the_owner_already_uses_is_a_conflict(app, users):
    taken, bundle = make_bundle(users.owner), make_bundle(users.owner)

    response = app.test_client().post(f"{PRIVATE}/edit_bundle/{bundle.id}", json={"name": taken.name},
                                      headers=api_headers(users.admin))

    assert response.status_code == 409 and reload(bundle).name != taken.name


def test_create_bundle_belongs_to_the_key_owner_with_its_rules_and_tags(app, users):
    rule, tag = make_rule(users.user), make_tag("workflow:todo", users.admin)

    response = app.test_client().post(f"{PRIVATE}/create", headers=api_headers(users.owner), json={
        "name": "API bundle", "description": "via API", "public": False, "tags": ["workflow:todo"],
        "vulnerabilities": ["CVE-2024-0001"], "rule_uuids": [rule.uuid], "folder": "Detections/Windows"})

    bundle = Bundle.query.filter_by(name="API bundle").one()
    assert response.get_json()["bundle_id"] == bundle.id and response.get_json()["rules_added"] == 1
    assert (bundle.user_id, bundle.access, bundle.description) == (users.owner.id, False, "via API")
    assert count(BundleTagAssociation, bundle_id=bundle.id, tag_id=tag.id) == 1
    assert BundleNode.query.filter_by(bundle_id=bundle.id, rule_id=rule.id).one().parent.name == "Windows"


@pytest.mark.parametrize("payload", [
    {"name": "Bad", "tags": ["no-such-tag"]},
    {"name": "Bad", "rule_ids": [424242]},
    {"name": "Bad", "public": "yes"},
    {"name": "   "},
    {},
])
def test_create_bundle_with_invalid_data_creates_nothing(payload, app, users):
    response = app.test_client().post(f"{PRIVATE}/create", json=payload, headers=api_headers(users.owner))

    assert response.status_code == 400
    assert count(Bundle) == 0


def test_create_bundle_with_a_trashed_rule_creates_nothing(app, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = app.test_client().post(f"{PRIVATE}/create", json={"name": "Bad", "rule_ids": [rule.id]},
                                      headers=api_headers(users.owner))

    assert response.status_code == 400 and count(Bundle) == 0


# ── Private namespace: changing a bundle ──────────────────────────────────────

@pytest.mark.parametrize("who, status", OWNER_OR_ADMIN)
def test_add_rule(who, status, app, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.user)

    response = _call(app, "POST", f"{PRIVATE}/add_rule_bundle", who, users,
                     json={"bundle_id": bundle.id, "rule_id": rule.id, "description": "why"})

    assert response.status_code == status
    assert count(BundleRuleAssociation, bundle_id=bundle.id) == (1 if status == 200 else 0)


@pytest.mark.parametrize("who, status", OWNER_OR_ADMIN)
def test_add_several_rules(who, status, app, users):
    bundle, rules = make_bundle(users.owner), [make_rule(users.user), make_rule(users.user)]

    response = _call(app, "POST", f"{PRIVATE}/add_rules_bundle", who, users,
                     json={"bundle_uuid": bundle.uuid, "rule_ids": [r.id for r in rules]})

    assert response.status_code == status
    assert count(BundleRuleAssociation, bundle_id=bundle.id) == (2 if status == 200 else 0)


@pytest.mark.parametrize("who, status", OWNER_OR_ADMIN)
def test_remove_rule(who, status, app, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)

    response = _call(app, "POST", f"{PRIVATE}/remove_rule_bundle", who, users,
                     json={"bundle_id": bundle.id, "rule_id": rule.id})

    assert response.status_code == status
    assert count(BundleRuleAssociation, bundle_id=bundle.id) == (0 if status == 200 else 1)


@pytest.mark.parametrize("who, status", OWNER_OR_ADMIN)
def test_edit_bundle(who, status, app, users):
    bundle = make_bundle(users.owner)

    response = _call(app, "POST", f"{PRIVATE}/edit_bundle/{bundle.id}", who, users,
                     json={"name": "Renamed via API", "public": False})

    assert response.status_code == status
    assert (reload(bundle).name == "Renamed via API") is (status == 200)
    assert reload(bundle).access is not (status == 200)


@pytest.mark.parametrize("who, status", OWNER_OR_ADMIN)
def test_replace_structure(who, status, app, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.owner)

    response = _call(app, "POST", f"{PRIVATE}/{bundle.uuid}/structure", who, users, json={"structure": [
        {"type": "folder", "name": "Main", "children": [{"type": "rule", "rule_uuid": rule.uuid},
                                                         {"type": "file", "name": "README.md", "content": "hi"}]}]})

    assert response.status_code == status
    assert count(BundleNode, bundle_id=bundle.id, rule_id=rule.id) == (1 if status == 200 else 0)


@pytest.mark.parametrize("who, status", OWNER_OR_ADMIN)
def test_delete_bundle(who, status, app, users):
    bundle = make_bundle(users.owner)

    response = _call(app, "POST", f"{PRIVATE}/delete_bundle/{bundle.id}", who, users)

    assert response.status_code == status
    assert (reload(bundle) is None) is (status == 200)


def test_edit_bundle_partially_keeps_the_other_fields(app, users):
    bundle = make_bundle(users.owner, vulnerability_identifiers='["CVE-2024-0001"]')
    description = bundle.description

    app.test_client().post(f"{PRIVATE}/edit_bundle/{bundle.id}", json={"name": "Only the name"},
                           headers=api_headers(users.owner))

    edited = reload(bundle)
    assert (edited.name, edited.description, edited.vulnerability_identifiers) == (
        "Only the name", description, '["CVE-2024-0001"]')


def test_edit_bundle_with_nothing_to_change_is_refused(app, users):
    bundle = make_bundle(users.owner)

    response = app.test_client().post(f"{PRIVATE}/edit_bundle/{bundle.id}", json={}, headers=api_headers(users.owner))

    assert response.status_code == 400


def test_replace_structure_with_an_unknown_rule_changes_nothing(app, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)

    response = app.test_client().post(f"{PRIVATE}/{bundle.id}/structure", headers=api_headers(users.owner),
                                      json={"structure": [{"type": "rule", "rule_id": 424242}]})

    assert response.status_code == 400
    assert count(BundleNode, bundle_id=bundle.id, rule_id=rule.id) == 1


def test_add_rule_to_an_unknown_bundle_is_not_found(app, users):
    rule = make_rule(users.owner)

    response = app.test_client().post(f"{PRIVATE}/add_rule_bundle", headers=api_headers(users.owner),
                                      json={"bundle_id": 424242, "rule_id": rule.id, "description": "x"})

    assert response.status_code == 404


# ── Private namespace: my bundles ─────────────────────────────────────────────

def test_my_bundles_lists_the_key_owners_bundles_private_included(app, users):
    public, private = make_bundle(users.owner), make_bundle(users.owner, public=False)
    make_bundle(users.user)

    data = app.test_client().get(f"{PRIVATE}/my_bundles", headers=api_headers(users.owner)).get_json()

    assert {b["name"] for b in data["bundle_list"]} == {public.name, private.name}


def test_my_bundles_needs_a_key(app, users):
    response = app.test_client().get(f"{PRIVATE}/my_bundles")

    assert response.status_code == 403
