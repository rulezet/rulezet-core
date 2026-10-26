"""References and other metadata read from a rule's text (app/features/rule/rule_metadata_core.py):
extraction per format, kept in sync when the rule changes, the re-parse job for existing rules,
the rule page and the admin preview."""
from app import db
from app.core.db_class.rule import Rule
from app.features.rule.rule_metadata_core import display_metadata, extract_rule_metadata
from tests_new.helpers.rules import make_rule

YARA = '''rule meta_example
{
    meta:
        author = "Someone"
        description = "Example"
        reference = "https://example.org/report-1"
        reference = "https://example.org/report-2"
        date = "2024-05-02"
        hash = "44d88612fea8a8f36de82e1278abb02f"
        hash = "3395856ce81f2b7382dee72602f798b642f14140"
        score = 80
        // commented = "not metadata"
    strings:
        $a = "reference = \\"https://not-a-meta.example\\""
    condition:
        $a
}'''

SIGMA = '''title: Example
id: 0e95725d-7320-415d-80f7-004da920fc11
status: test
description: d
references:
    - https://example.org/blog
author: me
date: 2024/01/10
tags:
    - attack.execution
logsource:
    product: windows
detection:
    selection:
        Image: x
    condition: selection
falsepositives:
    - Administrators
level: high'''

SURICATA = ('alert http any any -> any any (msg:"Example; with a semicolon"; content:"evil"; '
            'reference:url,www.example.org/advisory; reference:cve,2021-44228; classtype:trojan-activity; '
            'sid:1000001; rev:3; metadata: created_at 2024_01_01, tag foo, signature_severity Major;)')


def test_yara_meta():
    found = extract_rule_metadata("yara", YARA)
    assert found["references"] == ["https://example.org/report-1", "https://example.org/report-2"]
    extra = found["extra"]
    assert extra["date"] == "2024-05-02" and extra["score"] == "80"
    assert extra["hash"] == ["44d88612fea8a8f36de82e1278abb02f", "3395856ce81f2b7382dee72602f798b642f14140"]
    # Rulezet's own fields, comments and strings are never "other metadata"
    assert not {"author", "description", "commented"} & set(extra)


def test_sigma_keys():
    found = extract_rule_metadata("sigma", SIGMA)
    assert found["references"] == ["https://example.org/blog"]
    extra = found["extra"]
    assert extra["status"] == "test" and extra["level"] == "high" and extra["falsepositives"] == "Administrators"
    assert extra["logsource"] == "product: windows"
    assert not {"title", "id", "tags", "detection", "author", "description"} & set(extra)


def test_suricata_options():
    found = extract_rule_metadata("suricata", SURICATA)
    assert found["references"] == ["http://www.example.org/advisory", "CVE-2021-44228"]
    extra = found["extra"]
    assert extra["sid"] == "1000001" and extra["rev"] == "3" and extra["classtype"] == "trojan-activity"
    assert extra["signature_severity"] == "Major" and "tag" not in extra


def test_unknown_format_reads_only_known_header_keys():
    found = extract_rule_metadata("zeek", "# reference: https://z.example\n# todo: fix me\n# date: 2020\nevent x() {}")
    assert found == {"references": ["https://z.example"], "extra": {"date": "2020"}}


def test_bad_or_empty_content_never_raises():
    for fmt, content in (("sigma", "::: not yaml ["), ("elastic", "[[[["), ("yara", ""), (None, None), ("suricata", "(")):
        assert extract_rule_metadata(fmt, content) == {"references": [], "extra": {}} or extract_rule_metadata(fmt, content)


def test_limits():
    meta = "\n".join(f'        reference = "https://example.org/{i}"' for i in range(200))
    found = extract_rule_metadata("yara", f"rule big {{\n    meta:\n{meta}\n    condition:\n        true\n}}")
    assert len(found["references"]) == 50


def test_kept_in_sync_with_the_rule_text(app, users):
    rule = make_rule(users.user, to_string=YARA)
    assert rule.rule_references[0] == "https://example.org/report-1"
    assert rule.extra_metadata["date"] == "2024-05-02"
    rule.to_string = 'rule meta_example { meta: reference = "https://changed.example" condition: true }'
    db.session.commit()
    rule = db.session.get(Rule, rule.id)
    assert rule.rule_references == ["https://changed.example"] and rule.extra_metadata is None
    plain = make_rule(users.user)                       # nothing in its text: columns stay NULL
    assert plain.rule_references is None and plain.extra_metadata is None


def test_to_json_has_them(app, users):
    data = make_rule(users.user, to_string=YARA).to_json(is_favorited=False)
    assert data["references"][1] == "https://example.org/report-2" and data["extra_metadata"]["score"] == "80"


def test_reparse_job_fills_existing_rules_without_touching_them(app, clients, users):
    from app.features.jobs.job_worker import run_next_job
    rule = make_rule(users.user, to_string=YARA)
    before = (rule.to_string, rule.last_modif, rule.title)
    Rule.query.filter_by(id=rule.id).update({"rule_references": None, "extra_metadata": None})
    db.session.commit()
    res = clients["admin"].post("/account/admin/bulk_parse_fields/trigger_rule_metadata", json={"formats": ["yara"]})
    assert res.status_code == 200 and res.json["success"]
    run_next_job(app)
    db.session.expire_all()
    rule = db.session.get(Rule, rule.id)
    assert rule.rule_references and rule.extra_metadata["date"] == "2024-05-02"
    assert (rule.to_string, rule.last_modif, rule.title) == before


