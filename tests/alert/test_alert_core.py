"""
Tests for app/features/alert/alert_core.py — criteria validation, the
matching engine, the sweeper and the anti-spam protocol.
"""

import datetime
import uuid

import pytest

from app import db, mail
from app.core.db_class.db import (
    Alert, AlertEmailLog, AlertMatch, AttackTechnique, Bundle, InstanceConfig, Notification,
    Rule, RuleAttackAssociation, RuleTagAssociation, Tag, User,
)
from app.features.alert import alert_core as A


# ── helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx(app):
    """App context with an InstanceConfig row and mail configured."""
    app.config.update(MAIL_DEFAULT_SENDER='noreply@rulezet.test')
    with app.app_context():
        if not InstanceConfig.query.first():
            db.session.add(InstanceConfig(uuid=str(uuid.uuid4())))
            db.session.commit()
        yield app


def _users():
    return (User.query.filter_by(email="admin@admin.admin").first(),
            User.query.filter_by(email="t@t.t").first())


def _alert(user, criteria, name='Alert', targets=('rule',), events=('created',), email_mode='off',
           match_mode='any'):
    fields = A.validate_alert_payload({
        'name': name, 'targets': list(targets), 'events': list(events), 'criteria': criteria,
        'email_mode': email_mode, 'match_mode': match_mode,
    }, email_available=True)
    return A.create_alert(user.id, fields)


def _rule(owner, title='Rule', cve='[]', fmt='yara', source='manual', content='rule x { condition: true }'):
    now = datetime.datetime.utcnow()
    rule = Rule(format=fmt, title=title, license='MIT', description='d', uuid=str(uuid.uuid4()),
                source=source, author='x', version='1', user_id=owner.id, to_string=content, cve_id=cve,
                creation_date=now, last_modif=now, status='draft')
    db.session.add(rule)
    db.session.commit()
    return rule


def _bundle(owner, name='Bundle', public=True, vulns='[]'):
    bundle = Bundle(uuid=str(uuid.uuid4()), name=name, description='', user_id=owner.id, access=public,
                    created_at=datetime.datetime.utcnow(), vulnerability_identifiers=vulns)
    db.session.add(bundle)
    db.session.commit()
    return bundle


def _tag(rule, name, user):
    tag = Tag.query.filter_by(name=name).first()
    if not tag:
        tag = Tag(uuid=str(uuid.uuid4()), name=name, created_by=user.id)
        db.session.add(tag)
        db.session.commit()
    db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=rule.id, tag_id=tag.id, user_id=user.id))
    db.session.commit()


def _attack(rule, technique_id):
    if not AttackTechnique.query.filter_by(technique_id=technique_id).first():
        db.session.add(AttackTechnique(technique_id=technique_id, name=technique_id))
        db.session.commit()
    db.session.add(RuleAttackAssociation(uuid=str(uuid.uuid4()), rule_id=rule.id, technique_id=technique_id))
    db.session.commit()


def _matched_titles(alert):
    return sorted(Rule.query.get(m.object_id).title for m in
                  AlertMatch.query.filter_by(alert_id=alert.id, object_type='rule').all())


# ── validation ───────────────────────────────────────────────────────────────

def test_validation_rejects_empty_and_invalid(ctx):
    with pytest.raises(A.AlertError):
        A.validate_alert_payload({'name': 'x', 'targets': ['rule'], 'events': ['created'], 'criteria': {}}, True)
    with pytest.raises(A.AlertError):
        A.normalize_criteria({'attacks': ['NOT-A-TECHNIQUE']})
    with pytest.raises(A.AlertError):
        A.normalize_criteria({'keywords': ['ab']})
    with pytest.raises(A.AlertError):
        A.validate_alert_payload({'name': 'x', 'targets': ['rule'], 'events': ['created'],
                                  'criteria': {'keywords': ['abc']}, 'notify_in_app': False}, True)


def test_normalisation(ctx):
    c = A.normalize_criteria({'cves': ['cve-2026-1', 'CVE-2026-1'], 'tags': ['Ransomware'],
                              'github_repos': ['https://github.com/Elastic/Detection-Rules.git']})
    assert c['cves'] == ['CVE-2026-1']
    assert c['tags'] == ['ransomware']
    assert c['github_repos'] == ['elastic/detection-rules']


