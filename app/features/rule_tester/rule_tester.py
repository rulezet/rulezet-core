from flask import Blueprint, abort, render_template, redirect, url_for
from flask_login import current_user, login_required

from app.features.rule import rule_core as RuleModel
from . import rule_tester_core as TesterModel

rule_tester_blueprint = Blueprint('rule_tester', __name__)


# ── Helper: shared _nav_counts ────────────────────────────────────────────────

def _nav_counts(rule_id):
    from app.features.rule.rule import _nav_counts as _rule_nav_counts
    counts = _rule_nav_counts(rule_id)
    counts['test_count'] = TesterModel.count_visible_tests_for_rule(rule_id, current_user)
    return counts


# ── Test detail page ──────────────────────────────────────────────────────────

@rule_tester_blueprint.get('/rule_tester/test/<string:test_uuid>')
@login_required
def test_detail(test_uuid):
    test = TesterModel.get_test_by_uuid(test_uuid, viewer=current_user)
    if not test:
        abort(404)
    return render_template(
        'rule_tester/test_detail.html',
        test=test,
        test_json=test.to_json(),
    )


# ── Bulk test launcher ────────────────────────────────────────────────────────

@rule_tester_blueprint.get('/rule_tester/bulk')
@login_required
def bulk_test():
    from app.features.rule_tester.drivers import registry
    capabilities = registry.get_all_capabilities()
    return render_template('rule_tester/bulk_test.html', capabilities=capabilities)


# ── Rule sub-pages: Test & Test History ──────────────────────────────────────

@rule_tester_blueprint.get('/rule/detail_rule/<int:rule_id>/test')
@login_required
def rule_test_panel(rule_id):
    return redirect(url_for('rule_tester.rule_test_history', rule_id=rule_id))


@rule_tester_blueprint.get('/rule/detail_rule/<int:rule_id>/test_history')
def rule_test_history(rule_id):
    rule = RuleModel.get_rule(rule_id)
    if not rule:
        abort(404)
    if rule.is_deleted:
        return render_template('rule/rule_in_trash.html', rule=rule)
    return render_template(
        'rule/detail_rule/detail_rule_test_history.html',
        rule=rule,
        **_nav_counts(rule.id),
    )
