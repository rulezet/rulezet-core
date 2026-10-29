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
    assert extra["logsource_product"] == "windows"            # a simple object: one field per entry
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


def test_comma_lists_are_shown_one_item_per_line():
    from app.features.rule.rule_metadata_core import display_metadata, split_list_value
    assert split_list_value("mirai,gafgyt,tsunami") == ["mirai", "gafgyt", "tsunami"]
    assert split_list_value("Cobalt Strike, Mimikatz") == ["Cobalt Strike", "Mimikatz"]
    sentence = "Detects a loader, which then drops a payload. It runs quietly, in memory."
    assert split_list_value(sentence) == [sentence]                     # a sentence stays whole
    shown = display_metadata({"family": "mirai,gafgyt, mirai", "info": sentence})
    assert shown[0]["values"] == ["mirai", "gafgyt"] and shown[1]["values"] == [sentence]


def test_interesting_metadata_gets_colours():
    from app.features.rule.rule_metadata_core import display_metadata
    shown = {f["key"]: f for f in display_metadata({"family": "mirai,gafgyt", "confidence": "high",
                                                     "severity": "critical", "score": "85", "remark": "plain"})}
    assert [v["tone"] for v in shown["family"]["styled"]] == ["red", "red"]
    assert shown["confidence"]["styled"][0]["tone"] == "green"
    assert shown["severity"]["styled"][0]["tone"] == "red"
    assert shown["score"]["styled"][0]["percent"] == 85
    assert shown["remark"]["style"] is None and shown["remark"]["styled"][0]["tone"] is None   # unknown key: plain


def test_coloured_values_stay_escaped(clients, users):
    from tests_new.helpers.rules import make_rule
    rule = make_rule(users.owner)
    rule.extra_metadata = {"family": "<script>alert(1)</script>,mirai"}
    from app import db
    db.session.commit()
    page = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in page and "rule-meta-badge--red" in page


ELASTIC_WITH_NOTE = '''[metadata]
maturity = "production"

[rule]
name = "Elastic rule with a guide"
severity = "low"
note = """## Triage and analysis

- Check the **user**
- <script>alert(1)</script>
"""
setup = "Enable the integration."
'''


def test_elastic_note_and_setup_are_kept_whole_as_markdown():
    from app.features.rule.rule_metadata_core import display_metadata, extract_rule_metadata
    extra = extract_rule_metadata("elastic", ELASTIC_WITH_NOTE)["extra"]
    assert extra["note"].startswith("## Triage and analysis\n\n- Check the **user**")     # line breaks kept
    shown = {f["key"]: f for f in display_metadata(extra)}
    assert shown["note"]["long"] and shown["note"]["label"] == "Investigation guide"
    assert shown["setup"]["long"] and not shown["severity"].get("long")


def test_elastic_guide_on_the_rule_page_is_collapsed_and_never_raw_html(clients, users):
    from app import db
    from tests_new.helpers.rules import make_rule
    rule = make_rule(users.owner, format="elastic", to_string=ELASTIC_WITH_NOTE)
    from app.features.rule.rule_metadata_core import apply_rule_metadata
    apply_rule_metadata(rule)
    db.session.commit()
    page = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}").get_data(as_text=True)
    assert '<details class="rule-meta-long"' in page and "Investigation guide" in page
    assert "<script>alert(1)</script>" not in page          # the text reaches the page as JSON, rendered sanitized


def test_tlp_and_pap_get_the_official_tlp_style():
    from app.features.rule.rule_metadata_core import display_metadata
    shown = {f["key"]: f for f in display_metadata({"tlp": "TLP:AMBER+STRICT", "pap": "green", "sharing": "TLP:CLEAR"})}
    assert shown["tlp"]["style"] == "tlp" and shown["tlp"]["styled"][0]["tone"] == "amber"
    assert shown["pap"]["style"] == "tlp" and shown["pap"]["styled"][0]["tone"] == "green"
    assert shown["sharing"]["styled"][0]["tone"] == "clear"


def test_platforms_get_their_logo_and_colour():
    from app.features.rule.rule_metadata_core import display_metadata
    shown = {f["key"]: f for f in display_metadata({"integration": "aws", "os": "Windows, Linux", "family": "mirai"})}
    assert shown["integration"]["styled"][0]["platform"]["label"] == "AWS"
    assert [v["platform"]["icon"] for v in shown["os"]["styled"]] == ["fa-brands fa-windows", "fa-brands fa-linux"]
    assert shown["family"]["styled"][0]["platform"] is None                      # not a platform: its own red badge


