"""Bundle factories, structure builders and the payloads the bundle forms expect."""
import itertools
import uuid

from app import db
from app.core.db_class.db import BundleNote, Tag
from app.features.bundle import bundle_core as BundleModel

_counter = itertools.count(1)


def make_bundle(owner, *, public=True, **overrides):
    """A bundle owned by `owner` (public unless `public=False`), unique name per call."""
    n = next(_counter)
    bundle = BundleModel.create_bundle(
        {"name": overrides.pop("name", f"Test bundle {n}"),
         "description": overrides.pop("description", f"Description of test bundle {n}"),
         "public": public},
        owner,
    )
    for field, value in overrides.items():
        setattr(bundle, field, value)
    db.session.commit()
    return bundle


def add_rules(bundle, *rules):
    """Attach `rules` to `bundle` and place them in its folder tree."""
    for rule in rules:
        BundleModel.add_rule_to_bundle(bundle.id, rule.id, "added by the tests")
    return bundle


def share(bundle):
    """Create the bundle's private share link; returns its key."""
    return BundleModel.regenerate_share_token(bundle.id)


def make_release(bundle, user, version="v1.0.0"):
    """A published release of `bundle` (the bundle must hold a rule or a file)."""
    from app.features.bundle.bundle_release_core import create_release
    release, error = create_release(bundle.id, user, version, f"Release {version}", "notes")
    assert error is None, error
    return release


def make_tag(name, creator):
    """An active public tag (the seeded default tags carry no visibility)."""
    tag = Tag(uuid=str(uuid.uuid4()), name=name, is_active=True, visibility="public", created_by=creator.id)
    db.session.add(tag)
    db.session.commit()
    return tag


def make_note(bundle, author, **overrides):
    fields = dict(uuid=str(uuid.uuid4()), bundle_id=bundle.id, user_id=author.id,
                  title="A known issue", content="False positives on backups", severity="warning")
    fields.update(overrides)
    note = BundleNote(**fields)
    db.session.add(note)
    db.session.commit()
    return note


# ── Structure nodes, as the bundle editor sends them ──────────────────────────

def folder(name, *children):
    return {"name": name, "type": "folder", "children": list(children)}


def file(name, content=""):
    return {"name": name, "type": "file", "content": content, "children": []}


def rule_node(rule):
    return {"name": rule.title, "type": "file", "rule_id": rule.id, "children": []}


# ── Forms ─────────────────────────────────────────────────────────────────────

def new_bundle_form(**overrides):
    """What the "create bundle" form posts, for a new public bundle."""
    n = next(_counter)
    form = dict(name=f"Created bundle {n}", description="Created through the form", public="y")
    form.update(overrides)
    return form


def edit_bundle_form(bundle, **changes):
    """What the "edit bundle" form posts for `bundle`, with `changes` applied.
    A private bundle sends no `public` field (an unchecked checkbox)."""
    form = dict(name=bundle.name, description=bundle.description or "", vulnerabilities="[]")
    if bundle.access:
        form["public"] = "y"
    form.update(changes)
    return {k: v for k, v in form.items() if v is not None}
