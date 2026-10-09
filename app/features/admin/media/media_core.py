"""media_core.py — the admin Media manager (/admin/media).

Two kinds of files are managed:

* the **library**: the site's own images, shipped with the code —
  static/images/ (root, formats/, rulezy/, …) and static/image/ (logos,
  documentation screenshots, …). They can be replaced (same name, so nothing
  that points at them breaks), renamed, deleted, and new ones uploaded. Where
  each one is used is found by scanning the code and the blog covers.

* the **uploads**: what users and features stored at run time, by category —
  profile pictures, blog covers / attachments / graph pictures, workspace
  files, Pivotick backgrounds. Each file says what it belongs to; deleting one
  also clears that reference in the database.

Every path is resolved inside its root (no way out with ".."), only images
are accepted in, checked by their content, and an SVG carrying script is refused.
"""
import os
import re
import time
from io import BytesIO

from flask import current_app

from app import db

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.bmp'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._ -]{0,120}$')

# key -> (label, path under the app root, url prefix, description)
LIBRARY_ROOTS = {
    'images': ('Site images', ('static', 'images'), '/static/images',
               'Images of the pages: rule formats logos, Rulezy, covers…'),
    'image': ('Logos & docs', ('static', 'image'), '/static/image',
              'The Rulezet logos, documentation screenshots, Pivotick assets…'),
}

# key -> (label, icon, path under the app root, public url prefix or None)
UPLOAD_CATEGORIES = {
    'avatars':   ('Profile pictures', 'fa-user-circle', ('static', 'uploads', 'avatars'), '/static/uploads/avatars'),
    'blog':      ('Blog covers', 'fa-newspaper', ('static', 'uploads', 'blog'), '/static/uploads/blog'),
    'blog_files': ('Blog attachments & graphs', 'fa-paperclip', ('uploads', 'blog'), None),
    'workspace': ('Workspace files', 'fa-layer-group', ('uploads', 'workspace'), None),
    'pivotick':  ('Pivotick backgrounds', 'fa-diagram-project', ('static', 'uploads', 'pivotick_backgrounds'),
                  '/static/uploads/pivotick_backgrounds'),
    'game':      ('Game', 'fa-gamepad', ('static', 'uploads', 'game'), '/static/uploads/game'),
}


# ── paths ────────────────────────────────────────────────────────────────────

def _root_dir(parts):
    return os.path.realpath(os.path.join(current_app.root_path, *parts))


def library_dir(root):
    if root not in LIBRARY_ROOTS:
        raise ValueError('Unknown library.')
    return _root_dir(LIBRARY_ROOTS[root][1])


def upload_dir(category):
    if category not in UPLOAD_CATEGORIES:
        raise ValueError('Unknown category.')
    return _root_dir(UPLOAD_CATEGORIES[category][2])


def safe_path(base, rel, must_exist=True):
    """`rel` resolved inside `base`, or ValueError — never a path outside it."""
    rel = (rel or '').replace('\\', '/').strip('/')
    if not rel or any(part in ('', '.', '..') for part in rel.split('/')):
        raise ValueError('Invalid path.')
    path = os.path.realpath(os.path.join(base, rel))
    if os.path.commonpath([path, base]) != base:
        raise ValueError('Invalid path.')
    if must_exist and not os.path.isfile(path):
        raise ValueError('File not found.')
    return path


def _file_info(path, base, url_prefix):
    rel = os.path.relpath(path, base).replace(os.sep, '/')
    stat = os.stat(path)
    ext = os.path.splitext(path)[1].lower()
    info = {
        'name': os.path.basename(path),
        'rel': rel,
        'folder': os.path.dirname(rel),
        'ext': ext,
        'size': stat.st_size,
        'mtime': int(stat.st_mtime),
        'is_image': ext in IMAGE_EXTENSIONS,
        'url': f'{url_prefix}/{rel}?v={int(stat.st_mtime)}' if url_prefix else None,
        'width': None, 'height': None,
    }
    if info['is_image'] and ext not in ('.svg', '.ico'):
        try:
            from PIL import Image
            with Image.open(path) as im:
                info['width'], info['height'] = im.size
        except Exception:
            pass
    return info


