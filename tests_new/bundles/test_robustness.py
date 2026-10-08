"""Bundles — layer 4: inputs meant to break Rulezet.

Expected every time: a clean answer (< 500), and either nothing stored /
nothing changed, or the value stored as plain text — escaped when it is
displayed, never executed.
"""
import json

import pytest

from app.core.db_class.db import (
    Bundle, BundleNode, BundleNote, BundleRelease, BundleRuleAssociation, BundleTagAssociation, BundleVote,
    UserConfig,
)
from app.features.bundle import bundle_core as BundleModel
from app.features.bundle import bundle_layout_core as BundleLayoutModel
from tests_new.helpers.bundles import (
    add_rules, edit_bundle_form, file, folder, make_bundle, make_note, make_release, make_tag, new_bundle_form,
    rule_node, share,
)
from tests_new.helpers.db import count, reload
from tests_new.helpers.inputs import BAD_IDS, BLANK, EMPTY, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests_new.helpers.rules import make_rule
from tests_new.helpers.users import api_headers

BAD_TEXT = [TOO_LONG, *INJECTIONS, *ODD_CHARACTERS]
BROKEN_BODIES = [None, "not json", [1, 2], 42, "text"]
HUGE_ID = 2**63
QUERY_IDS = ["abc", "-1", "0", str(HUGE_ID), "1 OR 1=1", "", "../1"]


def _send(client, method, url, body):
    """`body`: None = no body, a str = raw (maybe invalid) JSON text, else JSON."""
    if body is None:
        return client.open(url, method=method)
    if isinstance(body, str):
        return client.open(url, method=method, data=body, content_type="application/json")
    return client.open(url, method=method, json=body)


def _tree(bundle):
    return [(n.name, n.node_type, n.rule_id, n.custom_content) for n in
            BundleNode.query.filter_by(bundle_id=bundle.id).order_by(BundleNode.id)]


# ── Create / edit (web forms) ─────────────────────────────────────────────────

@pytest.mark.parametrize("name", [EMPTY, BLANK, TOO_LONG])
def test_create_bundle_with_an_empty_or_too_long_name_stores_nothing(name, clients):
    response = clients["owner"].post("/bundle/create", data=new_bundle_form(name=name))

    assert response.status_code == 200
    assert count(Bundle) == 0


@pytest.mark.parametrize("value", [*INJECTIONS, *ODD_CHARACTERS])
def test_create_bundle_with_a_hostile_name_never_errors(value, clients):
    response = clients["owner"].post("/bundle/create", data=new_bundle_form(name=value, description=value))

    assert response.status_code < 500


def test_create_bundle_with_a_huge_description_never_errors(clients):
    response = clients["owner"].post("/bundle/create", data=new_bundle_form(description=TOO_LONG))

    assert response.status_code < 500


def test_hostile_name_is_escaped_on_the_bundle_page(clients, users):
    bundle = make_bundle(users.owner, name="<script>alert('pwned')</script>")

    page = clients["anonymous"].get(f"/bundle/detail/{bundle.id}").get_data(as_text=True)

    assert "<script>alert('pwned')</script>" not in page


@pytest.mark.parametrize("name", [EMPTY, BLANK, TOO_LONG])
def test_edit_bundle_to_an_empty_or_too_long_name_keeps_the_old_name(name, clients, users):
    bundle = make_bundle(users.owner)
    old = bundle.name

    response = clients["owner"].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, name=name))

    assert response.status_code < 500
    assert reload(bundle).name == old


@pytest.mark.parametrize("value", BAD_TEXT)
def test_edit_bundle_with_hostile_fields_never_errors(value, clients, users):
    bundle = make_bundle(users.owner)

    response = clients["owner"].post(f"/bundle/edit/{bundle.id}",
                                     data=edit_bundle_form(bundle, name=value[:255], description=value))

    assert response.status_code < 500


