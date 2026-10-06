"""Tags — layer 4: inputs meant to break Rulezet.

Expected every time: a clean answer (< 500), and either nothing stored or the
value stored as plain text — escaped when displayed, never interpreted.
"""
import pytest

from app import db
from app.core.db_class.db import BackgroundJob, Tag
from tests.helpers.db import count, reload
from tests.helpers.inputs import BAD_IDS, BLANK, EMPTY, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests.helpers.rules import make_rule
from tests.helpers.tags import GALAXY_UUID, fake_misp_data, make_tag, new_tag_payload
from tests.helpers.users import api_headers

DEFAULT_TAGS = 2
BROKEN_BODIES = [None, "not json", [1, 2], 42, "text"]


def _post_body(client, url, body):
    if body is None:
        return client.post(url)
    if body == "not json":
        return client.post(url, data="{not json", content_type="application/json")
    return client.post(url, json=body)


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [EMPTY, BLANK, *WRONG_TYPES])
def test_create_tag_with_a_missing_or_wrongly_typed_name_stores_nothing(name, clients):
    response = clients["owner"].post("/tags/create_tag", json=new_tag_payload(name=name))

    assert response.status_code == 400
    assert count(Tag) == DEFAULT_TAGS


@pytest.mark.parametrize("name", [*INJECTIONS, *[c for c in ODD_CHARACTERS if "\x00" not in c]])
def test_create_tag_with_a_hostile_name_stores_it_as_plain_text(name, clients):
    response = clients["owner"].post("/tags/create_tag", json=new_tag_payload(name=name))

    assert response.status_code == 200
    assert count(Tag, name=name.strip()) == 1


@pytest.mark.parametrize("name", [TOO_LONG, "null\x00byte"])
def test_create_tag_with_an_unstorable_name_is_refused(name, clients):
    """Longer than an imported tag name may be, or a NUL byte PostgreSQL can't store."""
    response = clients["owner"].post("/tags/create_tag", json=new_tag_payload(name=name))

    assert response.status_code == 400
    assert count(Tag) == DEFAULT_TAGS


def test_create_tag_trims_the_name(clients):
    clients["owner"].post("/tags/create_tag", json=new_tag_payload(name="  spaced:name  "))

    assert count(Tag, name="spaced:name") == 1


@pytest.mark.parametrize("field, value", [
    ("color", "#" + "F" * 60), ("icon", "fa-" + "x" * 60), ("visibility", "everyone"), ("visibility", ["public"]),
    ("color", {"r": 1}), ("description", ["a"]), ("description", "null\x00byte"), ("external_id", 5),
])
def test_create_tag_with_a_bad_field_stores_nothing(field, value, clients):
    response = clients["owner"].post("/tags/create_tag", json=new_tag_payload(**{field: value}))

    assert response.status_code == 400
    assert count(Tag) == DEFAULT_TAGS


@pytest.mark.parametrize("body", BROKEN_BODIES)
def test_create_tag_with_a_broken_body_never_errors(body, clients):
    response = _post_body(clients["owner"], "/tags/create_tag", body)

    assert response.status_code < 500
    assert count(Tag) == DEFAULT_TAGS


def test_create_tag_ignores_fields_a_user_may_not_set(clients, users):
    payload = new_tag_payload(is_active=True, is_approved_by_admin=True, created_by=users.admin.id)

    clients["owner"].post("/tags/create_tag", json=payload)

    tag = Tag.query.filter_by(name=payload["name"]).one()
    assert (tag.is_active, tag.is_approved_by_admin, tag.created_by) == (False, False, users.owner.id)


@pytest.mark.parametrize("source", ["Taxonomy", "Galaxy", "Imported"])
def test_create_tag_is_always_a_manual_tag(source, clients):
    """A user can't pass a tag off as an imported one (it would e.g. mark a
    MISP taxonomy as already imported, and escape their bulk-remove scope)."""
    payload = new_tag_payload(name="testtax:fake", source=source)

    clients["owner"].post("/tags/create_tag", json=payload)

    assert Tag.query.filter_by(name="testtax:fake").one().source == "Manual"


def test_hostile_tag_name_is_escaped_on_the_my_tags_page(clients, users):
    make_tag(users.owner, name="<script>alert('tag')</script>")

    page = clients["owner"].get("/tags/my_tags").get_data(as_text=True)

    assert "<script>alert('tag')</script>" not in page


# ── Edit ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [EMPTY, BLANK, TOO_LONG, "null\x00byte", *WRONG_TYPES])
def test_edit_tag_with_a_bad_name_keeps_the_old_one(name, clients, users):
    tag = make_tag(users.owner)
    old = tag.name

    response = clients["owner"].post(f"/tags/edit_tag/{tag.id}", json={"name": name})

    assert response.status_code == 400
    assert reload(tag).name == old


