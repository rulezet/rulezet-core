"""Collections — a user's private folders of rules and bundles.

Each item carries a personal note ("why I keep it"), a status (setting
`collection` → statuses) and an optional reminder: when `remind_at` comes,
the task-scheduler ticker (`fire_due_reminders`, called from
scheduler_engine.tick) sends the user a notification, once.

Everything is scoped to the owner: every function takes `user_id` and only
ever touches that user's rows. Design: docs/design/collections.md
"""
import datetime

from sqlalchemy import func, or_

from app import db
from app.core.db_class.bundle import Bundle
from app.core.db_class.collection import UserCollection, UserCollectionItem
from app.core.db_class.rule import Rule
from app.core.db_class.rule_proposal import RuleEditProposal
from app.core.utils.app_settings import setting
from app.features.rule.rule_core import _active

CONFIG = setting('collection')  # app/config/collection.json


def _cfg(key, default=None):
    try:
        return CONFIG.get(key, default)
    except Exception:
        return default


def status_keys():
    return [s['key'] for s in (_cfg('statuses') or [])] or ['todo', 'doing', 'done']


def _utcnow():
    return datetime.datetime.utcnow()


def _ids(values):
    """List of positive int ids from whatever the client sent (bad items dropped)."""
    if not isinstance(values, (list, tuple, set)):
        values = [values]
    out = []
    for v in values:
        if isinstance(v, bool):
            continue
        try:
            i = int(v)
        except (TypeError, ValueError):
            continue
        if 0 < i < 2**31:
            out.append(i)
    return out


def _text(value, limit):
    """A string field from JSON: non-strings become '' (never a 500)."""
    return value.strip()[:limit] if isinstance(value, str) else ''


def _parse_dt(value):
    """'2026-11-20T09:00' / ISO with Z → naive UTC datetime; '' / None → None."""
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        dt = value
    else:
        try:
            dt = datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except (ValueError, TypeError):
            raise ValueError("Invalid reminder date.")
    if dt.tzinfo:
        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return dt


def _iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else None


# ── Folders ──────────────────────────────────────────────────────────────────

def _folder(user_id, folder_id):
    ids = _ids(folder_id)
    if not ids:
        return None
    return UserCollection.query.filter_by(id=ids[0], user_id=user_id).first()


def ensure_defaults(user_id):
    """First visit: create the default folders of the setting (once — only
    when the user has no folder at all)."""
    if UserCollection.query.filter_by(user_id=user_id).first():
        return
    for pos, f in enumerate(_cfg('default_folders') or []):
        db.session.add(UserCollection(user_id=user_id, name=f.get('name', 'Folder')[:120],
                                      icon=f.get('icon'), color=f.get('color'),
                                      description=f.get('description'), position=pos))
    db.session.commit()


def tree(user_id):
    """Flat list of the user's folders (the front end nests them by parent_id)
    with item counts, open (not done) counts and due reminders."""
    folders = (UserCollection.query.filter_by(user_id=user_id)
               .order_by(UserCollection.position, UserCollection.id).all())
    now = _utcnow()
    counts = dict(db.session.query(UserCollectionItem.collection_id, func.count())
                  .filter(UserCollectionItem.user_id == user_id)
                  .group_by(UserCollectionItem.collection_id).all())
    open_counts = dict(db.session.query(UserCollectionItem.collection_id, func.count())
                       .filter(UserCollectionItem.user_id == user_id, UserCollectionItem.status != 'done')
                       .group_by(UserCollectionItem.collection_id).all())
    due_counts = dict(db.session.query(UserCollectionItem.collection_id, func.count())
                      .filter(UserCollectionItem.user_id == user_id,
                              UserCollectionItem.remind_at.isnot(None),
                              UserCollectionItem.remind_at <= now,
                              UserCollectionItem.status != 'done')
                      .group_by(UserCollectionItem.collection_id).all())
    out = []
    for f in folders:
        d = f.to_json()
        d['count'] = counts.get(f.id, 0)
        d['open'] = open_counts.get(f.id, 0)
        d['due'] = due_counts.get(f.id, 0)
        out.append(d)
    return out