def test_any_switch_supersedes_its_list(ctx):
    c = A.normalize_criteria({'cves': ['CVE-2026-1'], 'cve_any': True, 'attacks': ['T1190'], 'attack_any': True})
    assert c['cves'] == [] and c['cve_any'] is True
    assert c['attacks'] == [] and c['attack_any'] is True


def test_email_mode_kept_when_email_unavailable(ctx):
    fields = A.validate_alert_payload({'name': 'x', 'targets': ['rule'], 'events': ['created'],
                                       'criteria': {'keywords': ['abc']}, 'email_mode': 'off'},
                                      email_available=False, current_email_mode='daily')
    assert fields['email_mode'] == 'daily'


# ── matching engine / sweep ─────────────────────────────────────────────────

def test_sweep_matches_new_content_only_after_first_pass(ctx):
    me, other = _users()
    _rule(other, 'Old netscaler rule')          # exists before the alert: never alerted
    alert = _alert(me, {'keywords': ['netscaler']})
    A.run_sweep()
    _rule(other, 'New netscaler rule')
    _rule(other, 'Unrelated')
    A.run_sweep()
    assert _matched_titles(alert) == ['New netscaler rule']


def test_never_alerts_about_own_content(ctx):
    me, other = _users()
    alert = _alert(me, {'keywords': ['netscaler']})
    A.run_sweep()
    _rule(me, 'My netscaler rule')
    A.run_sweep()
    assert AlertMatch.query.filter_by(alert_id=alert.id).count() == 0


def test_private_bundles_never_match(ctx):
    me, other = _users()
    alert = _alert(me, {'keywords': ['netscaler']}, targets=('bundle',))
    A.run_sweep()
    _bundle(other, 'NetScaler private pack', public=False)
    public = _bundle(other, 'NetScaler public pack', public=True)
    A.run_sweep()
    assert [m.object_id for m in AlertMatch.query.filter_by(alert_id=alert.id).all()] == [public.id]


def test_sweep_is_idempotent(ctx):
    me, other = _users()
    alert = _alert(me, {'keywords': ['netscaler']})
    A.run_sweep()
    _rule(other, 'netscaler')
    A.run_sweep()
    A.run_sweep()
    assert AlertMatch.query.filter_by(alert_id=alert.id).count() == 1


def test_updates_only_count_real_edits(ctx):
    me, other = _users()
    alert = _alert(me, {'keywords': ['netscaler']}, events=('updated',))
    rule = _rule(other, 'netscaler')
    A.run_sweep()
    A.run_sweep()   # freshly created, never edited: not an update
    assert AlertMatch.query.filter_by(alert_id=alert.id).count() == 0
    rule.last_modif = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)
    db.session.commit()
    A.run_sweep()
    assert AlertMatch.query.filter_by(alert_id=alert.id, event='updated').count() == 1


def test_criteria_kinds(ctx):
    me, other = _users()
    by_cve = _alert(me, {'cves': ['CVE-2026-1']}, name='cve')
    by_tag = _alert(me, {'tags': ['ransomware']}, name='tag')
    by_attack = _alert(me, {'attacks': ['T1059']}, name='attack')   # also covers sub-techniques
    by_format = _alert(me, {'formats': ['sigma']}, name='format')
    by_user = _alert(me, {'users': [other.id]}, name='user')
    by_repo = _alert(me, {'github_repos': ['elastic/detection-rules']}, name='repo')
    A.run_sweep()

    r_cve = _rule(other, 'cve rule', cve='["CVE-2026-1"]')
    r_tag = _rule(other, 'tag rule'); _tag(r_tag, 'ransomware', other)
    r_att = _rule(other, 'attack rule'); _attack(r_att, 'T1059.001')
    _rule(other, 'sigma rule', fmt='sigma')
    _rule(other, 'repo rule', source='https://github.com/elastic/detection-rules/tree/main/x')
    A.run_sweep()

    assert _matched_titles(by_cve) == ['cve rule']
    assert _matched_titles(by_tag) == ['tag rule']
    assert _matched_titles(by_attack) == ['attack rule']
    assert _matched_titles(by_format) == ['sigma rule']
    assert len(_matched_titles(by_user)) == 5
    assert _matched_titles(by_repo) == ['repo rule']
    match = AlertMatch.query.filter_by(alert_id=by_attack.id).one()
    assert match.matched_on == ['attack:T1059.001']