@pytest.mark.parametrize("field, value", [("color", "#" + "F" * 60), ("icon", ["fa-tag"]), ("description", 5)])
def test_edit_tag_with_a_bad_field_changes_nothing(field, value, clients, users):
    tag = make_tag(users.owner)
    before = (tag.name, tag.color, tag.icon, tag.description)

    response = clients["owner"].post(f"/tags/edit_tag/{tag.id}", json={"name": "tests:renamed", field: value})

    tag = reload(tag)
    assert response.status_code == 400
    assert (tag.name, tag.color, tag.icon, tag.description) == before


@pytest.mark.parametrize("body", BROKEN_BODIES)
def test_edit_tag_with_a_broken_body_never_errors(body, clients, users):
    tag = make_tag(users.owner)
    old = tag.name

    response = _post_body(clients["owner"], f"/tags/edit_tag/{tag.id}", body)

    assert response.status_code < 500
    assert reload(tag).name == old


def test_edit_tag_to_an_external_id_already_used_is_a_conflict(clients, users):
    make_tag(users.owner, external_id="ext-1")
    tag = make_tag(users.owner)

    response = clients["owner"].post(f"/tags/edit_tag/{tag.id}", json={"name": tag.name, "external_id": "ext-1"})

    assert response.status_code == 409 and reload(tag).external_id is None


# ── Ids and query strings ─────────────────────────────────────────────────────

@pytest.mark.parametrize("tag_id", ["abc", "-1", str(2**63), "1 OR 1=1", ""])
def test_remove_tag_with_a_bad_id_removes_nothing(tag_id, clients):
    response = clients["admin"].get(f"/tags/remove_tag?tag_id={tag_id}")

    assert response.status_code == 404
    assert count(Tag) == DEFAULT_TAGS


@pytest.mark.parametrize("url", ["/tags/delete_tag/0", f"/tags/delete_tag/{2**63}", "/tags/edit_tag/0"])
def test_delete_or_edit_with_an_out_of_range_id_is_not_found(url, clients):
    response = clients["admin"].post(url, json={"name": "x"})

    assert response.status_code == 404
    assert count(Tag) == DEFAULT_TAGS


@pytest.mark.parametrize("ids", ["1", 1, {"a": 1}, [None], ["x"], [2**63], [[1]], [True]])
@pytest.mark.parametrize("role", ["owner", "admin"])
def test_bulk_remove_with_bad_ids_removes_nothing(ids, role, clients, users):
    make_tag(users.owner)

    response = clients[role].post("/tags/remove_tags_bulk", json={"ids": ids})

    assert 400 <= response.status_code < 500
    assert count(Tag) == DEFAULT_TAGS + 1


@pytest.mark.parametrize("body", BROKEN_BODIES)
@pytest.mark.parametrize("url", ["/tags/remove_tags_bulk", "/tags/delete_family", "/tags/add_tags_galaxy",
                                 "/tags/admin/validation/launch", "/tags/admin/validation/dismiss"])
def test_management_posts_with_a_broken_body_never_error(url, body, clients):
    response = _post_body(clients["admin"], url, body)

    assert response.status_code < 500


@pytest.mark.parametrize("family", [*WRONG_TYPES, "%", "_", "' OR 1=1 --"])
def test_delete_family_with_a_bad_family_removes_nothing(family, clients, users):
    make_tag(users.owner, name="fam:a")

    response = clients["admin"].post("/tags/delete_family", json={"family": family})

    assert 400 <= response.status_code < 500
    assert count(Tag) == DEFAULT_TAGS + 1


@pytest.mark.parametrize("url", [
    "/tags/get_tags", "/tags/get_tags_bundle", "/tags/get_all_tags", "/tags/get_all_tags_by_type",
    "/tags/get_my_tags_paged", "/tags/picker/tags", "/tags/get_tags_misp", "/tags/get_tags_galaxy",
])
@pytest.mark.parametrize("query", ["page=abc", "page=-1", f"page={2**63}", "per_page=abc&limit=abc&user_id=abc",
                                   "per_page=-5&limit=-1&user_id=-1", "sort=../../etc&dir=sideways&search=%25"])
