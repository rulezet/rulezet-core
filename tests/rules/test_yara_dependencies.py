"""YARA rules that reference other rules in their condition only compile
together with them — recursively (the rule it needs may need another one).

validate() resolves the chain from the rules already on the instance, create
and edit record it as auto `yara_condition_ref` links, and the Linked Rules
page reads the transitive "needs / needed by" graph."""

import datetime
import uuid

from app import db
from app.core.db_class.db import Rule, RuleRelation, User
from app.features.rule.rule_format.available_format.yara_format import (
    YaraRule, sync_yara_dependency_relations,
)
from app.features.rule.rule_format.main_format import verify_syntax_rule_by_format

C = 'rule Base_C { strings: $c = "ccc" condition: $c }'
B = 'rule Mid_B { condition: Base_C }'
A = 'rule Top_A { condition: Mid_B and filesize < 10MB }'


def _rule(title, content, fmt="yara"):
    r = Rule(format=fmt, title=title, license="MIT", description="d", uuid=str(uuid.uuid4()), source="test",
             author="a", version=1, user_id=User.query.filter_by(email="t@t.t").first().id, to_string=content,
             vote_up=0, vote_down=0, creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
             last_modif=datetime.datetime.now(tz=datetime.timezone.utc))
    db.session.add(r)
    db.session.commit()
    return r


def _owner():
    return (User.query.filter_by(email="t@t.t").first().id,)


def _links():
    db.session.expire_all()
    return {(Rule.query.get(r.source_rule_id).title, Rule.query.get(r.target_rule_id).title)
            for r in RuleRelation.query.filter_by(relation_type="yara_condition_ref")}


# ── validate() ───────────────────────────────────────────────────────────────

def test_a_rule_alone_is_unchanged(app):
    with app.app_context():
        res = YaraRule().validate(C)
        assert res.ok and res.dependencies == [] and res.normalized_content == C


def test_resolves_the_whole_chain_recursively_in_declaration_order(app):
    with app.app_context():
        c, b = _rule("Base_C", C), _rule("Mid_B", B)
        res = YaraRule().validate(A, owner_ids=_owner())
        assert res.ok, res.errors
        assert [d.title for d in res.dependencies] == ["Base_C", "Mid_B"]    # C declared before B
        assert res.normalized_content == A                                   # own text only
        assert any("Mid_B" in w for w in res.warnings)


def test_missing_link_in_the_chain_still_fails(app):
    with app.app_context():
        _rule("Mid_B", B)                                                    # Base_C doesn't exist
        res = YaraRule().validate(A, owner_ids=_owner())
        assert not res.ok and 'undefined identifier "Base_C"' in res.errors[0]


def test_a_rule_is_never_its_own_dependency(app):
    with app.app_context():
        r = _rule("Self_Ref", "rule Self_Ref { condition: true }")
        res = YaraRule().validate("rule Other { condition: Self_Ref }", rule_id=r.id, owner_ids=_owner())
        assert not res.ok
        assert YaraRule().validate("rule Other { condition: Self_Ref }", owner_ids=_owner()).ok


def test_module_needed_only_by_a_dependency_is_not_added_to_the_rule(app):
    with app.app_context():
        _rule("Is_PE", 'import "pe"\nrule Is_PE { condition: pe.is_pe }')
        own = "rule Uses_PE { condition: Is_PE }"
        res = YaraRule().validate(own, owner_ids=_owner())
        assert res.ok, res.errors
        assert res.normalized_content == own


def test_edit_and_create_syntax_check_accept_the_chain(app):
    """verify_syntax_rule_by_format is what the create and edit forms run."""
    with app.app_context():
        _rule("Base_C", C)
        _rule("Mid_B", B)
        from flask_login import login_user
        with app.test_request_context():
            login_user(User.query.filter_by(email="t@t.t").first())     # the author creating / editing
            ok, error = verify_syntax_rule_by_format({"format": "yara", "to_string": A})
        assert ok, error


# ── links recorded on create / edit ─────────────────────────────────────────

def test_create_records_every_link_of_the_chain(client, app):
    with app.app_context():
        _rule("Base_C", C)
        _rule("Mid_B", B)
        resp = client.post("/api/rule/private/create", headers={"X-API-KEY": "api_key_user_rule"}, json={
            "title": "Top_A", "format": "yara", "version": "1.0", "license": "MIT", "to_string": A})
        assert resp.status_code == 200, resp.get_json()
        assert _links() == {("Top_A", "Mid_B"), ("Mid_B", "Base_C")}


