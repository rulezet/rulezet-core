"""
"Has CVE / tags / license / ATT&CK" filters — rule_core.apply_presence_filters,
shared by /rule/data_table (RuleList toggles) and the background jobs'
_build_rule_query ("select all matching").
"""

import uuid

from app import db
from app.core.db_class.db import AttackTechnique, Rule, RuleAttackAssociation, RuleTagAssociation, Tag, User
from app.features.jobs.job_handlers import _build_rule_query


def _rule(title, user_id, **fields):
    rule = Rule(format="yara", title=title, license=fields.pop('license', 'Unknown'), description="d",
                uuid=str(uuid.uuid4()), source="test", author="test", version=1,
                user_id=user_id, to_string="rule t { condition: true }", **fields)
    db.session.add(rule)
    db.session.commit()
    return rule


def _tag(rule, name, user_id):
    tag = Tag.query.filter_by(name=name).first()
    if not tag:
        tag = Tag(name=name, uuid=str(uuid.uuid4()), created_by=user_id)
        db.session.add(tag)
        db.session.commit()
    db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=rule.id, tag_id=tag.id, user_id=user_id))
    db.session.commit()


def _ids(query):
    return {r.id for r in query.all()}


def _setup(app):
    with app.app_context():
        admin = User.query.filter_by(email="admin@admin.admin").first()
        plain = _rule("plain", admin.id, cve_id='[]')
        _tag(plain, 'tlp:clear', admin.id)  # default marking — must not count as "has tags"
        cve = _rule("cve", admin.id, cve_id='["CVE-2026-1"]')
        tagged = _rule("tagged", admin.id)
        _tag(tagged, 'ransomware', admin.id)
        licensed = _rule("licensed", admin.id, license='MIT')
        attack = _rule("attack", admin.id)
        if not AttackTechnique.query.filter_by(technique_id='T1190').first():
            db.session.add(AttackTechnique(technique_id='T1190', name='Exploit Public-Facing Application'))
            db.session.commit()
        db.session.add(RuleAttackAssociation(uuid=str(uuid.uuid4()), rule_id=attack.id, technique_id='T1190'))
        db.session.commit()
        return {k: v.id for k, v in dict(plain=plain, cve=cve, tagged=tagged,
                                         licensed=licensed, attack=attack).items()}


def test_job_query_presence_filters(app):
    ids = _setup(app)
    with app.app_context():
        assert ids['cve'] in _ids(_build_rule_query({'has_cve': True}))
        assert ids['plain'] not in _ids(_build_rule_query({'has_cve': True}))

        tagged = _ids(_build_rule_query({'has_tags': True}))
        assert ids['tagged'] in tagged
        assert ids['plain'] not in tagged

        licensed = _ids(_build_rule_query({'has_license': True}))
        assert ids['licensed'] in licensed
        assert ids['plain'] not in licensed

        attack = _ids(_build_rule_query({'has_attack': True}))
        assert attack & set(ids.values()) == {ids['attack']}


def test_data_table_presence_filters(app, client):
    ids = _setup(app)
    for flag, expected in (('has_cve', 'cve'), ('has_tags', 'tagged'),
                           ('has_license', 'licensed'), ('has_attack', 'attack')):
        res = client.get(f'/rule/data_table?{flag}=true&per_page=100')
        assert res.status_code == 200, flag
        returned = {r['id'] for r in res.get_json()['items']}
        assert ids[expected] in returned, flag
        assert ids['plain'] not in returned, flag