def _walk(base):
    for dirpath, _dirs, files in os.walk(base):
        for name in sorted(files):
            if name.startswith('.'):
                continue
            yield os.path.join(dirpath, name)


# ── where library images are used ───────────────────────────────────────────

_SCAN_DIRS = (('templates',), ('static', 'js'), ('static', 'css'), ('features',), ('api',), ('core',))
_SCAN_EXT = {'.html', '.js', '.css', '.py', '.md', '.json'}
_SCAN_SKIP = ('static/js/pivotick.iife.js', 'static/pivograph/', 'features/admin/media/')   # not this manager itself
_scan_cache = {'at': 0, 'files': None}


def _code_files():
    """(relative path, text) of the app's source files — cached a minute."""
    if _scan_cache['files'] is not None and time.time() - _scan_cache['at'] < 60:
        return _scan_cache['files']
    files = []
    root = current_app.root_path
    candidates = [os.path.join(root, *d) for d in _SCAN_DIRS] + [root]
    for top in candidates:
        if not os.path.isdir(top):
            continue
        walker = os.walk(top) if top != root else [(root, [], os.listdir(root))]
        for dirpath, dirs, names in walker:
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'modules', 'pivograph')]
            for name in names:
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, root).replace(os.sep, '/')
                if os.path.splitext(name)[1] not in _SCAN_EXT or rel.startswith(_SCAN_SKIP) or not os.path.isfile(path):
                    continue
                if os.path.getsize(path) > 2 * 1024 * 1024 or name.endswith('.min.js'):
                    continue
                try:
                    with open(path, encoding='utf-8', errors='ignore') as fp:
                        files.append((rel, fp.read()))
                except OSError:
                    pass
    _scan_cache.update(at=time.time(), files=files)
    return files


def invalidate_scan():
    _scan_cache.update(at=0, files=None)


def library_references(root, rel):
    """Where a library image is used: code files mentioning its path (or, in
    Python, its quoted file name — e.g. the formats catalog), and blog posts
    using it as their cover."""
    from app.core.db_class.db import BlogPost
    static_path = f'{LIBRARY_ROOTS[root][1][-1]}/{rel}'          # images/formats/yara.png
    name = os.path.basename(rel)
    quoted = (f'"{name}"', f"'{name}'")
    code = []
    for path, text in _code_files():
        if static_path in text or (path.endswith('.py') and any(q in text for q in quoted)):
            code.append(path)
    url = f'{LIBRARY_ROOTS[root][2]}/{rel}'
    posts = BlogPost.query.filter(BlogPost.cover_image_url.like(f'{url}%')).all()
    return {
        'code': sorted(code),
        'posts': [{'uuid': p.uuid, 'title': p.title} for p in posts],
    }


# ── library ──────────────────────────────────────────────────────────────────

def list_library(root, with_refs=True):
    base = library_dir(root)
    files = []
    for path in _walk(base):
        info = _file_info(path, base, LIBRARY_ROOTS[root][2])
        if not info['is_image']:
            continue
        if with_refs:
            refs = library_references(root, info['rel'])
            info['refs'] = refs
            info['ref_count'] = len(refs['code']) + len(refs['posts'])
        files.append(info)
    folders = sorted({f['folder'] for f in files})
    return {'root': root, 'label': LIBRARY_ROOTS[root][0], 'folders': folders, 'files': files}


def _check_image(data, ext):
    """Raise ValueError unless `data` is an image of type `ext`."""
    if not data:
        raise ValueError('The file is empty.')
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError('Image too large (max 10 MB).')
    if ext == '.svg':
        text = data[:2_000_000].decode('utf-8', errors='ignore').lower()
        if '<svg' not in text:
            raise ValueError('This is not an SVG image.')
        if re.search(r'<script|\son[a-z]+\s*=|javascript:|<foreignobject', text):
            raise ValueError('SVG images with scripts or event handlers are not allowed.')
        return
    if ext == '.ico':
        if not data.startswith(b'\x00\x00\x01\x00'):
            raise ValueError('This is not an ICO image.')
        return
    from PIL import Image
    expected = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.gif': 'GIF', '.webp': 'WEBP', '.bmp': 'BMP'}[ext]
    try:
        with Image.open(BytesIO(data)) as im:
            fmt = im.format
            im.verify()
    except Exception:
        raise ValueError('This file is not a valid image.')
    if fmt != expected:
        raise ValueError(f'The file is a {fmt} image, not {ext} — keep the same type to keep the same name.')