def test_sync_is_idempotent(app):
    with app.app_context():
        _rule("Base_C", C)
        _rule("Mid_B", B)
        a = _rule("Top_A", A)
        sync_yara_dependency_relations(a)
        sync_yara_dependency_relations(a)
        assert RuleRelation.query.filter_by(relation_type="yara_condition_ref").count() == 2


# ── dependency graph ─────────────────────────────────────────────────────────

def test_dependency_graph_both_directions(client, app):
    with app.app_context():
        c, b = _rule("Base_C", C), _rule("Mid_B", B)
        a = _rule("Top_A", A)
        sync_yara_dependency_relations(a)

        g = client.get(f"/rule_relation/rule/{a.id}/dependencies").get_json()
        roles = {n["title"]: (n["role"], n["depth"]) for n in g["nodes"]}
        assert roles == {"Top_A": ("self", 0), "Mid_B": ("requires", 1), "Base_C": ("requires", 2)}
        assert {(e["from"], e["to"]) for e in g["edges"]} == {(a.id, b.id), (b.id, c.id)}
        assert g["requires_count"] == 2 and g["required_by_count"] == 0

        g = client.get(f"/rule_relation/rule/{c.id}/dependencies").get_json()
        roles = {n["title"]: (n["role"], n["depth"], n["via"]) for n in g["nodes"]}
        assert roles["Top_A"] == ("required_by", 2, b.id) and roles["Mid_B"] == ("required_by", 1, c.id)

        b.is_deleted = True
        db.session.commit()
        g = client.get(f"/rule_relation/rule/{a.id}/dependencies").get_json()
        assert [n["title"] for n in g["nodes"]] == ["Top_A"]                 # trashed rules are hidden
        assert client.get("/rule_relation/rule/999999/dependencies").status_code == 404


# ── download with dependencies ───────────────────────────────────────────────

def test_install_order_puts_every_rule_after_what_it_needs():
    from app.features.rule_relation.rule_relation_core import dependency_install_order
    edges = [{"from": 1, "to": 2}, {"from": 2, "to": 3}, {"from": 4, "to": 1}]
    assert dependency_install_order([4, 1, 2, 3], edges) == [3, 2, 1, 4]


def test_download_zip_holds_the_chain_in_one_folder(client, app):
    import io
    import zipfile
    with app.app_context():
        c, b = _rule("Base_C", C), _rule("Mid_B", B)
        a = _rule("Top_A", A)
        user = _rule("Uses_A", "rule Uses_A { condition: Top_A }")
        sync_yara_dependency_relations(a)
        sync_yara_dependency_relations(user)

        resp = client.get(f"/rule_relation/rule/{a.id}/dependencies/download")
        assert resp.status_code == 200 and resp.mimetype == "application/zip"
        z = zipfile.ZipFile(io.BytesIO(resp.data))
        names = z.namelist()
        assert len({n.split("/")[0] for n in names}) == 1                     # one folder
        rule_files = sorted(n for n in names if n.endswith(".yar") and "combined" not in n)
        assert len(rule_files) == 3                                           # A + B + C, not Uses_A
        combined = z.read(next(n for n in names if n.endswith("_combined.yar"))).decode()
        assert combined.index("rule Base_C") < combined.index("rule Mid_B") < combined.index("rule Top_A")
        import yara
        yara.compile(source=combined)                                         # compiles on its own

        z = zipfile.ZipFile(io.BytesIO(client.get(
            f"/rule_relation/rule/{a.id}/dependencies/download?include=all").data))
        assert any("Uses_A" in n for n in z.namelist())
        assert client.get("/rule_relation/rule/999999/dependencies/download").status_code == 404


def test_public_validate_endpoint_never_resolves_dependencies(client, app):
    """Public and unauthenticated: resolving references costs lookups and
    compiles per call, so the content is checked on its own."""
    with app.app_context():
        _rule("Base_C", C)
        resp = client.post("/api/rule/public/validate", json={"format": "yara", "content": B})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valid"] is False and any("Base_C" in e for e in data["errors"])
        resp = client.post("/api/rule/public/validate",
                           json={"format": "yara", "content": "x" * (512 * 1024 + 1)})
        assert resp.status_code == 413