def test_any_flags(ctx):
    me, other = _users()
    any_cve = _alert(me, {'cve_any': True}, name='any cve')
    any_tag = _alert(me, {'tag_any': True}, name='any tag')
    any_attack = _alert(me, {'attack_any': True}, name='any attack')
    A.run_sweep()
    _rule(other, 'with cve', cve='["CVE-2026-9"]')
    _rule(other, 'empty cve', cve='[]')
    marked = _rule(other, 'marked only'); _tag(marked, 'tlp:clear', other)
    tagged = _rule(other, 'tagged'); _tag(tagged, 'apt29', other)
    mapped = _rule(other, 'mapped'); _attack(mapped, 'T1190')
    A.run_sweep()
    assert _matched_titles(any_cve) == ['with cve']
    assert _matched_titles(any_tag) == ['tagged']          # tlp:/pap: markings don't count
    assert _matched_titles(any_attack) == ['mapped']


def test_match_mode_all(ctx):
    me, other = _users()
    alert = _alert(me, {'cves': ['CVE-2026-1'], 'keywords': ['netscaler']}, match_mode='all')
    A.run_sweep()
    _rule(other, 'netscaler without cve')
    _rule(other, 'netscaler with cve', cve='["CVE-2026-1"]')
    A.run_sweep()
    assert _matched_titles(alert) == ['netscaler with cve']


def test_preview_excludes_own_content(ctx):
    me, other = _users()
    _rule(other, 'netscaler theirs')
    _rule(me, 'netscaler mine')
    out = A.preview({'keywords': ['netscaler']}, 'any', ['rule'], user_id=me.id)
    assert out['rules'] == 1


# ── anti-spam protocol ──────────────────────────────────────────────────────

def test_one_notification_per_alert_per_pass(ctx):
    me, other = _users()
    _alert(me, {'keywords': ['netscaler']})
    A.run_sweep()
    for i in range(5):
        _rule(other, f'netscaler {i}')
    A.run_sweep()
    notifs = Notification.query.filter_by(user_id=me.id, notif_type='alert_match').all()
    assert len(notifs) == 1 and '5 rules' in notifs[0].title


def test_notifications_collapse_when_many_alerts_fire(ctx):
    me, other = _users()
    for i in range(ctx.config['ALERT_NOTIF_COLLAPSE'] + 1):
        _alert(me, {'keywords': ['netscaler']}, name=f'alert {i}')
    A.run_sweep()
    _rule(other, 'netscaler')
    A.run_sweep()
    notifs = Notification.query.filter_by(user_id=me.id, notif_type='alert_match').all()
    assert len(notifs) == 1 and notifs[0].title.startswith(f"{ctx.config['ALERT_NOTIF_COLLAPSE'] + 1} of your alerts")


def test_per_pass_cap_stores_at_most_n_but_counts_everything(ctx):
    ctx.config['ALERT_MAX_MATCHES_PER_PASS'] = 3
    me, other = _users()
    alert = _alert(me, {'keywords': ['netscaler']})
    A.run_sweep()
    for i in range(7):
        _rule(other, f'netscaler {i}')
    A.run_sweep()
    db.session.refresh(alert)
    assert AlertMatch.query.filter_by(alert_id=alert.id).count() == 3
    assert alert.match_count == 7


def test_email_lists_at_most_ten_items(ctx):
    me, other = _users()
    _alert(me, {'keywords': ['netscaler']}, email_mode='instant')
    A.run_sweep()
    for i in range(15):
        _rule(other, f'netscaler {i}')
    with mail.record_messages() as outbox:
        A.run_sweep()
    assert len(outbox) == 1
    assert outbox[0].html.count('/rule/detail_rule/') == A.EMAIL_MAX_ITEMS
    assert '15 new matches' in outbox[0].subject
    assert AlertMatch.query.filter(AlertMatch.emailed_at.is_(None)).count() == 0


def test_user_daily_email_quota_holds_matches(ctx):
    ctx.config['ALERT_EMAILS_PER_USER_PER_DAY'] = 2
    me, other = _users()
    alert = _alert(me, {'keywords': ['netscaler']}, email_mode='instant')
    A.run_sweep()
    sent = 0
    for i in range(4):
        if alert.last_emailed_at:   # skip the 15 min instant cooldown
            alert.last_emailed_at -= datetime.timedelta(minutes=16)
            db.session.commit()
        _rule(other, f'netscaler {i}')
        with mail.record_messages() as outbox:
            A.run_sweep()
            sent += len(outbox)
    assert sent == 2
    assert AlertMatch.query.filter(AlertMatch.emailed_at.is_(None)).count() == 2   # held, not lost


