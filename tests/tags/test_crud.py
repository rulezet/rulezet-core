"""Tags — layer 2: create / read / edit / delete, checked in the database.

Lifecycle: a tag made by a user starts private, inactive and unapproved —
only its creator can pick it — until an admin (or tag manager) activates it.
An admin's tag is active and approved at once. Deleting a tag removes its
links to rules and bundles, never the rules or bundles themselves. MISP
taxonomies / galaxies are imported as public, active tags.
"""
import pytest

from app import db
from app.core.db_class.db import ActivityLog, BackgroundJob, Bundle, BundleTagAssociation, Rule, RuleTagAssociation, Tag
from tests.helpers.db import count, reload
from tests.helpers.rules import make_rule
from tests.helpers.tags import (
    CLUSTER_UUIDS, GALAXY_UUID, TAXONOMY_UUID, default_tag, fake_misp_data, make_bundle, make_tag,
    new_tag_payload, tag_bundle, tag_rule,
)


def _names(response):
    return {t["name"] for t in response.get_json()["tags"]}


# ── Default tags ──────────────────────────────────────────────────────────────

def test_default_tags_exist_public_and_active(app):
    for name in ("tlp:clear", "PAP:CLEAR"):
        tag = default_tag(name)
        assert tag.is_active is True


def test_creating_a_tag_named_like_a_default_tag_is_a_conflict(clients):
    response = clients["admin"].post("/tags/create_tag", json=new_tag_payload(name="tlp:clear"))

    assert response.status_code == 409
    assert count(Tag, name="tlp:clear") == 1


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_tag_stores_it_owned_by_the_creator(clients, users):
    payload = new_tag_payload(description="My tag", color="#ABCDEF", icon="fa-bug")

    response = clients["owner"].post("/tags/create_tag", json=payload)

    tag = Tag.query.filter_by(name=payload["name"]).one()
    assert response.status_code == 200 and response.get_json()["tag"]["id"] == tag.id
    assert tag.created_by == users.owner.id
    assert (tag.description, tag.color, tag.icon, tag.source) == ("My tag", "#ABCDEF", "fa-bug", "Manual")


def test_create_tag_by_a_user_starts_inactive_and_unapproved(clients):
    payload = new_tag_payload(visibility="public")

    clients["owner"].post("/tags/create_tag", json=payload)

    tag = Tag.query.filter_by(name=payload["name"]).one()
    assert tag.is_active is False and tag.is_approved_by_admin is False


def test_create_tag_by_an_admin_is_active_and_approved(clients):
    payload = new_tag_payload()

    clients["admin"].post("/tags/create_tag", json=payload)

    tag = Tag.query.filter_by(name=payload["name"]).one()
    assert tag.is_active is True and tag.is_approved_by_admin is True


def test_create_tag_is_private_unless_said_otherwise(clients):
    payload = new_tag_payload()
    del payload["visibility"]

    clients["owner"].post("/tags/create_tag", json=payload)

    assert Tag.query.filter_by(name=payload["name"]).one().visibility == "private"


def test_create_tag_sets_its_namespace(clients):
    clients["owner"].post("/tags/create_tag", json=new_tag_payload(name="family:member"))

    assert Tag.query.filter_by(name="family:member").one().namespace == "family"


def test_create_tag_records_the_activity(clients):
    payload = new_tag_payload()

    clients["owner"].post("/tags/create_tag", json=payload)

    assert count(ActivityLog, action="tag.create") == 1


def test_create_tag_with_a_name_already_used_is_a_conflict(clients, users):
    existing = make_tag(users.user)

    response = clients["owner"].post("/tags/create_tag", json=new_tag_payload(name=existing.name))

    assert response.status_code == 409
    assert count(Tag, name=existing.name) == 1 and reload(existing).created_by == users.user.id


def test_create_tag_without_a_name_is_refused(clients):
    response = clients["owner"].post("/tags/create_tag", json=new_tag_payload(name=""))

    assert response.status_code == 400
    assert count(Tag) == 2   # the default tags only


# ── Read ──────────────────────────────────────────────────────────────────────

