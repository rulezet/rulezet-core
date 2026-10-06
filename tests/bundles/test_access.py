"""Bundles — layer 1: who can do what.

Permission model: a public bundle (`Bundle.access = True`) is readable by
everyone; a private one only by its owner, an admin, or a logged-in user who
opened its current share link. Creating a bundle, voting, favoriting and
adding a note need an account (and read access); notes on a private bundle
are for its owner / admin only. Editing a bundle — details, visibility, tags,
rules, structure, share link, health fixes, releases — is for the owner or an
admin, as is rebuilding the structure from the attached rules. A note can be
edited / deleted / resolved by its author or the bundle's owner / admin; while
the bundle is private its author can't reach it, and gets it back (still
theirs) once the bundle is public again. A private bundle never shows up for anyone else
in a list, a search, a filter facet or a count.
"""
import pytest

from app import db
from app.core.db_class.db import (
    Bundle, BundleFavoriteUser, BundleNode, BundleNote, BundleRelease, BundleRuleAssociation,
    BundleTagAssociation, BundleVote, Tag,
)
from app.features.bundle import bundle_core as BundleModel
from tests.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from tests.helpers.bundles import (
    add_rules, edit_bundle_form, file, folder, make_bundle, make_note, make_release, make_tag, new_bundle_form,
    rule_node, share,
)
from tests.helpers.db import count, reload
from tests.helpers.rules import make_rule

EVERYONE = {"anonymous": OK, "user": OK, "owner": OK, "admin": OK}
LOGGED_IN = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK}
OWNER_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}
ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}
PRIVATE_READ = {"anonymous": FORBIDDEN, "user": FORBIDDEN, "owner": OK, "admin": OK}
PRIVATE_LOGGED_IN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK}


def _full_bundle(owner, *, public):
    """A bundle with one rule, a README file, a release, a note and a CVE —
    something to leak in every read route."""
    rule = make_rule(owner)
    bundle = add_rules(make_bundle(owner, public=public, vulnerability_identifiers='["CVE-2024-0001"]'), rule)
    BundleModel.save_workspace(bundle.id, [folder("Main", rule_node(rule), file("README.md", "secret readme"))])
    release = make_release(bundle, owner)
    make_note(bundle, owner, title="Owner note")
    return bundle, rule, release


# ── Reading a private bundle ──────────────────────────────────────────────────
# Every read route, on someone's private bundle. "{b}" = bundle id, "{u}" = uuid,
# "{r}" = rule id, "{rel}" = release id, "{v}" = release version.

PRIVATE_READ_ROUTES = [
    "/bundle/detail/{b}",
    "/bundle/detail/{u}",
    "/bundle/get_bundle_page?bundle_id={b}",
    "/bundle/get_bundle?bundle_id={b}",
    "/bundle/get_bundle_json/{b}",
    "/bundle/get_rules_page_from_bundle?bundle_id={b}",
    "/bundle/{b}/rule_content/{r}",
    "/bundle/history/{b}",
    "/bundle/{b}/health",
    "/bundle/{b}/notes",
    "/bundle/{b}/releases",
    "/bundle/{b}/releases/{v}/view",
    "/bundle/{b}/releases/{rel}/changes",
    "/bundle/{b}/releases/{rel}/rule/{r}/diff",
    "/bundle/{b}/releases/{rel}/download",
    "/bundle/attack_coverage/{b}",
    "/bundle/get_bundle_tags_display/{b}",
    "/bundle/get_bundle_vulnerabilities_display/{b}",
    "/bundle/get_tags/{b}",
    "/bundle/voters?bundleId={b}&voteType=up",
    "/bundle/download?bundle_id={b}",
    "/bundle/download_structure?bundle_id={b}",
    "/bundle/download_files?bundle_id={b}",
    "/bundle/download_full?bundle_id={b}",
    "/bundle/download_misp?bundle_id={b}",
    "/bundle/download?bundle_id={b}&release={v}",
]