SPLUNK_RULE = '''name: Splunk detection
how_to_implement: You need Sysmon logs.
known_false_positives: Admins may run it.
tests:
- name: True Positive Test
  attack_data:
  - data: https://example.org/data.log
search: '| tstats count'
'''


def test_more_long_and_structured_fields_are_kept():
    from app.features.rule.rule_metadata_core import display_metadata, extract_rule_metadata
    extra = extract_rule_metadata("splunk", SPLUNK_RULE)["extra"]
    shown = {f["key"]: f for f in display_metadata(extra)}
    assert shown["how_to_implement"]["kind"] == "markdown" and shown["known_false_positives"]["long"]
    assert shown["tests"]["kind"] == "json" and '"True Positive Test"' in shown["tests"]["text"]
    sigma = extract_rule_metadata("sigma", "title: x\nlogsource:\n  product: windows\n  definition: 'Requirements: enable auditing'\n")["extra"]
    assert sigma["logsource_definition"] == "Requirements: enable auditing"
    atr = extract_rule_metadata("atr", "title: x\ndetection:\n  false_positives:\n  - one long reason\n  - another one\n")["extra"]
    assert atr["false_positives"] == "- one long reason\n- another one"        # a list becomes Markdown bullets


def test_rules_list_filters_by_platform_and_detail(clients, users):
    from app import db
    from tests_new.helpers.rules import make_rule
    win = make_rule(users.owner, format="sigma", to_string="title: a\nlogsource:\n  product: windows\n  service: sysmon\n")
    aws = make_rule(users.owner, format="elastic", to_string='[metadata]\nintegration = "aws"\n[rule]\nname = "x"\n')
    db.session.commit()
    assert win.platforms == "|Windows|Windows:Sysmon|" and aws.platforms == "|AWS|"
    ids = lambda q: {r["id"] for r in clients["anonymous"].get(f"/rule/data_table?{q}").json["items"]}   # noqa: E731
    assert ids("platforms=Windows") == {win.id}
    assert ids("platforms=Windows:Sysmon") == {win.id}
    assert ids("platforms=AWS,Windows") == {win.id, aws.id}
    item = clients["anonymous"].get("/rule/data_table?platforms=AWS").json["items"][0]
    assert item["platforms"][0]["label"] == "AWS" and item["platforms"][0]["icon"] == "fa-brands fa-aws"
    usage = {p["name"]: p for p in clients["anonymous"].get("/rule/get_rules_platforms_usage").json}
    assert usage["Windows"]["count"] == 1 and usage["Windows"]["details"][0]["name"] == "Windows:Sysmon"
    assert clients["anonymous"].get("/rule/data_table?platforms=%25").status_code == 200        # no wildcard injection


def test_simple_objects_become_fields_and_deep_ones_json():
    from app.features.rule.rule_metadata_core import display_metadata, extract_rule_metadata
    extra = extract_rule_metadata("atr", "title: x\nresponse:\n  actions: [alert, snapshot]\n"
                                         "deep:\n  a:\n    b: 1\n")["extra"]
    assert extra["response_actions"] == ["alert", "snapshot"]   # a list of values, no "[…]" text
    shown = {f["key"]: f for f in display_metadata(extra)}
    assert shown["response_actions"]["values"] == ["alert", "snapshot"]
    assert shown["deep"]["kind"] == "json"


def test_tags_name_the_platforms_without_being_shown():
    from app.features.rule.rule_metadata_core import detect_platforms, display_metadata, extract_rule_metadata
    kunai = extract_rule_metadata("kunai", "name: x\nmeta:\n  tags:\n  - os:linux\n  comments:\n  - c\n")["extra"]
    assert detect_platforms(kunai) == ["Linux"]
    assert [f["key"] for f in display_metadata(kunai)] == ["comments"]             # tags never shown twice
    elastic = extract_rule_metadata("elastic", '[rule]\nname = "x"\ntags = ["OS: Windows", "Data Source: AWS"]\n')["extra"]
    assert detect_platforms(elastic) == ["Windows", "AWS"]