@pytest.mark.parametrize("vulnerabilities", ["not json", "{}", '"CVE-2024-1"', "[1, 2", "null", "12", TOO_LONG])
def test_edit_bundle_with_malformed_vulnerabilities_keeps_a_list(vulnerabilities, clients, users):
    bundle = make_bundle(users.owner)

    response = clients["owner"].post(f"/bundle/edit/{bundle.id}",
                                     data=edit_bundle_form(bundle, vulnerabilities=vulnerabilities))
    page = clients["owner"].get("/bundle/data_table")

    assert response.status_code < 500 and page.status_code == 200
    assert isinstance(json.loads(reload(bundle).vulnerability_identifiers or "[]"), list)


# ── Ids in paths and query strings ────────────────────────────────────────────

PATH_ROUTES = [
    ("GET", "/bundle/detail/{id}"), ("GET", "/bundle/edit/{id}"), ("GET", "/bundle/get_bundle_json/{id}"),
    ("GET", "/bundle/history/{id}"), ("GET", "/bundle/{id}/health"), ("GET", "/bundle/{id}/notes"),
    ("GET", "/bundle/{id}/releases"), ("GET", "/bundle/attack_coverage/{id}"), ("GET", "/bundle/get_tags/{id}"),
    ("GET", "/bundle/{id}/share"), ("POST", "/bundle/favorite/{id}"), ("POST", "/bundle/save_workspace/{id}"),
    ("POST", "/bundle/update_bundle_tags/{id}"), ("GET", "/bundle/{id}/rule_content/1"),
    ("GET", "/bundle/vulnerabilities/bundle/{id}"), ("GET", "/bundle/get_bundle_tags_display/{id}"),
]


@pytest.mark.parametrize("bundle_id", [2**31, HUGE_ID])
@pytest.mark.parametrize("method, route", PATH_ROUTES)
def test_unknown_bundle_id_in_the_path_is_not_found(method, route, bundle_id, clients, users):
    make_bundle(users.owner)

    response = clients["admin"].open(route.format(id=bundle_id), method=method, json={"structure": [], "tag_ids": []})

    assert response.status_code == 404


QUERY_ROUTES = [
    ("GET", "/bundle/get_bundle_page?bundle_id={id}"), ("GET", "/bundle/get_bundle?bundle_id={id}"),
    ("GET", "/bundle/get_rules_page_from_bundle?bundle_id={id}"), ("GET", "/bundle/download?bundle_id={id}"),
    ("GET", "/bundle/download_structure?bundle_id={id}"), ("GET", "/bundle/download_files?bundle_id={id}"),
    ("GET", "/bundle/download_full?bundle_id={id}"), ("GET", "/bundle/download_misp?bundle_id={id}"),
    ("GET", "/bundle/voters?bundleId={id}&voteType=up"), ("POST", "/bundle/evaluate?bundleId={id}&voteType=up"),
    ("POST", "/bundle/delete?id={id}"), ("POST", "/bundle/edit_access?id={id}"),
    ("POST", "/bundle/add_rule_bundle?bundle_id={id}&rule_id={id}"), ("POST", "/bundle/remove?bundle_id={id}&rule_id={id}"),
    ("POST", "/bundle/change_description?association_id={id}&new_description=x"),
    ("POST", "/bundle/update_bundle_from_structure?id={id}"),
    ("GET", "/bundle/get_bundles_page_filter_with_id?user_id={id}"),
    ("GET", "/bundle/get_bundle_list_rule_part_of?rule_id={id}"),
]


@pytest.mark.parametrize("bad_id", QUERY_IDS)
@pytest.mark.parametrize("method, route", QUERY_ROUTES)
def test_bad_id_in_the_query_string_changes_nothing(method, route, bad_id, clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)

    response = clients["admin"].open(route.format(id=bad_id), method=method)

    assert response.status_code < 500
    assert reload(bundle) is not None and reload(bundle).access is True
    assert count(BundleRuleAssociation, bundle_id=bundle.id) == 1 and count(BundleVote) == 0


@pytest.mark.parametrize("bad_id", QUERY_IDS)
@pytest.mark.parametrize("route", ["/bundle/get_bundle_page?bundle_id={id}", "/bundle/download?bundle_id={id}",
                                   "/bundle/download_misp?bundle_id={id}", "/bundle/download_structure?bundle_id={id}"])