# Read routes that need an account even for a public bundle.
PRIVATE_READ_ROUTES_LOGGED_IN = [
    "/bundle/get_bundle_tag_ids/{b}",
    "/bundle/vulnerabilities/bundle/{b}",
]


def _url(template, bundle, rule, release):
    return template.format(b=bundle.id, u=bundle.uuid, r=rule.id, rel=release.id, v=release.version)


@pytest.mark.parametrize("route", PRIVATE_READ_ROUTES)
@pytest.mark.parametrize("role, expected", matrix(PRIVATE_READ))
def test_read_private_bundle(role, expected, route, clients, users):
    bundle, rule, release = _full_bundle(users.owner, public=False)

    response = clients[role].get(_url(route, bundle, rule, release))

    assert_outcome(response, expected)
    if expected is not OK:
        assert bundle.name.encode() not in response.data
        assert rule.to_string.encode() not in response.data


@pytest.mark.parametrize("route", PRIVATE_READ_ROUTES_LOGGED_IN)
@pytest.mark.parametrize("role, expected", matrix(PRIVATE_LOGGED_IN))
def test_read_private_bundle_logged_in_routes(role, expected, route, clients, users):
    bundle, rule, release = _full_bundle(users.owner, public=False)

    response = clients[role].get(_url(route, bundle, rule, release))

    assert_outcome(response, expected)
    if expected is not OK:
        assert b"CVE-2024-0001" not in response.data


@pytest.mark.parametrize("route", PRIVATE_READ_ROUTES)
@pytest.mark.parametrize("role, expected", matrix(EVERYONE))
def test_read_public_bundle(role, expected, route, clients, users):
    bundle, rule, release = _full_bundle(users.owner, public=True)

    response = clients[role].get(_url(route, bundle, rule, release))

    assert_outcome(response, expected)


# ── Private bundles never leak in lists, searches or facets ───────────────────

def _names(items):
    return {b["name"] for b in items}


LISTINGS = {
    "data_table": lambda c, b, r, o: _names(c.get("/bundle/data_table?per_page=100").get_json()["items"]),
    "all_bundles": lambda c, b, r, o: _names(c.get("/bundle/get_all_bundles").get_json()["bundle_list_"]),
    "bundles_of_a_rule": lambda c, b, r, o: _names(
        c.get(f"/bundle/get_bundle_list_rule_part_of?rule_id={r.id}").get_json()["bundles"]),
    "global_search": lambda c, b, r, o: _names(c.get(f"/global_search?q={b.name}").get_json()["bundles"]),
    "vulnerability_facet": lambda c, b, r, o: (
        {b.name} if "CVE-2024-0001" in _names(c.get("/bundle/get_all_vulnerabilities_usage").get_json()["vulnerabilities"])
        else set()),
    "creator_facet": lambda c, b, r, o: (
        {b.name} if o.first_name in _names(c.get("/bundle/get_bundle_creators_usage").get_json()) else set()),
}
SEES_PRIVATE = {"anonymous": False, "user": False, "owner": True, "admin": True}


@pytest.mark.parametrize("listing", LISTINGS)
@pytest.mark.parametrize("role", SEES_PRIVATE)
def test_private_bundle_is_listed_only_for_its_owner_and_admins(role, listing, clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner, public=False, vulnerability_identifiers='["CVE-2024-0001"]'), rule)

    seen = LISTINGS[listing](clients[role], bundle, rule, users.owner)

    assert (bundle.name in seen) is SEES_PRIVATE[role]


@pytest.mark.parametrize("role", SEES_PRIVATE)
def test_private_bundle_tag_is_counted_only_for_its_owner_and_admins(role, clients, users):
    bundle = make_bundle(users.owner, public=False)
    tag = make_tag("workflow:todo", users.admin)
    BundleModel.update_bundle_tags(bundle.id, [tag.id], users.owner)

    tags = clients[role].get("/bundle/get_all_tags_usage").get_json()["tags"]

    assert (tag.name in _names(tags)) is SEES_PRIVATE[role]