def test_a_users_new_tag_is_pickable_by_its_creator_only(client_as, users):
    tag = make_tag(users.owner, visibility="public", active=False)

    for_creator = client_as(users.owner).get(f"/tags/get_all_tags?user_id={users.owner.id}")
    for_others = client_as(users.user).get(f"/tags/get_all_tags?user_id={users.user.id}")

    assert tag.name in _names(for_creator)
    assert tag.name not in _names(for_others)


def test_an_activated_public_tag_is_pickable_by_everyone(client_as, clients, users):
    tag = make_tag(users.owner, visibility="public", active=False)

    clients["admin"].get(f"/tags/toggle_status?tag_uuid={tag.uuid}")

    assert tag.name in _names(client_as(users.user).get("/tags/get_all_tags"))


def test_an_active_private_tag_stays_out_of_other_users_pickers(clients, users):
    tag = make_tag(users.owner, visibility="private")

    assert tag.name not in _names(clients["user"].get(f"/tags/get_all_tags?user_id={users.user.id}"))
    assert tag.name in _names(clients["owner"].get(f"/tags/get_all_tags?user_id={users.owner.id}"))


def test_admin_picks_every_active_tag(clients, users):
    private, inactive = make_tag(users.owner, visibility="private"), make_tag(users.owner, active=False)

    names = _names(clients["admin"].get("/tags/get_all_tags"))

    assert private.name in names and inactive.name not in names


def test_picker_folders_count_only_pickable_tags(clients, users):
    make_tag(users.admin, name="zz:one"), make_tag(users.admin, name="zz:two")
    make_tag(users.owner, name="zz:secret", visibility="private")

    groups = clients["user"].get("/tags/picker/namespaces").get_json()["groups"]

    assert {"namespace": "zz", "count": 2} in groups["Public"]
    assert "Private" not in groups


def test_picker_folder_lists_one_page_of_lean_tags(clients, users):
    for i in range(5):
        make_tag(users.admin, name=f"pg:t{i}")

    data = clients["user"].get("/tags/picker/tags?type=Public&namespace=pg&per_page=2&page=3").get_json()

    assert [t["name"] for t in data["tags"]] == ["pg:t4"]
    assert data["total"] == 5 and data["has_more"] is False
    assert set(data["tags"][0]) == {"id", "uuid", "name", "color", "icon", "source", "visibility", "namespace"}


def test_my_tags_lists_only_my_manual_tags(clients, users):
    mine = make_tag(users.owner)
    imported = make_tag(users.owner, source="Taxonomy")
    theirs = make_tag(users.user)

    names = {t["name"] for t in clients["owner"].get("/tags/get_my_tags").get_json()}
    paged = _names(clients["owner"].get("/tags/get_my_tags_paged"))

    assert names == paged == {mine.name}
    assert imported.name not in names and theirs.name not in names


def test_tag_listing_counts_rule_and_bundle_usage(clients, users):
    tag = make_tag(users.admin)
    tag_rule(make_rule(users.owner), tag)
    tag_rule(make_rule(users.owner), tag)
    tag_bundle(make_bundle(users.owner), tag)

    listed = next(t for t in clients["admin"].get("/tags/get_tags").get_json()["tags"] if t["id"] == tag.id)

    assert (listed["rule_count"], listed["bundle_count"]) == (2, 1)


def test_tag_listing_filters_by_search_and_visibility(clients, users):
    public = make_tag(users.admin, name="needle:public")
    private = make_tag(users.admin, name="needle:private", visibility="private")

    names = _names(clients["admin"].get("/tags/get_tags?search=needle&visibility=private"))

    assert names == {private.name} and public.name not in names


def test_tag_family_lists_its_members(clients, users):
    make_tag(users.admin, name="fam:a"), make_tag(users.admin, name="fam:b"), make_tag(users.admin, name="other:a")

    response = clients["admin"].get("/tags/get_family?family=fam")

    assert _names(response) == {"fam:a", "fam:b"}


# ── Edit ──────────────────────────────────────────────────────────────────────

