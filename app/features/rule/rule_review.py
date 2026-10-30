"""
rule_review.py — "this rule is good" / "this rule needs changes", by any signed-in user, from the
rule page (Review button): verdict, 1-5 rating, how the rule was written (human / AI / both), comment.
Everyone edits / deletes their own review; an admin edits / deletes any. The owner's / an admin's
"written with" becomes the rule's own (Rule.written_with). Feeds the quality score (review category) and the
rule's history (an activity-log line per review). Routes on the rule blueprint.
"""
import uuid as _uuid

from flask import jsonify, request
from flask_login import current_user, login_required

from app import db
from app.core.db_class.rule import Rule, RuleReview, RuleScope
from app.core.utils.activity_log import log_activity
from app.features.rule.rule import rule_blueprint
from app.features.rule.rule_core import _active

VERDICTS = {'approved': 'approved', 'changes_requested': 'requested changes on'}
MAX_COMMENT = 4000
WRITTEN_WITH = {'human': 'by a human', 'ai': 'with AI', 'human_ai': 'by a human with AI help'}


def _hash(text):
    from app.features.rule.rule_quality.quality_score_core import _content_hash
    return _content_hash(text)


def _quality(rule):
    from app.features.rule.rule_quality.quality_score_core import recompute_rule_quality_score
    recompute_rule_quality_score(rule)
    return {'quality_score': rule.quality_score, 'quality_score_breakdown': rule.quality_score_breakdown,
            'quality_score_computed_at': rule.quality_score_computed_at.strftime('%Y-%m-%d %H:%M')
            if rule.quality_score_computed_at else None}


def _average_rating(reviews, current):
    ratings = [r.rating for r in reviews if r.rating and r.content_hash == current]
    return round(sum(ratings) / len(ratings), 1) if ratings else None


def _payload(rule):
    current = _hash(rule.to_string)
    reviews = (RuleReview.query.filter_by(rule_id=rule.id).order_by(RuleReview.created_at.desc()).all())
    me = current_user.id if current_user.is_authenticated else None
    admin = current_user.is_authenticated and current_user.is_admin()
    return {
        'reviews': [{**r.to_json(current), 'can_edit': bool(me) and (admin or r.user_id == me)} for r in reviews],
        'my_review': next((r.to_json(current) for r in reviews if r.user_id == me), None),
        'can_review': bool(me),
        # the scopes I declared on this rule — the only ones my review can point to
        'my_scopes': [{'id': sc.id, 'works': sc.works, 'entries': sc.entries or []}
                      for sc in RuleScope.query.filter_by(rule_id=rule.id, user_id=me).all()] if me else [],
        'average_rating': _average_rating(reviews, current),
        'is_owner': bool(me) and me == rule.user_id,
        'can_moderate': admin,                       # admins edit / delete any review
    }


@rule_blueprint.route('/<int:rule_id>/reviews', methods=['GET'])
def rule_reviews(rule_id):
    rule = _active().filter(Rule.id == rule_id).first()
    if not rule:
        return jsonify({'message': 'Rule not found.'}), 404
    return jsonify(_payload(rule)), 200


