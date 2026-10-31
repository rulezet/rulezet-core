from flask_restx import Namespace, Resource
from flask import request, url_for
from flask_login import current_user
from wtforms.validators import Email, ValidationError

from app.core.utils.decorators import api_required
from app.core.utils.utils import as_db_id

from app.core.db_class.user import User
from app.features.account import account_core as AccountModel
from ...features.rule import rule_core as RuleModel

account_private_ns = Namespace(
    "Private account action 🔑 (with api key)",
    description="Private account operations"
)   

@account_private_ns.route('/edit')
class EditUser(Resource):
    @api_required
    def post(self):
        data = request.get_json(silent=True)
        if data is None:
            data = request.args.to_dict()
        if not isinstance(data, dict):
            return {"message": "The body must be a JSON object"}, 400
        error = AccountModel.account_fields_error(data, with_password=False)
        if error:
            return {"message": error}, 400
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")

        try:
            Email(message="Invalid email format")(None, type("DummyField", (), {"data": email})())
        except ValidationError:
            return {"message": "Invalid email format"}, 400



        if email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return {
                    "message": (
                        f"Email already registered. "
                        f'(Did you mean to <a href="{url_for("account.index")}">log in</a> instead?)'
                    )
                }, 409

        if data.get("password"):    
            password = data.get("password")
            if len(password) < 8 or len(password) > 64:
                return {"message": "Password must be between 8 and 64 characters."}, 400
            if not any(c.isupper() for c in password):
                return {"message": "Password must contain at least one uppercase letter."}, 400
            if not any(c.islower() for c in password):
                return {"message": "Password must contain at least one lowercase letter."}, 400
            if not any(c.isdigit() for c in password):
                return {"message": "Password must contain at least one digit."}, 400
            if not any(c in '@$!%*?&' for c in password):
                return {"message": "Password must contain at least one special character (@$!%*?&)."}, 400 
       
            form_dict = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "password": password
            }
        else:
            form_dict = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name
            }

        # Profile links (setting user.social_links): {"social_links": {"linkedin": "https://…", "bluesky": ""}}
        # — "" removes one, a key not sent is unchanged
        if isinstance(data.get("social_links"), dict):
            from app.features.account.social_links_core import clean_links
            _, errors = clean_links(data["social_links"])
            if errors:
                return {"message": " ".join(errors.values())}, 400
            form_dict["social_links"] = data["social_links"]

        is_sso = (current_user.auth_provider or 'local') != 'local'
        _, pending_email = AccountModel.edit_user_core(form_dict, current_user.id, is_sso=is_sso)
        if pending_email:
            AccountModel.request_email_change_core(current_user.id, pending_email)
            return {"message": "User updated successfully. A confirmation link was sent to the new "
                               "email address, which applies once confirmed."}, 200

        return {"message": "User updated successfully"}, 200

@account_private_ns.route("/favorite/get_rules_page_favorite")
class GetRulesPageFavorite(Resource):
    @api_required
    def get(self):
        page = request.args.get('page', 1, type=int)
        
        rules = RuleModel.get_rules_page_favorite(page, current_user.id)

        return {
            "rule": [rule.to_json() for rule in rules],
            "total_pages": rules.pages
        }
    
@account_private_ns.route("/favorite/delete_rule")
class RemoveRuleFavorite(Resource):
    @api_required
    def post(self):
        rule_id = as_db_id(request.args.get('id'))
        if rule_id is None:
            return {"success": False, "message": "Missing or invalid rule id"}, 400
        
        rep = AccountModel.remove_favorite(current_user.id, rule_id)

        if rep:
            return {"success": True, "message": "Rule deleted!"}
        return {"success": False, "message": "Access denied"}, 403
    


@account_private_ns.route("/notification_preferences")
@account_private_ns.doc(description="""
Read (GET) or change (POST, JSON `{"<key>": true|false, …}`) the authenticated user's notification
preferences — the same toggles as the Notifications › Preferences page, e.g. `favorite_rule_update`
(a rule you favorited had its content changed). Unknown keys are ignored.
""")
class NotificationPreferences(Resource):
    @api_required
    def get(self):
        """The authenticated user's notification preferences"""
        from app.features.notification.notification_core import get_preference
        return {"preferences": get_preference(current_user.id).to_json()}, 200

    @api_required
    def post(self):
        """Change some notification preferences"""
        from app.features.notification.notification_core import update_preference
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {"message": "Send a JSON object of preference keys and booleans."}, 400
        pref = update_preference(current_user.id, {k: v for k, v in data.items() if isinstance(v, bool)})
        if pref is None:
            return {"message": "Preferences could not be saved."}, 500
        return {"preferences": pref.to_json()}, 200
