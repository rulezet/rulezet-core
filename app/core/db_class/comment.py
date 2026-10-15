"""Comments and reactions on rules and bundles (legacy tables and the unified comment_v2).
"""
from app import db
import datetime
import uuid as _uuid_mod


class Comment(db.Model):
    """Model for user comments on rules."""

    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid     = db.Column(db.String(36), unique=True, nullable=True, index=True)
    rule_id  = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    user_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_name = db.Column(db.Text, nullable=False)
    content  = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, index=True)
    updated_at = db.Column(db.DateTime, index=True)
    likes    = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)

    user = db.relationship('User', backref=db.backref('comments_user', lazy='dynamic', cascade='all, delete-orphan'))
    rule = db.relationship('Rule', backref=db.backref('comments_rule', lazy='dynamic', cascade='all, delete-orphan'))
    parent_comment = db.relationship('Comment', remote_side=[id],
                                     backref=db.backref('replies', lazy='dynamic', cascade='all, delete-orphan'))

    def _get_reactions(self):
        from app.core.db_class.comment import RuleCommentReaction
        return RuleCommentReaction.query.filter_by(comment_id=self.id).all()

    def to_json(self, user_id=None, include_replies=True):
        reactions_raw = self._get_reactions()
        non_vote = [r.to_json() for r in reactions_raw if r.reaction_type not in ('like', 'dislike')]
        user_has_liked    = any(r.user_id == user_id and r.reaction_type == 'like'    for r in reactions_raw) if user_id else False
        user_has_disliked = any(r.user_id == user_id and r.reaction_type == 'dislike' for r in reactions_raw) if user_id else False
        data = {
            "id":               self.id,
            "uuid":             self.uuid,
            "rule_id":          self.rule_id,
            "user_id":          self.user_id,
            "user_name":        self.user_name,
            "content":          self.content,
            "created_at":       self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            "updated_at":       self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
            "likes":            self.likes,
            "dislikes":         self.dislikes,
            "is_admin":         self.user.is_admin() if self.user else False,
            "parent_comment_id": self.parent_comment_id,
            "reactions":        non_vote,
            "user_has_liked":   user_has_liked,
            "user_has_disliked": user_has_disliked,
        }
        if include_replies:
            data["replies"] = [r.to_json(user_id=user_id, include_replies=True)
                               for r in self.replies.order_by('id').all()]
        return data