@rule_blueprint.route('/<int:rule_id>/review', methods=['POST'])
@login_required
def rule_review_save(rule_id):
    rule = _active().filter(Rule.id == rule_id).first()
    if not rule:
        return jsonify({'message': 'Rule not found.', 'toast_class': 'danger-subtle'}), 404
    data = request.get_json(silent=True) or {}
    verdict = data.get('verdict')
    if verdict not in VERDICTS:
        return jsonify({'message': 'Choose: approve, or request changes.', 'toast_class': 'danger-subtle'}), 400
    comment = (data.get('comment') or '').strip()[:MAX_COMMENT]
    try:
        rating = int(data.get('rating') or 0) or None
    except (TypeError, ValueError):
        rating = None
    if rating is not None and not 1 <= rating <= 5:
        return jsonify({'message': 'The rating goes from 1 to 5.', 'toast_class': 'danger-subtle'}), 400
    written_with = data.get('written_with') or None
    if written_with is not None and written_with not in WRITTEN_WITH:
        return jsonify({'message': 'Unknown value for how it was written.', 'toast_class': 'danger-subtle'}), 400
    if verdict == 'changes_requested' and not comment:
        return jsonify({'message': 'Say what should change.', 'toast_class': 'danger-subtle'}), 400
    if data.get('review_uuid'):                  # editing an existing review: its author or an admin
        review = RuleReview.query.filter_by(uuid=data['review_uuid'], rule_id=rule.id).first()
        if not review:
            return jsonify({'message': 'Review not found.', 'toast_class': 'danger-subtle'}), 404
        if review.user_id != current_user.id and not current_user.is_admin():
            return jsonify({'message': 'You can only edit your own review.', 'toast_class': 'danger-subtle'}), 403
    else:
        review = RuleReview.query.filter_by(rule_id=rule.id, user_id=current_user.id).first()
        if not review:
            review = RuleReview(uuid=str(_uuid.uuid4()), rule_id=rule.id, user_id=current_user.id)
            db.session.add(review)
    review.verdict, review.comment, review.content_hash = verdict, comment or None, _hash(rule.to_string)
    review.rating, review.written_with = rating, written_with
    scope_id = data.get('scope_id')
    if scope_id:
        scope = RuleScope.query.filter_by(id=scope_id, rule_id=rule.id, user_id=review.user_id or current_user.id).first()
        if not scope:
            return jsonify({'message': 'A review can only link a scope its author declared on this rule.', 'toast_class': 'danger-subtle'}), 400
        review.scope_id = scope.id
    else:
        review.scope_id = None
    author_is_owner = review.user_id == rule.user_id or (review.user_id == current_user.id and current_user.is_admin())
    if written_with and author_is_owner:
        rule.written_with = written_with          # the owner's / an admin's own review says it for the rule
    from datetime import datetime, timezone
    review.created_at = datetime.now(tz=timezone.utc)
    db.session.commit()
    log_activity('rule.review', f"{current_user.get_username()} {VERDICTS[verdict]} the rule '{rule.title}'"
                 + (f" ({rating}/5)" if rating else '')
                 + (f", written {WRITTEN_WITH[written_with]}" if written_with else '')
                 + (f": {comment[:200]}" if comment else ''),
                 target_type='rule', target_id=rule.id, target_uuid=rule.uuid,
                 icon='fa-solid fa-user-check' if verdict == 'approved' else 'fa-solid fa-user-pen',
                 extra={'verdict': verdict})
    # The owner hears about every review of their rule by someone else (bell)
    if rule.user_id and rule.user_id != current_user.id:
        try:
            from app.features.notification.notification_core import create_notification
            word = 'approved' if verdict == 'approved' else 'requested changes on'
            create_notification(user_id=rule.user_id, notif_type='rule_review',
                                title=f"{current_user.get_username()} {word} your rule '{rule.title[:80]}'"
                                      + (f" — {rating}/5" if rating else ''),
                                body=(comment[:300] or None), link=f'/rule/detail_rule/{rule.id}',
                                icon='fa-solid fa-user-check' if verdict == 'approved' else 'fa-solid fa-user-pen')
        except Exception:
            pass
    return jsonify({**_payload(rule), **_quality(rule),
                    'message': 'Thanks — review saved.', 'toast_class': 'success-subtle'}), 200


@rule_blueprint.route('/review/<string:review_uuid>', methods=['DELETE'])
@login_required
def rule_review_delete(review_uuid):
    review = RuleReview.query.filter_by(uuid=review_uuid).first()
    if not review:
        return jsonify({'message': 'Review not found.', 'toast_class': 'danger-subtle'}), 404
    rule = db.session.get(Rule, review.rule_id)
    if review.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'message': 'You can only delete your own review.', 'toast_class': 'danger-subtle'}), 403
    db.session.delete(review)
    db.session.commit()
    log_activity('rule.review_removed', f"{current_user.get_username()} removed a review of '{rule.title}'",
                 target_type='rule', target_id=rule.id, target_uuid=rule.uuid, icon='fa-solid fa-user-xmark')
    return jsonify({**_payload(rule), **_quality(rule), 'message': 'Review removed.', 'toast_class': 'success-subtle'}), 200


@rule_blueprint.route('/<int:rule_id>/quality/recompute', methods=['POST'])
@login_required
def rule_quality_recompute(rule_id):
    """'Re-analyse now' of the Quality section — the owner or an admin."""
    rule = _active().filter(Rule.id == rule_id).first()
    if not rule:
        return jsonify({'message': 'Rule not found.', 'toast_class': 'danger-subtle'}), 404
    if rule.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'message': 'Only its owner or an admin can re-analyse it.', 'toast_class': 'danger-subtle'}), 403
    return jsonify({**_quality(rule), 'message': 'Re-analysed.', 'toast_class': 'success-subtle'}), 200



@rule_blueprint.route('/<int:rule_id>/written_with', methods=['POST'])
@login_required
def rule_written_with(rule_id):
    """How the rule was written (human / AI / both) — said by its owner or an admin."""
    rule = _active().filter(Rule.id == rule_id).first()
    if not rule:
        return jsonify({'message': 'Rule not found.', 'toast_class': 'danger-subtle'}), 404
    if rule.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'message': 'Only its owner or an admin can say it.', 'toast_class': 'danger-subtle'}), 403
    value = (request.get_json(silent=True) or {}).get('written_with') or None
    if value is not None and value not in WRITTEN_WITH:
        return jsonify({'message': 'Unknown value.', 'toast_class': 'danger-subtle'}), 400
    rule.written_with = value
    db.session.commit()
    log_activity('rule.written_with', f"{current_user.get_username()} said '{rule.title}' was written "
                 + (WRITTEN_WITH[value] if value else '— cleared'),
                 target_type='rule', target_id=rule.id, target_uuid=rule.uuid, icon='fa-solid fa-robot')
    return jsonify({**_quality(rule), 'written_with': value, 'message': 'Saved.', 'toast_class': 'success-subtle'}), 200
