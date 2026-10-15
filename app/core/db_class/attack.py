"""MITRE ATT&CK techniques and their links to rules.
"""
from app import db
import datetime


# ─────────────────────────────────────────────────────────────────────────────
#  MITRE ATT&CK
# ─────────────────────────────────────────────────────────────────────────────

class AttackTechnique(db.Model):
    __tablename__ = 'attack_technique'

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    technique_id        = db.Column(db.String(20), unique=True, nullable=False, index=True)  # T1059 / T1059.001
    name                = db.Column(db.String(300), nullable=False)
    tactic_keys         = db.Column(db.JSON, nullable=True)   # ["execution", "defense-evasion"]
    description         = db.Column(db.Text, nullable=True)
    url                 = db.Column(db.String(500), nullable=True)
    is_subtechnique     = db.Column(db.Boolean, default=False)
    parent_technique_id = db.Column(db.String(20), nullable=True)   # T1059 for T1059.001
    deprecated          = db.Column(db.Boolean, default=False)
    updated_at          = db.Column(db.DateTime, nullable=True)

    def to_json(self):
        return {
            'id':                  self.id,
            'technique_id':        self.technique_id,
            'name':                self.name,
            'tactic_keys':         self.tactic_keys or [],
            'description':         self.description,
            'url':                 self.url,
            'is_subtechnique':     self.is_subtechnique,
            'parent_technique_id': self.parent_technique_id,
            'deprecated':          self.deprecated,
            'updated_at':          self.updated_at.isoformat() if self.updated_at else None,
        }


class RuleAttackAssociation(db.Model):
    __tablename__ = 'rule_attack_association'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    rule_id     = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    technique_id = db.Column(db.String(20), db.ForeignKey('attack_technique.technique_id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)   # null = auto-parsed
    added_at    = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))
    source      = db.Column(db.String(20), default='manual')   # 'manual' | 'auto'

    rule      = db.relationship('Rule', backref=db.backref('attack_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    technique = db.relationship('AttackTechnique', backref=db.backref('rule_assocs', lazy='dynamic'))
    user      = db.relationship('User', backref=db.backref('user_attack_assocs', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('rule_id', 'technique_id', name='uq_rule_attack_technique'),
    )

    def to_json(self):
        t = self.technique
        return {
            'id':           self.id,
            'uuid':         self.uuid,
            'rule_id':      self.rule_id,
            'technique_id': self.technique_id,
            'name':         t.name if t else None,
            'tactic_keys':  t.tactic_keys if t else [],
            'url':          t.url if t else None,
            'is_subtechnique': t.is_subtechnique if t else False,
            'parent_technique_id': t.parent_technique_id if t else None,
            'user_id':      self.user_id,
            'added_at':     self.added_at.strftime('%Y-%m-%d %H:%M') if self.added_at else None,
            'source':       self.source,
        }
