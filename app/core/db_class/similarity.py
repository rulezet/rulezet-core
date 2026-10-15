"""Rule similarity scans and their results.
"""
from app import db
from sqlalchemy import func


#####################
#   Similar Rule    #
#####################

class SimilarResult(db.Model):
    """Stores the summary/history of a similarity computation task."""
    __tablename__ = "similar_result"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, unique=True)
    info = db.Column(db.String)  # Description or parameters used
    date = db.Column(db.DateTime, index=True, default=func.now())
    
    # 'global' for all rules, 'specific' for a subset/single rule
    mode = db.Column(db.String(20), nullable=False) 
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete='CASCADE'), nullable=False)

    total_rules_processed = db.Column(db.Integer, default=0)
    similar_pairs_found = db.Column(db.Integer, default=0)
    similar_pairs_skipped = db.Column(db.Integer, default=0)  # already existed — left as-is
    time_taken = db.Column(db.Integer, default=0) # in seconds

    def to_json(self):
        return {
            "uuid": self.uuid,
            "info": self.info,
            "date": self.date.isoformat() if self.date else None,
            "mode": self.mode,
            "user_id": self.user_id,
            "total_rules_processed": self.total_rules_processed,
            "similar_pairs_found": self.similar_pairs_found,
            "similar_pairs_skipped": self.similar_pairs_skipped,
            "time_taken": self.time_taken
        }


class RuleSimilarity(db.Model):
    """
    Association table storing the similarity score between two rules.
    We only store the Top 50 per rule.
    """
    __tablename__ = "rule_similarity"
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey("rule.id", ondelete='CASCADE'), index=True)
    similar_rule_id = db.Column(db.Integer, db.ForeignKey("rule.id", ondelete='CASCADE'), index=True)
    
    # score between 0.0 and 1.0
    score = db.Column(db.Float, index=True) 
    
    # Reference to which scan produced this result
    result_uuid = db.Column(db.String(36), db.ForeignKey("similar_result.uuid"))

    # Ensure we don't store duplicates for the same pair in the same scan
    __table_args__ = (db.UniqueConstraint('rule_id', 'similar_rule_id', name='_rule_pair_uc'),)

    def to_json(self):
        return {
            "rule_id": self.rule_id,
            "similar_rule_id": self.similar_rule_id,
            "score": self.score
        }