def summary(user_id):
    """Header numbers: items, open items, reminders due, upcoming reminders."""
    now = _utcnow()
    base = UserCollectionItem.query.filter_by(user_id=user_id)
    return {
        "items": base.count(),
        "open": base.filter(UserCollectionItem.status != 'done').count(),
        "due": base.filter(UserCollectionItem.remind_at.isnot(None), UserCollectionItem.remind_at <= now,
                           UserCollectionItem.status != 'done').count(),
        "upcoming": base.filter(UserCollectionItem.remind_at > now, UserCollectionItem.status != 'done').count(),
    }


def _depth(folder):
    d, cur = 1, folder
    while cur is not None and cur.parent_id:
        cur = cur.parent
        d += 1
    return d


def _clean_folder_fields(data):
    name = _text(data.get('name'), 120)
    icon = _text(data.get('icon'), 60) or None
    color = _text(data.get('color'), 20) or None
    if icon and not icon.startswith('fa-'):
        icon = None
    if color and not (color.startswith('#') and len(color) in (4, 7)):
        color = None
    desc = _text(data.get('description'), 1000) or None
    return name, icon, color, desc


def create_folder(user_id, data):
    name, icon, color, desc = _clean_folder_fields(data)
    if not name:
        return None, "A folder needs a name."
    if UserCollection.query.filter_by(user_id=user_id).count() >= int(_cfg('max_folders', 200)):
        return None, "You have reached the maximum number of folders."
    parent = None
    if data.get('parent_id'):
        parent = _folder(user_id, data['parent_id'])
        if not parent:
            return None, "Parent folder not found."
        if _depth(parent) >= int(_cfg('max_depth', 4)):
            return None, "Folders cannot be nested deeper."
    pos = (db.session.query(func.max(UserCollection.position))
           .filter(UserCollection.user_id == user_id,
                   UserCollection.parent_id == (parent.id if parent else None)).scalar() or 0) + 1
    f = UserCollection(user_id=user_id, parent_id=parent.id if parent else None, name=name,
                       icon=icon or 'fa-solid fa-folder', color=color or '#0d6efd',
                       description=desc, position=pos)
    db.session.add(f)
    db.session.commit()
    return f, "Folder created."


def update_folder(user_id, folder_id, data):
    f = _folder(user_id, folder_id)
    if not f:
        return None, "Folder not found."
    name, icon, color, desc = _clean_folder_fields({**f.to_json(), **data})
    if not name:
        return None, "A folder needs a name."
    f.name, f.icon, f.color, f.description = name, icon or f.icon, color or f.color, desc
    if 'parent_id' in data:
        new_parent_id = data.get('parent_id') or None
        if new_parent_id:
            parent = _folder(user_id, new_parent_id)
            if not parent:
                return None, "Parent folder not found."
            cur = parent        # refuse to move a folder inside itself / its own sub-folder
            while cur is not None:
                if cur.id == f.id:
                    return None, "A folder cannot go inside itself."
                cur = cur.parent
            if _depth(parent) >= int(_cfg('max_depth', 4)):
                return None, "Folders cannot be nested deeper."
            f.parent_id = parent.id
        else:
            f.parent_id = None
    db.session.commit()
    return f, "Folder saved."


def reorder_folders(user_id, ordered_ids):
    """Positions from the order of the ids (folders of one parent)."""
    ordered_ids = _ids(ordered_ids or [])
    owned = {f.id: f for f in UserCollection.query.filter(UserCollection.user_id == user_id,
                                                          UserCollection.id.in_(ordered_ids)).all()}
    for pos, fid in enumerate(ordered_ids or []):
        if fid in owned:
            owned[fid].position = pos
    db.session.commit()


