"""Imported tags — attaching the author's own tags to a new rule.

A new rule gets its native tags as public "Imported" tags owned by its
creator (approved only when the creator is an admin). An existing public tag
of the same name is reused; a private or inactive one is never attached; no
tag is ever minted in a MISP taxonomy / galaxy namespace; at most 25 per rule.
"""
import pytest

from app.core.db_class.db import Rule, RuleTagAssociation, Tag
from app.features.tags import imported_tags_core
from app.features.tags.imported_tags_core import IMPORTED_SOURCE, MAX_TAGS_PER_RULE
from tests_new.helpers.rules import new_rule_form
from tests_new.helpers.tags import make_tag


@pytest.fixture(autouse=True)
def _fresh_reserved_namespaces(monkeypatch):
    """The reserved-namespace list is cached per process — start each test cold."""
    monkeypatch.setitem(imported_tags_core._reserved_cache, "names", None)


def _create(client, header_tags="", meta_tags=None, name="Imported_tags_rule"):
    meta = f'meta:\n        tags = "{meta_tags}"\n    ' if meta_tags else ""
    content = f'rule {name}{" : " + header_tags if header_tags else ""}\n{{\n    {meta}condition:\n        true\n}}'
    form = new_rule_form(to_string=content)
    client.post("/rule/create_rule", data=form)
    return Rule.query.filter_by(title=form["title"]).one()


def _tags_of(rule):
    return {t.name: t for t in Tag.query.join(RuleTagAssociation, RuleTagAssociation.tag_id == Tag.id)
            .filter(RuleTagAssociation.rule_id == rule.id)}


def test_new_rule_gets_its_authors_tags_as_public_imported_tags(clients, users):
    rule = _create(clients["owner"], header_tags="malware ransomware", meta_tags="apt")

    tags = _tags_of(rule)
    assert {"malware", "ransomware", "apt", "tlp:clear", "PAP:CLEAR"} <= set(tags)
    for name in ("malware", "ransomware", "apt"):
        tag = tags[name]
        assert (tag.source, tag.visibility, tag.is_active) == (IMPORTED_SOURCE, "public", True)
        assert tag.created_by == users.owner.id


@pytest.mark.parametrize("role, approved", [("owner", False), ("admin", True)])
def test_imported_tags_are_approved_only_when_an_admin_made_the_rule(role, approved, clients):
    rule = _create(clients[role], header_tags="authortag")

    assert _tags_of(rule)["authortag"].is_approved_by_admin is approved


def test_an_existing_public_tag_is_reused(clients, users):
    existing = make_tag(users.user, name="malware")

    rule = _create(clients["owner"], header_tags="malware")

    assert _tags_of(rule)["malware"].id == existing.id
    assert Tag.query.filter_by(name="malware").count() == 1


@pytest.mark.parametrize("hidden", [dict(visibility="private"), dict(active=False)])
def test_a_private_or_inactive_tag_is_never_attached(hidden, clients, users):
    make_tag(users.user, name="secretname", **hidden)

    rule = _create(clients["owner"], header_tags="secretname")

    assert "secretname" not in _tags_of(rule)
    assert Tag.query.filter_by(name="secretname").count() == 1


def test_no_tag_is_minted_in_a_taxonomy_or_galaxy_namespace(clients):
    rule = _create(clients["owner"], meta_tags='tlp:red, misp-galaxy:tool, mine:ok')

    assert Tag.query.filter_by(name="tlp:red").first() is None
    assert Tag.query.filter(Tag.name.like("misp-galaxy:%")).count() == 0
    assert "mine:ok" in _tags_of(rule)


def test_at_most_25_imported_tags_per_rule(clients):
    rule = _create(clients["owner"], header_tags=" ".join(f"t{i}" for i in range(60)))

    imported = [t for t in _tags_of(rule).values() if t.source == IMPORTED_SOURCE]
    assert len(imported) == MAX_TAGS_PER_RULE
