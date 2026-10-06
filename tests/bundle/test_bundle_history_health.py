"""Bundle history (snapshots, coalescing, creation folding) and the
pre-deployment health checks."""

from app import db
from app.core.db_class.db import BundleHistory

from bundle_helpers import (D, F, R, SURICATA, admin, login, make_bundle, make_rule, other, owner,
                            save_structure, tag)


def _history(bundle_id):
    db.session.expire_all()
    return BundleHistory.query.filter_by(bundle_id=bundle_id).order_by(BundleHistory.id).all()


# ── history ───────────────────────────────────────────────────────────────

def test_creation_and_first_fill_are_one_entry(client, app):
    """Creating a bundle (from a filter / a workspace) then filling it must
    not produce one history entry per rule."""
    with app.app_context():
        rules = [make_rule(f"r{i}", "yara", f"rule r{i} {{ condition: true }}") for i in range(30)]
        b = make_bundle()
        login(client, owner())
        for k in (10, 20, 30):                       # editor autosaves
            save_structure(client, b.id, [D("Main", [R(r.id) for r in rules[:k]])])
        rows = _history(b.id)
        assert len(rows) == 1 and rows[0].action == "created"
        assert "30 rules" in rows[0].summary


def test_later_edits_are_coalesced_and_described(client, app):
    with app.app_context():
        r1 = make_rule("one", "yara", "rule one { condition: true }")
        b = make_bundle()
        # an entry by another user closes the "creation" window
        from app.features.bundle import bundle_core as BM
        BM.toggle_bundle_accessibility(b.id)
        login(client, admin())
        save_structure(client, b.id, [D("Main", [R(r1.id)])])
        save_structure(client, b.id, [D("Main", [R(r1.id), F("README.md", "v1")])])
        save_structure(client, b.id, [D("Main", [R(r1.id), F("README.md", "v2")])])
        structure_rows = [h for h in _history(b.id) if h.action == "structure"]
        assert len(structure_rows) == 1                # 3 autosaves → 1 entry
        fields = {c["field"] for c in structure_rows[0].changes}
        assert {"rules", "files", "folders"} <= fields


def test_description_change_shows_the_changed_part(client, app):
    from app.features.bundle.bundle_history_core import diff_snapshots
    with app.app_context():
        base = {"name": "x", "access": True, "tags": [], "vulnerabilities": [], "rules": {}, "files": {}, "folders": []}
        long = "# Title\n\n" + "Intro paragraph. " * 20
        c = diff_snapshots({**base, "description": long}, {**base, "description": long + "\nNEW LINE ADDED"})[0]
        assert c["field"] == "description"
        assert "NEW LINE ADDED" in c["new"]            # not just the (identical) opening
        assert c["old"] != c["new"]


def test_history_never_stores_the_share_token(client, app):
    with app.app_context():
        b = make_bundle(public=False)
        login(client, owner())
        token = client.post(f"/bundle/{b.id}/share").get_json()["url"].split("share=")[1]
        for h in _history(b.id):
            assert token not in str(h.old_snapshot) + str(h.new_snapshot) + str(h.changes)
        assert any(h.action == "sharing" for h in _history(b.id))


def test_history_is_readable_only_by_viewers(client, app):
    with app.app_context():
        b = make_bundle(public=False)
        assert client.get(f"/bundle/history/{b.id}").status_code == 403
        login(client, owner())
        d = client.get(f"/bundle/history/{b.id}").get_json()
        assert d["success"] and d["entries"][-1]["action"] == "created"


# ── health ────────────────────────────────────────────────────────────────

def _health(client, bundle_id):
    return {c["key"]: c for c in client.get(f"/bundle/{bundle_id}/health").get_json()["health"]["checks"]}


def test_health_detects_collisions_dependencies_and_marking(client, app):
    with app.app_context():
        s1 = make_rule("A", "suricata", SURICATA.format(msg="A", sid=9000001))
        s2 = make_rule("B", "suricata", SURICATA.format(msg="B", sid=9000001))        # same SID
        fb = make_rule("C", "suricata", 'alert http any any -> any any (msg:"C"; flowbits:isset,ET.never_set; sid:9000002; rev:1;)')
        wz = make_rule("W", "wazuh", '<group name="x"><rule id="100200" level="5"><if_sid>100100</if_sid><description>child</description></rule></group>')
        y1 = make_rule("Y1", "yara", "rule Same_Name { condition: true }")
        y2 = make_rule("Y2", "yara", "rule Same_Name { condition: false }")
        red = make_rule("Red", "yara", "rule Red_Rule { condition: true }")
        from app.core.db_class.db import RuleTagAssociation
        import uuid
        db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=red.id, tag_id=tag("tlp:red").id, user_id=owner().id))
        db.session.commit()

        b = make_bundle()
        from app.features.bundle import bundle_core as BM
        BM.update_bundle_tags(b.id, [tag("tlp:clear").id], owner())
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(x.id) for x in (s1, s2, fb, wz, y1, y2, red)] + [R(y1.id), D("empty", []), F("empty.txt", "")])])

        checks = _health(client, b.id)
        assert checks["collisions"]["level"] == "error"
        coll = " ".join(i["detail"] for i in checks["collisions"]["items"])
        assert "SID 9000001" in coll and "Same_Name" in coll
        deps = " ".join(i["detail"] for i in checks["dependencies"]["items"])
        assert "ET.never_set" in deps and "100100" in deps
        assert checks["marking"]["level"] == "error" and checks["marking"]["items"][0]["rule_id"] == red.id
        assert checks["duplicates"]["items"] and "2 times" in checks["duplicates"]["items"][0]["detail"]
        details = " ".join(i["detail"] for i in checks["structure"]["items"])
        assert "Empty folder" in details and "Empty file" in details
        assert all(c.get("fix") for c in checks.values() if c["level"] in ("error", "warning"))


