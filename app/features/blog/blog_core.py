import datetime
import re
import secrets
import uuid as uuid_module

from sqlalchemy import or_

from ... import db
from ...core.db_class.db import (
    BlogPost, BlogPostTagAssociation, BlogPostRuleAssociation,
    BlogPostBundleAssociation, BlogPostAttackAssociation, Tag,
    purge_unified_comments,
)


# ── Slug helpers ───────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Convert title to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text[:200]


def _make_slug(title: str, exclude_id: int = None) -> str:
    """Slugify title and append a numeric suffix if already taken."""
    base = _slugify(title)
    candidate = base
    counter = 2
    while True:
        q = BlogPost.query.filter_by(slug=candidate)
        if exclude_id:
            q = q.filter(BlogPost.id != exclude_id)
        if not q.first():
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1


def _make_share_key() -> str:
    return secrets.token_urlsafe(32)


# ── Tag / rule / bundle / attack sync ─────────────────────────────────────────

def _sync_tags(post: BlogPost, tag_names: list) -> None:
    """Replace post's tag associations with the given tag names."""
    BlogPostTagAssociation.query.filter_by(post_id=post.id).delete()
    for name in (tag_names or []):
        name = name.strip()
        if not name:
            continue
        tag = Tag.query.filter_by(name=name).first()
        if tag:
            db.session.add(BlogPostTagAssociation(post_id=post.id, tag_id=tag.id))


def _sync_rules(post: BlogPost, rule_ids: list) -> None:
    BlogPostRuleAssociation.query.filter_by(post_id=post.id).delete()
    for pos, rid in enumerate(rule_ids or []):
        try:
            db.session.add(BlogPostRuleAssociation(
                post_id=post.id, rule_id=int(rid), position=pos
            ))
        except (ValueError, TypeError):
            pass


def _sync_bundles(post: BlogPost, bundle_ids: list) -> None:
    BlogPostBundleAssociation.query.filter_by(post_id=post.id).delete()
    for pos, bid in enumerate(bundle_ids or []):
        try:
            db.session.add(BlogPostBundleAssociation(
                post_id=post.id, bundle_id=int(bid), position=pos
            ))
        except (ValueError, TypeError):
            pass


def _sync_attacks(post: BlogPost, technique_ids: list) -> None:
    BlogPostAttackAssociation.query.filter_by(post_id=post.id).delete()
    for tid in (technique_ids or []):
        tid = str(tid).strip()
        if tid:
            db.session.add(BlogPostAttackAssociation(
                post_id=post.id, technique_id=tid
            ))


# ── CRUD ───────────────────────────────────────────────────────────────────────

GRAPH_MAX_BYTES = 5 * 1024 * 1024     # embedded images (data: URLs) count
GRAPH_MAX_NODES = 3000
GRAPH_MAX_EDGES = 10000