def test_admin_only(clients):
    for who in ("anonymous", "user", "owner"):
        assert clients[who].post("/account/admin/bulk_parse_fields/trigger_rule_metadata", json={"formats": "ALL"}).status_code in (302, 401, 403)
        assert clients[who].post("/account/admin/bulk_parse_fields/rule_metadata/preview", json={"format": "yara", "content": YARA}).status_code in (302, 401, 403)
    res = clients["admin"].post("/account/admin/bulk_parse_fields/rule_metadata/preview", json={"format": "yara", "content": YARA})
    assert res.json["references"][0] == "https://example.org/report-1"
    assert {f["key"]: f["is_hash"] for f in res.json["extra"]}["hash"] is True


def test_rule_page_shows_them_safely(app, clients, users):
    hostile = YARA.replace('date = "2024-05-02"', 'date = "[[ constructor.constructor(\\"alert(1)\\")() ]]"')
    rule = make_rule(users.user, to_string=hostile)
    html = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}").get_data(as_text=True)
    assert "https://example.org/report-1" in html and "Other metadata" in html
    # the rule's own text is shown as text, never compiled by Vue
    start = html.index("Other metadata")
    assert 'v-pre' in html[start:start + 4000]
    assert "<script>" not in html[start:start + 4000]


def test_display_labels():
    fields = {f["key"]: f for f in display_metadata({"date": "x", "sha256": "a" * 64, "my_key": ["a", "b"]})}
    assert fields["date"]["label"] == "Date" and fields["sha256"]["is_hash"]
    assert fields["my_key"]["label"] == "My key" and fields["my_key"]["values"] == ["a", "b"]


# ── References added by hand (create / edit form) ─────────────────────────────

def test_create_form_keeps_references_added_by_hand(clients):
    from tests_new.helpers.rules import new_rule_form
    form = new_rule_form()
    form["to_string"] = YARA.replace("meta_example", "meta_create_example")
    form["references"] = "https://by-hand.example/1\nhttps://example.org/report-1\n\nhttps://by-hand.example/1"
    clients["owner"].post("/rule/create_rule", data=form)
    rule = Rule.query.filter_by(title=form["title"]).one()
    assert rule.manual_references == ["https://by-hand.example/1"]          # the text's one not kept twice
    assert rule.all_references == ["https://example.org/report-1", "https://example.org/report-2", "https://by-hand.example/1"]


def test_edit_form_changes_only_the_references_added_by_hand(app, clients, users):
    from tests_new.helpers.rules import edit_form
    rule = make_rule(users.owner, to_string=YARA)
    page = clients["owner"].get(f"/rule/edit_rule/{rule.id}").get_data(as_text=True)
    assert "Read from the rule" in page and "https://example.org/report-1" in page
    clients["owner"].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, references="https://by-hand.example/2"))
    rule = db.session.get(Rule, rule.id)
    assert rule.manual_references == ["https://by-hand.example/2"]
    assert rule.rule_references == ["https://example.org/report-1", "https://example.org/report-2"]
    clients["owner"].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, references=""))
    assert db.session.get(Rule, rule.id).manual_references is None


def test_references_by_hand_survive_a_change_of_the_text(app, users):
    from app.features.rule.rule_metadata_core import set_manual_references
    rule = make_rule(users.user, to_string=YARA)
    set_manual_references(rule, ["https://by-hand.example/3"])
    rule.to_string = 'rule meta_example { meta: reference = "https://changed.example" condition: true }'
    db.session.commit()
    rule = db.session.get(Rule, rule.id)
    assert rule.all_references == ["https://changed.example", "https://by-hand.example/3"]
    page_refs = rule.to_json(is_favorited=False)
    assert page_refs["references_manual"] == ["https://by-hand.example/3"]


# ── Exports: MISP, portable JSON (download / bundle), connectors ─────────────

def test_misp_object_carries_references_and_metadata(app, users):
    from app.features.misp.rule.misp_object import create_rulezet_metadata_misp_object
    from app.features.rule.rule_metadata_core import set_manual_references
    rule = make_rule(users.user, to_string=YARA)
    set_manual_references(rule, ["Internal report 42"])
    db.session.commit()
    attrs = [(a.object_relation, a.value) for a in create_rulezet_metadata_misp_object(rule.id).attributes]
    assert ("reference", "https://example.org/report-1") in attrs
    assert ("reference-text", "Internal report 42") in attrs
    assert ("extra-metadata", "date: 2024-05-02") in attrs


def test_portable_json_round_trip_keeps_references_added_by_hand(app, users):
    from app.features.rule.rule_metadata_core import set_manual_references
    from app.features.rule.rule_portable import normalize_rule_json, rule_to_portable
    rule = make_rule(users.user, to_string=YARA)
    set_manual_references(rule, ["https://by-hand.example/9"])
    db.session.commit()
    with app.test_request_context():                 # to_json() reads the current user
        exported = rule_to_portable(rule)
    assert exported["references_manual"] == ["https://by-hand.example/9"] and exported["extra_metadata"]["date"]
    rule_dict, error = normalize_rule_json(exported)
    assert error is None and rule_dict["references"] == ["https://by-hand.example/9"]


def test_connector_sync_keeps_references_added_by_hand(app, users):
    from app.features.connector.connector_core import clean_remote_rule
    clean = clean_remote_rule({"uuid": "6b3c5e2a-1f2d-4a9b-8c7d-0e1f2a3b4c5d", "to_string": YARA,
                               "references_manual": ["https://by-hand.example/7", 5]})
    assert clean["references_manual"] == ["https://by-hand.example/7"]
    assert "references_manual" not in clean_remote_rule({"uuid": "6b3c5e2a-1f2d-4a9b-8c7d-0e1f2a3b4c5e", "to_string": YARA})
