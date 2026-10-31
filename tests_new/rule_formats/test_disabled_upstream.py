"""Issue #62 — Suricata / Sagan rules commented out upstream but imported as active
(app/features/rule/disabled_upstream_core.py, job disabled_upstream_rules)."""
from app import db
from app.core.db_class.rule import Rule
from app.features.rule import disabled_upstream_core as D
from tests_new.helpers.rules import make_rule

ET_FILE = """# alert tcp any any -> any any (msg:"ET POLICY SSN Detected in Clear Text (dashed)"; sid:2001328; rev:5;)
alert tcp any any -> any any (msg:"ET MALWARE Something active"; sid:2009999; rev:1;)
# alert tcp any any -> any any (msg:"ET INFO Twice, enabled too"; sid:2008888; rev:1;)
alert tcp any any -> any any (msg:"ET INFO Twice, enabled too"; sid:2008888; rev:2;)
"""


def _suricata(owner, msg, sid, source="emerging-all.rules.zip"):
    return make_rule(owner, format="suricata", source=source, title=msg,
                     to_string=f'alert tcp any any -> any any (msg:"{msg}"; sid:{sid}; rev:1;)')


def test_reference_match_by_sid_and_msg_even_after_an_et_category_change(clients, users, monkeypatch):
    monkeypatch.setattr(D, "load_reference", lambda url: {sid: s["msgs"] for sid, s in D._states(ET_FILE).items()
                                                           if D._only_disabled(s)})
    ssn = _suricata(users.owner, "ET INFO SSN Detected in Clear Text (dashed)", 2001328)   # renamed INFO → POLICY since
    active = _suricata(users.owner, "ET MALWARE Something active", 2009999)
    both = _suricata(users.owner, "ET INFO Twice, enabled too", 2008888)                  # enabled in the file too
    reused = _suricata(users.owner, "My own rule", 2001328, source="community")           # same sid, other rule
    found = D.find_disabled_upstream(reference_urls=["ref"])
    assert found["reference"] == [ssn.id]
    assert active.id not in found["reference"] and both.id not in found["reference"] and reused.id not in found["reference"]


def test_git_rule_read_again_in_its_file(clients, users, monkeypatch, tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "et.rules").write_text(ET_FILE)
    from app.features.rule.rule_format.utils_format import utils_import_update
    monkeypatch.setattr(utils_import_update, "clone_or_access_repo", lambda *a, **k: (str(tmp_path), True))
    url = "https://github.com/example/et"
    off = make_rule(users.owner, format="suricata", source=url, github_path="rules/et.rules", title="ssn",
                    to_string='alert tcp any any -> any any (msg:"ET POLICY SSN Detected in Clear Text (dashed)"; sid:2001328; rev:5;)')
    on = make_rule(users.owner, format="suricata", source=url, github_path="rules/et.rules", title="on",
                   to_string='alert tcp any any -> any any (msg:"ET MALWARE Something active"; sid:2009999; rev:1;)')
    escape = make_rule(users.owner, format="suricata", source=url, github_path="../../etc/passwd", title="x",
                       to_string='alert tcp any any -> any any (msg:"x"; sid:1; rev:1;)')
    found = D.find_disabled_upstream(reference_urls=[])
    assert found["git"] == [off.id] and found["unreadable_files"] == 1      # a path leaving the clone is never read


def test_job_dry_run_then_trash(clients, users, monkeypatch):
    from app.core.db_class.job import BackgroundJob
    from app.features.jobs.job_handlers import handle_disabled_upstream_rules
    monkeypatch.setattr(D, "load_reference", lambda url: {2001328: {D._norm_msg("ET POLICY SSN Detected in Clear Text (dashed)")}})
    ssn = _suricata(users.owner, "ET INFO SSN Detected in Clear Text (dashed)", 2001328)
    for dry, gone in ((True, False), (False, True)):
        job = BackgroundJob(uuid=f"j{dry}", job_type="disabled_upstream_rules", status="running", total=0, done=0,
                            payload={"dry_run": dry, "reference_urls": ["ref"], "user_id": users.admin.id},
                            created_by=users.admin.id)
        db.session.add(job)
        db.session.commit()
        handle_disabled_upstream_rules(job, None)
        db.session.expire_all()
        assert db.session.get(Rule, ssn.id).is_deleted is gone
    rule = db.session.get(Rule, ssn.id)
    assert rule.delete_batch_uuid and rule.deleted_by_id == users.admin.id      # one batch, restorable together
