import json
import os
import uuid as _uuid_mod
from flask import Blueprint, abort, jsonify, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from . import blog_core as BlogModel
from app.core.utils.activity_log import log_activity

# ── File upload security constants ───────────────────────────────────────────
_ALLOWED_MIME_TYPES = {
    'application/pdf',
    'text/plain', 'text/csv', 'text/markdown',
    'application/json', 'application/xml', 'text/xml',
    'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml',
    'application/zip', 'application/x-tar', 'application/gzip',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
_ALLOWED_EXTENSIONS = {
    'pdf', 'txt', 'csv', 'md', 'json', 'xml',
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg',
    'zip', 'tar', 'gz', 'docx', 'xlsx',
}
_ALLOWED_IMAGE_MIME = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
_ALLOWED_IMAGE_EXT  = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
_MAX_FILE_SIZE      = 10 * 1024 * 1024   # 10 MB
_MAX_COVER_SIZE     =  5 * 1024 * 1024   #  5 MB

def _blog_upload_dir():
    from flask import current_app
    d = os.path.join(current_app.root_path, 'uploads', 'blog')
    os.makedirs(d, exist_ok=True)
    return d

def _cover_upload_dir():
    from flask import current_app
    d = os.path.join(current_app.root_path, 'static', 'uploads', 'blog')
    os.makedirs(d, exist_ok=True)
    return d

blog_blueprint = Blueprint(
    'blog',
    __name__,
    template_folder='templates',
    static_folder='static',
)


def _admin_required():
    """Return a 403 JSON response if the current user is not admin."""
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Admin access required.'}), 403
    return None


# ── Public routes ──────────────────────────────────────────────────────────────

@blog_blueprint.route('/')
def list_posts():
    return render_template('blog/list_blog.html')


@blog_blueprint.route('/post/<string:post_uuid>')
def detail(post_uuid):
    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        abort(404)
    # Private post: only admin or share-key access
    if not post.is_public:
        if not (current_user.is_authenticated and (
                current_user.id == post.user_id or current_user.is_admin())):
            abort(403)
    BlogModel.add_view(post)
    return render_template('blog/detail_blog.html', post=post, shared=False)


@blog_blueprint.route('/share/<string:post_uuid>/<string:key>')
def detail_shared(post_uuid, key):
    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        abort(404)
    if post.share_key != key:
        abort(403)
    BlogModel.add_view(post)
    return render_template('blog/detail_blog.html', post=post, shared=True)


# ── Admin page routes ──────────────────────────────────────────────────────────

@blog_blueprint.route('/admin/')
@login_required
def admin_list():
    if not current_user.is_admin():
        abort(403)
    return render_template('blog/admin_list.html')


@blog_blueprint.route('/admin/create')
@login_required
def admin_create():
    if not current_user.is_admin():
        abort(403)
    return render_template('blog/create_edit.html', is_edit=False, post=None, files_json=[])


@blog_blueprint.route('/admin/edit/<string:post_uuid>')
@login_required
def admin_edit(post_uuid):
    if not current_user.is_admin():
        abort(403)
    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        abort(404)
    files_json = [f.to_json() for f in post.files]
    return render_template('blog/create_edit.html', is_edit=True, post=post, files_json=files_json)


# ── Admin JSON action routes ───────────────────────────────────────────────────

@blog_blueprint.route('/admin/save', methods=['POST'])
@login_required
def admin_save():
    err = _admin_required()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    post_uuid = data.get('uuid')

    try:
        if post_uuid:
            post = BlogModel.get_post_by_uuid(post_uuid)
            if not post:
                return jsonify({'success': False, 'message': 'Post not found.'}), 404
            post = BlogModel.update_post(post, data)
            log_activity(
                'blog.edit', f"Edited blog post '{post.title}'",
                target_type='blog_post', target_id=post.id, target_uuid=post.uuid,
                is_public=post.is_public,
            )
            return jsonify({
                'success': True,
                'message': 'Post updated.',
                'toast_class': 'success-subtle',
                'uuid': post.uuid,
            })
        else:
            post = BlogModel.create_post(data, current_user.id)
            log_activity(
                'blog.create', f"Created blog post '{post.title}'",
                target_type='blog_post', target_id=post.id, target_uuid=post.uuid,
                is_public=post.is_public,
            )
            return jsonify({
                'success': True,
                'message': 'Post created.',
                'toast_class': 'success-subtle',
                'uuid': post.uuid,
            }), 201
    except ValueError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception as exc:
        return jsonify({'success': False, 'message': 'Server error.'}), 500


@blog_blueprint.route('/admin/delete/<string:post_uuid>', methods=['POST'])
@login_required
def admin_delete(post_uuid):
    err = _admin_required()
    if err:
        return err

    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        return jsonify({'success': False, 'message': 'Post not found.'}), 404

    title = post.title
    pid   = post.id
    ok    = BlogModel.delete_post(post.id)
    if ok:
        log_activity('blog.delete', f"Deleted blog post '{title}' (id={pid})",
                     target_type='blog_post', target_id=pid, target_uuid=post_uuid)
        return jsonify({'success': True, 'message': 'Post deleted.', 'toast_class': 'success-subtle'})
    return jsonify({'success': False, 'message': 'Delete failed.', 'toast_class': 'danger-subtle'}), 500


@blog_blueprint.route('/admin/toggle_access/<string:post_uuid>', methods=['POST'])
@login_required
def admin_toggle_access(post_uuid):
    err = _admin_required()
    if err:
        return err

    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        return jsonify({'success': False, 'message': 'Post not found.'}), 404

    is_public = BlogModel.toggle_public(post)
    log_activity(
        'blog.toggle_access',
        f"Toggled post '{post.title}' to {'public' if is_public else 'private'}",
        target_type='blog_post', target_id=post.id, target_uuid=post_uuid,
    )
    return jsonify({'success': True, 'is_public': is_public})


@blog_blueprint.route('/admin/toggle_draft/<string:post_uuid>', methods=['POST'])
@login_required
def admin_toggle_draft(post_uuid):
    err = _admin_required()
    if err:
        return err

    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        return jsonify({'success': False, 'message': 'Post not found.'}), 404

    is_draft, is_public = BlogModel.toggle_draft(post)
    log_activity(
        'blog.toggle_draft',
        f"Toggled post '{post.title}' to {'draft' if is_draft else 'published'}",
        target_type='blog_post', target_id=post.id, target_uuid=post_uuid,
    )
    return jsonify({'success': True, 'is_draft': is_draft, 'is_public': is_public})


@blog_blueprint.route('/admin/regenerate_key/<string:post_uuid>', methods=['POST'])
@login_required
def admin_regenerate_key(post_uuid):
    err = _admin_required()
    if err:
        return err

    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        return jsonify({'success': False, 'message': 'Post not found.'}), 404

    new_key = BlogModel.regenerate_share_key(post)
    share_url = url_for('blog.detail_shared', post_uuid=post_uuid, key=new_key, _external=True)
    return jsonify({'success': True, 'share_key': new_key, 'share_url': share_url})


# ── JSON API ───────────────────────────────────────────────────────────────────

@blog_blueprint.route('/api/posts')
def api_posts():
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search   = request.args.get('search', type=str) or None
    tags_raw = request.args.get('tags', type=str) or ''
    tag_names = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []
    status   = request.args.get('status', type=str) or None

    is_admin = current_user.is_authenticated and current_user.is_admin()
    pagination = BlogModel.get_posts_paginated(page, per_page, search, tag_names, is_admin, status)

    return jsonify({
        'items':       [p.to_json() for p in pagination.items],
        'total':       pagination.total,
        'total_pages': pagination.pages,
        'page':        page,
    })


@blog_blueprint.route('/api/post/<string:post_uuid>')
def api_post(post_uuid):
    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        return jsonify({'error': 'Not found.'}), 404

    if not post.is_public:
        share_key = request.args.get('key')
        if share_key and post.share_key == share_key:
            pass  # valid share-key access
        elif current_user.is_authenticated and (
                current_user.id == post.user_id or current_user.is_admin()):
            pass  # admin / owner
        else:
            return jsonify({'error': 'Forbidden.'}), 403

    data = post.to_json()
    if current_user.is_authenticated and current_user.is_admin():
        data['share_key'] = post.share_key
    return jsonify(data)


# ── Cover image upload ────────────────────────────────────────────────────────

@blog_blueprint.route('/admin/upload_cover/<string:post_uuid>', methods=['POST'])
@login_required
def admin_upload_cover(post_uuid):
    err = _admin_required()
    if err:
        return err

    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        return jsonify({'success': False, 'message': 'Post not found.'}), 404

    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'success': False, 'message': 'No file provided.'}), 400

    original_name = secure_filename(f.filename)
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if ext not in _ALLOWED_IMAGE_EXT:
        return jsonify({'success': False, 'message': f'.{ext} is not allowed. Use PNG, JPG, GIF or WEBP.'}), 400

    mime = f.mimetype or 'application/octet-stream'
    if mime not in _ALLOWED_IMAGE_MIME:
        return jsonify({'success': False, 'message': f'MIME type {mime} is not an accepted image type.'}), 400

    data = f.read(_MAX_COVER_SIZE + 1)
    if len(data) > _MAX_COVER_SIZE:
        return jsonify({'success': False, 'message': 'Image exceeds 5 MB limit.'}), 413

    # Delete old cover file if it was a local upload
    if post.cover_image_url and post.cover_image_url.startswith('/static/uploads/blog/'):
        old_filename = post.cover_image_url.split('/')[-1]
        old_path = os.path.join(_cover_upload_dir(), old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    stored_name = f'{_uuid_mod.uuid4()}.{ext}'
    dest = os.path.join(_cover_upload_dir(), stored_name)
    with open(dest, 'wb') as fp:
        fp.write(data)

    url = f'/static/uploads/blog/{stored_name}'

    from app import db
    post.cover_image_url = url
    import datetime
    post.updated_at = datetime.datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'url': url})