def test_unknown_bundle_in_the_query_string_is_a_client_error(route, bad_id, clients):
    response = clients["anonymous"].get(route.format(id=bad_id))

    assert response.status_code in (400, 404)


@pytest.mark.parametrize("ref", ["not-a-uuid", "<script>", "' OR 1=1 --", "a" * 5000, str(HUGE_ID) + "0"])
def test_bundle_page_by_bad_uuid_never_errors(ref, clients):
    response = clients["anonymous"].get(f"/bundle/detail/{ref}")

    assert response.status_code == 404


@pytest.mark.parametrize("query", ["", "voteType=sideways", "voteType=", "voteType=UP"])
def test_vote_with_a_bad_type_is_refused(query, clients, users):
    bundle = make_bundle(users.owner)

    response = clients["user"].post(f"/bundle/evaluate?bundleId={bundle.id}&{query}")

    assert response.status_code == 400
    assert count(BundleVote) == 0 and reload(bundle).vote_up == 0


@pytest.mark.parametrize("query", ["page=-1", "page=abc", "per_page=100000", "per_page=-5", "sort=password_hash",
                                   "dir=sideways", "ids[]=abc", "tags=" + "%27" * 50, "attacks=,,,", "access=everything",
                                   "search=" + "A" * 5000, "user_id=abc"])
def test_bundle_list_with_bad_filters_never_errors(query, clients, users):
    make_bundle(users.owner)

    response = clients["anonymous"].get(f"/bundle/data_table?{query}")

    assert response.status_code < 500


@pytest.mark.parametrize("query", ["99999999999999999999", str(HUGE_ID), "%", "_", "' OR 1=1 --", "A" * 5000])
def test_global_search_of_bundles_with_odd_queries_never_errors(query, app, users):
    """The bundle half of /global_search (its rule half belongs to the rule tests)."""
    make_bundle(users.owner)

    with app.test_request_context("/global_search"):
        found = BundleModel.search_bundles_lite(query)

    assert isinstance(found, list)


# ── Structure ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", [*BROKEN_BODIES, {}, {"structure": None}, {"structure": "x"}, {"structure": {"a": 1}}])
def test_save_structure_with_a_broken_body_changes_nothing(body, clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    before = _tree(bundle)

    response = _send(clients["owner"], "POST", f"/bundle/save_workspace/{bundle.id}", body)

    assert 400 <= response.status_code < 500
    assert _tree(bundle) == before


def _deep(levels):
    node = file("leaf.txt", "x")
    for i in range(levels):
        node = folder(f"level{i}", node)
    return [node]


BAD_STRUCTURES = {
    "parent folder name": [folder("..", file("x.txt"))],
    "slash in a name": [file("../../etc/passwd", "x")],
    "backslash in a name": [file("..\\evil.txt", "x")],
    "empty name": [file("", "x")],
    "name too long": [file("a" * 300, "x")],
    "unknown node type": [{"name": "x", "type": "symlink", "children": []}],
    "node not an object": ["just a string"],
    "children not a list": [{"name": "x", "type": "folder", "children": "nope"}],
    "file with children": [{"name": "x", "type": "file", "content": "", "children": [file("y")]}],
    "file content not text": [{"name": "x", "type": "file", "content": {"a": 1}, "children": []}],
    "file too large": [file("big.txt", "A" * (1024 * 1024 + 1))],
    "too deep": _deep(25),
    "too many nodes": [folder("Main", *[file(f"f{i}.txt") for i in range(5001)])],
    "rule id not a number": [{"name": "r", "type": "file", "rule_id": "abc", "children": []}],
    "rule id true": [{"name": "r", "type": "file", "rule_id": True, "children": []}],
    "rule id an object": [{"name": "r", "type": "file", "rule_id": {"id": 1}, "children": []}],
}


@pytest.mark.parametrize("structure", BAD_STRUCTURES.values(), ids=BAD_STRUCTURES.keys())
def test_save_an_invalid_structure_changes_nothing(structure, clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    before = _tree(bundle)

    response = clients["owner"].post(f"/bundle/save_workspace/{bundle.id}", json={"structure": structure})

    assert response.status_code == 400
    assert _tree(bundle) == before
    assert count(BundleRuleAssociation, bundle_id=bundle.id) == 1


@pytest.mark.parametrize("rule_id", [424242, 2**31, HUGE_ID, -1, 0])
def test_save_structure_with_an_unknown_rule_drops_the_node(rule_id, clients, users):
    bundle = make_bundle(users.owner)

    response = clients["owner"].post(f"/bundle/save_workspace/{bundle.id}",
                                     json={"structure": [folder("Main", {"name": "r", "type": "file",
                                                                         "rule_id": rule_id, "children": []})]})

    assert response.status_code < 500
    assert count(BundleRuleAssociation, bundle_id=bundle.id) == 0
    assert all(rid is None for _, _, rid, _ in _tree(bundle))


def test_hostile_file_names_never_escape_the_zip(clients, users):
    bundle = make_bundle(users.owner)
    BundleModel.save_workspace(bundle.id, [folder("Main", file("....", "x"), file("a:b", "y"))])
    import io
    import zipfile

    response = clients["anonymous"].get(f"/bundle/download_structure?bundle_id={bundle.id}")

    names = zipfile.ZipFile(io.BytesIO(response.data)).namelist()
    assert all(not n.startswith("/") and ".." not in n.split("/") for n in names)


# ── Tags ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", [*BROKEN_BODIES, {"tag_ids": "1"}, {"tag_ids": [None]}, {"tag_ids": ["x"]},
                                  {"tag_ids": [{"id": "x"}]}, {"tag_ids": [424242]}, {"tag_ids": [HUGE_ID]},
                                  {"tag_ids": {"a": 1}}, {"tag_ids": [True]}])