class RuleCommentReaction(db.Model):
    """Like / dislike / emoji reaction on a rule comment."""
    __tablename__ = 'rule_comment_reaction'

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid         = db.Column(db.String(36), unique=True, nullable=False, index=True)
    rule_id      = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    comment_id   = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reaction_type = db.Column(db.String(50), nullable=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user    = db.relationship('User',    backref=db.backref('rule_comment_reactions', lazy='dynamic', cascade='all, delete-orphan'))
    rule    = db.relationship('Rule',    backref=db.backref('comment_reactions',      lazy='dynamic'))
    comment = db.relationship('Comment', backref=db.backref('rule_reactions',         lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id":            self.id,
            "rule_id":       self.rule_id,
            "comment_id":    self.comment_id,
            "user_id":       self.user_id,
            "reaction_type": self.reaction_type,
            "created_at":    self.created_at.strftime('%Y-%m-%d %H:%M'),
        }


class CommentBundle(db.Model):
    """Model for user comments on Bundles."""
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, index=True)
    uuid = db.Column(db.String(36), index=True, unique=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_name = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, index=True)
    updated_at = db.Column(db.DateTime, index=True)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    # reaction = db.Column(db.String(50), nullable=True) # emodji reaction

    # respond from an other comment
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comment_bundle.id'), nullable=True)
   
    # Relations
    user = db.relationship('User', backref=db.backref('comments_users', lazy='dynamic' , cascade='all, delete-orphan'))
    bundle = db.relationship('Bundle', backref=db.backref('comments_bundles', lazy='dynamic', cascade='all, delete-orphan'))
    parent_comment = db.relationship(
        'CommentBundle', 
        remote_side=[id], 
        backref=db.backref('replies', lazy='dynamic', cascade='all, delete-orphan')
    )
    #get_all_reactions
    def get_all_reactions(self):
        """Only reaction different from like or dislike"""
        reactions = BundleReactionComment.query.filter_by(comment_id=self.id).all()
        # remove like and dislike from the list
        reactions = [reaction for reaction in reactions if reaction.reaction_type not in ['like', 'dislike']]
        return [reaction.to_json() for reaction in reactions]
    
    def get_username_by_id(self):
        user = User.query.get(self.user_id)  
        return user.first_name + " " + user.last_name if user else self.user_name

    def to_json(self, include_replies=True):
        data = {
            "id": self.id,
            "bundle_id": self.bundle_id,
            "user_id": self.user_id,
            "user_name": self.get_username_by_id(),
            "content": self.content,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            "is_admin": self.user.is_admin() if self.user else False,
            "parent_comment_id": self.parent_comment_id,
            "likes": self.likes,
            "dislikes": self.dislikes,
            # get all the reaction for this comment from BundleREactionComment not the champ reaction
            "reactions":  self.get_all_reactions(),
        }

        if include_replies:
            data["replies"] = [reply.to_json(include_replies=True) for reply in self.replies.all()]
        
        return data


class BundleReactionComment(db.Model):
    """ LIKE/DISLIKE/EMOJI reaction on comment in a Bundle """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, unique=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment_bundle.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reaction_type = db.Column(db.String(50), nullable=False) # e.g., 'like', 'dislike', 'emoji_name'
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    user = db.relationship('User', backref=db.backref('bundle_reactions', lazy='dynamic', cascade='all, delete-orphan'))
    bundle = db.relationship('Bundle', backref=db.backref('reactions', lazy='dynamic', cascade='all, delete-orphan'))
    comment = db.relationship('CommentBundle', backref=db.backref('reactions', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "bundle_id": self.bundle_id,
            "user_id": self.user_id,
            "reaction_type": self.reaction_type,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M'),
            "is_admin": self.user.is_admin(),
            "comment_id": self.comment_id
        }


def _gen_comment_uuid():
    return str(_uuid_mod.uuid4())


class UnifiedComment(db.Model):
    """Single polymorphic comment table for rules, bundles, and edit proposals."""
    __tablename__ = 'comment_v2'

    id               = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid             = db.Column(db.String(36), unique=True, nullable=False, index=True, default=_gen_comment_uuid)
    content          = db.Column(db.Text, nullable=False)
    content_original = db.Column(db.Text, nullable=True)

    # Thread structure
    parent_id = db.Column(db.Integer, db.ForeignKey('comment_v2.id', ondelete='SET NULL'), nullable=True, index=True)
    depth     = db.Column(db.Integer, default=0, nullable=False)
    root_id   = db.Column(db.Integer, nullable=True, index=True)

    # Polymorphic target — object_type: 'rule' | 'bundle' | 'proposal'
    object_type = db.Column(db.String(64), nullable=False, index=True)
    object_id   = db.Column(db.Integer,    nullable=False, index=True)

    is_public   = db.Column(db.Boolean, default=True,  nullable=False)
    is_active   = db.Column(db.Boolean, default=True,  nullable=False)
    deleted_at  = db.Column(db.DateTime, nullable=True)
    deleted_by  = db.Column(db.Integer, nullable=True)

    # Set when an admin turns this comment into an issue on the official
    # rulezet-core GitHub repo — keeps the button from filing duplicates.
    github_issue_url    = db.Column(db.String(500), nullable=True)
    github_issue_number = db.Column(db.Integer, nullable=True)

    created_at  = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    created_by  = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)

    author = db.relationship(
        'User',
        foreign_keys=[created_by],
        lazy='joined',
        primaryjoin='UnifiedComment.created_by == User.id',
    )
    reactions = db.relationship(
        'UnifiedCommentReaction',
        backref='comment',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    replies = db.relationship(
        'UnifiedComment',
        backref=db.backref('parent_comment', remote_side='UnifiedComment.id'),
        lazy='dynamic',
        foreign_keys=[parent_id],
        cascade='all, delete-orphan',
    )

    @property
    def reply_count(self):
        return UnifiedComment.query.filter_by(parent_id=self.id, is_active=True).count()

    @property
    def like_count(self):
        return self.reactions.filter_by(reaction='like').count()

    @property
    def dislike_count(self):
        return self.reactions.filter_by(reaction='dislike').count()

    def to_json(self, current_user_id=None, counts=None):
        """counts: optional {'reply_count', 'like_count', 'dislike_count', 'user_reaction'}
        pre-computed by the caller (see comment_api.py's _batch_comment_counts) to avoid
        the 3-4 extra per-instance queries below when serializing a whole page of comments.
        Falls back to the lazy per-instance computation when not provided."""
        author = self.author
        if author:
            initials = ''
            if author.first_name:
                initials += author.first_name[0].upper()
            if author.last_name:
                initials += author.last_name[0].upper()
            author_dict = {
                'id':       author.id,
                'name':     author.get_username(),
                'avatar':   author.profile_picture,
                'initials': initials or '?',
                'handle':   author.username,
            }
        else:
            author_dict = {'id': None, 'name': 'Deleted user', 'avatar': None, 'initials': '?', 'handle': None}

        if counts is not None:
            reply_count   = counts.get('reply_count', 0)
            like_count    = counts.get('like_count', 0)
            dislike_count = counts.get('dislike_count', 0)
            user_reaction = counts.get('user_reaction')
        else:
            reply_count   = self.reply_count
            like_count    = self.like_count
            dislike_count = self.dislike_count
            user_reaction = None
            if current_user_id:
                rxn = self.reactions.filter_by(user_id=current_user_id).first()
                if rxn:
                    user_reaction = rxn.reaction

        return {
            'id':            self.id,
            'uuid':          self.uuid,
            'content':       self.content if self.is_active else '[deleted]',
            'parent_id':     self.parent_id,
            'depth':         self.depth,
            'root_id':       self.root_id,
            'object_type':   self.object_type,
            'object_id':     self.object_id,
            'is_public':     self.is_public,
            'created_at':    self.created_at.isoformat() if self.created_at else None,
            'updated_at':    self.updated_at.isoformat() if self.updated_at else None,
            'created_by':    self.created_by,
            'is_active':     self.is_active,
            'is_deleted':    not self.is_active,
            'deleted_at':    self.deleted_at.isoformat() if self.deleted_at else None,
            'reply_count':   reply_count,
            'like_count':    like_count,
            'dislike_count': dislike_count,
            'user_reaction': user_reaction,
            'author':        author_dict,
            'is_admin':      author.is_admin() if author else False,
            'github_issue_url':    self.github_issue_url,
            'github_issue_number': self.github_issue_number,
        }


class UnifiedCommentReaction(db.Model):
    __tablename__ = 'comment_reaction'
    __table_args__ = (
        db.UniqueConstraint('comment_id', 'user_id', name='uq_comment_reaction_user'),
    )

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment_v2.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id',       ondelete='CASCADE'), nullable=False, index=True)
    reaction   = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    user = db.relationship('User', backref=db.backref('unified_comment_reactions', lazy='dynamic'))


def purge_unified_comments(object_type: str, object_ids) -> int:
    """Bulk-delete comment_v2 rows (and their reactions) for the given object(s).

    object_type/object_id is a polymorphic pseudo-FK, not a real foreign key,
    so deleting a rule/bundle/proposal/blog_post never cascades here on its
    own — every hard-delete path for those four types must call this.
    """
    ids = list(object_ids) if isinstance(object_ids, (list, tuple, set)) else [object_ids]
    if not ids:
        return 0
    comment_ids = [
        cid for (cid,) in db.session.query(UnifiedComment.id)
        .filter(UnifiedComment.object_type == object_type, UnifiedComment.object_id.in_(ids))
        .all()
    ]
    if not comment_ids:
        return 0
    UnifiedCommentReaction.query.filter(
        UnifiedCommentReaction.comment_id.in_(comment_ids)
    ).delete(synchronize_session=False)
    return UnifiedComment.query.filter(UnifiedComment.id.in_(comment_ids)).delete(synchronize_session=False)


# Imported last: these models are only used inside methods, and importing them
# at the top would be circular.
from app.core.db_class.user import User  # noqa: E402
