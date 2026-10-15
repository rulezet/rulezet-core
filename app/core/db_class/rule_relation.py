"""Typed links between two rules.
"""
from app import db
import datetime


# Manual relation types a user can pick when linking two rules by hand —
# auto-detected links (source='auto') instead use the format-specific kind
# that produced them (e.g. 'if_sid', 'correlation_hash') and aren't
# restricted to this list.
RULE_RELATION_TYPES = ['references', 'depends_on', 'related', 'variant_of', 'duplicate_of']


class RuleRelation(db.Model):
    """A curated, typed, directional edge between two rules — e.g. a
    Wazuh rule's <if_sid> pointing at another rule, two Kunai rules
    sharing a correlation hash, or a user manually noting that one rule
    is a variant of another. This is NOT RuleSimilarity/SimilarResult
    (a corpus-wide TF-IDF/FAISS content-similarity scan, fully
    automatic, no semantics beyond a fuzzy score) — the two systems are
    unrelated and both stay in place.

    source_rule_id -> target_rule_id is directional (A cites/references
    B); a rule's detail page shows both directions as separate outgoing/
    incoming sections rather than trying to store or display this
    symmetrically.
    """
    __tablename__ = 'rule_relation'

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid           = db.Column(db.String(36), unique=True, nullable=False, index=True)
    source_rule_id = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=False, index=True)
    target_rule_id = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=False, index=True)
    # Manual links: one of RULE_RELATION_TYPES ('references', 'depends_on',
    # 'related', 'variant_of', 'duplicate_of'). Auto-detected links: the
    # format-specific kind, e.g. 'if_sid' | 'if_group' | 'if_matched_sid' |
    # 'correlation_hash'.
    relation_type  = db.Column(db.String(32), nullable=False, default='references')
    # Raw evidence behind the link — the literal if_sid value, the shared
    # correlation hash, or a short free-text reason for a manual link.
    note           = db.Column(db.String(255), nullable=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)   # null = auto-detected
    source         = db.Column(db.String(20), default='manual')   # 'manual' | 'auto'
    added_at       = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    source_rule = db.relationship('Rule', foreign_keys=[source_rule_id],
                                   backref=db.backref('outgoing_relations', lazy='dynamic', cascade='all, delete-orphan'))
    target_rule = db.relationship('Rule', foreign_keys=[target_rule_id],
                                   backref=db.backref('incoming_relations', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('rule_relations_created', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('source_rule_id', 'target_rule_id', 'relation_type', name='uq_rule_relation_pair_type'),
        db.CheckConstraint('source_rule_id != target_rule_id', name='ck_rule_relation_no_self_link'),
    )

    def to_json(self, direction: str = 'outgoing'):
        """direction='outgoing' flattens target_rule's fields (this is a
        link FROM the rule you asked about); direction='incoming'
        flattens source_rule's fields (this is a link pointing AT the
        rule you asked about) — the caller always gets 'the other rule'
        under the same keys regardless of which side it queried from."""
        other = self.target_rule if direction == 'outgoing' else self.source_rule
        return {
            'id':            self.id,
            'uuid':          self.uuid,
            'relation_type': self.relation_type,
            'note':          self.note,
            'source':        self.source,
            'user_id':       self.user_id,
            'added_at':      self.added_at.strftime('%Y-%m-%d %H:%M') if self.added_at else None,
            'rule_id':       other.id if other else None,
            'rule_title':    other.title if other else None,
            'rule_format':   other.format if other else None,
            'rule_uuid':     other.uuid if other else None,
            'rule_is_deleted': other.is_deleted if other else True,
        }