def test_edit_tag_updates_its_fields(clients, users):
    tag = make_tag(users.owner)

    response = clients["owner"].post(f"/tags/edit_tag/{tag.id}", json={
        "name": "renamed:tag", "description": "New description", "color": "#000000", "icon": "fa-star"})

    tag = reload(tag)
    assert response.status_code == 200
    assert (tag.name, tag.description, tag.color, tag.icon) == ("renamed:tag", "New description", "#000000", "fa-star")
    assert tag.namespace == "renamed"


def test_edit_tag_never_lets_the_creator_activate_or_publish_it(clients, users):
    tag = make_tag(users.owner, visibility="private", active=False)

    clients["owner"].post(f"/tags/edit_tag/{tag.id}", json={
        "name": tag.name, "is_active": True, "is_approved_by_admin": True, "visibility": "public"})

    tag = reload(tag)
    assert (tag.is_active, tag.is_approved_by_admin, tag.visibility) == (False, False, "private")


def test_edit_tag_to_a_name_already_used_is_a_conflict(clients, users):
    tag, other = make_tag(users.owner), make_tag(users.owner)

    response = clients["owner"].post(f"/tags/edit_tag/{tag.id}", json={"name": other.name})

    assert response.status_code == 409
    assert reload(tag).name != other.name


def test_edit_tag_keeping_its_own_name_is_fine(clients, users):
    tag = make_tag(users.owner)

    response = clients["owner"].post(f"/tags/edit_tag/{tag.id}", json={"name": tag.name, "description": "Only this"})

    assert response.status_code == 200 and reload(tag).description == "Only this"


def test_edit_an_unknown_tag_is_not_found(clients):
    response = clients["admin"].post("/tags/edit_tag/999999", json={"name": "x"})

    assert response.status_code == 404


def test_toggle_visibility_goes_back_and_forth(clients, users):
    tag = make_tag(users.owner, visibility="private")

    clients["admin"].get(f"/tags/toggle_visibility?tag_uuid={tag.uuid}")
    assert reload(tag).visibility == "public"
    clients["admin"].get(f"/tags/toggle_visibility?tag_uuid={tag.uuid}")
    assert reload(tag).visibility == "private"


def test_toggle_status_goes_back_and_forth(clients, users):
    tag = make_tag(users.owner, active=False)

    clients["admin"].get(f"/tags/toggle_status?tag_uuid={tag.uuid}")
    assert reload(tag).is_active is True
    clients["admin"].get(f"/tags/toggle_status?tag_uuid={tag.uuid}")
    assert reload(tag).is_active is False


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_tag_removes_its_links_but_not_the_rules_or_bundles(clients, users):
    tag = make_tag(users.owner)
    rule, bundle = make_rule(users.owner), make_bundle(users.owner)
    tag_rule(rule, tag)
    tag_bundle(bundle, tag)

    response = clients["owner"].post(f"/tags/delete_tag/{tag.id}")

    assert response.status_code == 200
    assert reload(tag) is None
    assert count(RuleTagAssociation, tag_id=tag.id) == 0 and count(BundleTagAssociation, tag_id=tag.id) == 0
    assert reload(rule) is not None and reload(bundle) is not None


def test_delete_an_unknown_tag_is_not_found(clients):
    response = clients["admin"].post("/tags/delete_tag/999999")

    assert response.status_code == 404


def test_remove_tag_removes_it_and_its_links(clients, users):
    tag = make_tag(users.owner)
    tag_rule(make_rule(users.owner), tag)

    response = clients["admin"].get(f"/tags/remove_tag?tag_id={tag.id}")

    assert response.status_code == 200
    assert reload(tag) is None and count(RuleTagAssociation, tag_id=tag.id) == 0


@pytest.mark.parametrize("url", ["/tags/remove_tag?tag_id=999999", "/tags/toggle_visibility?tag_uuid=nope",
                                 "/tags/toggle_status?tag_uuid=nope"])
def test_acting_on_an_unknown_tag_is_not_found(url, clients):
    response = clients["admin"].get(url)

    assert response.status_code == 404


