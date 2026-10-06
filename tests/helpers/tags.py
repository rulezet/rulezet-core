"""Tag factories, tag links on rules / bundles, and a tiny fake MISP data set
(one taxonomy, one galaxy) so the import routes never read the real
submodules."""
import datetime
import itertools
import json
import uuid

from app import db
from app.core.db_class.db import Bundle, BundleTagAssociation, RuleTagAssociation, Tag

_counter = itertools.count(1)


def with_tagger(clients, client_as):
    """The role clients plus "tagger": a non-admin holding rule.tag_any
    (the "Tag manager" role) — the tag feature's special role."""
    from tests.helpers.users import make_user_with_permission
    return {**clients, "tagger": client_as(make_user_with_permission("rule.tag_any", "tagger"))}


def default_tag(name="tlp:clear"):
    """One of the tags the conftest seeds (tlp:clear, PAP:CLEAR)."""
    return Tag.query.filter_by(name=name).one()


def make_tag(creator, *, name=None, visibility="public", active=True, source="Manual", **overrides):
    """A tag created by `creator` — public and active unless told otherwise
    (what an admin-made tag looks like; a user-made one starts inactive)."""
    n = next(_counter)
    fields = dict(
        uuid=str(uuid.uuid4()),
        name=name or f"tests:tag-{n}",
        description=f"Test tag {n}",
        color="#123456",
        icon="fa-tag",
        visibility=visibility,
        is_active=active,
        is_approved_by_admin=active,
        source=source,
        created_by=creator.id,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    fields.update(overrides)
    tag = Tag(**fields)
    db.session.add(tag)
    db.session.commit()
    return tag


def new_tag_payload(**overrides):
    """What the "create tag" form posts (JSON) for a new tag."""
    payload = dict(name=f"tests:created-{next(_counter)}", description="Created through the form",
                   color="#00FF00", icon="fa-tag", visibility="private")
    payload.update(overrides)
    return payload


def tag_rule(rule, tag, by=None):
    """Link `tag` to `rule` (added by `by`, default the rule's owner)."""
    db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=rule.id, tag_id=tag.id,
                                      user_id=(by.id if by else rule.user_id)))
    db.session.commit()


def make_bundle(owner, *, public=True):
    """A bundle owned by `owner` (public = visible to everyone)."""
    bundle = Bundle(uuid=str(uuid.uuid4()), name=f"Test bundle {next(_counter)}", description="",
                    user_id=owner.id, access=public, vote_up=0, vote_down=0, created_by="user")
    db.session.add(bundle)
    db.session.commit()
    return bundle


def tag_bundle(bundle, tag, by=None):
    db.session.add(BundleTagAssociation(uuid=str(uuid.uuid4()), bundle_id=bundle.id, tag_id=tag.id,
                                        user_id=(by.id if by else bundle.user_id)))
    db.session.commit()


# ── Fake MISP taxonomies / galaxies ───────────────────────────────────────────

TAXONOMY_UUID = "11111111-1111-4111-8111-111111111111"
GALAXY_UUID = "22222222-2222-4222-8222-222222222222"
CLUSTER_UUIDS = ("33333333-3333-4333-8333-333333333333", "44444444-4444-4444-8444-444444444444")


def fake_misp_data(base, monkeypatch):
    """Point the tag import code at a temporary MISP data set under `base`:
    taxonomy "testtax" (2 values) and galaxy "testgal" (2 clusters)."""
    from app.features.tags import tags_core

    taxonomies = base / "misp-taxonomies"
    (taxonomies / "testtax").mkdir(parents=True)
    (taxonomies / "testtax" / "machinetag.json").write_text(json.dumps({
        "namespace": "testtax", "uuid": TAXONOMY_UUID, "version": 1,
        "description": "A test taxonomy", "expanded": "Test taxonomy",
        "predicates": [{"value": "first", "expanded": "First"}, {"value": "second", "expanded": "Second"}],
    }))

    galaxies = base / "misp-galaxy"
    (galaxies / "galaxies").mkdir(parents=True)
    (galaxies / "clusters").mkdir(parents=True)
    (galaxies / "galaxies" / "testgal.json").write_text(json.dumps({
        "name": "Test galaxy", "type": "testgal", "uuid": GALAXY_UUID, "version": 1,
        "description": "A test galaxy", "icon": "shield-alt",
    }))
    (galaxies / "clusters" / "testgal.json").write_text(json.dumps({
        "type": "testgal", "uuid": GALAXY_UUID,
        "values": [{"value": "Alpha", "uuid": CLUSTER_UUIDS[0], "description": "first cluster"},
                   {"value": "Beta", "uuid": CLUSTER_UUIDS[1], "description": "second cluster"}],
    }))

    monkeypatch.setattr(tags_core, "MISP_TAXONOMIES_PATH", str(taxonomies))
    monkeypatch.setattr(tags_core, "MISP_GALAXIES_PATH", str(galaxies))