def test_listings_with_bad_query_strings_never_error(url, query, clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    response = clients["admin"].get(f"{url}?{query}")

    assert response.status_code < 500


@pytest.mark.parametrize("query", ["tag_page=abc", f"tag_page={2**63}", "tag_per_page=abc", "tag_per_page=-1"])
def test_tag_filter_views_with_bad_paging_never_error(query, clients):
    response = clients["anonymous"].get(f"/rule/get_all_tags_usage?view=tags&{query}")

    assert response.status_code < 500


@pytest.mark.parametrize("galaxy_uuid", ["nope", "../../etc/passwd", "%2e%2e%2f", "a" * 3000])
def test_galaxy_clusters_with_a_bad_uuid_never_error(galaxy_uuid, clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    response = clients["admin"].get(f"/tags/get_galaxy_clusters/{galaxy_uuid}")

    assert response.status_code == 404


@pytest.mark.parametrize("cluster_uuids", ["one", 5, {"a": 1}, [None], [[1]]])
def test_import_galaxy_with_bad_cluster_uuids_never_errors(cluster_uuids, clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    response = clients["admin"].post("/tags/add_tags_galaxy", json={"uuid": GALAXY_UUID,
                                                                     "cluster_uuids": cluster_uuids})

    assert response.status_code < 500


@pytest.mark.parametrize("taxonomy_uuid", ["", "../../etc/passwd", "' OR 1=1 --"])
def test_import_taxonomy_with_a_bad_uuid_imports_nothing(taxonomy_uuid, clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    response = clients["admin"].get(f"/tags/add_tags_misp?uuid={taxonomy_uuid}")

    assert 400 <= response.status_code < 500
    assert count(Tag, source="Taxonomy") == 0


@pytest.mark.parametrize("limit", ["abc", -5, [1], {"a": 1}, 10**12])
def test_launch_validation_with_a_bad_limit_never_errors(limit, clients):
    response = clients["admin"].post("/tags/admin/validation/launch", json={"limit": limit})

    assert response.status_code < 500


@pytest.mark.parametrize("rule_ids", ["abc", 5, [None], [{"a": 1}], [2**63], [-1]])
def test_dismiss_with_bad_rule_ids_is_refused(rule_ids, clients, users):
    job = BackgroundJob(uuid="validation-run", job_type="rule_validation_run", status="done",
                        created_by=users.admin.id, payload={"result": {}})
    db.session.add(job)
    db.session.commit()

    response = clients["admin"].post("/tags/admin/validation/dismiss", json={"job_uuid": job.uuid,
                                                                            "rule_ids": rule_ids})

    assert response.status_code == 400
    assert not (reload(job).payload.get("result") or {}).get("dismissed_rule_ids")


@pytest.mark.parametrize("job_uuid", [5, [1], {"a": 1}, None])
def test_dismiss_with_a_wrongly_typed_run_is_not_found(job_uuid, clients):
    response = clients["admin"].post("/tags/admin/validation/dismiss", json={"job_uuid": job_uuid, "rule_ids": [1]})

    assert response.status_code == 404


# ── API ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", ["id=abc", f"id={2**63}", "id=-1", "uuid=' OR 1=1 --", "name=%25", "name=_",
                                   f"name={'a' * 3000}"])
def test_api_lookup_with_bad_parameters_never_errors(query, app, users):
    response = app.test_client().get(f"/api/tags/private/lookup?{query}", headers=api_headers(users.admin))

    assert response.status_code < 500


def test_api_lookup_by_name_treats_like_wildcards_literally(app, users):
    """"%" must not match every tag."""
    response = app.test_client().get("/api/tags/private/lookup?name=%25", headers=api_headers(users.admin))

    assert response.status_code == 404


@pytest.mark.parametrize("field", ["rule_ids", "rule_uuids", "tag_ids", "tag_uuids"])
@pytest.mark.parametrize("value", [*BAD_IDS, *WRONG_TYPES, [[1]], [{"a": 1}], [None], [True]])
def test_api_bulk_add_with_bad_identifiers_never_errors(field, value, app, users):
    rule, tag = make_rule(users.owner), make_tag(users.admin)
    body = {"rule_ids": [rule.id], "tag_ids": [tag.id], "confirm": True}
    body[field] = value if isinstance(value, list) else [value]

    response = app.test_client().post("/api/tags/private/bulk_add", json=body, headers=api_headers(users.admin))

    assert response.status_code < 500


@pytest.mark.parametrize("body", BROKEN_BODIES)
def test_api_bulk_add_with_a_broken_body_is_refused(body, app, users):
    client = app.test_client()
    headers = api_headers(users.admin)
    if body is None:
        response = client.post("/api/tags/private/bulk_add", headers=headers)
    elif body == "not json":
        response = client.post("/api/tags/private/bulk_add", data="{not json", headers=headers,
                               content_type="application/json")
    else:
        response = client.post("/api/tags/private/bulk_add", json=body, headers=headers)

    assert response.status_code == 400
    assert count(BackgroundJob) == 0
