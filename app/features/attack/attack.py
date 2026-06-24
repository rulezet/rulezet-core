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
    """Server-side paginated + sorted admin API for ATT&CK techniques."""
    if not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403

    from app import db
    from app.core.db_class.db import AttackTechnique, RuleAttackAssociation
    from sqlalchemy import func, asc, desc, cast, Text

    search          = request.args.get('search', '').strip()
    tactic          = request.args.get('tactic', '').strip()
    show_deprecated = request.args.get('show_deprecated', 'false').lower() == 'true'
    sort_by         = request.args.get('sort_by', 'technique_id')
    sort_dir        = request.args.get('sort_dir', 'asc').lower()
    try:
        page     = max(1, int(request.args.get('page', 1)))
        per_page = min(500, max(10, int(request.args.get('per_page', 50))))
    except (ValueError, TypeError):
        page, per_page = 1, 50

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

    if tactic:
        # Works on both PostgreSQL JSON and SQLite TEXT-cast
        q = q.filter(cast(AttackTechnique.tactic_keys, Text).ilike(f'%"{tactic}"%'))

    # Sorting
    _SORT_COLS = {
        'technique_id':  AttackTechnique.technique_id,
        'name':          AttackTechnique.name,
        'rule_count':    count_subq.c.cnt,
        'is_subtechnique': AttackTechnique.is_subtechnique,
        'deprecated':    AttackTechnique.deprecated,
    }
    sort_col = _SORT_COLS.get(sort_by, AttackTechnique.technique_id)
    order_fn = desc if sort_dir == 'desc' else asc
    # Secondary sort by technique_id for stable ordering
    q = q.order_by(order_fn(sort_col), AttackTechnique.technique_id)

    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page  = min(page, pages)

    rows = q.offset((page - 1) * per_page).limit(per_page).all()

    result = []
    for tech, rule_count in rows:
        d = tech.to_json()
        d['rule_count'] = int(rule_count)
        result.append(d)

    return jsonify({
        'techniques': result,
        'total':      total,
        'page':       page,
        'pages':      pages,
        'per_page':   per_page,
    })


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
