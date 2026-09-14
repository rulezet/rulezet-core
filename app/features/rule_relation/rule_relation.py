from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from . import rule_relation_core as RelationModel

rule_relation_blueprint = Blueprint('rule_relation_blueprint', __name__)


def _load_rule_or_none(rule_id):
    from ...core.db_class.db import Rule
    rule = Rule.query.get(rule_id)
    if not rule or rule.is_deleted:
        return None
    return rule


def _can_edit(rule):
    return (rule.user_id == current_user.id or current_user.is_admin()
            or current_user.has_permission('rule.tag_any'))


@rule_relation_blueprint.route('/rule/<int:rule_id>')
def get_rule_relations(rule_id):
    """Public read — same visibility as the rule detail page itself."""
    rule = _load_rule_or_none(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    return jsonify(RelationModel.get_relations_for_rule(rule_id))


@rule_relation_blueprint.route('/rule/<int:rule_id>/add', methods=['POST'])
@login_required
def add_to_rule(rule_id):
    from app.core.utils.activity_log import log_activity
    from app.features.rule import rule_core as RuleModel

    rule = _load_rule_or_none(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    if not _can_edit(rule):
        return jsonify({'error': 'Forbidden'}), 403

    data = request.json or {}
    target_rule_id = data.get('target_rule_id')
    relation_type = (data.get('relation_type') or 'references').strip()
    note = data.get('note')
    if not target_rule_id:
        return jsonify({'error': 'target_rule_id required'}), 400

    old_snapshot = RuleModel.rule_metadata_snapshot(rule)
    relation, status = RelationModel.add_relation(
        rule_id, int(target_rule_id), relation_type, note=note, user_id=current_user.id, source='manual'
    )
    if status in ('target_not_found', 'source_not_found'):
        return jsonify({'error': 'Rule not found'}), 404
    if status == 'invalid_relation_type':
        return jsonify({'error': 'Invalid relation type'}), 400
    if status == 'self_link_rejected':
        return jsonify({'error': "A rule can't be linked to itself"}), 400
    if status == 'limit_reached':
        return jsonify({'error': f"This rule already has the maximum of "
                                  f"{RelationModel.MAX_MANUAL_RELATIONS_PER_RULE} linked rules."}), 400

    is_owner_or_admin = rule.user_id == current_user.id or current_user.is_admin()
    if not is_owner_or_admin and status == 'created':
        # Credit + audit trail for a non-owner change — same treatment as
        # ATT&CK's own manual-edit route.
        RuleModel.add_contributor(current_user.id, rule_id)
        new_snapshot = RuleModel.rule_metadata_snapshot(rule)
        log_activity("rule.quick_meta", f"Linked rule '{rule.title}' (id={rule_id}) to another rule",
                     target_type="rule", target_id=rule_id, target_uuid=rule.uuid)
        RuleModel.create_rule_history({
            "id": rule_id, "title": rule.title, "success": True, "manual_submit": False,
            "message": "Related rules updated",
            "new_content": rule.to_string, "old_content": rule.to_string,
            "old_snapshot": old_snapshot, "new_snapshot": new_snapshot,
            "change_type": "metadata",
        })

    return jsonify({'success': True, 'status': status, 'relation': relation.to_json('outgoing') if relation else None})


@rule_relation_blueprint.route('/rule/<int:rule_id>/remove/<relation_uuid>', methods=['DELETE'])
@login_required
def remove_from_rule(rule_id, relation_uuid):
    from app.core.utils.activity_log import log_activity
    from app.features.rule import rule_core as RuleModel

    rule = _load_rule_or_none(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    if not _can_edit(rule):
        return jsonify({'error': 'Forbidden'}), 403

    relation = RelationModel.get_relation_by_uuid(relation_uuid)
    if not relation or relation.source_rule_id != rule_id:
        return jsonify({'error': 'Relation not found'}), 404

    old_snapshot = RuleModel.rule_metadata_snapshot(rule)
    removed = RelationModel.remove_relation(relation_uuid)

    is_owner_or_admin = rule.user_id == current_user.id or current_user.is_admin()
    if not is_owner_or_admin and removed:
        RuleModel.add_contributor(current_user.id, rule_id)
        new_snapshot = RuleModel.rule_metadata_snapshot(rule)
        log_activity("rule.quick_meta", f"Unlinked rule '{rule.title}' (id={rule_id}) from another rule",
                     target_type="rule", target_id=rule_id, target_uuid=rule.uuid)
        RuleModel.create_rule_history({
            "id": rule_id, "title": rule.title, "success": True, "manual_submit": False,
            "message": "Related rules updated",
            "new_content": rule.to_string, "old_content": rule.to_string,
            "old_snapshot": old_snapshot, "new_snapshot": new_snapshot,
            "change_type": "metadata",
        })

    return jsonify({'success': removed})


@rule_relation_blueprint.route('/rule/<int:rule_id>/page')
def get_rule_relations_page(rule_id):
    """Paginated one-direction feed for the dedicated Linked Rules page
    (app/templates/rule/detail_rule/detail_rule_linked_rules.html) — the
    picker's own get_rule_relations above stays unpaginated (bounded by
    MAX_MANUAL_RELATIONS_PER_RULE on the outgoing side), but an incoming
    count isn't capped (auto-detected links aren't), so the full page
    needs real pagination."""
    rule = _load_rule_or_none(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    direction = request.args.get('direction', 'outgoing')
    if direction not in ('outgoing', 'incoming'):
        return jsonify({'error': "direction must be 'outgoing' or 'incoming'"}), 400
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    return jsonify(RelationModel.get_relations_page(rule_id, direction, page=page, per_page=per_page))
