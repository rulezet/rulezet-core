import datetime
import json
import math
import uuid

from pathlib import Path

from flask_login import current_user
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import joinedload
from app import db
from app.core.db_class.db import Tag


# ─── CRUD basics ─────────────────────────────────────────────────────────────

def create_tag(form_data, created_by):
    """Create a new tag in the database."""
    try:
        existing_tag = Tag.query.filter_by(name=form_data['name']).first()
        if existing_tag:
            return False

        if created_by.is_admin():
            _is_active = True
            _approved_by_admin = True
        else:
            _is_active = False
            _approved_by_admin = False

        if not form_data.get('source'):
            form_data['source'] = 'Manual'

        tag = Tag(
            uuid=str(uuid.uuid4()),
            name=form_data['name'],
            description=form_data.get('description', ''),
            created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
            color=form_data.get('color', '#FFFFFF'),
            icon=form_data.get('icon', 'fa-tag'),
            created_by=created_by.id,
            is_active=_is_active,
            is_approved_by_admin=_approved_by_admin,
            visibility=form_data['visibility'],
            external_id=form_data.get('external_id', None),
            source=form_data.get('source', 'Manual')
        )
        db.session.add(tag)
        db.session.commit()
        return tag
    except Exception:
        db.session.rollback()
        return None


def _inject_usage_counts(tags):
    """
    Annotate a list of Tag objects with rule_count and bundle_count
    using two grouped COUNT queries instead of N per-tag queries.
    """
    if not tags:
        return tags

    tag_ids = [t.id for t in tags]

    from app.core.db_class.db import RuleTagAssociation, BundleTagAssociation
    from sqlalchemy import func

    rule_counts = dict(
        db.session.query(RuleTagAssociation.tag_id, func.count(RuleTagAssociation.id))
        .filter(RuleTagAssociation.tag_id.in_(tag_ids))
        .group_by(RuleTagAssociation.tag_id)
        .all()
    )
    bundle_counts = dict(
        db.session.query(BundleTagAssociation.tag_id, func.count(BundleTagAssociation.id))
        .filter(BundleTagAssociation.tag_id.in_(tag_ids))
        .group_by(BundleTagAssociation.tag_id)
        .all()
    )

    for tag in tags:
        tag._rule_count   = rule_counts.get(tag.id, 0)
        tag._bundle_count = bundle_counts.get(tag.id, 0)

    return tags


def get_tags(args):
    """Admin tag listing with full filter support."""
    # Tag.to_json() reads self.user.first_name — without eager loading that's
    # one extra lazy-loaded query PER TAG (up to 500/page here). joinedload
    # folds it into the single main query instead.
    query = Tag.query.options(joinedload(Tag.user))

    if args.get('search'):
        query = query.filter(Tag.name.ilike(f"%{args['search']}%"))

    if args.get('source') and args['source'] != 'all':
        query = query.filter_by(source=args['source'])

    if args.get('visibility') and args['visibility'] != 'all':
        query = query.filter_by(visibility=args['visibility'])

    if args.get('is_active') and args['is_active'] != 'all':
        query = query.filter_by(is_active=args['is_active'] == 'active')

    # rule_count/bundle_count are annotated after pagination (see
    # _inject_usage_counts below) via two grouped COUNT queries scoped to the
    # current page only — they can't be sorted on without a correlated
    # subquery running before pagination, so 'usage' isn't in this whitelist.
    sort_columns = {
        'name':        Tag.name,
        'created_at':  Tag.created_at,
        'visibility':  Tag.visibility,
        'is_active':   Tag.is_active,
        'source':      Tag.source,
    }
    sort_key = args.get('sort')
    sort_col = sort_columns.get(sort_key, Tag.created_at)
    default_dir = 'asc' if sort_key in sort_columns else 'desc'
    sort_dir = args.get('dir') or default_dir
    query = query.order_by(sort_col.asc() if sort_dir == 'asc' else sort_col.desc())

    page = int(args.get('page', 1))
    per_page = min(int(args.get('per_page', 20)), 500)
    pagination = query.paginate(page=page, per_page=per_page, max_per_page=500)
    _inject_usage_counts(pagination.items)
    return pagination


def _family_like_pattern(family):
    """
    Build the SQL LIKE pattern that matches every tag belonging to a family.

    Examples:
        'tlp'                       -> 'tlp:%'
        'misp-galaxy:atrm'          -> 'misp-galaxy:atrm=%'
        'misp-galaxy:threat-actor'  -> 'misp-galaxy:threat-actor=%'
    """
    if not family:
        return None
    if family.startswith("misp-galaxy:"):
        return f"{family}=%"
    return f"{family}:%"


def get_tags_by_family(family, source=None):
    """Return all tags belonging to a family (taxonomy namespace or galaxy type)."""
    pattern = _family_like_pattern(family)
    if not pattern:
        return []
    query = Tag.query.filter(Tag.name.ilike(pattern))
    if source and source != 'all':
        query = query.filter_by(source=source)
    return query.order_by(Tag.name.asc()).all()


