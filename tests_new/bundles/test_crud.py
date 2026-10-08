"""Bundles — layer 2: create / read / edit / delete, checked in the database.

Also the bundle's own lifecycle: rules and folder structure, votes,
favorites, notes, releases, share link, health, history and downloads.
"""
import io
import json
import zipfile

from app import db
from app.core.db_class.db import (
    Bundle, BundleFavoriteUser, BundleHistory, BundleNode, BundleNote, BundleRelease, BundleRuleAssociation,
    BundleTagAssociation, BundleVote, UserConfig,
)
from app.features.bundle import bundle_core as BundleModel
from app.features.bundle import bundle_layout_core as BundleLayoutModel
from tests_new.helpers.bundles import (
    add_rules, edit_bundle_form, file, folder, make_bundle, make_note, make_release, make_tag, new_bundle_form,
    rule_node, share,
)
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule, yara_rule


def _trash(rule):
    rule.is_deleted = True
    db.session.commit()
    return rule


def _zip_names(response):
    return zipfile.ZipFile(io.BytesIO(response.data)).namelist()


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_bundle_stores_it_owned_by_the_creator(clients, users):
    form = new_bundle_form()

    response = clients["owner"].post("/bundle/create", data=form)

    bundle = Bundle.query.filter_by(name=form["name"]).one()
    assert response.status_code == 302 and f"/bundle/edit/{bundle.id}" in response.headers["Location"]
    assert bundle.user_id == users.owner.id
    assert bundle.description == form["description"]
    assert bundle.access is True


def test_create_bundle_without_the_public_box_makes_it_private(clients):
    form = new_bundle_form()
    del form["public"]

    clients["owner"].post("/bundle/create", data=form)

    assert Bundle.query.filter_by(name=form["name"]).one().access is False


def test_create_bundle_records_a_creation_history_entry(clients):
    form = new_bundle_form()

    clients["owner"].post("/bundle/create", data=form)

    bundle = Bundle.query.filter_by(name=form["name"]).one()
    assert count(BundleHistory, bundle_id=bundle.id, action="created") == 1


def test_bundle_created_by_an_admin_is_verified(clients):
    by_admin, by_user = new_bundle_form(), new_bundle_form()

    clients["admin"].post("/bundle/create", data=by_admin)
    clients["owner"].post("/bundle/create", data=by_user)

    assert Bundle.query.filter_by(name=by_admin["name"]).one().is_verified is True
    assert Bundle.query.filter_by(name=by_user["name"]).one().is_verified is False


def test_create_bundle_with_a_name_you_already_use_is_refused(clients, users):
    existing = make_bundle(users.owner)

    response = clients["owner"].post("/bundle/create", data=new_bundle_form(name=existing.name))

    assert response.status_code == 200
    assert count(Bundle, name=existing.name) == 1


def test_create_bundle_with_a_name_another_user_uses_is_allowed(clients, users):
    """Bundle names are unique per user, not per instance."""
    existing = make_bundle(users.user)

    clients["owner"].post("/bundle/create", data=new_bundle_form(name=existing.name))

    assert count(Bundle, name=existing.name, user_id=users.owner.id) == 1


def test_rename_bundle_to_a_name_the_owner_already_uses_is_refused(clients, users):
    taken, bundle = make_bundle(users.owner), make_bundle(users.owner)

    clients["admin"].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, name=taken.name))

    assert reload(bundle).name != taken.name


def test_rename_bundle_to_a_name_another_user_uses_is_allowed(clients, users):
    other, bundle = make_bundle(users.user), make_bundle(users.owner)

    clients["owner"].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, name=other.name))

    assert reload(bundle).name == other.name


def test_create_private_bundle_for_a_rule(clients, users):
    rule = make_rule(users.owner)

    response = clients["owner"].post("/bundle/add-single-rule",
                                     json={"rule_id": rule.id, "new_bundle_name": "For my rule", "is_public": False})

    bundle = Bundle.query.filter_by(name="For my rule").one()
    assert response.get_json()["id"] == bundle.id
    assert bundle.user_id == users.owner.id and bundle.access is False


def test_create_bundle_for_a_trashed_rule_is_not_found(clients, users):
    rule = _trash(make_rule(users.owner))

    response = clients["owner"].post("/bundle/add-single-rule", json={"rule_id": rule.id, "new_bundle_name": "Nope"})

    assert response.status_code == 404
    assert count(Bundle) == 0