def delete_folder(user_id, folder_id):
    """Deletes the folder, its sub-folders and their items (never the rules)."""
    f = _folder(user_id, folder_id)
    if not f:
        return False
    ids, stack = [], [f]
    while stack:
        cur = stack.pop()
        ids.append(cur.id)
        stack.extend(cur.children)
    UserCollectionItem.query.filter(UserCollectionItem.collection_id.in_(ids)).delete(synchronize_session=False)
    for fid in reversed(ids):
        UserCollection.query.filter_by(id=fid).delete(synchronize_session=False)
    db.session.commit()
    return True


# ── Items ────────────────────────────────────────────────────────────────────

def _bundle_visible(user, bundle):
    return bool(bundle) and (bundle.access or bundle.user_id == user.id or user.is_admin())


def add_items(user, folder_ids, rule_ids=(), bundle_ids=(), note=None, remind_at=None, status=None):
    """Put rules / bundles in one or more folders. An item already in a folder
    keeps its own note unless a new one is given. Returns (added, message)."""
    folders = (UserCollection.query.filter(UserCollection.user_id == user.id,
                                           UserCollection.id.in_(_ids(folder_ids or []))).all())
    if not folders:
        return 0, "Choose at least one folder."
    try:
        remind = _parse_dt(remind_at)
    except ValueError as e:
        return 0, str(e)
    if not isinstance(status, str) or status not in status_keys():
        status = None
    rule_ids = [r.id for r in _active().filter(Rule.id.in_(_ids(rule_ids or []))).all()]
    bundles = Bundle.query.filter(Bundle.id.in_(_ids(bundle_ids or []))).all()
    bundle_ids = [b.id for b in bundles if _bundle_visible(user, b)]
    if not rule_ids and not bundle_ids:
        return 0, "Nothing to add."
    note = _text(note, 5000) or None
    max_items = int(_cfg('max_items_per_folder', 2000))
    added = 0
    for f in folders:
        existing_r = {i.rule_id: i for i in f.items.filter(UserCollectionItem.rule_id.in_(rule_ids)).all()} if rule_ids else {}
        existing_b = {i.bundle_id: i for i in f.items.filter(UserCollectionItem.bundle_id.in_(bundle_ids)).all()} if bundle_ids else {}
        room = max_items - f.items.count()
        for kind, ids, existing in (('rule', rule_ids, existing_r), ('bundle', bundle_ids, existing_b)):
            for oid in ids:
                item = existing.get(oid)
                if item:
                    if note:
                        item.note = note
                    if remind:
                        item.remind_at, item.reminded_at = remind, None
                    if status:
                        item.status = status
                    continue
                if room <= 0:
                    break
                db.session.add(UserCollectionItem(
                    collection_id=f.id, user_id=user.id,
                    rule_id=oid if kind == 'rule' else None,
                    bundle_id=oid if kind == 'bundle' else None,
                    note=note, remind_at=remind, status=status or 'todo'))
                room -= 1
                added += 1
    db.session.commit()
    return added, (f"{added} item(s) added." if added else "Already in the chosen folder(s) — updated.")


def _item(user_id, item_id):
    ids = _ids(item_id)
    return UserCollectionItem.query.filter_by(id=ids[0], user_id=user_id).first() if ids else None


def update_item(user_id, item_id, data):
    item = _item(user_id, item_id)
    if not item:
        return None, "Item not found."
    if 'note' in data:
        item.note = _text(data.get('note'), 5000) or None
    if 'status' in data:
        if not isinstance(data['status'], str) or data['status'] not in status_keys():
            return None, "Unknown status."
        item.status = data['status']
    if 'remind_at' in data:
        try:
            item.remind_at = _parse_dt(data.get('remind_at'))
        except ValueError as e:
            return None, str(e)
        item.reminded_at = None
    target_id = (_ids(data.get('collection_id')) or [None])[0] if data.get('collection_id') else None
    if data.get('collection_id') and target_id != item.collection_id:
        target = _folder(user_id, target_id)
        if not target:
            return None, "Folder not found."
        dup = target.items.filter_by(rule_id=item.rule_id, bundle_id=item.bundle_id).first() if (item.rule_id or item.bundle_id) else None
        if dup:
            return None, "Already in that folder."
        item.collection_id = target.id
    db.session.commit()
    return item, "Saved."