# ─── Association cleanup helpers ─────────────────────────────────────────────

def _delete_tag_associations(tag_id):
    """Remove all FK references to a single tag before deletion."""
    db.session.execute(
        db.text("DELETE FROM rule_tag_association WHERE tag_id = :id"),
        {"id": tag_id}
    )
    db.session.execute(
        db.text("DELETE FROM bundle_tag_association WHERE tag_id = :id"),
        {"id": tag_id}
    )


def _delete_tag_associations_bulk(int_ids):
    """Remove all FK references to a list of tags before deletion."""
    if not int_ids:
        return
    id_tuple = tuple(int_ids)
    db.session.execute(
        db.text("DELETE FROM rule_tag_association WHERE tag_id IN :ids"),
        {"ids": id_tuple}
    )
    db.session.execute(
        db.text("DELETE FROM bundle_tag_association WHERE tag_id IN :ids"),
        {"ids": id_tuple}
    )


# ─── Deletions ───────────────────────────────────────────────────────────────

def remove_tag(tag_id):
    try:
        tag = Tag.query.get(tag_id)
        if not tag:
            return False, "Tag not found."
        _delete_tag_associations(int(tag_id))
        db.session.delete(tag)
        db.session.commit()
        return True, "Tag deleted."
    except Exception as e:
        db.session.rollback()
        return False, f"Error deleting tag: {e}"


def remove_tags_bulk(tag_ids):
    """Delete a list of tags, cleaning up all associations first."""
    if not tag_ids:
        return 0, "No tags provided."
    try:
        int_ids = [int(i) for i in tag_ids]
        _delete_tag_associations_bulk(int_ids)
        deleted = Tag.query.filter(Tag.id.in_(int_ids)).delete(synchronize_session=False)
        db.session.commit()
        return deleted, f"Deleted {deleted} tag(s)."
    except Exception as e:
        db.session.rollback()
        return 0, f"Error during bulk delete: {e}"