# ── Read ──────────────────────────────────────────────────────────────────────

def test_bundle_page_shows_its_rules(clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)

    data = clients["anonymous"].get(f"/bundle/get_bundle_page?bundle_id={bundle.id}").get_json()

    assert data["bundle"]["name"] == bundle.name
    assert data["pagination"]["total_rules"] == 1


def test_bundle_page_tells_the_visitor_their_vote_and_favorite(clients, users):
    bundle = make_bundle(users.owner)
    clients["user"].post(f"/bundle/evaluate?bundleId={bundle.id}&voteType=up")
    clients["user"].post(f"/bundle/favorite/{bundle.id}")

    data = clients["user"].get(f"/bundle/get_bundle_page?bundle_id={bundle.id}").get_json()["bundle"]

    assert data["user_vote"] == "up" and data["is_favorited"] is True


def test_trashed_rules_are_hidden_from_the_bundle(clients, users):
    kept, trashed = make_rule(users.owner), make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), kept, trashed)
    _trash(trashed)

    page = clients["anonymous"].get(f"/bundle/get_bundle_page?bundle_id={bundle.id}").get_json()
    rules = clients["anonymous"].get(f"/bundle/get_rules_page_from_bundle?bundle_id={bundle.id}").get_json()
    content = clients["anonymous"].get(f"/bundle/{bundle.id}/rule_content/{trashed.id}")

    assert page["pagination"]["total_rules"] == 1
    assert [r["title"] for r in rules["rules_list"]] == [kept.title]
    assert content.status_code == 404


def test_bundle_rule_count_ignores_trashed_rules(clients, users):
    kept, trashed = make_rule(users.owner), make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), kept, trashed)
    _trash(trashed)

    items = clients["anonymous"].get("/bundle/data_table").get_json()["items"]

    assert [b["number_of_rules"] for b in items if b["id"] == bundle.id] == [1]


def test_bundle_list_filters_by_visibility_and_search(clients, users):
    public = make_bundle(users.owner, name="Ransomware pack")
    private = make_bundle(users.owner, name="Ransomware drafts", public=False)
    make_bundle(users.owner, name="Something else")

    public_only = clients["owner"].get("/bundle/data_table?access=public&search=ransomware").get_json()
    private_only = clients["owner"].get("/bundle/data_table?access=private").get_json()

    assert [b["name"] for b in public_only["items"]] == [public.name]
    assert [b["name"] for b in private_only["items"]] == [private.name]


def test_my_bundles_lists_mine_including_private_ones(clients, users):
    public, private = make_bundle(users.owner), make_bundle(users.owner, public=False)
    make_bundle(users.user)

    data = clients["owner"].get("/bundle/my-bundles").get_json()

    assert {b["name"] for b in data["bundles"]} == {public.name, private.name}


def test_bundles_containing_a_rule(clients, users):
    rule = make_rule(users.user)
    with_rule = add_rules(make_bundle(users.owner), rule)
    make_bundle(users.owner)

    data = clients["anonymous"].get(f"/bundle/get_bundle_list_rule_part_of?rule_id={rule.id}").get_json()

    assert [b["id"] for b in data["bundles"]] == [with_rule.id]
    assert data["bundles"][0]["rule_paths"] == [f"Unsorted/{rule.title}"]


# ── Edit ──────────────────────────────────────────────────────────────────────

def test_edit_bundle_changes_its_details_and_records_history(clients, users):
    """Edited by the admin: the owner's own edits right after creating it are
    folded into the "created" history entry."""
    bundle = make_bundle(users.owner)

    clients["admin"].post(f"/bundle/edit/{bundle.id}",
                          data=edit_bundle_form(bundle, name="New name", description="New description",
                                                vulnerabilities='["CVE-2024-1111"]'))

    edited = reload(bundle)
    assert (edited.name, edited.description) == ("New name", "New description")
    assert json.loads(edited.vulnerability_identifiers) == ["CVE-2024-1111"]
    assert count(BundleHistory, bundle_id=bundle.id, action="details") == 1