def replace_file(path, data):
    """Overwrite `path` with `data`, same name and type (checked)."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        raise ValueError('Only images can be replaced here.')
    _check_image(data, ext)
    tmp = path + '.tmp-replace'
    with open(tmp, 'wb') as fp:
        fp.write(data)
    os.replace(tmp, path)
    invalidate_scan()


_FOLDER_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,40}$')


def upload_library(root, folder, filename, data, create_folder=False):
    """Add an image to `folder` of a library ('' = its root). With
    `create_folder`, the folder (simple names, one or more levels) is made."""
    base = library_dir(root)
    folder = (folder or '').strip().strip('/')
    if folder and not all(_FOLDER_RE.match(part) for part in folder.split('/')):
        raise ValueError('Folder names: letters, digits, "-" and "_" only.')
    target_dir = base if not folder else os.path.dirname(safe_path(base, f'{folder}/x', must_exist=False))
    if os.path.commonpath([target_dir, base]) != base:
        raise ValueError('Unknown folder.')
    if not os.path.isdir(target_dir):
        if not create_folder:
            raise ValueError('Unknown folder.')
        os.makedirs(target_dir)
    name = os.path.basename(filename or '')
    ext = os.path.splitext(name)[1].lower()
    if not _NAME_RE.match(name) or ext not in IMAGE_EXTENSIONS:
        raise ValueError('Use a simple file name ending with an image extension (png, jpg, gif, webp, svg…).')
    path = os.path.join(target_dir, name)
    if os.path.exists(path):
        raise ValueError('A file with this name already exists here — use Replace to change it.')
    _check_image(data, ext)
    with open(path, 'wb') as fp:
        fp.write(data)
    invalidate_scan()
    return _file_info(path, base, LIBRARY_ROOTS[root][2])


def rename_library(root, rel, new_name):
    """Rename a library image (same folder, same extension). Blog covers that
    used it follow; code references are the caller's to update (listed)."""
    from app.core.db_class.db import BlogPost
    base = library_dir(root)
    path = safe_path(base, rel)
    ext = os.path.splitext(path)[1].lower()
    new_name = (new_name or '').strip()
    if not new_name.lower().endswith(ext):
        new_name += ext
    if not _NAME_RE.match(new_name) or os.path.splitext(new_name)[1].lower() != ext:
        raise ValueError(f'Use a simple file name, keeping the {ext} extension.')
    new_path = os.path.join(os.path.dirname(path), new_name)
    if os.path.exists(new_path):
        raise ValueError('A file with this name already exists here.')
    refs = library_references(root, rel)
    os.rename(path, new_path)
    new_rel = os.path.relpath(new_path, base).replace(os.sep, '/')
    old_url, new_url = f'{LIBRARY_ROOTS[root][2]}/{rel}', f'{LIBRARY_ROOTS[root][2]}/{new_rel}'
    for post in BlogPost.query.filter(BlogPost.cover_image_url.like(f'{old_url}%')).all():
        post.cover_image_url = new_url
    db.session.commit()
    invalidate_scan()
    return {'rel': new_rel, 'code_refs': refs['code'], 'posts_updated': len(refs['posts'])}


def delete_library(root, rel):
    """Delete a library image. Blog covers that used it are cleared."""
    from app.core.db_class.db import BlogPost
    base = library_dir(root)
    path = safe_path(base, rel)
    refs = library_references(root, rel)
    url = f'{LIBRARY_ROOTS[root][2]}/{rel}'
    for post in BlogPost.query.filter(BlogPost.cover_image_url.like(f'{url}%')).all():
        post.cover_image_url = None
    db.session.commit()
    os.remove(path)
    invalidate_scan()
    return {'code_refs': refs['code'], 'posts_cleared': len(refs['posts'])}