@pytest.mark.parametrize("role", ["anonymous", "user", "owner", "admin"])
def test_profile_list_shows_public_bundles_only(role, clients, users):
    public, private = make_bundle(users.owner), make_bundle(users.owner, public=False)

    data = clients[role].get(f"/bundle/get_bundles_page_filter_with_id?user_id={users.owner.id}").get_json()

    assert _names(data["bundles_list"]) == {public.name}


# ── Creating ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_create_bundle(role, expected, clients):
    form = new_bundle_form()

    response = clients[role].post("/bundle/create", data=form)

    assert_outcome(response, expected)
    assert count(Bundle, name=form["name"]) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_create_bundle_for_a_rule(role, expected, clients, users):
    rule = make_rule(users.owner)

    response = clients[role].post("/bundle/add-single-rule", json={"rule_id": rule.id, "new_bundle_name": "From rule"})

    assert_outcome(response, expected)
    assert count(Bundle, name="From rule") == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_pick_an_existing_bundle_for_a_rule(role, expected, clients, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.owner)

    response = clients[role].post("/bundle/add-single-rule", json={"rule_id": rule.id, "existing_bundle_id": bundle.id})

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_list_my_bundles(role, expected, clients, users):
    mine = make_bundle(users.owner, public=False)

    response = clients[role].get("/bundle/my-bundles")

    assert_outcome(response, expected)
    if expected is OK:
        assert (mine.name in _names(response.get_json()["bundles"])) is (role == "owner")


# ── Editing ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_open_edit_page(role, expected, clients, users):
    bundle = make_bundle(users.owner)

    response = clients[role].get(f"/bundle/edit/{bundle.id}")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_edit_bundle(role, expected, clients, users):
    bundle = make_bundle(users.owner)

    response = clients[role].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, name="Renamed bundle"))

    assert_outcome(response, expected)
    assert (reload(bundle).name == "Renamed bundle") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_change_bundle_visibility(role, expected, clients, users):
    bundle = make_bundle(users.owner)

    response = clients[role].post(f"/bundle/edit_access?id={bundle.id}")

    assert_outcome(response, expected)
    assert reload(bundle).access is not (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_set_bundle_tags(role, expected, clients, users):
    bundle = make_bundle(users.owner)
    tag = Tag.query.filter_by(name="tlp:clear").one()

    response = clients[role].post(f"/bundle/update_bundle_tags/{bundle.id}", json={"tag_ids": [tag.id]})

    assert_outcome(response, expected)
    assert (count(BundleTagAssociation, bundle_id=bundle.id) == 1) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_add_rule_to_bundle(role, expected, clients, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.user)

    response = clients[role].post(f"/bundle/add_rule_bundle?bundle_id={bundle.id}&rule_id={rule.id}")

    assert_outcome(response, expected)
    assert (count(BundleRuleAssociation, bundle_id=bundle.id) == 1) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_remove_rule_from_bundle(role, expected, clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)

    response = clients[role].post(f"/bundle/remove?bundle_id={bundle.id}&rule_id={rule.id}")

    assert_outcome(response, expected)
    assert (count(BundleRuleAssociation, bundle_id=bundle.id) == 0) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_change_why_a_rule_is_in_the_bundle(role, expected, clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)
    association = BundleRuleAssociation.query.filter_by(bundle_id=bundle.id).one()

    response = clients[role].post(f"/bundle/change_description?association_id={association.id}&new_description=why")

    assert_outcome(response, expected)
    db.session.rollback()   # what a request didn't commit is lost
    assert (reload(association).description == "why") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_save_bundle_structure(role, expected, clients, users):
    bundle = make_bundle(users.owner)

    response = clients[role].post(f"/bundle/save_workspace/{bundle.id}",
                                  json={"structure": [folder("Main", file("README.md", "hello"))]})

    assert_outcome(response, expected)
    assert (count(BundleNode, bundle_id=bundle.id, name="README.md") == 1) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_rebuild_structure_from_attached_rules(role, expected, clients, users):
    bundle, rule = make_bundle(users.owner), make_rule(users.owner)
    db.session.add(BundleRuleAssociation(bundle_id=bundle.id, rule_id=rule.id))
    db.session.commit()

    response = clients[role].post(f"/bundle/update_bundle_from_structure?id={bundle.id}")

    assert_outcome(response, expected)
    assert (count(BundleNode, bundle_id=bundle.id, rule_id=rule.id) == 1) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_apply_a_health_fix(role, expected, clients, users):
    rule = make_rule(users.owner)
    bundle = add_rules(make_bundle(users.owner), rule)

    response = clients[role].post(f"/bundle/{bundle.id}/health/fix",
                                  json={"fix": {"action": "remove_rule", "rule_id": rule.id}})

    assert_outcome(response, expected)
    assert (count(BundleRuleAssociation, bundle_id=bundle.id) == 0) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix({**OWNER_OR_ADMIN, "anonymous": FORBIDDEN}))