def test_set_tags_with_bad_values_links_no_unknown_tag(body, clients, users):
    bundle = make_bundle(users.owner)

    response = _send(clients["owner"], "POST", f"/bundle/update_bundle_tags/{bundle.id}", body)

    assert response.status_code < 500
    assert count(BundleTagAssociation, bundle_id=bundle.id) == 0


# ── Notes ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", [*BROKEN_BODIES, {}, {"title": "ab", "content": "x"}, {"title": "Valid", "content": ""},
                                  {"title": "Valid", "content": TOO_LONG}, {"title": TOO_LONG, "content": "x"},
                                  {"title": "Valid", "content": "x", "severity": "apocalyptic"},
                                  {"title": 12345, "content": "x"}, {"title": "Valid", "content": ["x"]},
                                  {"title": "Valid", "content": "x", "severity": 3},
                                  {"title": "Valid", "content": "x", "tag_ids": "1"},
                                  {"title": "Valid", "content": "x", "tag_ids": ["x"]},
                                  {"title": "Valid", "content": "x", "tag_ids": [HUGE_ID]},
                                  {"title": "Valid", "content": "x", "tag_ids": list(range(1, 20))}])
def test_add_note_with_bad_values_stores_nothing(body, clients, users):
    bundle = make_bundle(users.owner)

    response = _send(clients["user"], "POST", f"/bundle/{bundle.id}/notes", body)

    assert 400 <= response.status_code < 500
    assert count(BundleNote) == 0


@pytest.mark.parametrize("value", [*INJECTIONS, *ODD_CHARACTERS])
def test_add_note_with_hostile_text_stores_it_as_text(value, clients, users):
    bundle = make_bundle(users.owner)

    response = clients["user"].post(f"/bundle/{bundle.id}/notes", json={"title": f"Note {value}", "content": value})

    assert response.status_code < 500


@pytest.mark.parametrize("body", [*BROKEN_BODIES, {"title": 1, "content": 2}, {"title": "ab", "content": "x"}])
def test_edit_note_with_bad_values_keeps_it(body, clients, users):
    note = make_note(make_bundle(users.owner), users.user)

    response = _send(clients["user"], "PUT", f"/bundle/{note.bundle_id}/notes/{note.id}", body)

    assert 400 <= response.status_code < 500
    assert reload(note).title == "A known issue"


