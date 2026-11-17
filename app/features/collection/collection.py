"""Collections blueprint (/collection) — a user's private folders of rules and
bundles. Every route is for the logged-in user's own data only; logic in
collection_core.py."""
from flask import Blueprint, jsonify, redirect, request
from flask_login import current_user, login_required

from app.core.utils.activity_log import log_activity
from . import collection_core as CC

collection_blueprint = Blueprint('collection', __name__, template_folder='templates', static_folder='static')


def _body():
    """The JSON body as a dict ({} for anything else: list, string, invalid JSON)."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@collection_blueprint.before_request
@login_required
def _logged_in():
    """Every collection route needs a logged-in user."""
    return None


@collection_blueprint.route('/', methods=['GET'])
def index():
    """Folders live in the "My Folders" tab of My rules; old links land there
    with their folder / item / view."""
    args = {k: v for k, v in request.args.items() if k in ('folder', 'item', 'view') and str(v).isalnum()}
    query = ''.join(f"&{k}={v}" for k, v in args.items())
    return redirect('/rule/owner_rules?tab=folders' + query)


@collection_blueprint.route('/api/tree', methods=['GET'])
def api_tree():
    CC.ensure_defaults(current_user.id)
    return jsonify({"folders": CC.tree(current_user.id), "summary": CC.summary(current_user.id)}), 200


@collection_blueprint.route('/api/folders', methods=['POST'])
def api_create_folder():
    f, msg = CC.create_folder(current_user.id, _body())
    if not f:
        return jsonify({"message": msg}), 400
    log_activity("collection.folder_create", f"Folder '{f.name}' created",
                 target_type="collection", target_id=f.id, actor_id=current_user.id)
    return jsonify({"message": msg, "folder": f.to_json()}), 201


@collection_blueprint.route('/api/folders/<int:folder_id>', methods=['PATCH'])
def api_update_folder(folder_id):
    f, msg = CC.update_folder(current_user.id, folder_id, _body())
    if not f:
        return jsonify({"message": msg}), 400
    return jsonify({"message": msg, "folder": f.to_json()}), 200


@collection_blueprint.route('/api/folders/<int:folder_id>', methods=['DELETE'])
def api_delete_folder(folder_id):
    if not CC.delete_folder(current_user.id, folder_id):
        return jsonify({"message": "Folder not found."}), 404
    log_activity("collection.folder_delete", f"Folder #{folder_id} deleted",
                 target_type="collection", target_id=folder_id, actor_id=current_user.id)
    return jsonify({"message": "Folder deleted."}), 200


@collection_blueprint.route('/api/folders/reorder', methods=['POST'])
def api_reorder():
    data = request.get_json(silent=True)
    CC.reorder_folders(current_user.id, data.get('ids', []) if isinstance(data, dict) else [])
    return jsonify({"message": "Order saved."}), 200


@collection_blueprint.route('/api/items', methods=['GET'])
def api_items():
    a = request.args
    data = CC.list_items(current_user.id, folder_id=a.get('folder', type=int), view=a.get('view'),
                         status=a.get('status'), kind=a.get('kind'), search=a.get('search'),
                         page=a.get('page', 1, type=int), per_page=a.get('per_page', 20, type=int))
    return jsonify(data), 200


@collection_blueprint.route('/api/items', methods=['POST'])
def api_add_items():
    d = _body()
    added, msg = CC.add_items(current_user, d.get('folder_ids') or [], d.get('rule_ids') or [],
                              d.get('bundle_ids') or [], note=d.get('note'), remind_at=d.get('remind_at'),
                              status=d.get('status'))
    code = 200 if (added or msg.startswith('Already')) else 400
    if added:
        log_activity("collection.items_add", f"{added} item(s) added to folders",
                     target_type="collection", actor_id=current_user.id)
    return jsonify({"message": msg, "added": added}), code


@collection_blueprint.route('/api/items/<int:item_id>', methods=['PATCH'])
def api_update_item(item_id):
    item, msg = CC.update_item(current_user.id, item_id, _body())
    if not item:
        return jsonify({"message": msg}), 400
    return jsonify({"message": msg}), 200


@collection_blueprint.route('/api/items/remove', methods=['POST'])
def api_remove_items():
    n = CC.remove_items(current_user.id, (_body()).get('ids') or [])
    return jsonify({"message": f"{n} item(s) removed.", "removed": n}), 200


@collection_blueprint.route('/api/membership/<string:kind>/<int:object_id>', methods=['GET'])
def api_membership(kind, object_id):
    if kind not in ('rule', 'bundle'):
        return jsonify({"message": "Unknown kind."}), 400
    CC.ensure_defaults(current_user.id)
    return jsonify({"folders": CC.tree(current_user.id),
                    "membership": CC.membership(current_user.id, kind, object_id)}), 200


@collection_blueprint.route('/api/membership/<string:kind>/<int:object_id>/<int:folder_id>', methods=['DELETE'])
def api_remove_membership(kind, object_id, folder_id):
    if kind not in ('rule', 'bundle'):
        return jsonify({"message": "Unknown kind."}), 400
    n = CC.remove_object(current_user.id, folder_id, kind, object_id)
    return jsonify({"message": "Removed from the folder." if n else "Not in that folder.", "removed": n}), 200


@collection_blueprint.route('/api/folders/<int:folder_id>/rule_ids', methods=['GET'])
def api_folder_rule_ids(folder_id):
    return jsonify({"ids": CC.rule_ids_of_folder(current_user.id, folder_id)}), 200
