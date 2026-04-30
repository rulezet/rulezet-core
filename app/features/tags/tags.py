from flask import Blueprint, flash, jsonify, render_template, request
from flask_login import current_user, login_required
import app.features.tags.tags_core as tags_core


tags_blueprint = Blueprint(
    'tags',
    __name__,
    template_folder='templates',
    static_folder='static',
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _admin_only():
    if not current_user.is_admin():
        return {"status": "error", "message": "Admin access required.",
                "toast_class": "danger-subtle"}, 403
    return None


def _can_edit_tag(tag_id):
    """Return error response if current user cannot edit this tag."""
    from app.core.db_class.db import Tag
    tag = Tag.query.get(tag_id)
    if not tag:
        return {"status": "error", "message": "Tag not found."}, 404
    if not current_user.is_admin() and tag.created_by != current_user.id:
        return {"status": "error", "message": "You can only edit your own tags.",
                "toast_class": "danger-subtle"}, 403
    return None


def _can_delete_tag(tag_id):
    """Return error response if current user cannot delete this tag."""
    from app.core.db_class.db import Tag
    tag = Tag.query.get(tag_id)
    if not tag:
        return {"status": "error", "message": "Tag not found."}, 404
    if not current_user.is_admin() and tag.created_by != current_user.id:
        return {"status": "error", "message": "You can only delete your own tags.",
                "toast_class": "danger-subtle"}, 403
    return None


# ─── Pages ───────────────────────────────────────────────────────────────────

@tags_blueprint.route('/admin/list', methods=['GET'])
@login_required
def list_tags():
    if not current_user.is_admin():
        flash('You need to be admin to access this page.', 'danger')
        return render_template("access_denied.html")
    return render_template('tags/list.html')


@tags_blueprint.route('/my_tags', methods=['GET'])
@login_required
def my_tags():
    return render_template("tags/my_tags.html")


# ─── Tag listing ─────────────────────────────────────────────────────────────

@tags_blueprint.route('/get_tags', methods=['GET'])
@login_required
def get_tags():
    err = _admin_only()
    if err: return err
    pagination = tags_core.get_tags(request.args)
    return {
        "status": "success",
        "tags": [t.to_json() for t in pagination.items],
        "total_pages": pagination.pages,
        "total_tags": pagination.total,
    }, 200


@tags_blueprint.route('/get_tags_bundle', methods=['GET'])
@login_required
def get_tags_bundle():
    pagination = tags_core.get_tags_bundle(request.args)
    return {
        "status": "success",
        "tags": [t.to_json() for t in pagination.items],
        "total_pages": pagination.pages,
        "total_tags": pagination.total,
    }, 200


@tags_blueprint.route('/get_all_tags', methods=['GET'])
@login_required
def get_all_tags():
    tags = tags_core.get_all_tags(request.args)
    return {"status": "success", "tags": [t.to_json() for t in tags], "total_tags": len(tags)}, 200


@tags_blueprint.route('/get_all_tags_by_type', methods=['GET'])
@login_required
def get_all_tags_by_type():
    tags = tags_core.get_all_tags_by_type(request.args)
    return {"status": "success", "tags": [t.to_json() for t in tags], "total_tags": len(tags)}, 200


@tags_blueprint.route('/get_my_tags', methods=['GET'])
@login_required
def get_my_tags():
    return jsonify([t.to_json() for t in tags_core.get_my_tags()])


@tags_blueprint.route('/get_my_tags_paged', methods=['GET'])
@login_required
def get_my_tags_paged():
    """Paginated personal tags (Manual source, owned by current user)."""
    pagination = tags_core.get_my_tags_paged(request.args)
    return {
        "status": "success",
        "tags": [t.to_json() for t in pagination.items],
        "total_tags": pagination.total,
        "total_pages": pagination.pages,
    }, 200


# ─── Family operations (admin only) ──────────────────────────────────────────

@tags_blueprint.route('/get_family', methods=['GET'])
@login_required
def get_family():
    err = _admin_only()
    if err: return err
    family = request.args.get('family')
    source = request.args.get('source')
    if not family:
        return {"status": "error", "message": "Family is required."}, 400
    tags = tags_core.get_tags_by_family(family, source)
    return {"status": "success", "tags": [t.to_json() for t in tags], "total": len(tags)}, 200


@tags_blueprint.route('/delete_family', methods=['POST'])
@login_required
def delete_family():
    err = _admin_only()
    if err: return err
    data = request.json or {}
    family = data.get('family')
    source = data.get('source')
    if not family:
        return {"status": "error", "message": "Family is required."}, 400
    deleted, msg = tags_core.remove_family(family, source)
    return {"status": "success", "deleted": deleted, "message": msg, "toast_class": "success-subtle"}, 200


# ─── Single tag mutations ─────────────────────────────────────────────────────

@tags_blueprint.route('/remove_tag', methods=['GET'])
@login_required
def remove_tag():
    err = _admin_only()
    if err: return err
    tag_id = request.args.get("tag_id")
    success, message = tags_core.remove_tag(tag_id)
    cls = "success-subtle" if success else "danger-subtle"
    return {"status": "success" if success else "error", "message": message, "toast_class": cls}, (200 if success else 500)


@tags_blueprint.route('/remove_tags_bulk', methods=['POST'])
@login_required
def remove_tags_bulk():
    """Bulk delete tags. Admin: any tags. User: only their own Manual tags."""
    data = request.json or {}
    ids  = data.get('ids', [])
    if not isinstance(ids, list):
        return {"status": "error", "message": "ids must be a list."}, 400

    # non-admins: filter to only their own tags
    if not current_user.is_admin():
        from app.core.db_class.db import Tag
        owned = {t.id for t in Tag.query.filter(
            Tag.id.in_([int(i) for i in ids]),
            Tag.created_by == current_user.id,
            Tag.source == 'Manual',
        ).all()}
        ids = [i for i in ids if int(i) in owned]
        if not ids:
            return {"status": "error", "message": "No eligible tags to delete.", "toast_class": "warning-subtle"}, 400

    deleted, msg = tags_core.remove_tags_bulk(ids)
    if deleted > 0:
        return {"status": "success", "deleted": deleted, "message": msg, "toast_class": "success-subtle"}, 200
    return {"status": "error", "deleted": 0, "message": msg, "toast_class": "danger-subtle"}, 500


@tags_blueprint.route('/toggle_visibility', methods=['GET'])
@login_required
def toggle_visibility():
    err = _admin_only()
    if err: return err
    tag_uuid = request.args.get("tag_uuid")
    if not tag_uuid:
        return {"status": "error", "message": "Tag UUID is required."}, 400
    success, message = tags_core.toggle_tag_visibility(tag_uuid)
    cls = "success-subtle" if success else "danger-subtle"
    return {"status": "success" if success else "error", "message": message, "toast_class": cls}, (200 if success else 500)


@tags_blueprint.route('/toggle_status', methods=['GET'])
@login_required
def toggle_status():
    err = _admin_only()
    if err: return err
    tag_uuid = request.args.get("tag_uuid")
    if not tag_uuid:
        return {"status": "error", "message": "Tag UUID is required."}, 400
    success, message = tags_core.toggle_tag_status(tag_uuid)
    cls = "success-subtle" if success else "danger-subtle"
    return {"status": "success" if success else "error", "message": message, "toast_class": cls}, (200 if success else 500)


@tags_blueprint.route('/edit_tag/<int:tag_id>', methods=['POST'])
@login_required
def edit_tag(tag_id):
    # admin: edit anything / user: only their own Manual tags
    err = _can_edit_tag(tag_id)
    if err: return err
    if not tag_id:
        return {"status": "error", "message": "Tag ID is required."}, 400
    success, message = tags_core.edit_tag(request.json, tag_id)
    if success:
        return {"status": "success", "message": message, "toast_class": "success-subtle"}, 200
    if not message:
        return {"status": "error", "message": "Error while updating tag", "toast_class": "danger-subtle"}, 500
    return {"status": "error", "message": message, "toast_class": "warning-subtle"}, 201


@tags_blueprint.route('/create_tag', methods=['POST'])
@login_required
def create_tag():
    data = request.json
    if not data or not data.get('name'):
        return {"status": "error", "message": "Tag name is required."}, 400
    if 'visibility' not in data:
        data['visibility'] = 'private'
    tag = tags_core.create_tag(data, current_user)
    if tag is False:
        return {"status": "error", "message": "A tag with this name already exists.", "toast_class": "warning-subtle"}, 201
    if tag is None:
        return {"status": "error", "message": "Error while creating tag", "toast_class": "danger-subtle"}, 500
    return {
        "status": "success",
        "message": "Tag created successfully!",
        "tag": {"id": tag.id, "uuid": tag.uuid, "name": tag.name, "color": tag.color},
        "toast_class": "success-subtle",
    }, 200


@tags_blueprint.route('/delete_tag/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    # admin: delete anything / user: only their own tags
    err = _can_delete_tag(tag_id)
    if err: return err
    success, msg = tags_core.remove_tag(tag_id)
    cls = "success-subtle" if success else "danger-subtle"
    return jsonify({"status": "success" if success else "error", "message": msg, "toast_class": cls}), (200 if success else 500)


# ─── MISP Taxonomies ─────────────────────────────────────────────────────────

@tags_blueprint.route('/get_tags_misp', methods=['GET'])
@login_required
def get_tags_misp():
    err = _admin_only()
    if err: return err
    result = tags_core.list_all_misp_taxonomies_meta(request.args)
    return {
        "status": "success",
        "tags": result["items"],
        "total_pages": result["pages"],
        "total_tags": result["total"],
        "page": result["page"],
    }, 200


@tags_blueprint.route('/add_tags_misp', methods=['GET'])
@login_required
def add_tag_misp():
    err = _admin_only()
    if err: return err
    uuid_param = request.args.get("uuid")
    if not uuid_param:
        return {"success": False, "message": "UUID is required.", "toast_class": "danger-subtle"}, 400
    success, message = tags_core.add_tags_from_misp_taxonomy(uuid_param, created_by=current_user)
    cls = "success-subtle" if success else "danger-subtle"
    return {"success": bool(success), "message": message, "toast_class": cls}, (200 if success else 500)


# ─── MISP Galaxies ───────────────────────────────────────────────────────────

@tags_blueprint.route("/get_tags_galaxy", methods=['GET'])
@login_required
def get_tags_galaxy():
    err = _admin_only()
    if err: return err
    result = tags_core.list_all_misp_galaxies_meta(request.args)
    return jsonify({
        "tags": result["items"],
        "total_tags": result["total"],
        "total_pages": result["pages"],
        "current_page": result["page"],
    })


@tags_blueprint.route("/get_galaxy_clusters/<uuid_param>", methods=['GET'])
@login_required
def get_galaxy_clusters(uuid_param):
    err = _admin_only()
    if err: return err
    result, error = tags_core.get_galaxy_clusters(uuid_param)
    if error:
        return jsonify({"message": error, "toast_class": "danger-subtle"}), 404
    return jsonify(result)


@tags_blueprint.route("/add_tags_galaxy", methods=['GET', 'POST'])
@login_required
def add_tags_galaxy():
    err = _admin_only()
    if err: return err
    if request.method == 'POST':
        data          = request.json or {}
        uuid_param    = data.get("uuid")
        cluster_uuids = data.get("cluster_uuids") or None
    else:
        uuid_param    = request.args.get("uuid")
        cluster_uuids = None
    success, message = tags_core.add_tags_from_misp_galaxy(uuid_param, current_user, cluster_uuids)
    cls = "success-subtle" if success else "danger-subtle"
    return jsonify({"message": message, "toast_class": cls}), (200 if success else 400)