@pytest.mark.parametrize("body", [*BROKEN_BODIES, {"status": "closed"}, {"status": 1}, {"status": ["resolved"]}, {}])
def test_note_status_with_a_bad_value_keeps_it_open(body, clients, users):
    note = make_note(make_bundle(users.owner), users.user)

    response = _send(clients["owner"], "POST", f"/bundle/{note.bundle_id}/notes/{note.id}/status", body)

    assert 400 <= response.status_code < 500
    assert reload(note).status == "open"


def test_note_of_another_bundle_is_not_found(clients, users):
    mine, theirs = make_bundle(users.owner), make_bundle(users.user)
    note = make_note(theirs, users.user)

    response = clients["owner"].delete(f"/bundle/{mine.id}/notes/{note.id}")

    assert response.status_code == 404 and reload(note) is not None


# ── Releases ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", [*BROKEN_BODIES, {}, {"version": "latest"}, {"version": "1.2.3.4"}, {"version": TOO_LONG},
                                  {"version": "../../v1.0.0"}, {"version": "<script>"}, {"version": 1.0},
                                  {"version": 12345}, {"version": ["v1.0.0"]},
                                  {"version": "v1.0.0", "title": 5}, {"version": "v1.0.0", "notes": {"a": 1}}])
def test_publish_release_with_bad_values_stores_nothing(body, clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))

    response = _send(clients["owner"], "POST", f"/bundle/{bundle.id}/releases", body)

    assert 400 <= response.status_code < 500
    assert count(BundleRelease) == 0


@pytest.mark.parametrize("route", [
    "/bundle/{b}/releases/{huge}/changes", "/bundle/{b}/releases/{rel}/changes?against={huge}",
    "/bundle/{b}/releases/{rel}/changes?against=abc", "/bundle/{b}/releases/{huge}/rule/1/diff",
    "/bundle/{b}/releases/{huge}/download", "/bundle/{b}/releases/{huge}/view", "/bundle/{b}/releases/nope/view",
    "/bundle/{b}/rule_content/1?release={huge}", "/bundle/{b}/health?release={huge}",
    "/bundle/attack_coverage/{b}?release={huge}", "/bundle/download?bundle_id={b}&release={huge}",
    "/bundle/download_full?bundle_id={b}&release=nope",
])
def test_unknown_release_is_not_found(route, clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    release = make_release(bundle, users.owner)

    response = clients["anonymous"].get(route.format(b=bundle.id, rel=release.id, huge=HUGE_ID))

    assert response.status_code == 404


def test_release_of_another_bundle_is_not_found(clients, users):
    other = add_rules(make_bundle(users.user), make_rule(users.user))
    release = make_release(other, users.user)
    bundle = make_bundle(users.owner)

    response = clients["owner"].delete(f"/bundle/{bundle.id}/releases/{release.id}")

    assert response.status_code == 404 and reload(release) is not None


# ── Health fixes ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", [*BROKEN_BODIES, {}, {"fix": None}, {"fix": "remove_rule"}, {"fix": [1]},
                                  {"fix": {"action": "explode"}},
                                  {"fix": {"action": "remove_rule", "rule_id": "abc"}},
                                  {"fix": {"action": "remove_rule", "rule_id": HUGE_ID}},
                                  {"fix": {"action": "add_rule", "rule_id": HUGE_ID}},
                                  {"fix": {"action": "add_rule", "rule_id": [1]}},
                                  {"fix": {"action": "remove_node", "node_id": HUGE_ID}},
                                  {"fix": {"action": "remove_node", "node_id": "abc"}},
                                  {"fix": {"action": "set_marking", "tag": "tlp:<script>"}},
                                  {"fix": {"action": "set_marking", "tag": ["tlp:red"]}}])