def test_instance_email_budget(ctx):
    ctx.config['ALERT_EMAILS_PER_HOUR'] = 1
    me, other = _users()
    neo = User.query.filter_by(email="neo@admin.admin").first()
    _alert(me, {'keywords': ['netscaler']}, email_mode='instant')
    _alert(neo, {'keywords': ['netscaler']}, email_mode='instant')
    A.run_sweep()
    _rule(other, 'netscaler')
    with mail.record_messages() as outbox:
        A.run_sweep()
    assert len(outbox) == 1
    assert A.email_budget()['remaining'] == 0


def test_smtp_failure_stops_the_pass(ctx, monkeypatch):
    me, other = _users()
    _alert(me, {'keywords': ['netscaler']}, email_mode='instant')
    A.run_sweep()
    _rule(other, 'netscaler')

    def boom(msg):
        raise ConnectionError('SMTP down')
    monkeypatch.setattr(mail, 'send', boom)
    assert A.run_sweep()['emails_sent'] == 0
    assert AlertEmailLog.query.count() == 0
    assert AlertMatch.query.filter(AlertMatch.emailed_at.is_(None)).count() == 1   # retried next pass


def test_no_email_when_email_disabled(ctx):
    me, other = _users()
    _alert(me, {'keywords': ['netscaler']}, email_mode='instant')
    InstanceConfig.query.first().email_enabled = False
    db.session.commit()
    A.run_sweep()
    _rule(other, 'netscaler')
    with mail.record_messages() as outbox:
        A.run_sweep()
    assert outbox == []


def test_retention_purges_old_matches(ctx):
    me, other = _users()
    alert = _alert(me, {'keywords': ['netscaler']})
    db.session.add(AlertMatch(alert_id=alert.id, object_type='rule', object_id=999999, event='created',
                              created_at=datetime.datetime.utcnow() - datetime.timedelta(days=200)))
    db.session.commit()
    assert A.run_sweep()['pruned'] == 1


def test_unsubscribe_token_roundtrip(ctx):
    me, _ = _users()
    alert = _alert(me, {'keywords': ['netscaler']}, email_mode='daily')
    assert A.read_unsubscribe_token(A.make_unsubscribe_token(alert)) == alert.uuid
    assert A.read_unsubscribe_token('forged') is None


# ── activity logs ────────────────────────────────────────────────────────────

def _actions():
    from app.core.db_class.db import ActivityLog
    return [l.action for l in ActivityLog.query.filter(ActivityLog.action.like('alert.%')).all()]


def test_idle_pass_logs_nothing(ctx):
    me, _ = _users()
    _alert(me, {'keywords': ['netscaler']})
    A.run_sweep()
    A.run_sweep()
    assert _actions() == []


def test_pass_with_matches_and_email_is_logged(ctx):
    from app.core.db_class.db import ActivityLog
    me, other = _users()
    alert = _alert(me, {'keywords': ['netscaler']}, email_mode='instant')
    A.run_sweep()
    _rule(other, 'netscaler')
    A.run_sweep()
    actions = _actions()
    assert actions.count('alert.triggered') == 1
    assert actions.count('alert.email_sent') == 1
    assert actions.count('alert.sweep') == 1
    triggered = ActivityLog.query.filter_by(action='alert.triggered').one()
    assert triggered.user_id == me.id and triggered.target_id == alert.id and triggered.is_public is False
    assert ActivityLog.query.filter_by(action='alert.email_sent').one().user_id == me.id


def test_smtp_failure_is_logged_as_error(ctx, monkeypatch):
    from app.core.db_class.db import ActivityLog
    me, other = _users()
    _alert(me, {'keywords': ['netscaler']}, email_mode='instant')
    A.run_sweep()
    _rule(other, 'netscaler')
    monkeypatch.setattr(mail, 'send', lambda msg: (_ for _ in ()).throw(ConnectionError('SMTP down')))
    A.run_sweep()
    failed = ActivityLog.query.filter_by(action='alert.email_failed').one()
    assert failed.level == 'error'
    assert ActivityLog.query.filter_by(action='alert.sweep').one().level == 'warning'
