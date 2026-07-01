from flask import request
from flask_login import current_user
from flask_restx import Namespace, Resource

from app.features.rule import rule_core as RuleModel
from app.features.rule_tester import rule_tester_core as TesterModel

rule_tester_public_ns = Namespace(
    'Rule Tester — Public',
    description='Public rule test history endpoints',
)


@rule_tester_public_ns.route('/rule/<string:rule_uuid>/tests')
class PublicTestHistory(Resource):
    def get(self, rule_uuid):
        """Return public test history for a rule."""
        rule = RuleModel.get_rule_by_uuid(rule_uuid)
        if not rule:
            return {'message': 'Rule not found'}, 404

        page     = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 50)

        pagination = TesterModel.get_tests_for_rule(rule.id, current_user,
                                                     page=page, per_page=per_page)
        items = []
        for t in pagination.items:
            item = t.to_json_summary()
            # mask user info for private tests if viewer is not owner/admin
            is_own  = current_user.is_authenticated and current_user.id == t.user_id
            is_admin = current_user.is_authenticated and current_user.is_admin()
            if not t.is_public and not is_own and not is_admin:
                item['user_id'] = None
            else:
                from app.core.db_class.db import User
                u = User.query.get(t.user_id)
                item['user'] = {
                    'id':       u.id,
                    'username': u.get_username(),
                    'avatar':   u.get_avatar_url(),
                } if u else None
            items.append(item)

        return {
            'tests':   items,
            'total':   pagination.total,
            'pages':   pagination.pages,
            'page':    page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        }
