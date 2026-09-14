"""default_platform_tag_configs.json — structural sanity checks (every entry
has the fields validate_platform_tag_config() requires, every regex
compiles) that don't need the referenced MISP galaxy tags actually
imported, plus the insert_default_platform_tag_configs() admin-fallback
fix (it used to silently no-op — and permanently skip seeding any
not-yet-created template, including ones added later — on an instance
where the literal demo account admin@admin.admin doesn't exist)."""

import json
import re
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "app" / "core" / "utils" / "default_platform_tag_configs.json"


def _load():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_fixture_is_valid_json():
    templates = _load()
    assert isinstance(templates, dict)
    assert len(templates) > 0


def test_every_entry_has_required_fields_and_a_compilable_regex():
    templates = _load()
    for template_name, entries in templates.items():
        assert isinstance(entries, list) and entries, f'"{template_name}" has no entries'
        for entry in entries:
            for key in ("label", "tag_name", "regex"):
                assert entry.get(key), f'"{template_name}" entry missing "{key}": {entry}'
            assert entry["tag_name"].startswith(("misp-galaxy:", "ms-caro-malware-full:", "runtime-packer:")), (
                f'"{template_name}" / "{entry["label"]}": unexpected tag_name prefix: {entry["tag_name"]}'
            )
            try:
                re.compile(entry["regex"], re.IGNORECASE)
            except re.error as e:
                raise AssertionError(f'"{template_name}" / "{entry["label"]}": invalid regex — {e}')


def test_no_duplicate_tag_name_within_a_single_template():
    """Two patterns pointing at the same tag in one config would collide in
    validate_platform_tag_config's seen_tag_ids check — catch that here
    instead of only at seed/save time."""
    templates = _load()
    for template_name, entries in templates.items():
        tag_names = [e["tag_name"] for e in entries]
        assert len(tag_names) == len(set(tag_names)), f'"{template_name}" has duplicate tag_name entries'


def test_insert_default_platform_tag_configs_falls_back_to_any_admin(app):
    """Regression test for the get_admin_user() fallback — that function
    only ever looks up the literal admin@admin.admin account. On an
    instance where that account doesn't exist (renamed, merged, or a
    fresh non-demo admin), seeding must still fall back to any admin
    instead of silently doing nothing."""
    import uuid as uuid_mod
    from app import db
    from app.core.db_class.db import FieldParserConfig, Tag, User
    from app.core.utils.init_db import insert_default_platform_tag_configs

    with app.app_context():
        # Simulate the "renamed" scenario the fallback exists for: the demo
        # admin@admin.admin account (seeded by create_admin_test()) no
        # longer has that email, but is still an admin.
        other_admin = User.query.filter_by(email="admin@admin.admin").first()
        assert other_admin is not None
        other_admin.email = "renamed-admin@example.com"
        db.session.commit()
        assert User.query.filter_by(email="admin@admin.admin").first() is None

        # Seed exactly one referenced tag so at least one template can partially resolve.
        tag = Tag.query.filter_by(name='misp-galaxy:operating-system="Windows"').first()
        if not tag:
            tag = Tag(uuid=str(uuid_mod.uuid4()), name='misp-galaxy:operating-system="Windows"',
                      color="#000000", created_by=other_admin.id)
            db.session.add(tag)
            db.session.commit()

        assert FieldParserConfig.query.filter_by(name="Platforms", config_type="platform_tags").first() is None

        insert_default_platform_tag_configs()

        cfg = FieldParserConfig.query.filter_by(name="Platforms", config_type="platform_tags").first()
        assert cfg is not None
        assert cfg.user_id == other_admin.id
        assert any(p["tag_name"] == tag.name for p in cfg.config["patterns"])