def remove_items(user_id, item_ids):
    n = (UserCollectionItem.query
         .filter(UserCollectionItem.user_id == user_id, UserCollectionItem.id.in_(_ids(item_ids or [])))
         .delete(synchronize_session=False))
    db.session.commit()
    return n


def remove_object(user_id, folder_id, kind, object_id):
    """Take a rule / bundle out of one folder (used by the picker)."""
    col = UserCollectionItem.rule_id if kind == 'rule' else UserCollectionItem.bundle_id
    n = (UserCollectionItem.query
         .filter(UserCollectionItem.user_id == user_id, UserCollectionItem.collection_id == int(folder_id),
                 col == int(object_id))
         .delete(synchronize_session=False))
    db.session.commit()
    return n


def membership(user_id, kind, object_id):
    """Folders holding this rule / bundle, with that item's note/status/reminder."""
    col = UserCollectionItem.rule_id if kind == 'rule' else UserCollectionItem.bundle_id
    items = UserCollectionItem.query.filter(UserCollectionItem.user_id == user_id, col == int(object_id)).all()
    return [{"item_id": i.id, "collection_id": i.collection_id, "note": i.note, "status": i.status,
             "remind_at": _iso(i.remind_at)} for i in items]


def _pending_proposals(rule_ids):
    if not rule_ids:
        return {}
    return dict(db.session.query(RuleEditProposal.rule_id, func.count())
                .filter(RuleEditProposal.rule_id.in_(rule_ids), RuleEditProposal.status == 'pending')
                .group_by(RuleEditProposal.rule_id).all())


def list_items(user_id, folder_id=None, view=None, status=None, kind=None, search=None, page=1, per_page=20):
    """Items of a folder (sub-folders not included) or of a smart view:
    view='all' every item, 'due' reminders due now, 'upcoming' future reminders.
    Deleted rules stay listed (flagged) so the note is not lost."""
    now = _utcnow()
    q = (UserCollectionItem.query.filter(UserCollectionItem.user_id == user_id)
         .outerjoin(Rule, Rule.id == UserCollectionItem.rule_id)
         .outerjoin(Bundle, Bundle.id == UserCollectionItem.bundle_id))
    if folder_id:
        q = q.filter(UserCollectionItem.collection_id == ((_ids(folder_id) or [0])[0]))
    if view == 'due':
        q = q.filter(UserCollectionItem.remind_at.isnot(None), UserCollectionItem.remind_at <= now,
                     UserCollectionItem.status != 'done')
    elif view == 'upcoming':
        q = q.filter(UserCollectionItem.remind_at > now, UserCollectionItem.status != 'done')
    if status in status_keys():
        q = q.filter(UserCollectionItem.status == status)
    if kind == 'rule':
        q = q.filter(UserCollectionItem.rule_id.isnot(None))
    elif kind == 'bundle':
        q = q.filter(UserCollectionItem.bundle_id.isnot(None))
    if isinstance(search, str) and search.strip():
        s = f"%{search.strip()[:200]}%"
        q = q.filter(or_(Rule.title.ilike(s), Bundle.name.ilike(s), UserCollectionItem.note.ilike(s),
                         Rule.format.ilike(s)))
    if view in ('due', 'upcoming'):
        q = q.order_by(UserCollectionItem.remind_at.asc())
    else:
        q = q.order_by(UserCollectionItem.updated_at.desc(), UserCollectionItem.id.desc())
    pag = q.paginate(page=max(1, int(page)), per_page=min(max(1, int(per_page)), 100), error_out=False)

    proposals = _pending_proposals([i.rule_id for i in pag.items if i.rule_id])
    folders = {f.id: f for f in UserCollection.query.filter_by(user_id=user_id).all()}
    items = []
    for i in pag.items:
        d = {"id": i.id, "collection_id": i.collection_id, "note": i.note, "status": i.status,
             "remind_at": _iso(i.remind_at), "created_at": _iso(i.created_at), "updated_at": _iso(i.updated_at),
             "due": bool(i.remind_at and i.remind_at <= now and i.status != 'done')}
        f = folders.get(i.collection_id)
        d['folder'] = {"id": f.id, "name": f.name, "icon": f.icon, "color": f.color} if f else None
        if i.rule_id:
            r = i.rule
            d['kind'] = 'rule'
            d['object'] = {"id": r.id, "title": r.title, "format": r.format, "author": r.author,
                           "user_id": r.user_id, "deleted": bool(r.is_deleted),
                           "pending_proposals": proposals.get(r.id, 0),
                           "url": f"/rule/detail_rule/{r.id}"} if r else None
        else:
            b = i.bundle
            d['kind'] = 'bundle'
            d['object'] = {"id": b.id, "title": b.name, "user_id": b.user_id,
                           "rules": b.rules_assoc.count() if hasattr(b.rules_assoc, 'count') else None,
                           "url": f"/bundle/detail/{b.id}"} if b else None
        items.append(d)
    return {"items": items, "total": pag.total, "total_pages": pag.pages, "page": pag.page}