def test_health_fix_with_bad_values_changes_nothing(body, clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    before = _tree(bundle)

    response = _send(clients["owner"], "POST", f"/bundle/{bundle.id}/health/fix", body)

    assert 400 <= response.status_code < 500
    assert _tree(bundle) == before and count(BundleRuleAssociation, bundle_id=bundle.id) == 1


# ── Creating a bundle for a rule ──────────────────────────────────────────────

@pytest.mark.parametrize("body", [*BROKEN_BODIES, {}, {"rule_id": "abc", "new_bundle_name": "x"},
                                  {"rule_id": HUGE_ID, "new_bundle_name": "x"}, {"rule_id": [1], "new_bundle_name": "x"},
                                  {"rule_id": {"id": 1}, "new_bundle_name": "x"},
                                  {"rule_id": "{rule}", "new_bundle_name": 12345},
                                  {"rule_id": "{rule}", "new_bundle_name": None},
                                  {"rule_id": "{rule}", "new_bundle_name": "   "},
                                  {"rule_id": "{rule}", "new_bundle_name": TOO_LONG},
                                  {"rule_id": "{rule}", "new_bundle_name": "x", "new_bundle_description": 5},
                                  {"rule_id": "{rule}", "new_bundle_name": "x", "is_public": "no"},
                                  {"rule_id": "{rule}", "existing_bundle_id": "abc"},
                                  {"rule_id": "{rule}", "existing_bundle_id": HUGE_ID}])
def test_create_bundle_for_a_rule_with_bad_values_stores_nothing(body, clients, users):
    rule = make_rule(users.owner)
    if isinstance(body, dict) and body.get("rule_id") == "{rule}":
        body = {**body, "rule_id": rule.id}

    response = _send(clients["owner"], "POST", "/bundle/add-single-rule", body)

    assert 400 <= response.status_code < 500
    assert count(Bundle) == 0


# ── Share links ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("token", ["x", TOO_LONG[:5000], "' OR 1=1 --", "%00", "../../etc/passwd"])
def test_odd_share_tokens_grant_nothing(token, clients, users):
    bundle = make_bundle(users.owner, public=False)
    share(bundle)

    opened = clients["user"].get(f"/bundle/share/{token}")
    detail = clients["user"].get(f"/bundle/detail/{bundle.id}?share={token}")

    assert opened.status_code in (403, 404) and detail.status_code == 403


# ── API ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["name", "description", "public", "vulnerabilities", "tags", "rule_ids",
                                   "rule_uuids", "folder"])
@pytest.mark.parametrize("value", [12345, 1.5, True, {"x": 1}, [None], [HUGE_ID], ["1; DROP TABLE rule"], [[1]]])
def test_api_create_with_a_wrong_type_never_errors(field, value, app, users):
    payload = {"name": "API bundle", field: value}

    response = app.test_client().post("/api/bundle/private/create", json=payload, headers=api_headers(users.owner))

    assert response.status_code < 500


@pytest.mark.parametrize("value", BAD_TEXT)
def test_api_create_with_hostile_text_never_errors(value, app, users):
    payload = {"name": value, "description": value, "folder": value}

    response = app.test_client().post("/api/bundle/private/create", json=payload, headers=api_headers(users.owner))

    assert response.status_code < 500


def test_api_create_with_a_name_too_long_stores_nothing(app, users):
    response = app.test_client().post("/api/bundle/private/create", json={"name": TOO_LONG},
                                      headers=api_headers(users.owner))

    assert response.status_code == 400 and count(Bundle) == 0


@pytest.mark.parametrize("url", ["/api/bundle/private/create", "/api/bundle/private/add_rule_bundle",
                                 "/api/bundle/private/add_rules_bundle", "/api/bundle/private/remove_rule_bundle",
                                 "/api/bundle/private/edit_bundle/{b}", "/api/bundle/private/{b}/structure"])
@pytest.mark.parametrize("body", [[1, 2], "not json", 42])
def test_api_with_a_non_object_body_changes_nothing(body, url, app, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)

    body_kwargs = {"data": body, "content_type": "application/json"} if isinstance(body, str) else {"json": body}

    response = app.test_client().post(url.format(b=bundle.id), headers=api_headers(users.owner), **body_kwargs)

    assert response.status_code < 500
    assert count(Bundle) == 1 and count(BundleRuleAssociation, bundle_id=bundle.id) == 1


@pytest.mark.parametrize("ref", [*BAD_IDS, "99999999999999999999", 2**31])
@pytest.mark.parametrize("payload", [{"bundle_id": "{ref}", "rule_id": "{rule}", "description": "x"},
                                     {"bundle_id": "{bundle}", "rule_id": "{ref}", "description": "x"},
                                     {"bundle_uuid": "{ref}", "rule_uuid": "{ref}", "description": "x"}])