def test_rerun_the_health_checks(role, expected, clients, users):
    bundle = make_bundle(users.owner)

    response = clients[role].get(f"/bundle/{bundle.id}/health?refresh=1")

    assert_outcome(response, expected)


# ── Deleting ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_delete_bundle(role, expected, clients, users):
    bundle = make_bundle(users.owner)

    response = clients[role].post(f"/bundle/delete?id={bundle.id}")

    assert_outcome(response, expected)
    assert (reload(bundle) is None) is (expected is OK)


# ── Share link ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_read_share_link(role, expected, clients, users):
    bundle = make_bundle(users.owner, public=False)
    key = share(bundle)

    response = clients[role].get(f"/bundle/{bundle.id}/share")

    assert_outcome(response, expected)
    assert (key in response.get_data(as_text=True)) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_create_share_link(role, expected, clients, users):
    bundle = make_bundle(users.owner, public=False)

    response = clients[role].post(f"/bundle/{bundle.id}/share")

    assert_outcome(response, expected)
    assert (reload(bundle).share_token is not None) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_revoke_share_link(role, expected, clients, users):
    bundle = make_bundle(users.owner, public=False)
    share(bundle)

    response = clients[role].delete(f"/bundle/{bundle.id}/share")

    assert_outcome(response, expected)
    assert (reload(bundle).share_token is None) is (expected is OK)


def test_share_link_lets_a_logged_in_user_read_the_private_bundle(clients, users):
    bundle = make_bundle(users.owner, public=False)
    key = share(bundle)

    opened = clients["user"].get(f"/bundle/share/{key}")
    response = clients["user"].get(f"/bundle/get_bundle_page?bundle_id={bundle.id}")

    assert_outcome(opened, OK)
    assert_outcome(response, OK)


def test_share_link_on_the_detail_url_works_too(clients, users):
    bundle = make_bundle(users.owner, public=False)
    key = share(bundle)

    response = clients["user"].get(f"/bundle/detail/{bundle.id}?share={key}")

    assert_outcome(response, OK)
    assert bundle.name.encode() in response.data


def test_share_link_needs_an_account(clients, users):
    bundle = make_bundle(users.owner, public=False)
    key = share(bundle)

    assert_outcome(clients["anonymous"].get(f"/bundle/share/{key}"), LOGIN)
    assert_outcome(clients["anonymous"].get(f"/bundle/detail/{bundle.id}?share={key}"), LOGIN)


def test_unknown_share_key_grants_nothing(clients, users):
    bundle = make_bundle(users.owner, public=False)
    share(bundle)

    opened = clients["user"].get("/bundle/share/not-the-key")
    response = clients["user"].get(f"/bundle/detail/{bundle.id}?share=not-the-key")

    assert_outcome(opened, FORBIDDEN)
    assert_outcome(response, FORBIDDEN)