# ── Public file download ───────────────────────────────────────────────────────

@blog_blueprint.route('/file/<string:file_uuid>')
def public_file_download(file_uuid):
    """Download a file attached to a blog post. Respects post visibility."""
    from app.core.db_class.db import BlogPostFile
    bf = BlogPostFile.query.filter_by(uuid=file_uuid).first()
    if not bf:
        abort(404)

    post = BlogModel.get_post_by_uuid_by_id(bf.post_id)
    if not post:
        abort(404)

    if not post.is_public:
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)

    path = os.path.join(_blog_upload_dir(), bf.stored_name)
    if not os.path.exists(path):
        abort(404)

    as_attachment = request.args.get('download', '0') == '1'
    return send_file(path, as_attachment=as_attachment, download_name=bf.original_name, mimetype=bf.mime_type)


# ── File attachment routes ─────────────────────────────────────────────────────

@blog_blueprint.route('/admin/file/upload/<string:post_uuid>', methods=['POST'])
@login_required
def admin_file_upload(post_uuid):
    err = _admin_required()
    if err:
        return err

    post = BlogModel.get_post_by_uuid(post_uuid)
    if not post:
        return jsonify({'success': False, 'message': 'Post not found.'}), 404

    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'success': False, 'message': 'No file provided.'}), 400

    original_name = secure_filename(f.filename)
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if ext not in _ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'message': f'File type .{ext} is not allowed.'}), 400

    mime = f.mimetype or 'application/octet-stream'
    if mime not in _ALLOWED_MIME_TYPES:
        return jsonify({'success': False, 'message': f'MIME type {mime} is not allowed.'}), 400

    # Read with size guard
    data = f.read(_MAX_FILE_SIZE + 1)
    if len(data) > _MAX_FILE_SIZE:
        return jsonify({'success': False, 'message': 'File exceeds 10 MB limit.'}), 413

    file_uuid = str(_uuid_mod.uuid4())
    stored_name = f'{file_uuid}.{ext}'
    dest = os.path.join(_blog_upload_dir(), stored_name)
    with open(dest, 'wb') as fp:
        fp.write(data)

    from app.core.db_class.db import BlogPostFile
    from app import db
    import datetime
    bf = BlogPostFile(
        uuid=file_uuid,
        post_id=post.id,
        original_name=original_name,
        stored_name=stored_name,
        mime_type=mime,
        size_bytes=len(data),
        uploaded_by=current_user.id,
        created_at=datetime.datetime.utcnow(),
    )
    db.session.add(bf)
    db.session.commit()

    log_activity('blog.file_upload', f"Uploaded file '{original_name}' to post id={post.id}",
                 target_type='blog_post', target_id=post.id)
    return jsonify({'success': True, 'file': bf.to_json()})


@blog_blueprint.route('/admin/file/<string:file_uuid>', methods=['GET'])
@login_required
def admin_file_download(file_uuid):
    err = _admin_required()
    if err:
        return err

    from app.core.db_class.db import BlogPostFile
    bf = BlogPostFile.query.filter_by(uuid=file_uuid).first()
    if not bf:
        abort(404)

    path = os.path.join(_blog_upload_dir(), bf.stored_name)
    if not os.path.exists(path):
        abort(404)

    return send_file(path, as_attachment=True, download_name=bf.original_name, mimetype=bf.mime_type)


@blog_blueprint.route('/admin/file/delete/<string:file_uuid>', methods=['POST'])
@login_required
def admin_file_delete(file_uuid):
    err = _admin_required()
    if err:
        return err

    from app.core.db_class.db import BlogPostFile
    from app import db
    bf = BlogPostFile.query.filter_by(uuid=file_uuid).first()
    if not bf:
        return jsonify({'success': False, 'message': 'File not found.'}), 404

    path = os.path.join(_blog_upload_dir(), bf.stored_name)
    if os.path.exists(path):
        os.remove(path)

    db.session.delete(bf)
    db.session.commit()
    return jsonify({'success': True})