def clean_graph(graph):
    """Check a Pivograph document sent with a post (None removes the graph).
    Returns it unchanged, or raises ValueError with a message for the editor."""
    import json as _json
    if graph is None:
        return None
    if not isinstance(graph, dict):
        raise ValueError("The graph must be a Pivograph JSON document.")
    nodes, edges = graph.get('nodes', []), graph.get('edges', [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("The graph's nodes and edges must be lists.")
    if len(nodes) > GRAPH_MAX_NODES or len(edges) > GRAPH_MAX_EDGES:
        raise ValueError(f"The graph is too big (max {GRAPH_MAX_NODES} nodes, {GRAPH_MAX_EDGES} edges).")
    if len(_json.dumps(graph)) > GRAPH_MAX_BYTES:
        raise ValueError(f"The graph is too big (max {GRAPH_MAX_BYTES // (1024 * 1024)} MB with its images).")
    return graph


def graph_image_path(post) -> str:
    """Where the PNG of a post's graph (for its PDF / Markdown exports) is kept."""
    import os as _os
    from flask import current_app
    d = _os.path.join(current_app.root_path, 'uploads', 'blog')
    _os.makedirs(d, exist_ok=True)
    return _os.path.join(d, f'graph-{post.uuid}.png')


def store_graph_image(post, data_url):
    """Save the PNG sent with the graph (a data:image/png URL), or remove it
    (None). Anything that isn't a PNG under 8 MB is ignored."""
    import base64 as _b64, binascii as _binascii, os as _os
    path = graph_image_path(post)
    if not data_url:
        if _os.path.exists(path):
            _os.remove(path)
        return
    prefix = 'data:image/png;base64,'
    if not isinstance(data_url, str) or not data_url.startswith(prefix) or len(data_url) > 11_000_000:
        return
    try:
        png = _b64.b64decode(data_url[len(prefix):], validate=True)
    except (_binascii.Error, ValueError):
        return
    if not png.startswith(b'\x89PNG\r\n\x1a\n'):
        return
    with open(path, 'wb') as fp:
        fp.write(png)


def create_post(data: dict, user_id: int) -> BlogPost:
    """Create a new BlogPost from the submitted data dict."""
    title = (data.get('title') or '').strip()
    if not title:
        raise ValueError("Title is required.")

    is_draft  = bool(data.get('is_draft', False))
    is_public = bool(data.get('is_public', False)) and not is_draft

    post = BlogPost(
        uuid=str(uuid_module.uuid4()),
        slug=_make_slug(title),
        title=title,
        excerpt=(data.get('excerpt') or '').strip() or None,
        content=data.get('content') or '',
        user_id=user_id,
        is_public=is_public,
        is_draft=is_draft,
        share_key=_make_share_key(),
        view_count=0,
        cve_ids=data.get('cve_ids') or [],
        cover_image_url=(data.get('cover_image_url') or '').strip() or None,
        external_links=data.get('external_links') or [],
        graph=clean_graph(data.get('graph')),
        graph_view='simple' if data.get('graph_view') == 'simple' else 'full',
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
        published_at=datetime.datetime.utcnow() if is_public else None,
    )
    db.session.add(post)
    db.session.flush()  # get post.id before associations
    if post.graph is not None:
        store_graph_image(post, data.get('graph_image'))

    _sync_tags(post, data.get('tag_names') or [])
    _sync_rules(post, data.get('rule_ids') or [])
    _sync_bundles(post, data.get('bundle_ids') or [])
    _sync_attacks(post, data.get('technique_ids') or [])

    db.session.commit()
    return post


def update_post(post: BlogPost, data: dict) -> BlogPost:
    """Update an existing BlogPost in place."""
    title = (data.get('title') or '').strip()
    if not title:
        raise ValueError("Title is required.")

    was_public = post.is_public
    is_draft   = bool(data.get('is_draft', False))
    is_public  = bool(data.get('is_public', False)) and not is_draft

    post.title           = title
    post.slug            = _make_slug(title, exclude_id=post.id)
    post.excerpt         = (data.get('excerpt') or '').strip() or None
    post.content         = data.get('content') or ''
    post.is_public       = is_public
    post.is_draft        = is_draft
    post.cve_ids         = data.get('cve_ids') or []
    post.cover_image_url = (data.get('cover_image_url') or '').strip() or None
    post.external_links  = data.get('external_links') or []
    if 'graph' in data:                      # absent = unchanged, null = removed
        post.graph = clean_graph(data['graph'])
        store_graph_image(post, data.get('graph_image') if post.graph is not None else None)
    if 'graph_view' in data:
        post.graph_view = 'simple' if data['graph_view'] == 'simple' else 'full'
    post.updated_at      = datetime.datetime.utcnow()

    if is_public and not was_public:
        post.published_at = datetime.datetime.utcnow()

    _sync_tags(post, data.get('tag_names') or [])
    _sync_rules(post, data.get('rule_ids') or [])
    _sync_bundles(post, data.get('bundle_ids') or [])
    _sync_attacks(post, data.get('technique_ids') or [])

    db.session.commit()
    return post


def delete_post(post_id: int) -> bool:
    """Hard-delete a post and all its associations (cascade)."""
    post = BlogPost.query.get(post_id)
    if not post:
        return False
    try:
        purge_unified_comments('blog_post', post_id)
        store_graph_image(post, None)        # its graph picture, if any
        db.session.delete(post)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def get_post_by_uuid(post_uuid: str) -> BlogPost | None:
    return BlogPost.query.filter_by(uuid=post_uuid).first()


def get_post_by_uuid_by_id(post_id: int) -> BlogPost | None:
    return BlogPost.query.get(post_id)


# ── JSON export ────────────────────────────────────────────────────────────────

EXPORT_SCHEMA_VERSION = '1.0'

def export_post_json(post: BlogPost, base_url: str) -> dict:
    """Build a portable, safe JSON export of a public blog post.

    Fields intentionally omitted: is_draft, is_public, share_key,
    view_count, user_id, author info, created_at/updated_at, slug.
    Rule/bundle associations are included as reference objects (uuid + label)
    so a receiving instance can match them if the same content exists.
    """
    from ...core.db_class.db import Rule, Bundle

    base = base_url.rstrip('/')

    # Make cover URL absolute if it's a local path
    cover = post.cover_image_url or ''
    if cover.startswith('/'):
        cover = base + cover

    # Resolve rule references (uuid + title, not internal IDs)
    rule_refs = []
    for assoc in post.rules:
        rule = Rule.query.get(assoc.rule_id)
        if rule and not rule.is_deleted:
            rule_refs.append({'uuid': rule.uuid, 'title': rule.title, 'format': rule.format})

    # Resolve bundle references (uuid + name)
    bundle_refs = []
    for assoc in post.bundles:
        bundle = Bundle.query.get(assoc.bundle_id)
        if bundle:
            bundle_refs.append({'uuid': bundle.uuid, 'name': bundle.name})

    return {
        '_meta': {
            'schema_version':  EXPORT_SCHEMA_VERSION,
            'generator':       'Rulezet Blog Export',
            'exported_at':     datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source':          base,
            'post_uuid':       post.uuid,
        },
        'title':           post.title,
        'excerpt':         post.excerpt or '',
        'content':         post.content or '',
        'cover_image_url': cover,
        'tags':            [a.tag.name for a in post.tags if a.tag],
        'attack_techniques': [a.technique_id for a in post.attacks],
        'vulnerabilities': post.cve_ids or [],
        'external_links':  post.external_links or [],
        'attachments': [
            {
                'name':       f.original_name,
                'mime_type':  f.mime_type,
                'size_bytes': f.size_bytes,
                'url':        f'{base}/blog/file/{f.uuid}?download=1',
            }
            for f in post.files
        ],
        'referenced_rules':   rule_refs,
        'referenced_bundles': bundle_refs,
    }


_SORTABLE_COLUMNS = {
    'title':      BlogPost.title,
    'view_count': BlogPost.view_count,
    'created_at': BlogPost.created_at,
}


def get_posts_paginated(page: int, per_page: int, search: str = None,
                        tag_names: list = None, is_admin: bool = False,
                        status: str = None, sort: str = None, sort_dir: str = None):
    """Return a SQLAlchemy Pagination for the blog list."""
    q = BlogPost.query

    if not is_admin:
        q = q.filter(BlogPost.is_public == True, BlogPost.is_draft == False)
    else:
        if status == 'draft':
            q = q.filter(BlogPost.is_draft == True)
        elif status == 'public':
            q = q.filter(BlogPost.is_public == True, BlogPost.is_draft == False)
        elif status == 'private':
            q = q.filter(BlogPost.is_public == False, BlogPost.is_draft == False)

    if search:
        term = f'%{search}%'
        q = q.filter(or_(BlogPost.title.ilike(term), BlogPost.excerpt.ilike(term)))

    if tag_names:
        for name in tag_names:
            q = q.filter(
                BlogPost.tags.any(
                    BlogPostTagAssociation.tag.has(Tag.name == name)
                )
            )

    sort_col = _SORTABLE_COLUMNS.get(sort, BlogPost.created_at)
    q = q.order_by(sort_col.asc() if sort_dir == 'asc' else sort_col.desc())
    return q.paginate(page=page, per_page=per_page, error_out=False)


def add_view(post: BlogPost) -> None:
    post.view_count = (post.view_count or 0) + 1
    db.session.commit()


def toggle_public(post: BlogPost) -> bool:
    post.is_public = not post.is_public
    if post.is_public and not post.published_at:
        post.published_at = datetime.datetime.utcnow()
    post.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    return post.is_public


def toggle_draft(post: BlogPost) -> tuple:
    post.is_draft = not post.is_draft
    if post.is_draft:
        post.is_public = False
    elif not post.published_at:
        post.published_at = datetime.datetime.utcnow()
    post.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    return post.is_draft, post.is_public


def regenerate_share_key(post: BlogPost) -> str:
    post.share_key = _make_share_key()
    post.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    return post.share_key