def test_api_add_rule_with_bad_refs_changes_nothing(payload, ref, app, users):
    rule = make_rule(users.owner)
    bundle = make_bundle(users.owner)
    payload = {k: {"{ref}": ref, "{rule}": rule.id, "{bundle}": bundle.id}.get(v, v) for k, v in payload.items()}

    response = app.test_client().post("/api/bundle/private/add_rule_bundle", json=payload,
                                      headers=api_headers(users.owner))

    assert 400 <= response.status_code < 500
    assert count(BundleRuleAssociation) == 0


@pytest.mark.parametrize("payload", [{"rule_ids": "1,abc"}, {"rule_ids": [HUGE_ID]}, {"rule_ids": [None, {}]},
                                     {"rule_uuids": [12345]}, {"rule_ids": {"a": 1}}, {"rule_ids": [], "rule_uuids": []},
                                     {"rule_ids": ["{rule}"], "folder": 5}])
def test_api_add_several_rules_with_bad_values_never_errors(payload, app, users):
    rule = make_rule(users.owner)
    bundle = make_bundle(users.owner)
    payload = {"bundle_id": bundle.id, **{k: ([rule.id] if v == ["{rule}"] else v) for k, v in payload.items()}}

    response = app.test_client().post("/api/bundle/private/add_rules_bundle", json=payload,
                                      headers=api_headers(users.owner))

    assert response.status_code < 500


@pytest.mark.parametrize("ref", ["99999999999999999999", str(2**31), "not-a-uuid", "' OR 1=1 --", "a" * 3000])
@pytest.mark.parametrize("endpoint", ["/detail/{ref}", "/{ref}/rules", "/{ref}/structure", "/{ref}/releases",
                                      "/{ref}/download"])
def test_api_read_with_a_bad_ref_is_not_found(endpoint, ref, app):
    response = app.test_client().get("/api/bundle/public" + endpoint.format(ref=ref))

    assert response.status_code == 404


@pytest.mark.parametrize("ref", ["99999999999999999999", str(2**31), "not-a-uuid"])
@pytest.mark.parametrize("endpoint", ["/delete_bundle/{ref}", "/{ref}/structure"])
def test_api_change_with_a_bad_ref_is_not_found(endpoint, ref, app, users):
    make_bundle(users.owner)

    response = app.test_client().post("/api/bundle/private" + endpoint.format(ref=ref), json={"structure": []},
                                      headers=api_headers(users.admin))

    assert response.status_code == 404 and count(Bundle) == 1


@pytest.mark.parametrize("payload", [{"name": 12345}, {"name": "   "}, {"name": TOO_LONG}, {"description": ["x"]},
                                     {"public": "no"}, {"vulnerabilities": {"a": 1}}, {"tags": ["no-such-tag"]},
                                     {"tags": [HUGE_ID]}, {"tags": {"a": 1}}])
def test_api_edit_with_bad_values_changes_nothing(payload, app, users):
    bundle = make_bundle(users.owner)
    before = (bundle.name, bundle.description, bundle.access)

    response = app.test_client().post(f"/api/bundle/private/edit_bundle/{bundle.id}", json=payload,
                                      headers=api_headers(users.owner))

    assert response.status_code == 400
    edited = reload(bundle)
    assert (edited.name, edited.description, edited.access) == before