# ── uploads ──────────────────────────────────────────────────────────────────

def _owners(category):
    """filename / relative path -> what it belongs to, for one category."""
    from app.core.db_class.db import User, BlogPost, BlogPostFile, Workspace, WorkspaceFile, PivotickBackground
    owners = {}
    if category == 'avatars':
        for u in User.query.filter(User.profile_picture.isnot(None)).all():
            owners[u.profile_picture] = {'label': f'Profile picture of {u.get_username()}',
                                         'link': f'/account/detail_user/{u.id}'}
    elif category == 'blog':
        for p in BlogPost.query.filter(BlogPost.cover_image_url.like('/static/uploads/blog/%')).all():
            rel = p.cover_image_url[len('/static/uploads/blog/'):].split('?')[0]
            owners[rel] = {'label': f'Cover of "{p.title}"', 'link': f'/blog/post/{p.uuid}'}
    elif category == 'blog_files':
        for f in BlogPostFile.query.all():
            post = BlogPost.query.get(f.post_id)
            owners[f.stored_name] = {'label': f'Attachment "{f.original_name}" of "{post.title if post else "?"}"',
                                     'link': f'/blog/post/{post.uuid}' if post else None}
        for p in BlogPost.query.filter(BlogPost.graph.isnot(None)).all():
            owners[f'graph-{p.uuid}.png'] = {'label': f'Graph picture of "{p.title}"', 'link': f'/blog/post/{p.uuid}'}
    elif category == 'workspace':
        for f in WorkspaceFile.query.all():
            ws = Workspace.query.get(f.workspace_id)
            if ws:
                owners[f'{ws.uuid}/{f.stored_name}'] = {'label': f'"{f.original_name}" in workspace "{ws.name}"',
                                                        'link': f'/workspace/{ws.uuid}'}
    elif category == 'pivotick':
        for bg in PivotickBackground.query.all():
            owners[bg.filename] = {'label': f'Pivotick background "{getattr(bg, "name", bg.filename)}"', 'link': '/admin/pivotick'}
    return owners


def list_uploads():
    out = []
    for key, (label, icon, _parts, url_prefix) in UPLOAD_CATEGORIES.items():
        base = upload_dir(key)
        files = []
        if os.path.isdir(base):
            owners = _owners(key)
            for path in _walk(base):
                info = _file_info(path, base, url_prefix)
                if not info['url']:                         # private: served by the admin route
                    info['url'] = f'/admin/media/file/{key}/{info["rel"]}?v={info["mtime"]}'
                info['owner'] = owners.get(info['rel'])
                files.append(info)
        out.append({'key': key, 'label': label, 'icon': icon, 'files': files,
                    'size': sum(f['size'] for f in files)})
    return out


def delete_upload(category, rel):
    """Delete an uploaded file and what points at it in the database."""
    from app.core.db_class.db import User, BlogPost, BlogPostFile, Workspace, WorkspaceFile, PivotickBackground
    path = safe_path(upload_dir(category), rel)
    if category == 'avatars':
        for u in User.query.filter_by(profile_picture=rel).all():
            u.profile_picture = None
    elif category == 'blog':
        for p in BlogPost.query.filter(BlogPost.cover_image_url.like(f'/static/uploads/blog/{rel}%')).all():
            p.cover_image_url = None
    elif category == 'blog_files':
        BlogPostFile.query.filter_by(stored_name=rel).delete()
    elif category == 'workspace' and '/' in rel:
        ws_uuid, stored = rel.split('/', 1)
        ws = Workspace.query.filter_by(uuid=ws_uuid).first()
        if ws:
            WorkspaceFile.query.filter_by(workspace_id=ws.id, stored_name=stored).delete()
    elif category == 'pivotick':
        PivotickBackground.query.filter_by(filename=rel).delete()
    db.session.commit()
    os.remove(path)


def replace_upload(category, rel, data):
    replace_file(safe_path(upload_dir(category), rel), data)
