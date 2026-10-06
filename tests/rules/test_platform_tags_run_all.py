"""combine_all_platform_tag_patterns() and the "Run All Saved Configs"
option it backs (ALL_PLATFORM_CONFIGS sentinel, bulk_parse_fields_trigger_
platform_tags route, handle_bulk_tag_platforms job handler) — replaces the
old "Everything" config that had to be manually regenerated (and did go
stale in practice) whenever a new config was added."""

import uuid as uuid_mod

from app.core.db_class.db import User


def _login(client, email):
    user = User.query.filter_by(email=email).first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    return user


def _make_tag(db, name, admin_id):
    from app.core.db_class.db import Tag
    tag = Tag.query.filter_by(name=name).first()
    if tag:
        return tag
    tag = Tag(uuid=str(uuid_mod.uuid4()), name=name, color="#000000", created_by=admin_id)
    db.session.add(tag)
    db.session.commit()
    return tag


def test_combine_all_platform_tag_patterns_dedupes_by_tag_id(app):
    from app import db
    from app.core.db_class.db import FieldParserConfig, User
    from app.features.rule.field_parser_core import combine_all_platform_tag_patterns

    with app.app_context():
        admin = User.query.filter_by(admin=True).first()
        tag_a = _make_tag(db, "misp-galaxy:test-run-all=\"A\"", admin.id)
        tag_b = _make_tag(db, "misp-galaxy:test-run-all=\"B\"", admin.id)

        db.session.add(FieldParserConfig(
            name="RunAll Config 1", config_type="platform_tags", user_id=admin.id,
            config={"patterns": [
                {"label": "A", "tag_id": tag_a.id, "tag_name": tag_a.name, "regex": r"\ba\b", "enabled": True},
            ]},
        ))
        db.session.add(FieldParserConfig(
            name="RunAll Config 2", config_type="platform_tags", user_id=admin.id,
            config={"patterns": [
                # Same tag_id as config 1 — must be deduped, first one wins.
                {"label": "A dup", "tag_id": tag_a.id, "tag_name": tag_a.name, "regex": r"\bax\b", "enabled": True},
                {"label": "B", "tag_id": tag_b.id, "tag_name": tag_b.name, "regex": r"\bb\b", "enabled": True},
            ]},
        ))
        db.session.commit()

        ok, error, resolved = combine_all_platform_tag_patterns()
        assert ok, error
        tag_ids = [p["tag_id"] for p in resolved]
        assert tag_ids.count(tag_a.id) == 1
        assert tag_b.id in tag_ids
        # get_all_configs orders newest-first, so "RunAll Config 2" (saved
        # after Config 1) is seen first and its version of the shared tag wins.
        assert next(p for p in resolved if p["tag_id"] == tag_a.id)["label"] == "A dup"


def test_combine_all_platform_tag_patterns_no_configs(app):
    from app.core.db_class.db import FieldParserConfig
    from app.features.rule.field_parser_core import combine_all_platform_tag_patterns

    with app.app_context():
        FieldParserConfig.query.filter_by(config_type="platform_tags").delete()
        from app import db
        db.session.commit()

        ok, error, resolved = combine_all_platform_tag_patterns()
        assert not ok
        assert resolved == []
        assert "No saved" in error


def test_trigger_platform_tags_with_all_sentinel(app, client):
    from app import db
    from app.core.db_class.db import FieldParserConfig, User, BackgroundJob
    from app.features.rule.field_parser_core import ALL_PLATFORM_CONFIGS

    with app.app_context():
        admin = User.query.filter_by(admin=True).first()
        tag = _make_tag(db, "misp-galaxy:test-run-all=\"Trigger\"", admin.id)
        db.session.add(FieldParserConfig(
            name="RunAll Trigger Config", config_type="platform_tags", user_id=admin.id,
            config={"patterns": [
                {"label": "Trigger", "tag_id": tag.id, "tag_name": tag.name, "regex": r"\btrigger\b", "enabled": True},
            ]},
        ))
        db.session.commit()
        _login(client, admin.email)

    res = client.post("/account/admin/bulk_parse_fields/trigger_platform_tags",
                       json={"config_id": ALL_PLATFORM_CONFIGS})
    data = res.get_json()
    assert res.status_code == 200, data
    assert data["success"] is True

    with app.app_context():
        job = BackgroundJob.query.filter_by(uuid=data["job"]["uuid"]).first()
        assert job is not None
        assert job.payload["config_id"] == ALL_PLATFORM_CONFIGS