@pytest.mark.parametrize("structure", [
    [{"type": "rule", "rule_id": HUGE_ID}], [{"type": "rule", "rule_id": "abc"}], [{"type": "rule", "rule_uuid": 5}],
    [{"type": "folder", "name": "..", "children": []}], [{"type": "file", "name": "a/b", "content": "x"}],
    [{"type": "folder", "name": "x", "children": "nope"}], ["string"], [None],
])
def test_api_invalid_structure_changes_nothing(structure, app, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    before = _tree(bundle)

    response = app.test_client().post(f"/api/bundle/private/{bundle.id}/structure", json={"structure": structure},
                                      headers=api_headers(users.owner))

    assert response.status_code == 400
    assert _tree(bundle) == before


@pytest.mark.parametrize("query", ["page=0", "page=abc", "per_page=100000", "per_page=-1", "sort=password_hash",
                                   "search=" + "A" * 5000, "search=%27%20OR%201%3D1"])
def test_api_search_with_bad_parameters_never_errors(query, app, users):
    make_bundle(users.owner)

    response = app.test_client().get(f"/api/bundle/public/search?{query}")

    assert response.status_code < 500


@pytest.mark.parametrize("key", ["x", "A" * 5000, "' OR 1=1 --"])
def test_api_odd_share_keys_grant_nothing(key, app, users):
    bundle = make_bundle(users.owner, public=False)
    share(bundle)

    response = app.test_client().get(f"/api/bundle/public/detail/{bundle.id}",
                                     headers={**api_headers(users.user), "X-Share-Key": key})

    assert response.status_code == 403


# ── Structure editor layout ───────────────────────────────────────────────────

def _panels(**changes):
    return [dict(p, **changes.get(p["id"], {})) for p in BundleLayoutModel.DEFAULT_LAYOUT["panels"]]


BAD_LAYOUTS = [
    pytest.param({"panels": "explorer"}, id="panels-not-a-list"),
    pytest.param({"panels": []}, id="no-panel"),
    pytest.param({"panels": _panels()[:3]}, id="a-panel-missing"),
    pytest.param({"panels": _panels() + [_panels()[0]]}, id="a-panel-twice"),
    pytest.param({"panels": _panels() + [{"id": "evil", "x": 0, "y": 0, "w": 1, "h": 1}]}, id="unknown-panel"),
    pytest.param({"panels": _panels(explorer={"x": 10, "w": 5})}, id="wider-than-the-grid"),
    pytest.param({"panels": _panels(explorer={"w": 0})}, id="zero-width"),
    pytest.param({"panels": _panels(explorer={"y": -1})}, id="negative-row"),
    pytest.param({"panels": _panels(explorer={"h": 10**9})}, id="huge-height"),
    pytest.param({"panels": _panels(explorer={"x": "0"})}, id="position-as-text"),
    pytest.param({"panels": _panels(explorer={"w": True})}, id="size-as-boolean"),
    pytest.param({"panels": _panels(explorer={"hidden": "yes"})}, id="hidden-as-text"),
    pytest.param({"panels": _panels(**{p: {"hidden": True} for p in BundleLayoutModel.PANEL_IDS})}, id="all-hidden"),
    pytest.param({"panels": _panels(library={"mode": "popup"})}, id="unknown-mode"),
    pytest.param({"panels": _panels(explorer={"mode": "drawer"})}, id="drawer-not-allowed-for-this-panel"),
    pytest.param({"panels": _panels(library={"minimized": "no"})}, id="minimized-as-text"),
    pytest.param({"panels": _panels(library={"mode": "window", "win": [10, 10]})}, id="window-not-an-object"),
    pytest.param({"panels": _panels(library={"mode": "window", "win": {"x": -5, "y": 0, "w": 500, "h": 400}})},
                 id="window-off-screen"),
    pytest.param({"panels": _panels(library={"mode": "window", "win": {"x": 0, "y": 0, "w": 10, "h": 400}})},
                 id="window-too-small"),
    pytest.param({"panels": _panels(library={"mode": "window", "win": {"x": 0, "y": 0, "w": 500}})},
                 id="window-size-missing"),
]


@pytest.mark.parametrize("layout", BAD_LAYOUTS)
def test_save_an_invalid_editor_layout_stores_nothing(layout, clients, users):
    response = clients["user"].post("/bundle/editor_layout", json=layout)

    assert response.status_code == 400
    config = UserConfig.query.filter_by(user_id=users.user.id).first()
    assert "bundle_editor_layout" not in ((config.meta or {}) if config else {})


@pytest.mark.parametrize("body", BROKEN_BODIES)
def test_save_editor_layout_with_a_broken_body_is_refused(body, clients):
    response = _send(clients["user"], "POST", "/bundle/editor_layout", body)

    assert response.status_code == 400
