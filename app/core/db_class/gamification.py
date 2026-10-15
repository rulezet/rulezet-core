"""Points, levels and badges.
"""
from app import db
from sqlalchemy import event
from sqlalchemy.orm import attributes
from sqlalchemy.orm.attributes import PASSIVE_NO_INITIALIZE
import datetime


############################################
#    Gamification of users contribution    #
############################################

# --- Point Definitions (Used in Gamification Listener) ---
POINTS = {
    'suggestions_accepted': 100,
    'rules_owned': 10,
    'rules_liked_or_disliked': 1,
    'consecutive_days_active': 1,
    'rules_popular_score': 1,
    'bundles_owned': 15,
    'rule_tests_contributed': 1,
    'attack_mappings_contributed': 5,
}


# if you have more than 15000 points you will be level 3...
LEVEL_THRESHOLDS = {
    1: 0,
    2: 500,
    3: 15000,
    4: 30000,
    5: 50000,
    10: 150000,
    20: 300000,
    100: 1500000
}


class Gamification(db.Model):
    __tablename__ = "gamification"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete='CASCADE'), nullable=False) 

    # ----------------------------------------------------
    # 1. CORE SCORES AND RANKING
    # ----------------------------------------------------
    total_points = db.Column(db.Integer, default=0, index=True)
    current_level = db.Column(db.Integer, default=1)
    # addition of all the level points
    
    # ----------------------------------------------------
    # 2. CONTRIBUTION METRICS (RuleSuggestion)
    # ----------------------------------------------------
    suggestions_submitted = db.Column(db.Integer, default=0)
    suggestions_accepted = db.Column(db.Integer, default=0, index=True)
    suggestions_rejected = db.Column(db.Integer, default=0)
    
    # ----------------------------------------------------
    # 3. RULE IMPORTATION METRICS (Rule)
    # ----------------------------------------------------
    rules_owned = db.Column(db.Integer, default=0)
    rules_popular_score = db.Column(db.Integer, default=0)
    
    # ----------------------------------------------------
    # 4. COMMUNITY INTERACTION METRICS (RuleLike)
    # ----------------------------------------------------
    rules_liked = db.Column(db.Integer, default=0, index=True)
    rules_disliked = db.Column(db.Integer, default=0)

    # ----------------------------------------------------
    # 5. ACTIVITY / TIMING
    # ----------------------------------------------------
    last_contribution_date = db.Column(db.DateTime, nullable=True)
    consecutive_days_active = db.Column(db.Integer, default=0)

    # ----------------------------------------------------
    # 6. NEWER FEATURES (Bundle, RuleTest, RuleAttackAssociation)
    # ----------------------------------------------------
    bundles_owned = db.Column(db.Integer, default=0)
    rule_tests_contributed = db.Column(db.Integer, default=0)
    attack_mappings_contributed = db.Column(db.Integer, default=0)

    # ----------------------------------------------------
    # 7. RELATIONSHIP
    # ----------------------------------------------------

    user = db.relationship('User', backref=db.backref('gamification_stats', uselist=False, cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "user": self.user.to_json(),
            "total_points": self.total_points,
            "current_level": self.current_level,
            "suggestions_submitted": self.suggestions_submitted,
            "suggestions_accepted": self.suggestions_accepted,
            "suggestions_rejected": self.suggestions_rejected,
            "rules_owned": self.rules_owned,
            "rules_popular_score": self.rules_popular_score,
            "rules_liked": self.rules_liked,
            "rules_disliked": self.rules_disliked,
            "last_contribution_date": self.last_contribution_date,
            "consecutive_days_active": self.consecutive_days_active,
            "bundles_owned": self.bundles_owned,
            "rule_tests_contributed": self.rule_tests_contributed,
            "attack_mappings_contributed": self.attack_mappings_contributed,
            "global_rank": self.get_global_rank()
        }
    
    def get_global_rank(self):
        if self.total_points is None:
            return None
        
        try:
            rank = (
                db.session.query(Gamification)
                .filter(Gamification.total_points > self.total_points)
                .count()
            )
            return rank + 1
            
        except Exception as e:
            return None
    def calculate_total_points(self):
        score = 0
        score += self.suggestions_accepted * POINTS['suggestions_accepted']
        score += self.rules_owned * POINTS['rules_owned']
        score += self.rules_popular_score * POINTS['rules_popular_score']
        score += self.rules_liked * POINTS['rules_liked_or_disliked']
        score += (self.consecutive_days_active or 0) * POINTS['consecutive_days_active']
        score += (self.bundles_owned or 0) * POINTS['bundles_owned']
        score += (self.rule_tests_contributed or 0) * POINTS['rule_tests_contributed']
        score += (self.attack_mappings_contributed or 0) * POINTS['attack_mappings_contributed']
        return score

    def calculate_current_level(self, points):
        level = 1
        sorted_levels = sorted(LEVEL_THRESHOLDS.keys(), reverse=True)
        
        for lvl in sorted_levels:
            if points >= LEVEL_THRESHOLDS[lvl]:
                level = lvl
                break
        return level

    def update_scores(self):
        new_points = self.calculate_total_points()
        
        if self.total_points != new_points:
            self.total_points = new_points
            self.current_level = self.calculate_current_level(new_points)


def receive_before_flush(session, flush_context, instances):
    """
    Listener to check and update Gamification scores before a transaction is committed.
    """
    for instance in session.dirty:
        if isinstance(instance, Gamification):
            has_changed = False
            for field in ['suggestions_accepted', 'rules_owned', 'rules_liked', 'rules_popular_score', 'consecutive_days_active',
                          'bundles_owned', 'rule_tests_contributed', 'attack_mappings_contributed']:
                
               
                history = attributes.instance_state(instance).get_history(field, passive=PASSIVE_NO_INITIALIZE)

                
                if history.has_changes():
                    has_changed = True
                    break
            
            if has_changed:
                instance.update_scores()


event.listen(db.session, 'before_flush', receive_before_flush)


class UserBadge(db.Model):
    """One row per badge a user has actually unlocked. The badge catalog
    itself (name/description/icon/unlock rule) lives in code, not the DB —
    see app/features/account/badges.py — this table only records *events*
    (who unlocked what, and when), which is what lets the UI show a
    congratulations moment exactly once, the first time it becomes true,
    instead of recomputing the same badge list fresh on every page load."""
    __tablename__ = "user_badge"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id", ondelete='CASCADE'), nullable=False, index=True)
    badge_key  = db.Column(db.String(64), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    user = db.relationship('User', backref=db.backref('badges', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'badge_key', name='uq_user_badge_user_key'),
    )

    def to_json(self):
        return {
            "badge_key": self.badge_key,
            "unlocked_at": self.unlocked_at.strftime('%Y-%m-%d') if self.unlocked_at else None,
        }
