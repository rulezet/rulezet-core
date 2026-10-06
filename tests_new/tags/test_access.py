"""Tags — layer 1: who can do what.

Roles: "owner" is the user who created the tag, "tagger" a non-admin holding
`rule.tag_any` (the "Tag manager" role).

Permission model: every tag route needs an account. Any user may create tags
(theirs start inactive and unapproved) and list the tags they may pick —
active public ones, plus their own. Editing and deleting one tag through
/edit_tag and /delete_tag is for its creator or an admin. Everything on the
tag management pages — the full listing, families, remove / bulk remove,
visibility and status toggles, MISP taxonomy / galaxy imports and the rule
validation tool — is for admins and taggers. Tagging a bundle is for its
owner or an admin.
"""
import pytest

from app.core.db_class.db import BackgroundJob, BundleTagAssociation, Tag
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import make_rule
from tests_new.helpers.tags import (
    GALAXY_UUID, TAXONOMY_UUID, fake_misp_data, make_bundle, make_tag, new_tag_payload, tag_bundle, tag_rule,
    with_tagger,
)

LOGGED_IN = {"anonymous": LOGIN, "user": OK, "owner": OK, "admin": OK, "tagger": OK}
CREATOR_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK, "tagger": FORBIDDEN}
TAG_MANAGERS = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK, "tagger": OK}
BUNDLE_OWNER_OR_ADMIN = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": OK, "admin": OK, "tagger": FORBIDDEN}


@pytest.fixture
def every(clients, client_as):
    return with_tagger(clients, client_as)


@pytest.fixture
def misp(tmp_path, monkeypatch):
    fake_misp_data(tmp_path, monkeypatch)


# ── Pages ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_open_tag_management_page(role, expected, every):
    response = every[role].get("/tags/admin/list")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_open_rule_validation_page(role, expected, every):
    response = every[role].get("/tags/admin/validation")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_open_my_tags_page(role, expected, every):
    response = every[role].get("/tags/my_tags")

    assert_outcome(response, expected)


# ── Listing ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_list_every_tag(role, expected, every, users):
    private = make_tag(users.owner, visibility="private")

    response = every[role].get("/tags/get_tags?per_page=100")

    assert_outcome(response, expected)
    if expected is OK:
        assert private.name in {t["name"] for t in response.get_json()["tags"]}


@pytest.mark.parametrize("url", ["/tags/get_all_tags", "/tags/get_all_tags_by_type", "/tags/get_tags_bundle",
                                 "/tags/picker/namespaces", "/tags/picker/tags", "/tags/get_my_tags",
                                 "/tags/get_my_tags_paged"])
@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_list_pickable_tags(role, expected, url, every):
    response = every[role].get(url)

    assert_outcome(response, expected)


@pytest.mark.parametrize("url", ["/tags/get_all_tags", "/tags/get_tags_bundle"])
@pytest.mark.parametrize("role", ["user", "tagger"])
def test_list_pickable_tags_never_shows_someone_elses_private_tag(role, url, every, users):
    """Passing the creator's user_id must not unlock their private tags."""
    private = make_tag(users.owner, visibility="private")

    response = every[role].get(f"{url}?user_id={users.owner.id}")

    assert private.name not in {t["name"] for t in response.get_json()["tags"]}


SEES_PRIVATE_TAG = {"anonymous": False, "user": False, "owner": True, "admin": True, "tagger": False}


@pytest.mark.parametrize("view", ["", "?view=tags&tag_ns=pv", "?view=selected&names=pv:secret"])
@pytest.mark.parametrize("role, sees", SEES_PRIVATE_TAG.items(), ids=SEES_PRIVATE_TAG)
def test_rule_tag_filter_shows_a_private_tag_to_its_creator_and_admins_only(role, sees, view, every, users):
    """The tag facet of the rule list (MultiTagFilter) — never a leak, even
    after an admin's response was computed for the same query string."""
    private = make_tag(users.owner, name="pv:secret", visibility="private")
    tag_rule(make_rule(users.owner), private)
    every["admin"].get(f"/rule/get_all_tags_usage{view}")

    response = every[role].get(f"/rule/get_all_tags_usage{view}")

    assert (private.name in {t["name"] for t in response.get_json()["tags"]}) is sees


@pytest.mark.parametrize("role, visible_bundles", [("anonymous", 1), ("user", 1), ("owner", 2), ("admin", 2)])
def test_bundle_tag_filter_counts_only_visible_bundles(role, visible_bundles, every, users):
    tag = make_tag(users.admin, name="bf:one")
    tag_bundle(make_bundle(users.owner, public=True), tag)
    tag_bundle(make_bundle(users.owner, public=False), tag)

    response = every[role].get("/bundle/get_all_tags_usage?view=tags&tag_ns=bf")

    assert response.get_json()["tags"][0]["usage_count"] == visible_bundles


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_list_a_tag_family(role, expected, every, users):
    make_tag(users.owner, name="fam:one")

    response = every[role].get("/tags/get_family?family=fam")

    assert_outcome(response, expected)


# ── Creating / editing / deleting one tag ─────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(LOGGED_IN))
def test_create_tag(role, expected, every):
    payload = new_tag_payload()

    response = every[role].post("/tags/create_tag", json=payload)

    assert_outcome(response, expected)
    assert count(Tag, name=payload["name"]) == (1 if expected is OK else 0)