def test_edit_bundle_comes_back_on_the_settings_tab(clients, users):
    bundle = make_bundle(users.owner)

    response = clients["owner"].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, name="Renamed"))

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/bundle/edit/{bundle.id}?tab=settings")


def test_edit_bundle_unticking_public_makes_it_private(clients, users):
    bundle = make_bundle(users.owner)

    clients["owner"].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, public=None))

    assert reload(bundle).access is False


def test_edit_bundle_to_another_bundles_name_is_refused(clients, users):
    other, bundle = make_bundle(users.owner), make_bundle(users.owner)

    clients["owner"].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, name=other.name))

    assert reload(bundle).name != other.name


def test_change_visibility_toggles_it_and_answers_the_new_visibility(clients, users):
    bundle = make_bundle(users.owner)

    first = clients["owner"].post(f"/bundle/edit_access?id={bundle.id}").get_json()
    assert first["new_access"] is False and reload(bundle).access is False

    second = clients["owner"].post(f"/bundle/edit_access?id={bundle.id}").get_json()
    assert second["new_access"] is True and reload(bundle).access is True


def test_set_tags_replaces_the_bundle_tags(clients, users):
    old, new = make_tag("workflow:todo", users.admin), make_tag("workflow:done", users.admin)
    bundle = make_bundle(users.owner)
    BundleModel.update_bundle_tags(bundle.id, [old.id], users.owner)

    clients["owner"].post(f"/bundle/update_bundle_tags/{bundle.id}", json={"tag_ids": [new.id]})

    assert [a.tag_id for a in BundleTagAssociation.query.filter_by(bundle_id=bundle.id)] == [new.id]


# ── Rules and structure ───────────────────────────────────────────────────────

def test_add_rule_attaches_it_and_places_it_in_the_tree(clients, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.user)

    clients["owner"].post(f"/bundle/add_rule_bundle?bundle_id={bundle.id}&rule_id={rule.id}&description=why")

    assert BundleRuleAssociation.query.filter_by(bundle_id=bundle.id, rule_id=rule.id).one().description == "why"
    node = BundleNode.query.filter_by(bundle_id=bundle.id, rule_id=rule.id).one()
    assert node.parent.name == "Unsorted"


def test_add_the_same_rule_twice_creates_no_duplicate(clients, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.owner)

    for _ in range(2):
        clients["owner"].post(f"/bundle/add_rule_bundle?bundle_id={bundle.id}&rule_id={rule.id}")

    assert count(BundleRuleAssociation, bundle_id=bundle.id) == 1
    assert count(BundleNode, bundle_id=bundle.id, rule_id=rule.id) == 1


def test_add_a_trashed_rule_is_refused(clients, users):
    bundle, rule = make_bundle(users.owner), _trash(make_rule(users.owner))

    response = clients["owner"].post(f"/bundle/add_rule_bundle?bundle_id={bundle.id}&rule_id={rule.id}")

    assert 400 <= response.status_code < 500
    assert count(BundleRuleAssociation, bundle_id=bundle.id) == 0


def test_remove_rule_detaches_it_and_drops_it_from_the_tree(clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)

    clients["owner"].post(f"/bundle/remove?bundle_id={bundle.id}&rule_id={rule.id}")

    assert count(BundleRuleAssociation, bundle_id=bundle.id) == 0
    assert count(BundleNode, bundle_id=bundle.id, rule_id=rule.id) == 0


def test_change_why_a_rule_is_in_the_bundle_saves_it(clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    association = BundleRuleAssociation.query.filter_by(bundle_id=bundle.id).one()

    clients["owner"].post(f"/bundle/change_description?association_id={association.id}&new_description=Covers%20T1059")

    db.session.rollback()
    assert reload(association).description == "Covers T1059"


def test_save_structure_stores_the_tree_and_syncs_the_rules(clients, users):
    kept, dropped, added = make_rule(users.owner), make_rule(users.owner), make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), kept, dropped)

    response = clients["owner"].post(f"/bundle/save_workspace/{bundle.id}", json={"structure": [
        folder("Detection", rule_node(kept), folder("New", rule_node(added))),
        file("README.md", "how to deploy"),
    ]})

    assert response.status_code == 200
    assert {a.rule_id for a in BundleRuleAssociation.query.filter_by(bundle_id=bundle.id)} == {kept.id, added.id}
    assert BundleNode.query.filter_by(bundle_id=bundle.id, name="README.md").one().custom_content == "how to deploy"
    assert BundleNode.query.filter_by(bundle_id=bundle.id, rule_id=added.id).one().parent.name == "New"


