"""Imported tags — the rule author's own tags (GitHub issue #70).

Parsers for every format that carries tags, the automatic attach on new
rules, the `import_native_tags` re-parse job, and the admin-only routes of
the Bulk Field Parser's "Imported Tags" tab."""

import datetime
import uuid

import pytest

from app import db
from app.core.db_class.db import BackgroundJob, Rule, RuleTagAssociation, Tag, User
from app.features.tags.imported_tags_core import extract_native_tags, IMPORTED_SOURCE

ISSUE_EXAMPLE = """rule ExampleRule : malware ransomware windows
{
    meta:
        author = "Example"
        tags = "apt malware"

    condition:
        true
}"""


# ── Parsers ──────────────────────────────────────────────────────────────────

def test_issue_example_exactly():
    assert extract_native_tags("yara", ISSUE_EXAMPLE) == ["malware", "ransomware", "windows", "apt"]


@pytest.mark.parametrize("fmt,content,expected", [
    # YARA: several rules, private/global modifiers, `tag` singular, commas, case
    ("yara", 'private rule A : One Two { condition: true }\nglobal rule B { meta: tag = "three, one" condition: true }',
     ["one", "two", "three"]),
    # commented-out header / meta never count; strings don't either
    ("yara", 'rule A { meta: author = "x // rule Z : fake" \n // tags = "no"\n /* rule Y : nope { */ condition: true }', []),
    ("nova", 'rule A\n{\n meta:\n  tags = "prompt injection"\n keywords:\n  $a = "x"\n condition:\n  keywords.$a\n}',
     ["prompt", "injection"]),
    ("sigma", "title: t\ntags:\n  - attack.execution\n  - ATTACK.T1059\n  - attack.execution\nlogsource: {}\n",
     ["attack.execution", "attack.t1059"]),
    ("kunai", "name: x\nmeta:\n  tags:\n  - os:linux\n  - persistence\ncondition: true\n", ["os:linux", "persistence"]),
    ("elastic", '[rule]\nname = "x"\ntags = ["Domain: Endpoint", "OS: Linux"]\n', ["domain:endpoint", "os:linux"]),
    ("splunk", "name: x\ntags:\n  analytic_story:\n    - Ransomware\n    - Log4Shell\n  asset_type: Endpoint\n",
     ["ransomware", "log4shell"]),
    ("atr", "title: x\ntags:\n  category: prompt-injection\n  subcategory: persona\n  confidence: high\n",
     ["prompt-injection", "persona"]),
    ("crs", "SecRule ARGS \"@rx x\" \"id:1,tag:'attack-sqli',tag:'OWASP_CRS',pass\"", ["attack-sqli", "owasp_crs"]),
    ("suricata", 'alert http any any -> any any (msg:"x"; metadata:created_at 2024_01_01, tag Phishing, tag none; sid:1;)',
     ["phishing"]),
    ("nse", 'categories = {"discovery", "safe"}', ["discovery", "safe"]),
    ("wazuh", "<rule id='1'><group>authentication_failed,pci_dss_10.2.4,</group></rule>",
     ["authentication_failed", "pci_dss_10.2.4"]),
    ("kql", "// Tags: identity, brute force\nSigninLogs | take 1", ["identity", "brute force"]),
    # namespaced values stay ONE tag, whatever the spacing around the colon
    ("yara", 'rule A { meta: Tags = "exploit: cve-2017-11882" condition: true }', ["exploit:cve-2017-11882"]),
    ("yara", 'rule A { meta: tags = "Family: Rhadamanthys, apt malware" condition: true }',
     ["family:rhadamanthys", "apt", "malware"]),
    ("yara", 'rule A { meta: tags = "exploit :cve-1  exploit:cve-1 x:" condition: true }', ["exploit:cve-1"]),
    ("zeek", "event x() {}", []),
    ("sigma", "not: [valid", []),
])
def test_format_parsers(fmt, content, expected):
    assert extract_native_tags(fmt, content) == expected


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user(email):
    return User.query.filter_by(email=email).first()