@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_edit_tag(role, expected, every, users):
    tag = make_tag(users.owner)

    response = every[role].post(f"/tags/edit_tag/{tag.id}", json={"name": "tests:renamed"})

    assert_outcome(response, expected)
    assert (reload(tag).name == "tests:renamed") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(CREATOR_OR_ADMIN))
def test_delete_tag(role, expected, every, users):
    tag = make_tag(users.owner)

    response = every[role].post(f"/tags/delete_tag/{tag.id}")

    assert_outcome(response, expected)
    assert (reload(tag) is None) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_remove_any_tag_from_the_management_page(role, expected, every, users):
    tag = make_tag(users.user)

    response = every[role].get(f"/tags/remove_tag?tag_id={tag.id}")

    assert_outcome(response, expected)
    assert (reload(tag) is None) is (expected is OK)


@pytest.mark.parametrize("role, expected", [
    ("anonymous", LOGIN), ("user", FORBIDDEN), ("owner", OK), ("admin", OK), ("tagger", FORBIDDEN)])
def test_bulk_remove_tags(role, expected, every, users):
    """Admins remove any tag; everyone else only their own manual tags."""
    tags = [make_tag(users.owner), make_tag(users.owner)]

    response = every[role].post("/tags/remove_tags_bulk", json={"ids": [t.id for t in tags]})

    if expected is FORBIDDEN:
        assert response.status_code == 400   # "no eligible tags": nothing of theirs in the list
    else:
        assert_outcome(response, expected)
    assert all((reload(t) is None) is (expected is OK) for t in tags)


def test_bulk_remove_tags_only_removes_your_own(every, users):
    mine, theirs = make_tag(users.user), make_tag(users.owner)

    response = every["user"].post("/tags/remove_tags_bulk", json={"ids": [mine.id, theirs.id]})

    assert_outcome(response, OK)
    assert reload(mine) is None and reload(theirs) is not None


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_toggle_tag_visibility(role, expected, every, users):
    tag = make_tag(users.owner, visibility="private")

    response = every[role].get(f"/tags/toggle_visibility?tag_uuid={tag.uuid}")

    assert_outcome(response, expected)
    assert (reload(tag).visibility == "public") is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_toggle_tag_status(role, expected, every, users):
    tag = make_tag(users.owner, active=False)

    response = every[role].get(f"/tags/toggle_status?tag_uuid={tag.uuid}")

    assert_outcome(response, expected)
    assert reload(tag).is_active is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_delete_a_tag_family(role, expected, every, users):
    tag = make_tag(users.owner, name="fam:one")

    response = every[role].post("/tags/delete_family", json={"family": "fam"})

    assert_outcome(response, expected)
    assert (reload(tag) is None) is (expected is OK)


# ── MISP taxonomies / galaxies ────────────────────────────────────────────────

@pytest.mark.parametrize("url", ["/tags/get_tags_misp", "/tags/get_tags_galaxy",
                                 f"/tags/get_galaxy_clusters/{GALAXY_UUID}"])
@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_browse_misp_data(role, expected, url, every, misp):
    response = every[role].get(url)

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_import_a_taxonomy(role, expected, every, misp):
    response = every[role].get(f"/tags/add_tags_misp?uuid={TAXONOMY_UUID}")

    assert_outcome(response, expected)
    assert (count(Tag, source="Taxonomy") == 2) is (expected is OK)


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_import_a_galaxy(role, expected, every, misp):
    response = every[role].post("/tags/add_tags_galaxy", json={"uuid": GALAXY_UUID})

    assert_outcome(response, expected)
    assert (count(Tag, source="Galaxy") == 2) is (expected is OK)


@pytest.mark.parametrize("url, job_type", [
    ("/tags/admin/update_misp", "update_misp_data"),
    ("/tags/admin/import_all_taxonomies", "import_all_taxonomies"),
    ("/tags/admin/import_all_galaxies", "import_all_galaxies"),
    ("/tags/admin/validation/launch", "rule_validation_run"),
])
@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_launch_a_tag_job(role, expected, url, job_type, every):
    response = every[role].post(url, json={})

    assert_outcome(response, expected)
    assert count(BackgroundJob, job_type=job_type) == (1 if expected is OK else 0)


# ── Rule validation review ────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_list_quarantined_rules(role, expected, every):
    response = every[role].get("/tags/admin/validation/rules_data_table?job_uuid=unknown")

    assert_outcome(response, expected)


@pytest.mark.parametrize("role, expected", matrix(TAG_MANAGERS))
def test_dismiss_quarantined_rules(role, expected, every, users):
    job = BackgroundJob(uuid="validation-run", job_type="rule_validation_run", status="done",
                        created_by=users.admin.id, payload={"result": {"quarantined": []}})
    from app import db
    db.session.add(job)
    db.session.commit()

    response = every[role].post("/tags/admin/validation/dismiss",
                                json={"job_uuid": job.uuid, "rule_ids": [1]})

    assert_outcome(response, expected)
    dismissed = (reload(job).payload.get("result") or {}).get("dismissed_rule_ids")
    assert (dismissed == [1]) is (expected is OK)


# ── Tagging a bundle ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("role, expected", matrix(BUNDLE_OWNER_OR_ADMIN))
def test_tag_a_bundle(role, expected, every, users):
    bundle = make_bundle(users.owner)
    tag = make_tag(users.admin)

    response = every[role].post(f"/bundle/update_bundle_tags/{bundle.id}", json={"tag_ids": [tag.id]})

    assert_outcome(response, expected)
    assert (count(BundleTagAssociation, bundle_id=bundle.id, tag_id=tag.id) == 1) is (expected is OK)