def remove_family(family, source=None):
    """Delete every tag in a given family, cleaning up all associations first."""
    pattern = _family_like_pattern(family)
    if not pattern:
        return 0, "Invalid family."
    try:
        query = Tag.query.filter(Tag.name.ilike(pattern))
        if source and source != 'all':
            query = query.filter_by(source=source)
        ids = [t.id for t in query.with_entities(Tag.id).all()]
        if not ids:
            return 0, f"No tags found in family '{family}'."
        _delete_tag_associations_bulk(ids)
        deleted = Tag.query.filter(Tag.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return deleted, f"Deleted {deleted} tags from family '{family}'."
    except Exception as e:
        db.session.rollback()
        return 0, f"Error deleting family: {e}"


# ─── Visibility / status toggles ─────────────────────────────────────────────

def toggle_tag_visibility(tag_uuid):
    try:
        tag = Tag.query.filter_by(uuid=tag_uuid).first()
        if not tag:
            return False, "Tag not found."
        tag.visibility = "private" if tag.visibility == "public" else "public"
        db.session.commit()
        return True, f"Visibility set to {tag.visibility}."
    except Exception:
        db.session.rollback()
        return False, "Error toggling visibility."


def toggle_tag_status(tag_uuid):
    try:
        tag = Tag.query.filter_by(uuid=tag_uuid).first()
        if not tag:
            return False, "Tag not found."
        tag.is_active = not tag.is_active
        db.session.commit()
        return True, f"Status set to {'active' if tag.is_active else 'inactive'}."
    except Exception:
        db.session.rollback()
        return False, "Error toggling status."


# ─── Edit ────────────────────────────────────────────────────────────────────

def edit_tag(form_data, tag_id):
    try:
        tag = Tag.query.get(tag_id)
        if not tag:
            return False, "Tag not found."

        if tag.name != form_data['name'] and Tag.query.filter_by(name=form_data['name']).first():
            return False, "A tag with this name already exists."

        if (form_data.get('external_id') and tag.external_id != form_data['external_id']
                and Tag.query.filter_by(external_id=form_data['external_id']).first()):
            return False, "A tag with this UUID already exists."

        tag.name        = form_data['name']
        tag.description = form_data.get('description', tag.description)
        tag.color       = form_data.get('color', tag.color)
        tag.icon        = form_data.get('icon', tag.icon)
        tag.external_id = form_data.get('external_id', tag.external_id)
        tag.updated_at  = datetime.datetime.now(tz=datetime.timezone.utc)

        db.session.commit()
        return True, "Tag updated."
    except Exception:
        db.session.rollback()
        return False, None


# ─── Bundle / public listings ────────────────────────────────────────────────

def get_tags_bundle(args):
    query = Tag.query
    if current_user.is_authenticated:
        if current_user.is_admin():
            query = query.filter_by(is_active=True)
        elif args.get('user_id'):
            if current_user.id == int(args.get('user_id')):
                from sqlalchemy import or_
                query = query.filter_by(is_active=True).filter(
                    or_(Tag.visibility == 'public', Tag.created_by == current_user.id)
                )
            else:
                query = query.filter_by(is_active=True, visibility='public')
        else:
            query = query.filter_by(is_active=True, visibility='public')
    else:
        query = query.filter_by(is_active=True, visibility='public')

    if args.get('search'):
        query = query.filter(Tag.name.ilike(f"%{args['search']}%"))

    sort_order = args.get('sort_order', 'desc')
    query = query.order_by(Tag.created_at.desc() if sort_order == 'desc' else Tag.created_at.asc())

    page = int(args.get('page', 1))
    pagination = query.paginate(page=page, per_page=20, max_per_page=20)
    _inject_usage_counts(pagination.items)
    return pagination


def get_my_tags():
    """All Manual tags created by the current user (unpaginated)."""
    tags = Tag.query.filter(
        Tag.created_by == current_user.id,
        Tag.source == "Manual",
    ).order_by(Tag.created_at.desc()).all()
    return _inject_usage_counts(tags)


def get_my_tags_paged(args):
    """Paginated Manual tags created by the current user."""
    query = Tag.query.filter(
        Tag.created_by == current_user.id,
        Tag.source == "Manual",
    )
    if args.get('search'):
        query = query.filter(Tag.name.ilike(f"%{args['search']}%"))

    if args.get('visibility') and args['visibility'] != 'all':
        query = query.filter_by(visibility=args['visibility'])

    sort_order = args.get('sort_order', 'desc')
    query = query.order_by(Tag.created_at.desc() if sort_order == 'desc' else Tag.created_at.asc())

    page     = int(args.get('page', 1))
    per_page = min(int(args.get('per_page', 20)), 100)
    pagination = query.paginate(page=page, per_page=per_page, max_per_page=100)
    _inject_usage_counts(pagination.items)
    return pagination


def _picker_scope(args, query=None):
    """Tags the current user may pick — the single visibility rule of every
    tag picker endpoint: admins see every active tag; a user passing their
    own user_id sees active public tags plus every tag they created;
    everyone else sees active public tags only."""
    query = query if query is not None else Tag.query
    if current_user.is_authenticated and current_user.is_admin():
        return query.filter(Tag.is_active == True)
    user_id = args.get('user_id')
    if current_user.is_authenticated and user_id and str(user_id) == str(current_user.id):
        return query.filter(or_(
            and_(Tag.is_active == True, Tag.visibility == 'public'),
            Tag.created_by == current_user.id,
        ))
    return query.filter(Tag.is_active == True, Tag.visibility == 'public')


def _prefix_first(query, search):
    """A tag whose name *starts with* the search term (e.g. "tlp:clear" for
    "tlp") is almost always the one wanted — ranked above a tag merely
    containing it."""
    return query.order_by(case((Tag.name.ilike(f"{search}%"), 0), else_=1), Tag.name.asc())


def get_all_tags(args):
    """Tag picker search (TagInput.js) + admin bulk-tag tool.

    Neither caller displays rule_count/bundle_count, so this skips
    _inject_usage_counts() entirely. Tag.user is eager-loaded (joinedload)
    because Tag.to_json() reads self.user.first_name.

    An optional `limit` caps how many rows come back — used by the picker's
    live search so a broad term can't ship thousands of rows to an
    autocomplete dropdown. Everything is filtered, ranked and limited in SQL
    (the user_id branch used to load every public tag into Python first —
    2 s per keystroke with ~75k tags).
    """
    limit = args.get('limit')
    limit = int(limit) if limit else None
    search = args.get('search')

    query = _picker_scope(args, Tag.query.options(joinedload(Tag.user)))
    if search:
        query = _prefix_first(query.filter(Tag.name.ilike(f"%{search}%")), search)
    else:
        sort_order = args.get('sort_order', 'desc')
        query = query.order_by(Tag.created_at.desc() if sort_order == 'desc' else Tag.created_at.asc())

    if limit:
        query = query.limit(limit)
    return query.all()


# ─── Lazy tag pickers (folders first, one folder at a time) ─────────────────

PICKER_MAX_PER_PAGE = 200


def picker_tag_json(tag) -> dict:
    """What a picker needs to render / select a tag — no author lookup, no
    dates or counters (Tag.to_json() is ~10x heavier)."""
    return {
        "id": tag.id, "uuid": tag.uuid, "name": tag.name, "color": tag.color, "icon": tag.icon,
        "source": tag.source, "visibility": tag.visibility, "namespace": tag.namespace or "",
    }


def _visibility_bucket():
    return case((Tag.visibility == 'public', 'Public'), else_='Private')


def picker_namespaces(args) -> dict:
    """{"Public": [{"namespace", "count"}], "Private": [...]} — the folders of
    the tag picker with how many pickable tags each holds. One GROUP BY
    instead of downloading every tag to group them client-side."""
    bucket = _visibility_bucket().label('bucket')
    ns = func.coalesce(Tag.namespace, '').label('ns')
    rows = (_picker_scope(args, db.session.query(bucket, ns, func.count(Tag.id)))
            .group_by(bucket, ns).all())
    groups = {}
    for b, n, count in rows:
        groups.setdefault(b, []).append({"namespace": n, "count": count})
    for folders in groups.values():
        folders.sort(key=lambda f: (f["namespace"] == "", f["namespace"].lower()))
    return {k: groups[k] for k in ("Public", "Private") if k in groups}


def picker_tags(args) -> dict:
    """One page of one folder: type=Public|Private, namespace ('' = no
    namespace), page, per_page (max 200). Sorted by name."""
    page = max(1, int(args.get('page') or 1))
    per_page = min(PICKER_MAX_PER_PAGE, max(1, int(args.get('per_page') or 50)))
    query = _picker_scope(args)
    bucket = (args.get('type') or '').strip()
    if bucket == 'Public':
        query = query.filter(Tag.visibility == 'public')
    elif bucket == 'Private':
        query = query.filter(or_(Tag.visibility != 'public', Tag.visibility.is_(None)))
    if 'namespace' in args:
        namespace = args.get('namespace') or ''
        query = query.filter(func.coalesce(Tag.namespace, '') == namespace)
    total = query.count()
    tags = query.order_by(Tag.name.asc()).offset((page - 1) * per_page).limit(per_page).all()
    return {"tags": [picker_tag_json(t) for t in tags], "page": page, "per_page": per_page,
            "total": total, "has_more": page * per_page < total}


# ─── Lazy tag filters (MultiTagFilter.js — rule / bundle facets) ────────────

def usage_snapshot(usage: dict) -> list:
    """{tag_id: usage_count} -> one lean dict per used tag, carrying the
    fields the per-user visibility check needs. Cacheable as-is: nothing in
    it depends on who asks (see _snapshot_visible)."""
    ids = list(usage)
    rows = []
    for i in range(0, len(ids), 5000):
        for t in (Tag.query.with_entities(Tag.id, Tag.uuid, Tag.name, Tag.color, Tag.icon, Tag.source,
                                          Tag.visibility, Tag.namespace, Tag.is_active, Tag.created_by)
                  .filter(Tag.id.in_(ids[i:i + 5000]))):
            rows.append({"id": t.id, "uuid": t.uuid, "name": t.name, "color": t.color, "icon": t.icon,
                         "source": t.source, "visibility": t.visibility, "namespace": t.namespace or "",
                         "is_active": bool(t.is_active), "created_by": t.created_by,
                         "usage_count": int(usage[t.id])})
    return rows


def _snapshot_visible(rows) -> list:
    """Same visibility as the full tag-usage facets: admins see every active
    tag, a user public ones + their own private ones, a visitor public ones."""
    me = current_user.id if current_user.is_authenticated else None
    admin = bool(me) and current_user.is_admin()

    def ok(t):
        if not t["is_active"]:
            return False
        vis = (t["visibility"] or "").lower()
        if admin or vis == "public":
            return True
        return bool(me) and vis == "private" and t["created_by"] == me

    return [t for t in rows if ok(t)]


_SNAPSHOT_PRIVATE = ("is_active", "created_by")


def _out(t):
    return {k: v for k, v in t.items() if k not in _SNAPSHOT_PRIVATE}


def _label(namespace):
    return (namespace or 'other').upper()


def usage_view(snapshot: list, args) -> dict:
    """One lazy view of a tag facet, from a usage snapshot (usage_snapshot):
    the tags used by the rules / bundles matching the page's other filters.

    ?view=namespaces[&tag_source=]   folders + how many used tags each holds
    ?view=tags[&tag_source=&tag_ns=&tag_q=&tag_page=&tag_per_page=]
                                     one page of tags, most used first
    ?view=selected&names=a,b         the given tags (chips of the selection)
    """
    view = args.get('view')
    tags = _snapshot_visible(snapshot)

    if view == 'selected':
        names = {n.strip().lower() for n in (args.get('names') or '').split(',') if n.strip()}
        found = {t["name"].lower(): _out(t) for t in tags if t["name"].lower() in names}
        missing = names - set(found)
        if missing:
            # A selected tag no rule matching the other filters uses any more
            # still needs its chip.
            query = _usage_visibility(Tag.query).filter(func.lower(Tag.name).in_(list(missing)[:200]))
            found.update({t.name.lower(): {**picker_tag_json(t), "usage_count": 0} for t in query.all()})
        return {"tags": list(found.values())}

    source = args.get('tag_source')
    if source and source != 'all':
        tags = [t for t in tags if t["source"] == source]

    if view == 'namespaces':
        folders = {}
        for t in tags:
            f = folders.setdefault(t["namespace"], {"namespace": t["namespace"], "label": _label(t["namespace"]),
                                                    "tag_count": 0, "usage": 0})
            f["tag_count"] += 1
            f["usage"] += t["usage_count"]
        return {"namespaces": sorted(folders.values(), key=lambda f: (-f["usage"], f["namespace"]))}

    # view == 'tags'
    page = max(1, int(args.get('tag_page') or 1))
    per_page = min(PICKER_MAX_PER_PAGE, max(1, int(args.get('tag_per_page') or 50)))
    if 'tag_ns' in args:
        tags = [t for t in tags if t["namespace"] == (args.get('tag_ns') or '')]
    search = (args.get('tag_q') or '').strip().lower()
    if search:
        tags = [t for t in tags if search in t["name"].lower()]
        tags.sort(key=lambda t: (not t["name"].lower().startswith(search), -t["usage_count"], t["name"]))
    else:
        tags.sort(key=lambda t: (-t["usage_count"], t["name"]))
    total = len(tags)
    page_tags = tags[(page - 1) * per_page: page * per_page]
    return {"tags": [_out(t) for t in page_tags], "page": page, "per_page": per_page,
            "total": total, "has_more": page * per_page < total}


def _usage_visibility(query):
    query = query.filter(Tag.is_active.is_(True))
    if current_user.is_authenticated:
        if not current_user.is_admin():
            query = query.filter(or_(
                Tag.visibility.ilike('public'),
                and_(Tag.visibility.ilike('private'), Tag.created_by == current_user.id),
            ))
        return query
    return query.filter(Tag.visibility.ilike('public'))


def get_all_tags_by_type(args):
    return get_all_tags(args)


# ─── MISP Taxonomies ─────────────────────────────────────────────────────────

MISP_TAXONOMIES_PATH = "app/modules/misp-taxonomies"


def list_all_misp_taxonomies_meta(args):
    taxonomies = []
    base_path = Path(MISP_TAXONOMIES_PATH)
    existing_namespaces = get_all_taxonomies_in_db()

    for taxonomy_dir in sorted(base_path.iterdir()):
        if not taxonomy_dir.is_dir():
            continue
        for json_file in taxonomy_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                namespace = data.get("namespace")
                if not namespace or namespace in existing_namespaces:
                    continue
                taxonomies.append({
                    "version":     data.get("version"),
                    "description": data.get("description"),
                    "expanded":    data.get("expanded"),
                    "exclusive":   data.get("exclusive", False),
                    "namespace":   namespace,
                    "uuid":        data.get("uuid"),
                })
            except Exception:
                continue

    search_term = args.get("search", "").lower()
    if search_term:
        taxonomies = [
            t for t in taxonomies
            if search_term in (t["description"] or "").lower()
            or search_term in (t["expanded"] or "").lower()
            or search_term in (t["namespace"] or "").lower()
        ]

    page     = int(args.get("page", 1))
    per_page = 20
    total    = len(taxonomies)
    total_pages = math.ceil(total / per_page) or 1
    start    = (page - 1) * per_page

    return {"items": taxonomies[start:start + per_page], "page": page, "pages": total_pages, "total": total}


def add_tags_from_misp_taxonomy(uuid_from_misp, created_by):
    if not uuid_from_misp:
        return None, "Missing UUID"

    taxonomy_path = None
    base_path = Path(MISP_TAXONOMIES_PATH)

    for taxonomy_dir in base_path.iterdir():
        if not taxonomy_dir.is_dir():
            continue
        for json_file in taxonomy_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("uuid") == uuid_from_misp:
                    taxonomy_path = json_file
                    break
            except Exception:
                continue
        if taxonomy_path:
            break

    if not taxonomy_path:
        return None, "Taxonomy not found"

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        taxonomy_data = json.load(f)

    namespace  = taxonomy_data.get("namespace", "unknown")
    tags_added = 0

    if namespace in get_all_taxonomies_in_db():
        return True, "Taxonomy already imported."

    if "values" in taxonomy_data:
        for block in taxonomy_data.get("values", []):
            predicate = block.get("predicate")
            if not predicate:
                continue
            for entry in block.get("entry", []):
                value = entry.get("value")
                if not value:
                    continue
                tag_name = f'{namespace}:{predicate}="{value}"'[:1000]
                if Tag.query.filter_by(name=tag_name).first():
                    continue
                db.session.add(Tag(
                    name=tag_name,
                    description=entry.get("description") or entry.get("expanded"),
                    color=entry.get("colour") or "#FFFFFF",
                    icon="fa-tag",
                    uuid=str(uuid.uuid4()),
                    created_by=created_by.id,
                    is_active=True,
                    is_approved_by_admin=True,
                    visibility="public",
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    updated_at=datetime.datetime.now(datetime.timezone.utc),
                    external_id=entry.get("uuid"),
                    source="Taxonomy",
                ))
                tags_added += 1

    elif "predicates" in taxonomy_data:
        for pred in taxonomy_data.get("predicates", []):
            value = pred.get("value")
            if not value:
                continue
            tag_name = f"{namespace}:{value}"[:1000]
            if Tag.query.filter_by(name=tag_name).first():
                continue
            db.session.add(Tag(
                name=tag_name,
                description=pred.get("description") or pred.get("expanded"),
                color=pred.get("colour") or "#FFFFFF",
                icon="fa-tag",
                uuid=str(uuid.uuid4()),
                external_id=pred.get("uuid"),
                created_by=created_by.id,
                is_active=True,
                is_approved_by_admin=True,
                visibility="public",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                updated_at=datetime.datetime.now(datetime.timezone.utc),
                source="Taxonomy",
            ))
            tags_added += 1

    if tags_added:
        db.session.commit()
        return True, f"Imported {tags_added} tags from {namespace}."
    return None, "No tags were added."


def get_all_taxonomies_in_db():
    namespaces = set()
    for tag in Tag.query.filter(Tag.source == "Taxonomy").all():
        if ":" in tag.name:
            namespaces.add(tag.name.split(":", 1)[0])
    return namespaces


# ─── MISP Galaxies ───────────────────────────────────────────────────────────

MISP_GALAXIES_PATH = "app/modules/misp-galaxy"


def list_all_misp_galaxies_meta(args):
    galaxies = []
    galaxies_path = Path(MISP_GALAXIES_PATH) / "galaxies"
    clusters_path = Path(MISP_GALAXIES_PATH) / "clusters"
    existing_galaxies = get_all_galaxies_in_db()

    for galaxy_file in sorted(galaxies_path.glob("*.json")):
        try:
            with open(galaxy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            galaxy_type = data.get("type")
            if not galaxy_type or galaxy_type in existing_galaxies:
                continue

            cluster_count = 0
            cluster_file  = clusters_path / galaxy_file.name
            if cluster_file.exists():
                with open(cluster_file, "r", encoding="utf-8") as f:
                    cluster_data = json.load(f)
                cluster_count = len(cluster_data.get("values", []))

            galaxies.append({
                "name":        data.get("name"),
                "type":        galaxy_type,
                "description": data.get("description"),
                "uuid":        data.get("uuid"),
                "version":     data.get("version"),
                "icon":        data.get("icon"),
                "count":       cluster_count,
            })
        except Exception:
            continue

    search_term = args.get("search", "").lower()
    if search_term:
        galaxies = [
            g for g in galaxies
            if search_term in (g["name"] or "").lower()
            or search_term in (g["description"] or "").lower()
            or search_term in (g["type"] or "").lower()
        ]

    page     = int(args.get("page", 1))
    per_page = 20
    total    = len(galaxies)
    total_pages = math.ceil(total / per_page) or 1
    start    = (page - 1) * per_page

    return {"items": galaxies[start:start + per_page], "page": page, "pages": total_pages, "total": total}


def get_galaxy_clusters(uuid_from_misp):
    """Return all clusters of a galaxy without importing them."""
    if not uuid_from_misp:
        return None, "Missing UUID"

    galaxies_path = Path(MISP_GALAXIES_PATH) / "galaxies"
    clusters_path = Path(MISP_GALAXIES_PATH) / "clusters"

    galaxy_data      = None
    matched_filename = None
    for galaxy_file in galaxies_path.glob("*.json"):
        try:
            with open(galaxy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("uuid") == uuid_from_misp:
                galaxy_data      = data
                matched_filename = galaxy_file.name
                break
        except Exception:
            continue

    if not galaxy_data or not matched_filename:
        return None, "Galaxy not found"

    cluster_file = clusters_path / matched_filename
    if not cluster_file.exists():
        return None, "Cluster file not found"

    with open(cluster_file, "r", encoding="utf-8") as f:
        cluster_data = json.load(f)

    galaxy_type = galaxy_data.get("type", "unknown")
    existing    = {tag.external_id for tag in Tag.query.filter_by(source="Galaxy").all() if tag.external_id}

    clusters = []
    for cluster in cluster_data.get("values", []):
        value        = cluster.get("value")
        cluster_uuid = cluster.get("uuid")
        if not value:
            continue
        clusters.append({
            "uuid":             cluster_uuid,
            "value":            value,
            "description":      cluster.get("description", ""),
            "already_imported": cluster_uuid in existing,
        })

    return {
        "galaxy_type": galaxy_type,
        "galaxy_name": galaxy_data.get("name"),
        "icon":        galaxy_data.get("icon", "atom"),
        "clusters":    clusters,
    }, None


def add_tags_from_misp_galaxy(uuid_from_misp, created_by, cluster_uuids=None):
    """Import clusters of a galaxy as Tags with source='Galaxy'.

    If cluster_uuids is provided, only those clusters are imported.
    Otherwise all clusters are imported (original behaviour).
    """
    if not uuid_from_misp:
        return None, "Missing UUID"

    galaxies_path = Path(MISP_GALAXIES_PATH) / "galaxies"
    clusters_path = Path(MISP_GALAXIES_PATH) / "clusters"

    galaxy_data      = None
    matched_filename = None
    for galaxy_file in galaxies_path.glob("*.json"):
        try:
            with open(galaxy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("uuid") == uuid_from_misp:
                galaxy_data      = data
                matched_filename = galaxy_file.name
                break
        except Exception:
            continue

    if not galaxy_data or not matched_filename:
        return None, "Galaxy not found"

    galaxy_type = galaxy_data.get("type", "unknown")
    # Store the raw MISP icon name (e.g. "shield-alt"), not a resolved FA
    # class — every display path (mapIcon() in JS, TagTable's edit UI, the
    # taxonomy import path via "fa-tag") resolves Tag.icon at render time,
    # so pre-resolving it here double-maps it into a nonexistent class and
    # the icon silently disappears.
    raw_icon    = galaxy_data.get("icon") or "atom"

    if cluster_uuids is None and galaxy_type in get_all_galaxies_in_db():
        return True, "Galaxy already imported."

    cluster_file = clusters_path / matched_filename
    if not cluster_file.exists():
        return None, "Cluster file not found"

    with open(cluster_file, "r", encoding="utf-8") as f:
        cluster_data = json.load(f)

    allowed    = set(cluster_uuids) if cluster_uuids else None
    tags_added = 0

    for cluster in cluster_data.get("values", []):
        value        = cluster.get("value")
        cluster_uuid = cluster.get("uuid")
        if not value:
            continue
        if allowed is not None and cluster_uuid not in allowed:
            continue
        tag_name = f'misp-galaxy:{galaxy_type}="{value}"'[:1000]
        if Tag.query.filter_by(name=tag_name).first():
            continue
        db.session.add(Tag(
            name=tag_name,
            description=cluster.get("description", ""),
            color="#9b7ede",
            icon=raw_icon,
            uuid=str(uuid.uuid4()),
            created_by=created_by.id,
            is_active=True,
            is_approved_by_admin=True,
            visibility="public",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc),
            external_id=cluster_uuid,
            source="Galaxy",
            galaxy_meta=cluster.get("meta"),
        ))
        tags_added += 1

    if tags_added:
        db.session.commit()
        return True, f"Imported {tags_added} clusters from galaxy '{galaxy_type}'."
    return None, "No clusters were added."


def get_all_galaxies_in_db():
    galaxy_types = set()
    for tag in Tag.query.filter_by(source="Galaxy").all():
        if tag.name.startswith("misp-galaxy:") and "=" in tag.name:
            galaxy_type = tag.name.split(":", 1)[1].split("=", 1)[0]
            galaxy_types.add(galaxy_type)
    return galaxy_types


# ─── Bulk helpers for the update job ─────────────────────────────────────────

def get_all_taxonomy_uuids_from_disk():
    """Return list of (uuid, namespace) for every taxonomy JSON on disk."""
    items = []
    base_path = Path(MISP_TAXONOMIES_PATH)
    if not base_path.exists():
        return items
    for taxonomy_dir in sorted(base_path.iterdir()):
        if not taxonomy_dir.is_dir():
            continue
        for json_file in taxonomy_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                uid = data.get("uuid")
                ns  = data.get("namespace")
                if uid and ns:
                    items.append((uid, ns))
            except Exception:
                continue
    return items


def get_imported_taxonomy_uuids_from_disk():
    """Return list of (uuid, namespace) only for taxonomies ALREADY imported in DB."""
    imported = get_all_taxonomies_in_db()
    return [(uid, ns) for uid, ns in get_all_taxonomy_uuids_from_disk() if ns in imported]


def get_all_galaxy_uuids_from_disk():
    """Return list of (uuid, type) for every galaxy JSON on disk."""
    items = []
    galaxies_path = Path(MISP_GALAXIES_PATH) / "galaxies"
    if not galaxies_path.exists():
        return items
    for galaxy_file in sorted(galaxies_path.glob("*.json")):
        try:
            with open(galaxy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            uid  = data.get("uuid")
            gtype = data.get("type")
            if uid and gtype:
                items.append((uid, gtype))
        except Exception:
            continue
    return items


def get_imported_galaxy_uuids_from_disk():
    """Return list of (uuid, type) only for galaxies ALREADY imported in DB."""
    imported = get_all_galaxies_in_db()
    return [(uid, gtype) for uid, gtype in get_all_galaxy_uuids_from_disk() if gtype in imported]


def update_tags_from_misp_taxonomy(uuid_from_misp, created_by):
    """Add only NEW tags from an already-imported taxonomy (update pass).
    Skips entirely if the namespace hasn't been imported yet.
    Returns (True, summary) or (None, reason).
    """
    if not uuid_from_misp:
        return None, "Missing UUID"

    base_path = Path(MISP_TAXONOMIES_PATH)
    taxonomy_path = None
    for taxonomy_dir in base_path.iterdir():
        if not taxonomy_dir.is_dir():
            continue
        for json_file in taxonomy_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("uuid") == uuid_from_misp:
                    taxonomy_path = json_file
                    break
            except Exception:
                continue
        if taxonomy_path:
            break

    if not taxonomy_path:
        return None, "Taxonomy not found on disk"

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        taxonomy_data = json.load(f)

    namespace = taxonomy_data.get("namespace", "unknown")

    # Only update if already imported
    if namespace not in get_all_taxonomies_in_db():
        return None, f"'{namespace}' not imported — skipped"

    tags_added = 0

    if "values" in taxonomy_data:
        for block in taxonomy_data.get("values", []):
            predicate = block.get("predicate")
            if not predicate:
                continue
            for entry in block.get("entry", []):
                value = entry.get("value")
                if not value:
                    continue
                tag_name = f'{namespace}:{predicate}="{value}"'[:1000]
                if Tag.query.filter_by(name=tag_name).first():
                    continue
                db.session.add(Tag(
                    name=tag_name,
                    description=entry.get("description") or entry.get("expanded"),
                    color=entry.get("colour") or "#FFFFFF",
                    icon="fa-tag",
                    uuid=str(uuid.uuid4()),
                    created_by=created_by.id,
                    is_active=True,
                    is_approved_by_admin=True,
                    visibility="public",
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    updated_at=datetime.datetime.now(datetime.timezone.utc),
                    external_id=entry.get("uuid"),
                    source="Taxonomy",
                ))
                tags_added += 1

    elif "predicates" in taxonomy_data:
        for pred in taxonomy_data.get("predicates", []):
            value = pred.get("value")
            if not value:
                continue
            tag_name = f"{namespace}:{value}"[:1000]
            if Tag.query.filter_by(name=tag_name).first():
                continue
            db.session.add(Tag(
                name=tag_name,
                description=pred.get("description") or pred.get("expanded"),
                color=pred.get("colour") or "#FFFFFF",
                icon="fa-tag",
                uuid=str(uuid.uuid4()),
                external_id=pred.get("uuid"),
                created_by=created_by.id,
                is_active=True,
                is_approved_by_admin=True,
                visibility="public",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                updated_at=datetime.datetime.now(datetime.timezone.utc),
                source="Taxonomy",
            ))
            tags_added += 1

    if tags_added:
        db.session.commit()
        return True, f"{namespace}: {tags_added} new tag(s) added"
    return True, f"{namespace}: already up to date"


def update_tags_from_misp_galaxy(uuid_from_misp, created_by):
    """Add only NEW clusters from an already-imported galaxy (update pass).
    Skips entirely if the galaxy hasn't been imported yet.
    """
    if not uuid_from_misp:
        return None, "Missing UUID"

    galaxies_path = Path(MISP_GALAXIES_PATH) / "galaxies"
    clusters_path = Path(MISP_GALAXIES_PATH) / "clusters"

    galaxy_data = matched_filename = None
    for galaxy_file in galaxies_path.glob("*.json"):
        try:
            with open(galaxy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("uuid") == uuid_from_misp:
                galaxy_data = data
                matched_filename = galaxy_file.name
                break
        except Exception:
            continue

    if not galaxy_data:
        return None, "Galaxy not found on disk"

    galaxy_type = galaxy_data.get("type", "unknown")

    # Only update if already imported
    if galaxy_type not in get_all_galaxies_in_db():
        return None, f"'{galaxy_type}' not imported — skipped"

    raw_icon = galaxy_data.get("icon") or "atom"
    cluster_file = clusters_path / matched_filename
    if not cluster_file.exists():
        return None, "Cluster file not found"

    with open(cluster_file, "r", encoding="utf-8") as f:
        cluster_data = json.load(f)

    tags_added = 0
    for cluster in cluster_data.get("values", []):
        value = cluster.get("value")
        if not value:
            continue
        tag_name = f'misp-galaxy:{galaxy_type}="{value}"'[:1000]
        if Tag.query.filter_by(name=tag_name).first():
            continue
        db.session.add(Tag(
            name=tag_name,
            description=cluster.get("description", ""),
            color="#9b7ede",
            icon=raw_icon,
            uuid=str(uuid.uuid4()),
            created_by=created_by.id,
            is_active=True,
            is_approved_by_admin=True,
            visibility="public",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc),
            external_id=cluster.get("uuid"),
            source="Galaxy",
            galaxy_meta=cluster.get("meta"),
        ))
        tags_added += 1

    if tags_added:
        db.session.commit()
        return True, f"{galaxy_type}: {tags_added} new cluster(s) added"
    return True, f"{galaxy_type}: already up to date"