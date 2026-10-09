"""media_routes.py — the admin Media manager (/admin/media): the site's images
(library) and the uploaded files, see media_core.py. Admin only."""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app.core.utils.activity_log import log_activity
from app.features.admin.media import media_core as MediaModel

media_blueprint = Blueprint('media', __name__)


@media_blueprint.before_request
def _require_admin():
    if not current_user.is_authenticated:
        return redirect(url_for('account.login'))
    if not current_user.is_admin():
        abort(403)


def _error(exc, code=400):
    return jsonify({'success': False, 'message': str(exc)}), code


def _upload_data():
    f = request.files.get('file')
    if not f or not f.filename:
        raise ValueError('No file sent.')
    return f.filename, f.read(MediaModel.MAX_IMAGE_BYTES + 1)


@media_blueprint.route('/admin/media', methods=['GET'])
def media_page():
    return render_template('admin/media.html',
                           library_roots={k: v[0] for k, v in MediaModel.LIBRARY_ROOTS.items()})


# ── library (static/images, static/image) ──────────────────────────────────

@media_blueprint.route('/admin/media/library.json', methods=['GET'])
def library_list():
    root = request.args.get('root', 'images')
    try:
        data = MediaModel.list_library(root, with_refs=request.args.get('refs', '1') == '1')
    except ValueError as exc:
        return _error(exc)
    return jsonify({'success': True, **data})


@media_blueprint.route('/admin/media/library/replace', methods=['POST'])
def library_replace():
    root, rel = request.form.get('root', ''), request.form.get('rel', '')
    try:
        _name, data = _upload_data()
        MediaModel.replace_file(MediaModel.safe_path(MediaModel.library_dir(root), rel), data)
    except ValueError as exc:
        return _error(exc)
    log_activity('admin.media_replace', f"Replaced site image {root}/{rel}", is_public=False)
    return jsonify({'success': True, 'message': 'Image replaced — same name, nothing to update.'})


@media_blueprint.route('/admin/media/library/upload', methods=['POST'])
def library_upload():
    root, folder = request.form.get('root', ''), request.form.get('folder', '')
    try:
        name, data = _upload_data()
        info = MediaModel.upload_library(root, folder, name, data, create_folder=request.form.get('new_folder') == '1')
    except ValueError as exc:
        return _error(exc)
    log_activity('admin.media_upload', f"Added site image {root}/{info['rel']}", is_public=False)
    return jsonify({'success': True, 'file': info, 'message': 'Image added.'})


@media_blueprint.route('/admin/media/library/rename', methods=['POST'])
def library_rename():
    data = request.get_json(silent=True) or {}
    root, rel = data.get('root', ''), data.get('rel', '')
    try:
        result = MediaModel.rename_library(root, rel, data.get('name', ''))
    except ValueError as exc:
        return _error(exc)
    log_activity('admin.media_rename', f"Renamed site image {root}/{rel} → {result['rel']}", is_public=False)
    return jsonify({'success': True, **result})


@media_blueprint.route('/admin/media/library/delete', methods=['POST'])
def library_delete():
    data = request.get_json(silent=True) or {}
    root, rel = data.get('root', ''), data.get('rel', '')
    try:
        result = MediaModel.delete_library(root, rel)
    except ValueError as exc:
        return _error(exc)
    log_activity('admin.media_delete', f"Deleted site image {root}/{rel}", is_public=False)
    return jsonify({'success': True, **result})


# ── uploads ─────────────────────────────────────────────────────────────────

@media_blueprint.route('/admin/media/uploads.json', methods=['GET'])
def uploads_list():
    return jsonify({'success': True, 'categories': MediaModel.list_uploads()})


@media_blueprint.route('/admin/media/file/<string:category>/<path:rel>', methods=['GET'])
def upload_file(category, rel):
    """Serve an uploaded file kept outside static/ (blog attachments, workspace files)."""
    try:
        path = MediaModel.safe_path(MediaModel.upload_dir(category), rel)
    except ValueError:
        abort(404)
    resp = send_file(path, as_attachment=request.args.get('download') == '1')
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'"
    return resp


@media_blueprint.route('/admin/media/upload/replace', methods=['POST'])
def upload_replace():
    category, rel = request.form.get('category', ''), request.form.get('rel', '')
    try:
        _name, data = _upload_data()
        MediaModel.replace_upload(category, rel, data)
    except ValueError as exc:
        return _error(exc)
    log_activity('admin.media_replace', f"Replaced uploaded file {category}/{rel}", is_public=False)
    return jsonify({'success': True, 'message': 'File replaced — same name.'})


@media_blueprint.route('/admin/media/upload/delete', methods=['POST'])
def upload_delete():
    data = request.get_json(silent=True) or {}
    category, rel = data.get('category', ''), data.get('rel', '')
    try:
        MediaModel.delete_upload(category, rel)
    except ValueError as exc:
        return _error(exc)
    log_activity('admin.media_delete', f"Deleted uploaded file {category}/{rel}", is_public=False)
    return jsonify({'success': True})


# ── edit an image (remove a flat background, make it square) ────────────────

def _edit_target(data):
    """(base dir, file path, public url prefix, scope) of the image to edit."""
    if data.get('scope') == 'uploads':
        category = data.get('category', '')
        base = MediaModel.upload_dir(category)
        return base, MediaModel.safe_path(base, data.get('rel', '')), MediaModel.UPLOAD_CATEGORIES[category][3], 'uploads'
    root = data.get('root', '')
    base = MediaModel.library_dir(root)
    return base, MediaModel.safe_path(base, data.get('rel', '')), MediaModel.LIBRARY_ROOTS[root][2], 'library'


def _edit_options(data):
    return dict(remove_bg=bool(data.get('remove_bg')), tolerance=data.get('tolerance', 18),
                square=data.get('square', 'none'), padding=data.get('padding', 6), size=data.get('size') or None)


@media_blueprint.route('/admin/media/edit/preview', methods=['POST'])
def edit_preview():
    """The edited image, not stored — for the preview in the drawer."""
    import base64
    data = request.get_json(silent=True) or {}
    try:
        _base, path, _url, _scope = _edit_target(data)
        png = MediaModel.process_image(path, **_edit_options(data))
    except (ValueError, OSError) as exc:
        return _error(exc)
    return jsonify({'success': True, 'image': 'data:image/png;base64,' + base64.b64encode(png).decode(), 'size': len(png)})


@media_blueprint.route('/admin/media/edit/save', methods=['POST'])
def edit_save():
    data = request.get_json(silent=True) or {}
    try:
        base, path, url_prefix, scope = _edit_target(data)
        mode = data.get('mode', 'copy')
        if scope == 'uploads' and mode != 'replace':
            raise ValueError('Uploaded files can only be replaced (nothing would point at a copy).')
        png = MediaModel.process_image(path, **_edit_options(data))
        info = MediaModel.save_processed(base, path, url_prefix, png, mode, data.get('name') or None)
    except (ValueError, OSError) as exc:
        return _error(exc)
    log_activity('admin.media_edit', f"Edited image {data.get('root') or data.get('category')}/{data.get('rel')} ({mode})", is_public=False)
    return jsonify({'success': True, 'file': info,
                    'message': 'Original replaced.' if mode == 'replace' else f"Saved as {info['name']}."})
