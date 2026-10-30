"""
issue_report_routes.py — "Create issue" (issue_report.py): the Markdown report of a rule or of a Git
source, to post as an issue on its repository. On the rule blueprint.
"""
from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from app.core.db_class.git import GithubRepo
from app.core.db_class.rule import Rule
from app.features.rule.issue_report import repo_report, rule_report
from app.features.rule.rule import rule_blueprint
from app.features.rule.rule_core import _active


def _base_url():
    return current_app.config.get('INSTANCE_PUBLIC_URL') or request.host_url


def _admin_only():
    if not current_user.is_admin():
        return jsonify({'message': 'Admins only.'}), 403
    return None


@rule_blueprint.route('/<int:rule_id>/issue_report', methods=['GET'])
@login_required
def rule_issue_report(rule_id):
    """Admins only: the report is meant to be posted on the rule's repository by the instance."""
    if (denied := _admin_only()):
        return denied
    rule = _active().filter(Rule.id == rule_id).first()
    if not rule:
        return jsonify({'message': 'Rule not found.'}), 404
    return jsonify(rule_report(rule, _base_url())), 200


@rule_blueprint.route('/github/issue_report', methods=['GET'])
@login_required
def repo_issue_report():
    """A Git source's import report (admins only)."""
    if (denied := _admin_only()):
        return denied
    url = (request.args.get('url') or '').strip().rstrip('/')
    if url.endswith('.git'):
        url = url[:-4]
    repo = GithubRepo.query.filter_by(url=url).first()
    if not repo:
        return jsonify({'message': 'Git source not found.'}), 404
    return jsonify(repo_report(repo, _base_url())), 200