def test_revoked_share_link_stops_working(clients, users):
    bundle = make_bundle(users.owner, public=False)
    key = share(bundle)
    clients["user"].get(f"/bundle/share/{key}")

    BundleModel.revoke_share_token(bundle.id)
    response = clients["user"].get(f"/bundle/get_bundle_page?bundle_id={bundle.id}")

    assert_outcome(response, FORBIDDEN)


def test_regenerated_share_link_invalidates_the_old_one(clients, users):
    bundle = make_bundle(users.owner, public=False)
    key = share(bundle)
    clients["user"].get(f"/bundle/share/{key}")

    share(bundle)
    response = clients["user"].get(f"/bundle/get_bundle_page?bundle_id={bundle.id}")

    assert_outcome(response, FORBIDDEN)


def test_share_link_holder_can_not_edit_the_bundle(clients, users):
    bundle = make_bundle(users.owner, public=False)
    clients["user"].get(f"/bundle/share/{share(bundle)}")

    edit = clients["user"].post(f"/bundle/edit/{bundle.id}", data=edit_bundle_form(bundle, name="Hijacked"))
    delete = clients["user"].post(f"/bundle/delete?id={bundle.id}")

    assert_outcome(edit, FORBIDDEN)
    assert_outcome(delete, FORBIDDEN)
    assert reload(bundle).name != "Hijacked"


# ── Community actions ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("public, table", [(True, LOGGED_IN), (False, PRIVATE_LOGGED_IN)], ids=["public", "private"])
@pytest.mark.parametrize("role", ["anonymous", "user", "owner", "admin"])
def test_vote_on_bundle(role, public, table, clients, users):
    bundle = make_bundle(users.owner, public=public)

    response = clients[role].post(f"/bundle/evaluate?bundleId={bundle.id}&voteType=up")

    assert_outcome(response, table[role])
    assert (count(BundleVote, bundle_id=bundle.id) == 1) is (table[role] is OK)


@pytest.mark.parametrize("public, table", [(True, LOGGED_IN), (False, PRIVATE_LOGGED_IN)], ids=["public", "private"])
@pytest.mark.parametrize("role", ["anonymous", "user", "owner", "admin"])
def test_favorite_bundle(role, public, table, clients, users):
    bundle = make_bundle(users.owner, public=public)

    response = clients[role].post(f"/bundle/favorite/{bundle.id}")

    assert_outcome(response, table[role])
    assert (count(BundleFavoriteUser, bundle_id=bundle.id) == 1) is (table[role] is OK)


# ── Notes ─────────────────────────────────────────────────────────────────────

NOTE = {"title": "False positives", "content": "Fires on backup jobs", "severity": "warning"}


@pytest.mark.parametrize("public, table", [(True, LOGGED_IN), (False, PRIVATE_LOGGED_IN)], ids=["public", "private"])
@pytest.mark.parametrize("role", ["anonymous", "user", "owner", "admin"])
def test_add_note(role, public, table, clients, users):
    bundle = make_bundle(users.owner, public=public)

    response = clients[role].post(f"/bundle/{bundle.id}/notes", json=NOTE)

    assert_outcome(response, table[role])
    assert (count(BundleNote, bundle_id=bundle.id) == 1) is (table[role] is OK)


def test_share_link_holder_can_not_add_a_note_to_a_private_bundle(clients, users):
    bundle = make_bundle(users.owner, public=False)
    clients["user"].get(f"/bundle/share/{share(bundle)}")

    response = clients["user"].post(f"/bundle/{bundle.id}/notes", json=NOTE)

    assert_outcome(response, FORBIDDEN)
    assert count(BundleNote) == 0