def test_remove_tag_records_the_activity(clients, users):
    tag = make_tag(users.owner)

    clients["admin"].get(f"/tags/remove_tag?tag_id={tag.id}")

    assert count(ActivityLog, action="tag.delete") == 1


def test_bulk_remove_of_unknown_tags_is_not_found(clients):
    response = clients["admin"].post("/tags/remove_tags_bulk", json={"ids": [999998, 999999]})

    assert response.status_code == 404 and count(Tag) == 2


def test_bulk_remove_removes_the_listed_tags_and_their_links(clients, users):
    gone = [make_tag(users.owner), make_tag(users.owner)]
    kept = make_tag(users.owner)
    rule = make_rule(users.owner)
    for tag in (*gone, kept):
        tag_rule(rule, tag)

    response = clients["admin"].post("/tags/remove_tags_bulk", json={"ids": [t.id for t in gone]})

    assert response.status_code == 200 and response.get_json()["deleted"] == 2
    assert all(reload(t) is None for t in gone) and reload(kept) is not None
    assert {a.tag_id for a in RuleTagAssociation.query.filter_by(rule_id=rule.id)} == {kept.id}


def test_bulk_remove_never_removes_a_users_imported_tags(clients, users):
    """A user only bulk-removes their own *manual* tags."""
    imported = make_tag(users.owner, source="Taxonomy")

    response = clients["owner"].post("/tags/remove_tags_bulk", json={"ids": [imported.id]})

    assert response.status_code == 400 and reload(imported) is not None


def test_delete_family_removes_every_member_only(clients, users):
    members = [make_tag(users.admin, name="fam:a"), make_tag(users.admin, name="fam:b")]
    outsider = make_tag(users.admin, name="family:a")
    tag_rule(make_rule(users.owner), members[0])
    linked_id = members[0].id

    response = clients["admin"].post("/tags/delete_family", json={"family": "fam"})

    assert response.status_code == 200 and response.get_json()["deleted"] == 2
    assert all(reload(t) is None for t in members) and reload(outsider) is not None
    assert count(RuleTagAssociation, tag_id=linked_id) == 0


def test_delete_family_can_be_limited_to_one_source(clients, users):
    manual = make_tag(users.admin, name="fam:manual")
    taxonomy = make_tag(users.admin, name="fam:taxonomy", source="Taxonomy")

    clients["admin"].post("/tags/delete_family", json={"family": "fam", "source": "Taxonomy"})

    assert reload(taxonomy) is None and reload(manual) is not None


def test_delete_an_unknown_family_is_not_found(clients, users):
    tag = make_tag(users.admin, name="fam:a")

    response = clients["admin"].post("/tags/delete_family", json={"family": "nothing-here"})

    assert response.status_code == 404 and reload(tag) is not None


# ── MISP taxonomies / galaxies ────────────────────────────────────────────────

