from flask import Blueprint, jsonify, request, render_template, abort
from flask_login import login_required, current_user
from . import attack_core as AttackModel
from ..jobs import jobs_core as JobModel

attack_blueprint = Blueprint('attack_blueprint', __name__)


# ── Technique catalogue ───────────────────────────────────────────────────────

@attack_blueprint.route('/techniques')
def list_techniques():
    tactic = request.args.get('tactic')
    return jsonify(AttackModel.get_all_techniques(tactic))


@attack_blueprint.route('/techniques/search')
def search_techniques():
    q = request.args.get('q', '')
    limit = min(int(request.args.get('limit', 20)), 50)
    return jsonify(AttackModel.search_techniques(q, limit))


@attack_blueprint.route('/stats')
def stats():
    return jsonify(AttackModel.get_stats())


@attack_blueprint.route('/techniques/usage')
def techniques_usage():
    """Techniques that are actually associated with at least one rule, with counts.
    Used by the RuleList ATT&CK filter dropdown."""
    from ...core.db_class.db import RuleAttackAssociation, AttackTechnique
    from app import db
    from sqlalchemy import func, cast, Text
    rows = (
        db.session.query(
            AttackTechnique.technique_id,
            AttackTechnique.name,
            func.count(RuleAttackAssociation.id).label('count'),
        )
        .join(RuleAttackAssociation, RuleAttackAssociation.technique_id == AttackTechnique.technique_id)
        .group_by(AttackTechnique.technique_id, AttackTechnique.name)
        .order_by(func.count(RuleAttackAssociation.id).desc())
        .all()
    )
    # Fetch tactic_keys separately to avoid GROUP BY on JSON column
    tech_ids = [r.technique_id for r in rows]
    tactic_map = {}
    if tech_ids:
        tac_rows = (
            db.session.query(AttackTechnique.technique_id, AttackTechnique.tactic_keys)
            .filter(AttackTechnique.technique_id.in_(tech_ids))
            .all()
        )
        tactic_map = {r.technique_id: r.tactic_keys or [] for r in tac_rows}
    return jsonify({'techniques': [
        {'id': r.technique_id, 'name': r.name, 'tactic_keys': tactic_map.get(r.technique_id, []), 'count': r.count}
        for r in rows
    ]})


# ── Per-rule associations ─────────────────────────────────────────────────────

@attack_blueprint.route('/rule/<int:rule_id>')
def get_rule_techniques(rule_id):
    return jsonify(AttackModel.get_techniques_for_rule(rule_id))


@attack_blueprint.route('/rule/<int:rule_id>/add', methods=['POST'])
@login_required
def add_to_rule(rule_id):
    from ...core.db_class.db import Rule
    rule = Rule.query.get(rule_id)
    if not rule or rule.is_deleted:
        return jsonify({'error': 'Rule not found'}), 404
    if rule.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403

    technique_id = (request.json or {}).get('technique_id', '')
    if not technique_id:
        return jsonify({'error': 'technique_id required'}), 400

    assoc, status = AttackModel.add_technique_to_rule(rule_id, technique_id, current_user.id, 'manual')
    if status == 'technique_not_found':
        return jsonify({'error': 'Technique not found'}), 404
    return jsonify({'success': True, 'status': status, 'assoc': assoc.to_json() if assoc else None})


@attack_blueprint.route('/rule/<int:rule_id>/remove/<technique_id>', methods=['DELETE'])
@login_required
def remove_from_rule(rule_id, technique_id):
    from ...core.db_class.db import Rule
    rule = Rule.query.get(rule_id)
    if not rule or rule.is_deleted:
        return jsonify({'error': 'Rule not found'}), 404
    if rule.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403

    removed = AttackModel.remove_technique_from_rule(rule_id, technique_id)
    return jsonify({'success': removed})


# ── Admin: trigger jobs ───────────────────────────────────────────────────────

@attack_blueprint.route('/admin/list')
@login_required
def admin_list():
    if not current_user.is_admin():
        abort(403)
    return render_template('admin/attack_list.html')


@attack_blueprint.route('/admin/techniques')
@login_required
def admin_techniques():
    """Paginated admin API — all techniques with rule counts."""
    if not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403

    from app import db
    from app.core.db_class.db import AttackTechnique, RuleAttackAssociation
    from sqlalchemy import func

    search          = request.args.get('search', '').strip()
    tactic          = request.args.get('tactic', '').strip()
    show_deprecated = request.args.get('show_deprecated', 'false').lower() == 'true'

    count_subq = (
        db.session.query(
            RuleAttackAssociation.technique_id,
            func.count(RuleAttackAssociation.id).label('cnt'),
        )
        .group_by(RuleAttackAssociation.technique_id)
        .subquery()
    )

    q = (
        db.session.query(AttackTechnique, func.coalesce(count_subq.c.cnt, 0).label('rule_count'))
        .outerjoin(count_subq, count_subq.c.technique_id == AttackTechnique.technique_id)
    )

    if not show_deprecated:
        q = q.filter(AttackTechnique.deprecated == False)

    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            AttackTechnique.technique_id.ilike(like),
            AttackTechnique.name.ilike(like),
        ))

    rows = q.order_by(AttackTechnique.technique_id).all()

    result = []
    for tech, rule_count in rows:
        d = tech.to_json()
        d['rule_count'] = int(rule_count)
        result.append(d)

    if tactic:
        result = [t for t in result if tactic in (t.get('tactic_keys') or [])]

    return jsonify({'techniques': result, 'total': len(result)})


@attack_blueprint.route('/admin/trigger_update', methods=['POST'])
@login_required
def trigger_update():
    if not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    job = JobModel.create_job(
        job_type='update_attack_data',
        payload={},
        label='Update MITRE ATT&CK data',
        created_by=current_user.id,
        total=1,
    )
    return jsonify({'success': True, 'job_id': job.id, 'job_uuid': job.uuid})


@attack_blueprint.route('/admin/trigger_parse', methods=['POST'])
@login_required
def trigger_parse():
    if not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    data = request.json or {}
    job = JobModel.create_job(
        job_type='bulk_parse_attack_rules',
        payload={'format': data.get('format')},
        label='Auto-parse ATT&CK techniques from rules',
        created_by=current_user.id,
        total=0,
    )
    return jsonify({'success': True, 'job_id': job.id, 'job_uuid': job.uuid})
