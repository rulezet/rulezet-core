"""Edit proposals on a rule, their discussion and contributors.
"""
from app import db
import datetime


    

class RuleEditProposal(db.Model):
    __tablename__ = 'rule_edit_proposal'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    proposed_content = db.Column(db.Text, nullable=False)
    old_content = db.Column(db.Text) 
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    status = db.Column(db.String(20), default="pending") # pending, accepted, rejected, superseded

    edit_type = db.Column(db.String(50), nullable=True) # ex: 'typo', 'content_update', 'legal'
    change_score = db.Column(db.Float, nullable=True)   # (0-100)
    
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)   # the reviewer's note — on a rejection or an acceptance

    # Set when this proposal continues a prior one. The prior proposal stays
    # fully independent and decidable — it is never auto-closed by this link.
    previous_proposal_id = db.Column(db.Integer, db.ForeignKey('rule_edit_proposal.id'), nullable=True)

    # Relations
    rule = db.relationship('Rule', backref=db.backref('edit_proposals', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('proposed_edits', lazy='dynamic', cascade='all, delete-orphan'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by_id])
    previous_proposal = db.relationship('RuleEditProposal', remote_side=[id],
                                         backref=db.backref('revisions', lazy='dynamic'))

    def get_rule_title(self):
        rule_obj = Rule.query.get(self.rule_id)  
        return rule_obj.title if rule_obj else None


    def _revision_link(self, proposal):
        if not proposal:
            return None
        return {
            'id': proposal.id, 'status': proposal.status,
            'discuss_url': f"/rule/proposal_content_discuss?id={proposal.id}",
            'user_id': proposal.user_id,
            'user_name': f"{proposal.user.first_name} {proposal.user.last_name}" if proposal.user else "Unknown",
            'user_avatar': proposal.user.get_avatar_url() if proposal.user else None,
        }

    def to_json(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': self.get_rule_title(),
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}" if self.user else "Unknown",
            'user_avatar': self.user.get_avatar_url() if self.user else None,
            'proposed_content': self.proposed_content,
            'old_content': self.old_content,
            'message': self.message,
            'status': self.status,
            'edit_type': self.edit_type,
            'change_score': self.change_score,
            'comment_count': UnifiedComment.query.filter_by(
                object_type='proposal', object_id=self.id, is_active=True
            ).count(),
            'timestamp': self.timestamp.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by_id': self.reviewed_by_id,
            'reviewed_by_name': f"{self.reviewer.first_name} {self.reviewer.last_name}" if self.reviewer else None,
            'reviewed_by_avatar': self.reviewer.get_avatar_url() if self.reviewer else None,
            'rejection_reason': self.rejection_reason,
            'decision_reason': self.rejection_reason,
            'previous_proposal_id': self.previous_proposal_id,
            'previous_proposal': self._revision_link(self.previous_proposal),
            'revisions': [self._revision_link(r) for r in self.revisions.order_by(RuleEditProposal.timestamp.asc())],
            'comments': [comment.to_json() for comment in self.comments.order_by(RuleEditComment.created_at.asc())] if hasattr(self, 'comments') else []
        }
    def to_json_for_discuss(self):
        rule_obj = Rule.query.get(self.rule_id)

        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': rule_obj.title if rule_obj else "Unknown Rule",
            'rule_format': rule_obj.format if rule_obj else "N/A",
            'status': self.status,
            'edit_type': self.edit_type or 'general',
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M'),
            'change_score': self.change_score,
            'message': self.message,
            'discuss_url': f"/rule/proposal_content_discuss?id={self.id}",
            'status_color': {
                'pending': 'warning',
                'accepted': 'success',
                'approved': 'success',
                'rejected': 'danger',
                'superseded': 'secondary',
            }.get(self.status, 'secondary')
        }


class RuleEditComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('rule_edit_proposal.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    proposal = db.relationship('RuleEditProposal', backref=db.backref('comments', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User')

    def to_json(self):
        return {
            'id': self.id,
            'proposal_id': self.proposal_id,
            'user_id': self.user_id,
            'user_name': self.user.first_name if self.user else None,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }


class RuleEditContribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Nullable: set when the contribution comes from an accepted edit proposal;
    # NULL for a direct credit (admin/non-owner editing the rule, or the
    # previous owner after an ownership transfer) with no proposal involved.
    proposal_id = db.Column(db.Integer, db.ForeignKey('rule_edit_proposal.id'), nullable=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    user = db.relationship('User', backref=db.backref('contributions', lazy='dynamic', cascade='all, delete-orphan'))
    proposal = db.relationship('RuleEditProposal', backref=db.backref('contributors', lazy='dynamic', cascade='all, delete-orphan'))
    rule = db.relationship('Rule', backref=db.backref('RULE_proposals', lazy='dynamic',  cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.first_name if self.user else None,
            "proposal_id": self.proposal_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule.title if self.rule else None,
            'created_at': self.created_at.isoformat(),
            "user_name": self.user.first_name if self.user else None,
            "user_avatar": self.user.get_avatar_url() if self.user else None,
        }


# Imported last: these models are only used inside methods, and importing them
# at the top would be circular.
from app.core.db_class.comment import UnifiedComment  # noqa: E402
from app.core.db_class.rule import Rule  # noqa: E402
