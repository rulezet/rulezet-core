"""
REST API for the unified comment system.

Endpoints (all under /api/comments):
  GET    /                        list root comments for an object (+ replies via parent_id param)
  POST   /                        create a comment or reply
  PUT    /<uuid>                   edit content (author or moderator)
  DELETE /<uuid>                   soft-delete (author or moderator)
  POST   /<uuid>/restore           restore a soft-deleted comment (moderator only)
  POST   /<uuid>/react             toggle like / dislike
"""
import datetime
import uuid as _uuid_mod

from flask import request
from flask_login import current_user
from flask_restx import Namespace, Resource, fields

from app.core.db_class.db import UnifiedComment, UnifiedCommentReaction
from app.core.utils.activity_log import log_activity
from app import db

comment_ns = Namespace('comments', description='Unified comment thread API')

_VALID_OBJECT_TYPES = {'rule', 'bundle', 'proposal'}
_PER_PAGE_MAX = 50


def _get_or_404(uuid):
    c = UnifiedComment.query.filter_by(uuid=uuid).first()
    if not c:
        comment_ns.abort(404, 'Comment not found')
    return c


def _can_moderate():
    return current_user.is_authenticated and current_user.is_admin()


def _can_edit(comment):
    if not current_user.is_authenticated:
        return False
    return comment.created_by == current_user.id or _can_moderate()


# ── List / Create ──────────────────────────────────────────────────────────────