def test_healthy_bundle_is_ready(client, app):
    with app.app_context():
        s1 = make_rule("A", "suricata", SURICATA.format(msg="A", sid=9100001))
        s2 = make_rule("B", "suricata", SURICATA.format(msg="B", sid=9100002))
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(s1.id), R(s2.id)])])
        h = client.get(f"/bundle/{b.id}/health").get_json()["health"]
        assert h["counts"]["error"] == 0
        assert {"collisions", "dependencies", "marking", "duplicates"} <= {c["key"] for c in h["checks"] if c["level"] == "ok"}


def test_health_rerun_is_owner_or_admin_only(client, app):
    with app.app_context():
        b = make_bundle()
        login(client, other())
        d = client.get(f"/bundle/{b.id}/health").get_json()
        assert d["success"] and d["can_rerun"] is False
        assert client.get(f"/bundle/{b.id}/health?refresh=1").status_code == 403
        login(client, owner())
        assert client.get(f"/bundle/{b.id}/health?refresh=1").get_json()["can_rerun"] is True


def test_wazuh_builtin_parents_are_not_missing_dependencies(client, app):
    """if_sid < 100000 = Wazuh default ruleset, present on every manager."""
    with app.app_context():
        builtin_child = make_rule("Puppet ran", "wazuh", '<group name="p"><rule id="100300" level="3"><if_sid>80090</if_sid><description>x</description></rule></group>')
        custom_child = make_rule("Custom child", "wazuh", '<group name="p"><rule id="100301" level="3"><if_sid>100999</if_sid><description>x</description></rule></group>')
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(builtin_child.id), R(custom_child.id)])])
        dep = _health(client, b.id)["dependencies"]
        assert [i["rule_id"] for i in dep["items"]] == [custom_child.id]
        assert "80090" in dep["message"] and "default ruleset" in dep["message"]


def test_health_edit_opens_the_bundle_editor_for_managers_only(client, app):
    with app.app_context():
        s1 = make_rule("A", "suricata", SURICATA.format(msg="A", sid=9200001))
        s2 = make_rule("B", "suricata", SURICATA.format(msg="B", sid=9200001), author_id=admin().id)
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(s1.id), R(s2.id)])])
        items = _health(client, b.id)["collisions"]["items"]
        assert all(i["can_edit"] for i in items)          # bundle owner, even for someone else's rule
        login(client, other())
        assert not any(i["can_edit"] for i in _health(client, b.id)["collisions"]["items"])

        login(client, owner())
        page = client.get(f"/bundle/edit/{b.id}?focus_rule={s2.id}&check=Identifier+collisions&issue=SID+9200001+%5B%5B+1%2B1+%5D%5D")
        html = page.get_data(as_text=True)
        assert page.status_code == 200 and "Back to the health check" in html
        assert f"const _FOCUS_RULE_ID = {s2.id}" in html
        # the banner is not compiled by Vue (no [[ ]] template injection from the URL)
        banner = html[html.index("Health check —"):]
        start = html.index("{# Arrived") if "{# Arrived" in html else html.index("Health check —") - 1200
        assert "v-pre" in html[start:html.index("Health check —")]
        assert "[[ 1+1 ]]" in banner


def test_marking_without_bundle_tlp_only_flags_restricted_rules(client, app):
    """Regression: a bundle with no TLP/PAP tag flagged every rule carrying
    tlp:clear / tlp:white (i.e. every rule, since tlp:clear is auto-attached)."""
    from app.core.db_class.db import RuleTagAssociation
    import uuid
    with app.app_context():
        clear = make_rule("clear", "yara", "rule clear_r { condition: true }")
        white = make_rule("white", "yara", "rule white_r { condition: true }")
        amber = make_rule("amber", "yara", "rule amber_r { condition: true }")
        for r, t in ((clear, "tlp:clear"), (white, "TLP:WHITE"), (amber, "tlp:amber"), (clear, "pap:clear")):
            db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=r.id, tag_id=tag(t).id, user_id=owner().id))
        db.session.commit()
        b = make_bundle()                       # no TLP / PAP tag on the bundle
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(clear.id), R(white.id)])])
        assert _health(client, b.id)["marking"]["level"] == "ok"

        save_structure(client, b.id, [D("Main", [R(clear.id), R(white.id), R(amber.id)])])
        m = _health(client, b.id)["marking"]
        assert m["level"] == "error" and [i["rule_id"] for i in m["items"]] == [amber.id]
        assert "no TLP tag" in m["message"]