def test_trigger_platform_tags_forwards_rule_ids_and_format_filter(app, client):
    """Regression test for the rule-scope UI: the trigger route used to
    always hardcode {'rule_ids': 'ALL', 'format_filter': None} into the job
    payload no matter what the client sent — the new "Select Rules" card on
    the Platform Tags tab needs these actually forwarded."""
    from app import db
    from app.core.db_class.db import FieldParserConfig, User, BackgroundJob

    with app.app_context():
        admin = User.query.filter_by(admin=True).first()
        tag = _make_tag(db, "misp-galaxy:test-run-all=\"Scoped\"", admin.id)
        cfg = FieldParserConfig(
            name="RunAll Scoped Config", config_type="platform_tags", user_id=admin.id,
            config={"patterns": [
                {"label": "Scoped", "tag_id": tag.id, "tag_name": tag.name, "regex": r"\bscoped\b", "enabled": True},
            ]},
        )
        db.session.add(cfg)
        db.session.commit()
        cfg_id = cfg.id
        _login(client, admin.email)

    res = client.post("/account/admin/bulk_parse_fields/trigger_platform_tags",
                       json={"config_id": cfg_id, "rule_ids": [1, 2, 3]})
    data = res.get_json()
    assert res.status_code == 200, data

    with app.app_context():
        job = BackgroundJob.query.filter_by(uuid=data["job"]["uuid"]).first()
        assert job.payload["rule_ids"] == [1, 2, 3]
        assert job.payload["format_filter"] is None

    res2 = client.post("/account/admin/bulk_parse_fields/trigger_platform_tags",
                        json={"config_id": cfg_id, "format_filter": "yara"})
    data2 = res2.get_json()
    assert res2.status_code == 200, data2
    with app.app_context():
        job2 = BackgroundJob.query.filter_by(uuid=data2["job"]["uuid"]).first()
        assert job2.payload["rule_ids"] == "ALL"
        assert job2.payload["format_filter"] == "yara"


def test_trigger_platform_tags_rejects_bad_rule_ids_type(app, client):
    from app import db
    from app.core.db_class.db import FieldParserConfig, User

    with app.app_context():
        admin = User.query.filter_by(admin=True).first()
        tag = _make_tag(db, "misp-galaxy:test-run-all=\"BadType\"", admin.id)
        cfg = FieldParserConfig(
            name="RunAll BadType Config", config_type="platform_tags", user_id=admin.id,
            config={"patterns": [
                {"label": "BadType", "tag_id": tag.id, "tag_name": tag.name, "regex": r"\bx\b", "enabled": True},
            ]},
        )
        db.session.add(cfg)
        db.session.commit()
        cfg_id = cfg.id
        _login(client, admin.email)

    res = client.post("/account/admin/bulk_parse_fields/trigger_platform_tags",
                       json={"config_id": cfg_id, "rule_ids": "not-a-list-or-ALL"})
    assert res.status_code == 400


def test_trigger_platform_tags_all_sentinel_fails_with_no_configs(app, client):
    from app import db
    from app.core.db_class.db import FieldParserConfig, User
    from app.features.rule.field_parser_core import ALL_PLATFORM_CONFIGS

    with app.app_context():
        FieldParserConfig.query.filter_by(config_type="platform_tags").delete()
        db.session.commit()
        admin = User.query.filter_by(admin=True).first()
        _login(client, admin.email)

    res = client.post("/account/admin/bulk_parse_fields/trigger_platform_tags",
                       json={"config_id": ALL_PLATFORM_CONFIGS})
    data = res.get_json()
    assert res.status_code == 400
    assert data["success"] is False