# A note written by the admin on the owner's bundle: "user" is neither its
# author nor a manager of the bundle.
@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_edit_someone_elses_note(role, expected, clients, users):
    note = make_note(make_bundle(users.owner), users.admin)

    response = clients[role].put(f"/bundle/{note.bundle_id}/notes/{note.id}", json={**NOTE, "title": "Edited note"})

    assert_outcome(response, expected)
    assert (reload(note).title == "Edited note") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_delete_someone_elses_note(role, expected, clients, users):
    note = make_note(make_bundle(users.owner), users.admin)

    response = clients[role].delete(f"/bundle/{note.bundle_id}/notes/{note.id}")

    assert_outcome(response, expected)
    assert (reload(note) is None) is (expected is OK)


def test_author_can_edit_and_delete_their_own_note(clients, users):
    bundle = make_bundle(users.owner)
    note = make_note(bundle, users.user)

    edit = clients["user"].put(f"/bundle/{bundle.id}/notes/{note.id}", json={**NOTE, "title": "Edited by author"})
    assert_outcome(edit, OK)
    assert reload(note).title == "Edited by author"

    delete = clients["user"].delete(f"/bundle/{bundle.id}/notes/{note.id}")
    assert_outcome(delete, OK)
    assert reload(note) is None


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_resolve_someone_elses_note(role, expected, clients, users):
    note = make_note(make_bundle(users.owner), users.admin)

    response = clients[role].post(f"/bundle/{note.bundle_id}/notes/{note.id}/status", json={"status": "resolved"})

    assert_outcome(response, expected)
    assert (reload(note).status == "resolved") is (expected is OK)


def test_author_loses_their_note_when_the_bundle_goes_private(clients, users):
    bundle = make_bundle(users.owner)
    note = make_note(bundle, users.user)
    bundle.access = False
    db.session.commit()

    response = clients["user"].put(f"/bundle/{bundle.id}/notes/{note.id}", json={**NOTE, "title": "Edited"})

    assert_outcome(response, FORBIDDEN)
    assert reload(note).title != "Edited"


def test_author_resolves_their_own_note(clients, users):
    note = make_note(make_bundle(users.owner), users.user)

    response = clients["user"].post(f"/bundle/{note.bundle_id}/notes/{note.id}/status", json={"status": "resolved"})

    assert_outcome(response, OK)
    assert reload(note).status == "resolved"


def test_author_gets_their_note_back_when_the_bundle_is_public_again(clients, users):
    bundle = make_bundle(users.owner)
    note = make_note(bundle, users.user)
    clients["owner"].post(f"/bundle/edit_access?id={bundle.id}")   # private
    clients["owner"].post(f"/bundle/edit_access?id={bundle.id}")   # public again

    edit = clients["user"].put(f"/bundle/{bundle.id}/notes/{note.id}", json={**NOTE, "title": "Edited again"})
    resolve = clients["user"].post(f"/bundle/{bundle.id}/notes/{note.id}/status", json={"status": "resolved"})

    assert_outcome(edit, OK)
    assert_outcome(resolve, OK)
    assert (reload(note).user_id, reload(note).title, reload(note).status) == (users.user.id, "Edited again", "resolved")


# ── Releases ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_draft_release(role, expected, clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))

    response = clients[role].get(f"/bundle/{bundle.id}/releases/draft")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_publish_release(role, expected, clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))

    response = clients[role].post(f"/bundle/{bundle.id}/releases", json={"version": "v1.0.0"})

    assert_outcome(response, expected)
    assert (count(BundleRelease, bundle_id=bundle.id) == 1) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(OWNER_OR_ADMIN))
def test_delete_release(role, expected, clients, users):
    bundle = add_rules(make_bundle(users.owner), make_rule(users.owner))
    release = make_release(bundle, users.owner)

    response = clients[role].delete(f"/bundle/{bundle.id}/releases/{release.id}")

    assert_outcome(response, expected)
    assert (reload(release) is None) is (expected is OK)