def test_import_taxonomy_creates_public_active_tags(clients, users, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    response = clients["admin"].get(f"/tags/add_tags_misp?uuid={TAXONOMY_UUID}")

    tags = Tag.query.filter_by(source="Taxonomy").all()
    assert response.status_code == 200
    assert {t.name for t in tags} == {"testtax:first", "testtax:second"}
    assert all(t.visibility == "public" and t.is_active and t.is_approved_by_admin for t in tags)
    assert all(t.created_by == users.admin.id for t in tags)


def test_import_taxonomy_twice_adds_nothing(clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)
    clients["admin"].get(f"/tags/add_tags_misp?uuid={TAXONOMY_UUID}")

    response = clients["admin"].get(f"/tags/add_tags_misp?uuid={TAXONOMY_UUID}")

    assert response.status_code == 200 and count(Tag, source="Taxonomy") == 2


def test_imported_taxonomy_leaves_the_import_list(clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)
    before = clients["admin"].get("/tags/get_tags_misp").get_json()["tags"]

    clients["admin"].get(f"/tags/add_tags_misp?uuid={TAXONOMY_UUID}")

    after = clients["admin"].get("/tags/get_tags_misp").get_json()["tags"]
    assert [t["namespace"] for t in before] == ["testtax"] and after == []


def test_import_an_unknown_taxonomy_is_not_found(clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    response = clients["admin"].get("/tags/add_tags_misp?uuid=00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404 and count(Tag, source="Taxonomy") == 0


def test_import_galaxy_creates_one_tag_per_cluster(clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    response = clients["admin"].post("/tags/add_tags_galaxy", json={"uuid": GALAXY_UUID})

    tags = Tag.query.filter_by(source="Galaxy").all()
    assert response.status_code == 200
    assert {t.name for t in tags} == {'misp-galaxy:testgal="Alpha"', 'misp-galaxy:testgal="Beta"'}
    assert {t.external_id for t in tags} == set(CLUSTER_UUIDS)
    assert all(t.icon == "shield-alt" and t.namespace == "testgal" for t in tags)


def test_import_galaxy_can_pick_clusters(clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    clients["admin"].post("/tags/add_tags_galaxy", json={"uuid": GALAXY_UUID, "cluster_uuids": [CLUSTER_UUIDS[1]]})

    assert [t.name for t in Tag.query.filter_by(source="Galaxy")] == ['misp-galaxy:testgal="Beta"']


def test_galaxy_clusters_show_which_are_already_imported(clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)
    clients["admin"].post("/tags/add_tags_galaxy", json={"uuid": GALAXY_UUID, "cluster_uuids": [CLUSTER_UUIDS[0]]})

    clusters = clients["admin"].get(f"/tags/get_galaxy_clusters/{GALAXY_UUID}").get_json()["clusters"]

    assert {c["value"]: c["already_imported"] for c in clusters} == {"Alpha": True, "Beta": False}


def test_import_an_unknown_galaxy_is_refused(clients, tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)

    response = clients["admin"].post("/tags/add_tags_galaxy", json={"uuid": "nope"})

    assert response.status_code in (400, 404) and count(Tag, source="Galaxy") == 0


def test_import_all_taxonomies_job_imports_and_is_idempotent(app, users, tmp_path, monkeypatch):
    from app.features.jobs.job_handlers import handle_import_all_taxonomies
    fake_misp_data(tmp_path, monkeypatch)

    for _ in range(2):
        job = BackgroundJob(uuid=f"job-{_}", job_type="import_all_taxonomies", status="running",
                            created_by=users.admin.id)
        db.session.add(job)
        db.session.commit()
        handle_import_all_taxonomies(job, app)

    assert count(Tag, source="Taxonomy") == 2


# ── Rule validation review ────────────────────────────────────────────────────

def test_dismissing_quarantined_rules_is_recorded_on_the_run(clients, users):
    job = BackgroundJob(uuid="validation-run", job_type="rule_validation_run", status="done",
                        created_by=users.admin.id, payload={"result": {"dismissed_rule_ids": [1]}})
    db.session.add(job)
    db.session.commit()

    response = clients["admin"].post("/tags/admin/validation/dismiss",
                                     json={"job_uuid": job.uuid, "rule_ids": [2, "3"]})

    assert response.status_code == 200
    assert sorted(reload(job).payload["result"]["dismissed_rule_ids"]) == [1, 2, 3]


def test_dismissing_on_an_unknown_run_is_not_found(clients):
    response = clients["admin"].post("/tags/admin/validation/dismiss", json={"job_uuid": "nope", "rule_ids": [1]})

    assert response.status_code == 404


def test_quarantined_rules_list_the_runs_rules_with_their_risk(clients, users):
    rule, other = make_rule(users.owner), make_rule(users.owner)
    job = BackgroundJob(uuid="validation-run", job_type="rule_validation_run", status="done",
                        created_by=users.admin.id, payload={"result": {"quarantined": [
                            {"rule_id": rule.id, "hits": 3, "proposed_tag": "false-positive:risk=high"}]}})
    db.session.add(job)
    db.session.commit()

    data = clients["admin"].get(f"/tags/admin/validation/rules_data_table?job_uuid={job.uuid}").get_json()

    assert [i["id"] for i in data["items"]] == [rule.id] and other.id not in [i["id"] for i in data["items"]]
    assert data["items"][0]["validation_risk"]["proposed_level"] == "high"