def _rule(content, fmt="yara", owner=None):
    r = Rule(format=fmt, title=f"R {uuid.uuid4().hex[:6]}", license="MIT", description="d", uuid=str(uuid.uuid4()),
             source="test", author="a", version=1, user_id=(owner or _user("t@t.t")).id, to_string=content,
             creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
             last_modif=datetime.datetime.now(tz=datetime.timezone.utc), vote_up=0, vote_down=0)
    db.session.add(r)
    db.session.commit()
    return r


def _rule_tags(rule_id):
    db.session.expire_all()
    return {t.name: t for t in Tag.query.join(RuleTagAssociation, RuleTagAssociation.tag_id == Tag.id)
            .filter(RuleTagAssociation.rule_id == rule_id)}


def _run_job(payload, admin):
    from app.features.jobs.job_handlers import handle_import_native_tags
    job = BackgroundJob(uuid=str(uuid.uuid4()), created_by=admin.id, job_type="import_native_tags",
                        status="running", payload=payload)
    db.session.add(job)
    db.session.commit()
    handle_import_native_tags(job, None)
    db.session.refresh(job)
    return job


def _login(client, user):
    from flask import g
    with client.session_transaction() as s:
        s["_user_id"] = str(user.id)
        s["_fresh"] = True
    g.pop("_login_user", None)


# ── New rules get their tags automatically ──────────────────────────────────

def test_new_rule_gets_its_imported_tags(client, app):
    with app.app_context():
        resp = client.post("/api/rule/private/create", headers={"X-API-KEY": "api_key_user_rule"}, json={
            "title": "Issue 70", "format": "yara", "version": "1.0", "license": "MIT",
            "to_string": ISSUE_EXAMPLE})
        assert resp.status_code == 200, resp.get_json()
        rule = Rule.query.filter_by(title="Issue 70").first()
        tags = _rule_tags(rule.id)
        for name in ("malware", "ransomware", "windows", "apt"):
            t = tags[name]
            assert t.source == IMPORTED_SOURCE and t.visibility == "public" and t.is_active
            assert t.created_by == _user("t@t.t").id
        # default tags are still there
        assert "tlp:clear" in tags or not Tag.query.filter_by(name="tlp:clear").first()


# ── The re-parse job ─────────────────────────────────────────────────────────

def test_job_tags_existing_rules_and_is_idempotent(app):
    with app.app_context():
        admin = _user("admin@admin.admin")
        y = _rule(ISSUE_EXAMPLE)
        s = _rule("title: s\ntags:\n  - attack.t1059\n", fmt="sigma")
        other = _rule('alert http any any -> any any (msg:"x"; metadata: tag Phishing; sid:9;)', fmt="suricata")

        job = _run_job({"formats": ["yara", "sigma"], "rule_ids": "ALL"}, admin)
        assert job.status != "failed" and job.done == job.total
        assert set(_rule_tags(y.id)) >= {"malware", "ransomware", "windows", "apt"}
        assert "attack.t1059" in _rule_tags(s.id)
        assert _rule_tags(other.id) == {}                     # format not selected
        t = Tag.query.filter_by(name="ransomware").first()
        assert t.created_by == admin.id and t.source == IMPORTED_SOURCE and t.visibility == "public"

        count = RuleTagAssociation.query.count()
        _run_job({"formats": ["yara", "sigma"], "rule_ids": "ALL"}, admin)
        assert RuleTagAssociation.query.count() == count      # nothing added twice
        assert Tag.query.filter(Tag.name == "malware").count() == 1


def test_job_reuses_public_tags_and_never_attaches_private_ones(app):
    with app.app_context():
        admin, user = _user("admin@admin.admin"), _user("neo@admin.admin")
        manual = Tag(uuid=str(uuid.uuid4()), name="malware", source="Manual", visibility="public",
                     is_active=True, created_by=user.id)
        private = Tag(uuid=str(uuid.uuid4()), name="windows", source="Manual", visibility="private",
                      is_active=True, created_by=user.id)
        db.session.add_all([manual, private])
        db.session.commit()
        r = _rule(ISSUE_EXAMPLE)
        _run_job({"formats": ["yara"], "rule_ids": [r.id]}, admin)
        tags = _rule_tags(r.id)
        assert tags["malware"].id == manual.id                # reused, no duplicate
        assert "windows" not in tags                          # private tag never attached
        assert Tag.query.filter(Tag.name == "windows").count() == 1
        assert tags["ransomware"].source == IMPORTED_SOURCE