# ── only trusted rules are ever pulled in ────────────────────────────────────

def _rule_of(email, title, content, source="test"):
    r = _rule(title, content)
    r.user_id = User.query.filter_by(email=email).first().id
    r.source = source
    db.session.commit()
    return r


def test_a_rule_from_someone_else_elsewhere_is_never_pulled_in(app):
    """Anyone can publish a rule named like a common identifier — it must
    not end up compiled into other people's rules."""
    with app.app_context():
        _rule_of("neo@admin.admin", "Base_C", C, source="https://github.com/attacker/repo")
        res = YaraRule().validate(B, owner_ids=_owner(), source="https://github.com/victim/repo")
        assert not res.ok and res.dependencies == []


def test_trusted_candidates_same_source_owner_or_existing_link(app):
    with app.app_context():
        mine = _rule_of("t@t.t", "Base_C", C)
        _rule_of("neo@admin.admin", "Base_C", C, source="https://github.com/attacker/repo")
        assert [d.id for d in YaraRule().validate(B, owner_ids=_owner()).dependencies] == [mine.id]

        theirs = _rule_of("neo@admin.admin", "Lib_X", 'rule Lib_X { strings: $x = "x" condition: $x }',
                          source="https://github.com/shared/lib")
        use = "rule Uses_X { condition: Lib_X }"
        assert YaraRule().validate(use, source="https://github.com/shared/lib").ok       # same source
        assert not YaraRule().validate(use, owner_ids=_owner()).ok                       # stranger's rule
        me = _rule_of("t@t.t", "Uses_X", use)
        from app.features.rule_relation.rule_relation_core import add_relation
        add_relation(me.id, theirs.id, "depends_on", user_id=me.user_id)                 # linked by hand
        assert YaraRule().validate(use, rule_id=me.id, owner_ids=_owner()).ok


def test_a_global_rule_is_never_a_dependency(app):
    with app.app_context():
        _rule_of("t@t.t", "Base_C", 'global rule Base_C { condition: filesize < 1MB }')
        res = YaraRule().validate(B, owner_ids=_owner())
        assert not res.ok and res.dependencies == []


def test_an_edit_removing_a_reference_removes_the_link(app):
    with app.app_context():
        _rule("Base_C", C)
        b = _rule("Mid_B", B)
        sync_yara_dependency_relations(b)
        assert _links() == {("Mid_B", "Base_C")}
        b.to_string = 'rule Mid_B { condition: true }'
        db.session.commit()
        sync_yara_dependency_relations(b)
        assert _links() == set()


def test_dependency_download_logged_once_per_downloader(client, app, monkeypatch):
    """Public route: repeated downloads don't flood the activity log."""
    from app import memory_cache
    from app.core.db_class.db import ActivityLog
    store = {}
    monkeypatch.setattr(memory_cache, "get", lambda k: store.get(k))
    monkeypatch.setattr(memory_cache, "set", lambda k, v, timeout=None: store.__setitem__(k, v))
    with app.app_context():
        _rule("Base_C", C)
        b = _rule("Mid_B", B)
        sync_yara_dependency_relations(b)
        for _ in range(5):
            assert client.get(f"/rule_relation/rule/{b.id}/dependencies/download").status_code == 200
        n = ActivityLog.query.filter_by(action="rule.download", target_id=b.id).count()
        assert n == 1


def test_editing_or_proposing_on_someone_elses_rule_keeps_its_dependencies(app):
    """The author's own rules stay trusted dependencies when an admin edits
    the rule or another user proposes an edit."""
    from flask_login import login_user
    with app.app_context():
        _rule("Base_C", C)                                                  # author: t@t.t
        b = _rule("Mid_B", B)
        edited = B.replace("condition: Base_C", "condition: Base_C and filesize < 5MB")
        for email in ("admin@admin.admin", "neo@admin.admin"):
            with app.test_request_context():
                login_user(User.query.filter_by(email=email).first())
                ok, error = verify_syntax_rule_by_format({"format": "yara", "to_string": edited}, rule=b)
                assert ok, (email, error)
                ok, _ = verify_syntax_rule_by_format({"format": "yara", "to_string": edited})
                assert not ok                                                 # without the rule's context
