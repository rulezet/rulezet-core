"""Health tab "Fix it for me": which findings get a fix, and each fix actually
resolves its finding — scoped to the bundle and to its owner / admins."""

import uuid

from app import db
from app.core.db_class.db import BundleNode, BundleRuleAssociation, RuleTagAssociation

from bundle_helpers import D, F, R, SURICATA, admin, login, make_bundle, make_rule, other, owner, save_structure, tag


def _checks(client, bundle_id):
    return {c["key"]: c for c in client.get(f"/bundle/{bundle_id}/health").get_json()["health"]["checks"]}


def _fix(client, bundle_id, fix):
    return client.post(f"/bundle/{bundle_id}/health/fix", json={"fix": fix})


def test_fix_sid_collision_by_removing_one_rule(client, app):
    with app.app_context():
        a = make_rule("A", "suricata", SURICATA.format(msg="A", sid=9300001))
        b_ = make_rule("B", "suricata", SURICATA.format(msg="B", sid=9300001))
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(a.id), R(b_.id)])])
        item = [i for i in _checks(client, b.id)["collisions"]["items"] if i["rule_id"] == b_.id][0]
        assert item["fix"]["action"] == "remove_rule" and item["fix"]["confirm"] is True
        assert _fix(client, b.id, item["fix"]).get_json()["success"]
        assert _checks(client, b.id)["collisions"]["level"] == "ok"
        db.session.expire_all()
        assert not BundleNode.query.filter_by(bundle_id=b.id, rule_id=b_.id).first()
        assert not BundleRuleAssociation.query.filter_by(bundle_id=b.id, rule_id=b_.id).first()


def test_fix_missing_wazuh_parent_adds_it_next_to_the_child(client, app):
    with app.app_context():
        parent = make_rule("Parent", "wazuh", '<group name="p"><rule id="100500" level="3"><description>parent</description></rule></group>')
        child = make_rule("Child", "wazuh", '<group name="p"><rule id="100501" level="5"><if_sid>100500</if_sid><description>child</description></rule></group>')
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [D("hids", [R(child.id)])])])
        fx = _checks(client, b.id)["dependencies"]["items"][0]["fix"]
        assert fx["action"] == "add_rule" and fx["rule_id"] == parent.id
        assert _fix(client, b.id, fx).get_json()["success"]
        assert _checks(client, b.id)["dependencies"]["level"] == "ok"
        db.session.expire_all()
        p_node = BundleNode.query.filter_by(bundle_id=b.id, rule_id=parent.id).first()
        c_node = BundleNode.query.filter_by(bundle_id=b.id, rule_id=child.id).first()
        assert p_node.parent_id == c_node.parent_id                    # same folder ('hids')


def test_fix_missing_flowbit_setter(client, app):
    with app.app_context():
        setter = make_rule("Setter", "suricata", 'alert http any any -> any any (msg:"set"; flowbits:set,ET.demo_bit; flowbits:noalert; sid:9300010; rev:1;)')
        checker = make_rule("Checker", "suricata", 'alert http any any -> any any (msg:"check"; flowbits:isset,ET.demo_bit; sid:9300011; rev:1;)')
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(checker.id)])])
        fx = _checks(client, b.id)["dependencies"]["items"][0]["fix"]
        assert fx["rule_id"] == setter.id
        _fix(client, b.id, fx)
        assert _checks(client, b.id)["dependencies"]["level"] == "ok"


def test_fix_marking_duplicates_and_structure(client, app):
    with app.app_context():
        amber = make_rule("Amber", "yara", "rule amber_x { condition: true }")
        db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=amber.id, tag_id=tag("tlp:amber").id, user_id=owner().id))
        db.session.commit()
        unplaced = make_rule("Unplaced", "yara", "rule unplaced_x { condition: true }")
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(amber.id), R(amber.id), D("empty", []), F("empty.txt", "")])])
        from app.features.bundle import bundle_core as BM
        BM.add_rule_to_bundle(b.id, unplaced.id, "x")

        c = _checks(client, b.id)
        assert _fix(client, b.id, c["marking"]["items"][0]["fix"]).get_json()["success"]      # → bundle TLP:AMBER
        assert _fix(client, b.id, c["duplicates"]["items"][0]["fix"]).get_json()["success"]   # keep one copy
        for it in c["structure"]["items"]:
            assert it.get("fix"), it
            assert _fix(client, b.id, it["fix"]).get_json()["success"]

        c = _checks(client, b.id)
        assert c["marking"]["level"] == "ok"
        assert c["duplicates"]["level"] == "ok"
        assert c["structure"]["level"] == "ok"
        assert any(h["action"] in ("tags", "structure", "rules")
                   for h in client.get(f"/bundle/history/{b.id}").get_json()["entries"])


def test_fixes_only_for_managers_and_scoped_to_the_bundle(client, app):
    with app.app_context():
        a = make_rule("A", "suricata", SURICATA.format(msg="A", sid=9300020))
        b_ = make_rule("B", "suricata", SURICATA.format(msg="B", sid=9300020))
        outsider = make_rule("Outsider", "yara", "rule o { condition: true }")
        b = make_bundle()
        other_bundle = make_bundle("other")
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(a.id), R(b_.id)])])
        save_structure(client, other_bundle.id, [D("Main", [R(outsider.id), F("keep.md", "not empty")])])
        other_node = BundleNode.query.filter_by(bundle_id=other_bundle.id, node_type="file", rule_id=None).first()

        # a node / rule of another bundle, or a non-empty file, can't be touched
        assert not _fix(client, b.id, {"action": "remove_node", "node_id": other_node.id}).get_json()["success"]
        assert not _fix(client, b.id, {"action": "remove_rule", "rule_id": outsider.id}).get_json()["success"]
        assert not _fix(client, other_bundle.id, {"action": "remove_node", "node_id": other_node.id}).get_json()["success"]
        assert not _fix(client, b.id, {"action": "set_marking", "tag": "'; drop table"}).get_json()["success"]
        assert not _fix(client, b.id, {"action": "nope"}).get_json()["success"]

        login(client, other())
        items = _checks(client, b.id)["collisions"]["items"]
        assert all("fix" not in i for i in items)                  # not offered…
        assert _fix(client, b.id, {"action": "remove_rule", "rule_id": a.id}).status_code == 403   # …nor accepted
        login(client, admin())
        assert _fix(client, b.id, {"action": "remove_rule", "rule_id": a.id}).get_json()["success"]


def test_no_fix_offered_on_a_release(client, app):
    with app.app_context():
        a = make_rule("A", "suricata", SURICATA.format(msg="A", sid=9300030))
        b_ = make_rule("B", "suricata", SURICATA.format(msg="B", sid=9300030))
        b = make_bundle()
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(a.id), R(b_.id)])])
        client.post(f"/bundle/{b.id}/releases", json={"version": "v1.0.0"})
        h = client.get(f"/bundle/{b.id}/health?release=v1.0.0").get_json()["health"]
        assert all("fix" not in i for c in h["checks"] for i in c["items"])