def test_job_without_formats_fails_cleanly(app):
    with app.app_context():
        job = _run_job({"formats": []}, _user("admin@admin.admin"))
        assert job.status == "failed"


# ── Admin routes ─────────────────────────────────────────────────────────────

def test_admin_routes_are_admin_only(client, app):
    with app.app_context():
        _login(client, _user("t@t.t"))
        assert client.post("/account/admin/bulk_parse_fields/imported_tags/preview",
                           json={"format": "yara", "content": ISSUE_EXAMPLE}).status_code == 403
        assert client.post("/account/admin/bulk_parse_fields/trigger_imported_tags",
                           json={"formats": ["yara"]}).status_code == 403
        assert BackgroundJob.query.filter_by(job_type="import_native_tags").count() == 0


def test_admin_preview_and_trigger(client, app):
    with app.app_context():
        _login(client, _user("admin@admin.admin"))
        data = client.post("/account/admin/bulk_parse_fields/imported_tags/preview",
                           json={"format": "yara", "content": ISSUE_EXAMPLE}).get_json()
        assert data["tags"] == ["malware", "ransomware", "windows", "apt"]
        assert client.post("/account/admin/bulk_parse_fields/imported_tags/preview",
                           json={"format": "zeek", "content": "x"}).status_code == 400

        url = "/account/admin/bulk_parse_fields/trigger_imported_tags"
        assert client.post(url, json={"formats": []}).status_code == 400
        assert client.post(url, json={"formats": ["nope"]}).status_code == 400
        assert client.post(url, json={"formats": ["yara"], "rule_ids": "some"}).status_code == 400
        resp = client.post(url, json={"formats": ["yara", "sigma"]})
        assert resp.status_code == 200 and resp.get_json()["job"]["uuid"]
        job = BackgroundJob.query.filter_by(job_type="import_native_tags").first()
        assert job.payload == {"formats": ["yara", "sigma"], "rule_ids": "ALL"}

        page = client.get("/account/admin/bulk_parse_fields")
        assert page.status_code == 200 and b"Imported Tags" in page.data


def test_rerunning_the_job_repairs_a_previous_bad_import(app):
    """An older parser split "exploit: cve-2017-11882" into "exploit:" and
    "cve-2017-11882" — re-running the job detaches what the content no
    longer yields and deletes the imported tags left unused."""
    with app.app_context():
        admin = _user("admin@admin.admin")
        r = _rule('rule A { meta: Tags = "exploit: cve-2017-11882" condition: true }')
        keep = _rule('rule B { meta: tags = "cve-2017-11882" condition: true }')      # really has that tag
        manual = Tag(uuid=str(uuid.uuid4()), name="curated", source="Manual", visibility="public",
                     is_active=True, created_by=admin.id)
        db.session.add(manual)
        db.session.flush()
        for name in ("exploit:", "cve-2017-11882"):
            t = Tag(uuid=str(uuid.uuid4()), name=name, source=IMPORTED_SOURCE, visibility="public",
                    is_active=True, created_by=admin.id)
            db.session.add(t)
            db.session.flush()
            db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=r.id, tag_id=t.id, user_id=admin.id))
            if name == "cve-2017-11882":
                db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=keep.id, tag_id=t.id, user_id=admin.id))
        db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=r.id, tag_id=manual.id, user_id=admin.id))
        db.session.commit()

        _run_job({"formats": ["yara"], "rule_ids": "ALL"}, admin)

        tags = _rule_tags(r.id)
        assert "exploit:cve-2017-11882" in tags
        assert "exploit:" not in tags and "cve-2017-11882" not in tags
        assert "curated" in tags                                   # a Manual tag is never detached
        assert Tag.query.filter_by(name="exploit:").first() is None    # orphan deleted
        assert "cve-2017-11882" in _rule_tags(keep.id)                 # still used elsewhere: kept