def rule_ids_of_folder(user_id, folder_id):
    """Active rule ids of a folder — for "download" / "make a bundle" actions."""
    return [rid for (rid,) in db.session.query(UserCollectionItem.rule_id)
            .join(Rule, Rule.id == UserCollectionItem.rule_id)
            .filter(UserCollectionItem.user_id == user_id, UserCollectionItem.collection_id == int(folder_id),
                    Rule.is_deleted.is_(False)).all()]


# ── Cleanup (called when a rule / bundle / user is deleted for good) ─────────

def purge_objects(kind, ids):
    """Drop the folder items of rules / bundles being deleted for good.
    No commit — runs inside the caller's delete transaction (the FK also
    cascades on PostgreSQL; this keeps SQLite and the ORM in step)."""
    ids = [int(i) for i in (ids if isinstance(ids, (list, tuple, set)) else [ids])]
    if not ids:
        return
    col = UserCollectionItem.rule_id if kind == 'rule' else UserCollectionItem.bundle_id
    UserCollectionItem.query.filter(col.in_(ids)).delete(synchronize_session=False)


def purge_user(user_id):
    """A user deleted: their folders and items go too (no commit)."""
    UserCollectionItem.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    UserCollection.query.filter_by(user_id=user_id).update({'parent_id': None}, synchronize_session=False)
    UserCollection.query.filter_by(user_id=user_id).delete(synchronize_session=False)


# ── Reminders (called by the task-scheduler ticker) ──────────────────────────

def fire_due_reminders(now=None):
    """One notification per item whose reminder has come, once."""
    from app.features.notification.notification_core import create_notification
    now = now or _utcnow()
    due = (UserCollectionItem.query
           .filter(UserCollectionItem.remind_at.isnot(None), UserCollectionItem.remind_at <= now,
                   UserCollectionItem.reminded_at.is_(None))
           .limit(500).all())
    for i in due:
        i.reminded_at = now
        if i.status == 'done':
            continue
        title = (i.rule.title if i.rule_id and i.rule else i.bundle.name if i.bundle_id and i.bundle else 'an item')
        folder = i.collection.name if i.collection else 'a folder'
        create_notification(
            i.user_id, 'collection_reminder',
            f"Reminder: {title[:120]}",
            body=(f"[{folder}] " + (i.note or 'You asked to be reminded about it.'))[:500],
            link=f"/rule/owner_rules?tab=folders&folder={i.collection_id}&item={i.id}")
    db.session.commit()
    return len(due)