@comment_ns.route('/')
class CommentList(Resource):

    def get(self):
        """List comments for an object (paginated). Pass parent_id to fetch replies."""
        object_type = request.args.get('object_type', '').strip()
        object_id   = request.args.get('object_id', type=int)
        parent_id   = request.args.get('parent_id', type=int, default=None)
        page        = request.args.get('page', 1, type=int)
        per_page    = min(request.args.get('per_page', 20, type=int), _PER_PAGE_MAX)

        if object_type not in _VALID_OBJECT_TYPES or not object_id:
            return {'message': 'object_type and object_id are required'}, 400

        uid = current_user.id if current_user.is_authenticated else None

        q = (UnifiedComment.query
             .filter_by(object_type=object_type, object_id=object_id, is_active=True)
             .filter(UnifiedComment.parent_id == parent_id)
             .order_by(UnifiedComment.created_at.asc()))

        paginated = q.paginate(page=page, per_page=per_page, error_out=False)

        return {
            'items':    [c.to_json(current_user_id=uid) for c in paginated.items],
            'total':    paginated.total,
            'page':     page,
            'per_page': per_page,
            'has_next': paginated.has_next,
        }

    def post(self):
        """Create a new comment or reply. Requires login."""
        if not current_user.is_authenticated:
            return {'message': 'Login required'}, 401

        data = request.get_json(silent=True) or {}
        object_type = data.get('object_type', '').strip()
        object_id   = data.get('object_id')
        content     = data.get('content', '').strip()
        parent_id   = data.get('parent_id')

        if object_type not in _VALID_OBJECT_TYPES:
            return {'message': f'object_type must be one of {_VALID_OBJECT_TYPES}'}, 400
        if not object_id:
            return {'message': 'object_id is required'}, 400
        if not content:
            return {'message': 'content is required'}, 400
        if len(content) > 10000:
            return {'message': 'comment too long (max 10 000 chars)'}, 400

        depth   = 0
        root_id = None

        if parent_id:
            parent = UnifiedComment.query.filter_by(id=parent_id, is_active=True).first()
            if not parent:
                return {'message': 'Parent comment not found'}, 404
            if parent.object_type != object_type or parent.object_id != object_id:
                return {'message': 'Parent comment does not belong to this object'}, 400
            depth   = parent.depth + 1
            root_id = parent.root_id or parent.id

        now = datetime.datetime.now(datetime.timezone.utc)
        comment = UnifiedComment(
            uuid=str(_uuid_mod.uuid4()),
            content=content,
            object_type=object_type,
            object_id=object_id,
            parent_id=parent_id,
            depth=depth,
            root_id=root_id,
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.session.add(comment)
        db.session.commit()

        # Activity log
        if object_type == 'rule':
            from app.core.db_class.db import Rule
            rule = Rule.query.get(object_id)
            log_activity("comment.add",
                         f"Added comment on rule '{rule.title if rule else object_id}'",
                         target_type="comment", target_id=comment.id,
                         extra={"rule_id": object_id, "rule_uuid": rule.uuid if rule else None})
        elif object_type == 'bundle':
            from app.core.db_class.db import Bundle
            bundle = Bundle.query.get(object_id)
            log_activity("bundle_comment.add",
                         f"Added comment on bundle id={object_id}",
                         target_type="bundle_comment", target_id=comment.id,
                         extra={"bundle_id": object_id, "bundle_uuid": bundle.uuid if bundle else None},
                         is_public=bool(bundle.access) if bundle else False)

        return {'message': 'Comment posted', 'comment': comment.to_json(current_user_id=current_user.id)}, 201


# ── Single comment ─────────────────────────────────────────────────────────────

@comment_ns.route('/<string:uuid>')
class CommentDetail(Resource):

    def put(self, uuid):
        """Edit a comment's content. Requires authorship or moderation."""
        if not current_user.is_authenticated:
            return {'message': 'Login required'}, 401

        comment = _get_or_404(uuid)
        if not _can_edit(comment):
            return {'message': 'Not allowed'}, 403
        if not comment.is_active:
            return {'message': 'Cannot edit a deleted comment'}, 400

        data    = request.get_json(silent=True) or {}
        content = data.get('content', '').strip()
        if not content:
            return {'message': 'content is required'}, 400
        if len(content) > 10000:
            return {'message': 'comment too long (max 10 000 chars)'}, 400

        if comment.content_original is None:
            comment.content_original = comment.content
        comment.content    = content
        comment.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.commit()

        return {'message': 'Comment updated', 'comment': comment.to_json(current_user_id=current_user.id)}

    def delete(self, uuid):
        """Soft-delete a comment. Requires authorship or moderation."""
        if not current_user.is_authenticated:
            return {'message': 'Login required'}, 401

        comment = _get_or_404(uuid)
        if not _can_edit(comment):
            return {'message': 'Not allowed'}, 403
        if not comment.is_active:
            return {'message': 'Already deleted'}, 400

        now = datetime.datetime.now(datetime.timezone.utc)
        comment.is_active  = False
        comment.deleted_at = now
        comment.deleted_by = current_user.id
        db.session.commit()

        return {'message': 'Comment deleted'}


# ── Restore ────────────────────────────────────────────────────────────────────

@comment_ns.route('/<string:uuid>/restore')
class CommentRestore(Resource):

    def post(self, uuid):
        """Restore a soft-deleted comment (moderators only)."""
        if not _can_moderate():
            return {'message': 'Moderation required'}, 403

        comment = _get_or_404(uuid)
        if comment.is_active:
            return {'message': 'Comment is not deleted'}, 400

        comment.is_active  = True
        comment.deleted_at = None
        comment.deleted_by = None
        db.session.commit()

        return {'message': 'Comment restored', 'comment': comment.to_json(current_user_id=current_user.id)}


# ── Resolve (deep-link helper) ────────────────────────────────────────────────

@comment_ns.route('/resolve/<int:comment_id>')
class CommentResolve(Resource):

    def get(self, comment_id):
        """Return a comment's root_id and ordered ancestor chain for deep-link navigation."""
        c = UnifiedComment.query.get(comment_id)
        if not c or not c.is_active:
            return {'message': 'Comment not found'}, 404

        ancestors = []
        cur = c
        while cur.parent_id:
            parent = UnifiedComment.query.get(cur.parent_id)
            if not parent:
                break
            ancestors.insert(0, parent.id)
            cur = parent

        return {
            'id':       c.id,
            'root_id':  c.root_id,
            'ancestors': ancestors,
        }


# ── React ──────────────────────────────────────────────────────────────────────

@comment_ns.route('/<string:uuid>/react')
class CommentReact(Resource):

    def post(self, uuid):
        """Toggle a like or dislike on a comment. Requires login."""
        if not current_user.is_authenticated:
            return {'message': 'Login required'}, 401

        comment = _get_or_404(uuid)
        if not comment.is_active:
            return {'message': 'Cannot react to a deleted comment'}, 400

        data     = request.get_json(silent=True) or {}
        reaction = data.get('reaction', '').strip()
        if reaction not in ('like', 'dislike'):
            return {'message': 'reaction must be "like" or "dislike"'}, 400

        existing = UnifiedCommentReaction.query.filter_by(
            comment_id=comment.id, user_id=current_user.id
        ).first()

        if existing:
            if existing.reaction == reaction:
                # toggle off
                db.session.delete(existing)
            else:
                existing.reaction = reaction
        else:
            db.session.add(UnifiedCommentReaction(
                comment_id=comment.id,
                user_id=current_user.id,
                reaction=reaction,
                created_at=datetime.datetime.now(datetime.timezone.utc),
            ))

        db.session.commit()

        # Re-query counts after commit
        like_count    = UnifiedCommentReaction.query.filter_by(comment_id=comment.id, reaction='like').count()
        dislike_count = UnifiedCommentReaction.query.filter_by(comment_id=comment.id, reaction='dislike').count()
        new_rxn       = UnifiedCommentReaction.query.filter_by(comment_id=comment.id, user_id=current_user.id).first()

        return {
            'like_count':    like_count,
            'dislike_count': dislike_count,
            'user_reaction': new_rxn.reaction if new_rxn else None,
        }