def test_save_structure_drops_trashed_rules(clients, users):
    bundle, trashed = make_bundle(users.owner), _trash(make_rule(users.owner))

    clients["owner"].post(f"/bundle/save_workspace/{bundle.id}", json={"structure": [folder("Main", rule_node(trashed))]})

    assert count(BundleRuleAssociation, bundle_id=bundle.id) == 0
    assert count(BundleNode, bundle_id=bundle.id, rule_id=trashed.id) == 0


def test_structure_is_returned_as_saved(clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    BundleModel.save_workspace(bundle.id, [folder("Main", rule_node(rule), file("README.md", "hi"))])

    tree = clients["anonymous"].get(f"/bundle/get_bundle_json/{bundle.id}").get_json()["structure"]

    assert tree[0]["name"] == "Main"
    assert [c.get("rule_id") for c in tree[0]["children"]] == [rule.id, None]


def test_rebuild_structure_places_attached_rules_in_unsorted(clients, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.owner)
    db.session.add(BundleRuleAssociation(bundle_id=bundle.id, rule_id=rule.id))
    db.session.commit()

    clients["admin"].post(f"/bundle/update_bundle_from_structure?id={bundle.id}")

    assert BundleNode.query.filter_by(bundle_id=bundle.id, rule_id=rule.id).one().parent.name == "Unsorted"


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_bundle_removes_it_and_what_belongs_to_it(clients, users):
    """Folder nodes and favorites go through the database's ON DELETE CASCADE
    (PostgreSQL), which the SQLite test database doesn't enforce."""
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    BundleModel.update_bundle_tags(bundle.id, [make_tag("workflow:todo", users.admin).id], users.owner)
    make_note(bundle, users.user)
    make_release(bundle, users.owner)
    clients["user"].post(f"/bundle/evaluate?bundleId={bundle.id}&voteType=up")
    clients["user"].post(f"/bundle/favorite/{bundle.id}")
    bundle_id = bundle.id

    response = clients["owner"].post(f"/bundle/delete?id={bundle_id}")

    assert response.status_code == 200 and reload(bundle) is None
    for model in (BundleRuleAssociation, BundleTagAssociation, BundleNote, BundleRelease, BundleVote):
        assert count(model, bundle_id=bundle_id) == 0, model.__name__
    assert reload(rule) is not None


def test_delete_bundle_without_an_id_deletes_nothing(clients, users):
    bundle = make_bundle(users.admin)

    response = clients["admin"].post("/bundle/delete")

    assert response.status_code == 400
    assert reload(bundle) is not None


# ── Votes and favorites ───────────────────────────────────────────────────────

def test_vote_up_counts_once_and_a_second_click_cancels_it(clients, users):
    bundle = make_bundle(users.owner)

    first = clients["user"].post(f"/bundle/evaluate?bundleId={bundle.id}&voteType=up").get_json()
    second = clients["user"].post(f"/bundle/evaluate?bundleId={bundle.id}&voteType=up").get_json()

    assert (first["vote_up"], first["user_vote"]) == (1, "up")
    assert (second["vote_up"], second["user_vote"]) == (0, None)
    assert count(BundleVote, bundle_id=bundle.id) == 0


def test_vote_down_after_up_switches_the_vote(clients, users):
    bundle = make_bundle(users.owner)

    clients["user"].post(f"/bundle/evaluate?bundleId={bundle.id}&voteType=up")
    data = clients["user"].post(f"/bundle/evaluate?bundleId={bundle.id}&voteType=down").get_json()

    assert (data["vote_up"], data["vote_down"], data["user_vote"]) == (0, 1, "down")
    assert BundleVote.query.filter_by(bundle_id=bundle.id).one().vote_type == "down"


def test_voters_lists_who_voted(clients, users):
    bundle = make_bundle(users.owner)
    clients["user"].post(f"/bundle/evaluate?bundleId={bundle.id}&voteType=up")

    data = clients["anonymous"].get(f"/bundle/voters?bundleId={bundle.id}&voteType=up").get_json()

    assert data["total"] == 1 and data["users"][0]["id"] == users.user.id


def test_favorite_toggles(clients, users):
    bundle = make_bundle(users.owner)

    added = clients["user"].post(f"/bundle/favorite/{bundle.id}").get_json()
    favorites = clients["user"].get("/bundle/data_table?favorites=true").get_json()["items"]
    removed = clients["user"].post(f"/bundle/favorite/{bundle.id}").get_json()

    assert added["is_favorited"] is True and [b["id"] for b in favorites] == [bundle.id]
    assert removed["is_favorited"] is False and count(BundleFavoriteUser) == 0


# ── Notes ─────────────────────────────────────────────────────────────────────

def test_add_note_stores_it(clients, users):
    bundle = make_bundle(users.owner)

    response = clients["user"].post(f"/bundle/{bundle.id}/notes",
                                    json={"title": "Noisy on DCs", "content": "Tune it", "severity": "critical"})

    note = BundleNote.query.filter_by(bundle_id=bundle.id).one()
    assert response.status_code == 201
    assert (note.user_id, note.title, note.severity, note.status) == (users.user.id, "Noisy on DCs", "critical", "open")


def test_add_note_with_an_allowed_tag(clients, users):
    bundle, tag = make_bundle(users.owner), make_tag("false-positive:risk=high", users.admin)

    clients["user"].post(f"/bundle/{bundle.id}/notes", json={"title": "False positive", "content": "x", "tag_ids": [tag.id]})

    assert [a.tag_id for a in BundleNote.query.one().tag_assocs] == [tag.id]


def test_add_note_with_a_tag_outside_the_note_taxonomies_is_refused(clients, users):
    bundle, tag = make_bundle(users.owner), make_tag("tlp:red", users.admin)

    response = clients["user"].post(f"/bundle/{bundle.id}/notes", json={"title": "False positive", "content": "x", "tag_ids": [tag.id]})

    assert response.status_code == 400 and count(BundleNote) == 0


def test_notes_list_open_ones_first(clients, users):
    bundle = make_bundle(users.owner)
    resolved = make_note(bundle, users.user, title="Old issue", status="resolved")
    open_note = make_note(bundle, users.user, title="Current issue")

    data = clients["anonymous"].get(f"/bundle/{bundle.id}/notes").get_json()

    assert [n["id"] for n in data["notes"]] == [open_note.id, resolved.id]
    assert data["open"] == 1


def test_edit_note_changes_it(clients, users):
    note = make_note(make_bundle(users.owner), users.user)

    clients["user"].put(f"/bundle/{note.bundle_id}/notes/{note.id}",
                        json={"title": "Updated title", "content": "Updated content", "severity": "info"})

    edited = reload(note)
    assert (edited.title, edited.content, edited.severity) == ("Updated title", "Updated content", "info")


def test_resolve_and_reopen_note(clients, users):
    note = make_note(make_bundle(users.owner), users.user)
    url = f"/bundle/{note.bundle_id}/notes/{note.id}/status"

    clients["owner"].post(url, json={"status": "resolved"})
    resolved = reload(note)
    assert (resolved.status, resolved.resolved_by_id) == ("resolved", users.owner.id)

    clients["owner"].post(url, json={"status": "open"})
    assert (reload(note).status, reload(note).resolved_by_id) == ("open", None)


def test_too_many_notes_in_an_hour_are_refused(clients, users):
    bundle = make_bundle(users.owner)
    for i in range(10):
        make_note(bundle, users.user, title=f"Note {i}")

    response = clients["user"].post(f"/bundle/{bundle.id}/notes", json={"title": "One more", "content": "x"})

    assert response.status_code == 429 and count(BundleNote, bundle_id=bundle.id) == 10


# ── Releases ──────────────────────────────────────────────────────────────────

def test_publish_release_freezes_the_bundle(clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    frozen = rule.to_string

    response = clients["owner"].post(f"/bundle/{bundle.id}/releases", json={"version": "v1.0.0", "title": "First"})
    rule.to_string = yara_rule("changed_after_release")
    db.session.commit()
    released = clients["anonymous"].get(f"/bundle/{bundle.id}/rule_content/{rule.id}?release=v1.0.0").get_json()

    release = BundleRelease.query.filter_by(bundle_id=bundle.id).one()
    assert response.status_code == 201
    assert (release.version, release.title, release.rule_count, release.user_id) == ("v1.0.0", "First", 1, users.owner.id)
    assert released["content"] == frozen


def test_publish_release_with_an_existing_version_is_refused(clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    make_release(bundle, users.owner, "v1.0.0")

    response = clients["owner"].post(f"/bundle/{bundle.id}/releases", json={"version": "v1.0.0"})

    assert response.status_code == 400 and count(BundleRelease, bundle_id=bundle.id) == 1


def test_publish_release_of_an_empty_bundle_is_refused(clients, users):
    bundle = make_bundle(users.owner)

    response = clients["owner"].post(f"/bundle/{bundle.id}/releases", json={"version": "v1.0.0"})

    assert response.status_code == 400 and count(BundleRelease) == 0


def test_releases_are_listed_newest_first(clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    make_release(bundle, users.owner, "v1.0.0")
    BundleModel.add_rule_to_bundle(bundle.id, make_rule(users.owner).id, "")
    make_release(bundle, users.owner, "v1.1.0")

    data = clients["anonymous"].get(f"/bundle/{bundle.id}/releases").get_json()

    assert [r["version"] for r in data["releases"]] == ["v1.1.0", "v1.0.0"]
    assert data["can_manage"] is False


def test_release_changes_against_the_live_bundle(clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    release = make_release(bundle, users.owner)
    added = make_rule(users.owner)
    BundleModel.add_rule_to_bundle(bundle.id, added.id, "")

    data = clients["anonymous"].get(f"/bundle/{bundle.id}/releases/{release.id}/changes").get_json()

    assert data["from"] == "v1.0.0" and data["to"] == "current"
    assert added.title in json.dumps(data["diff"])


def test_download_release(clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    release = make_release(bundle, users.owner)

    response = clients["anonymous"].get(f"/bundle/{bundle.id}/releases/{release.id}/download")

    assert response.status_code == 200 and response.mimetype == "application/zip"
    assert any(rule.title in name for name in _zip_names(response))


def test_delete_release_removes_only_that_release(clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    first = make_release(bundle, users.owner, "v1.0.0")
    BundleModel.add_rule_to_bundle(bundle.id, make_rule(users.owner).id, "")
    second = make_release(bundle, users.owner, "v1.1.0")

    clients["owner"].delete(f"/bundle/{bundle.id}/releases/{first.id}")

    assert reload(first) is None and reload(second) is not None


# ── Share link ────────────────────────────────────────────────────────────────

def test_share_link_create_regenerate_and_revoke(clients, users):
    bundle = make_bundle(users.owner, public=False)
    url = f"/bundle/{bundle.id}/share"

    created = clients["owner"].post(url).get_json()["url"]
    first_key = reload(bundle).share_token
    clients["owner"].post(url)
    second_key = reload(bundle).share_token
    clients["owner"].delete(url)

    assert first_key in created and first_key != second_key
    assert reload(bundle).share_token is None
    assert clients["owner"].get(url).get_json()["url"] is None


# ── Health and history ────────────────────────────────────────────────────────

def test_health_report_runs_the_checks(clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))

    data = clients["anonymous"].get(f"/bundle/{bundle.id}/health").get_json()

    assert data["success"] is True and data["health"]["checks"]
    assert data["can_rerun"] is False


def test_health_fix_places_an_attached_rule(clients, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.owner)
    db.session.add(BundleRuleAssociation(bundle_id=bundle.id, rule_id=rule.id))
    db.session.commit()

    response = clients["owner"].post(f"/bundle/{bundle.id}/health/fix", json={"fix": {"action": "place_rule", "rule_id": rule.id}})

    assert response.status_code == 200
    assert count(BundleNode, bundle_id=bundle.id, rule_id=rule.id) == 1


def test_history_lists_the_changes(clients, users):
    bundle = make_bundle(users.owner)
    clients["admin"].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, description="Changed"))

    data = clients["anonymous"].get(f"/bundle/history/{bundle.id}").get_json()
    entry = clients["anonymous"].get(f"/bundle/history/{bundle.id}/{data['entries'][0]['id']}").get_json()

    assert [e["action"] for e in data["entries"]] == ["details", "created"]
    assert entry["entry"]["action"] == "details"


# ── Downloads ─────────────────────────────────────────────────────────────────

def test_download_rules_ships_active_rules_only_and_counts_it(clients, users):
    kept, trashed = make_rule(users.owner), make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), kept, trashed)
    _trash(trashed)

    response = clients["anonymous"].get(f"/bundle/download?bundle_id={bundle.id}")

    names = _zip_names(response)
    assert any(kept.title.replace(" ", "_") in n for n in names)
    assert not any(trashed.title.replace(" ", "_") in n for n in names)
    assert reload(bundle).download_count == 1


def test_download_structure_follows_the_tree(clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    BundleModel.save_workspace(bundle.id, [folder("Main", rule_node(rule), file("README.md", "hi"))])

    names = _zip_names(clients["anonymous"].get(f"/bundle/download_structure?bundle_id={bundle.id}"))

    assert f"Main/{rule.title}.yar" in names and "Main/README.md" in names


def test_download_files_ships_only_the_custom_files(clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    BundleModel.save_workspace(bundle.id, [folder("Main", rule_node(rule), file("README.md", "hi"))])

    names = _zip_names(clients["anonymous"].get(f"/bundle/download_files?bundle_id={bundle.id}"))

    assert names == ["Main/README.md"]


def test_download_full_has_everything(clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))

    names = _zip_names(clients["anonymous"].get(f"/bundle/download_full?bundle_id={bundle.id}"))

    assert {"README.md", "description.md", "bundle.json"} <= set(names)


def test_download_misp_is_a_misp_event(clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))

    response = clients["anonymous"].get(f"/bundle/download_misp?bundle_id={bundle.id}")

    assert response.status_code == 200 and response.mimetype == "application/json"
    assert bundle.name in json.dumps(json.loads(response.data))


# ── Structure editor layout (per user) ────────────────────────────────────────

def _layout(**changes):
    """The default layout with some panels changed: {panel_id: {field: value}}."""
    panels = [dict(p, **changes.get(p["id"], {})) for p in BundleLayoutModel.DEFAULT_LAYOUT["panels"]]
    return {"panels": panels}


def _stored_layout(user):
    config = UserConfig.query.filter_by(user_id=user.id).first()
    return (config.meta or {}).get("bundle_editor_layout") if config else None


def test_editor_layout_is_the_default_until_saved(clients):
    response = clients["user"].get("/bundle/editor_layout")

    assert response.get_json() == BundleLayoutModel.DEFAULT_LAYOUT


def test_save_editor_layout_stores_it_for_the_user(clients, users):
    layout = _layout(library={"x": 0, "y": 0, "w": 12, "h": 10}, explorer={"y": 10}, overview={"hidden": False})

    response = clients["user"].post("/bundle/editor_layout", json=layout)

    assert response.status_code == 200
    assert _stored_layout(users.user) == layout
    assert clients["user"].get("/bundle/editor_layout").get_json() == layout


def test_save_editor_layout_keeps_floating_panels(clients, users):
    """A panel shown as a window keeps its position and size; the library can be a drawer."""
    window = {"x": 900, "y": 120, "w": 640, "h": 600}
    layout = _layout(preview={"mode": "window", "win": window, "minimized": True},
                     library={"mode": "drawer", "win": {"x": 0, "y": 0, "w": 560, "h": 800}})

    clients["user"].post("/bundle/editor_layout", json=layout)

    stored = {p["id"]: p for p in _stored_layout(users.user)["panels"]}
    assert (stored["preview"]["mode"], stored["preview"]["win"], stored["preview"]["minimized"]) == ("window", window, True)
    assert stored["library"]["mode"] == "drawer"


def test_editor_layout_belongs_to_one_user(clients, users):
    clients["owner"].post("/bundle/editor_layout", json=_layout(preview={"hidden": True}))

    response = clients["user"].get("/bundle/editor_layout")

    assert response.get_json() == BundleLayoutModel.DEFAULT_LAYOUT
    assert _stored_layout(users.user) is None


def test_reset_editor_layout_forgets_it(clients, users):
    clients["user"].post("/bundle/editor_layout", json=_layout(preview={"hidden": True}))

    response = clients["user"].post("/bundle/editor_layout/reset")

    assert response.get_json() == BundleLayoutModel.DEFAULT_LAYOUT
    assert _stored_layout(users.user) is None
