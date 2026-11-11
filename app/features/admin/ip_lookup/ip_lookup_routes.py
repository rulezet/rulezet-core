"""IP lookup (whois / RDAP) behind the magnifier next to every IP address in the admin pages. Admins only."""
from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from app.features.admin.ip_lookup import ip_lookup_core

ip_lookup_blueprint = Blueprint('ip_lookup', __name__)


@ip_lookup_blueprint.before_request
def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin():
        abort(403)


@ip_lookup_blueprint.route('/admin/ip-lookup/<path:ip>', methods=['GET'])
def ip_lookup(ip):
    try:
        data = ip_lookup_core.lookup(ip, refresh=request.args.get('refresh') == '1')
    except ip_lookup_core.LookupError_ as e:
        return jsonify({"success": False, "ip": ip, "message": str(e)}), 400
    except Exception:
        return jsonify({"success": False, "ip": ip, "message": "The lookup failed."}), 502
    return jsonify({"success": True, **data})
