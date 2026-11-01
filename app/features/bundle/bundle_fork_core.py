"""
bundle_fork_core.py — forks and merge requests of bundles ("GitHub for bundles").
Plan and every case: docs/future/bundle_forks.md. Models: app/core/db_class/bundle_fork.py.

    fork_bundle(bundle, user)              → a copy that stays linked to its upstream
    fork_rule_copy(fork, rule, content)    → edit a rule you don't own, in your fork only (copy-on-write)
    open_merge_request(source, target, …)  → changes of a fork proposed to its upstream (or the reverse: sync)
    refresh_merge_request(mr)              → recompute the changes (either side moved)
    set_decision(mr, item_id, decision)    → accept / reject an item, pick a side for a conflict
    merge(mr, user)                        → apply the accepted items to the target, atomically
    sync_fork(fork, user)                  → bring the upstream's new changes into the fork

How changes are found — a three-way comparison, like git:
    base   = the upstream as it was when the fork was made / last synced or merged (hashes only)
    source = the bundle the changes come from, now
    target = the bundle they go to, now
For each rule (matched by uuid — a fork's copy of a rule is matched with its original), custom file
(matched by path), folder and metadata field: changed only in source → proposed; changed only in
target → kept; changed on both sides differently → conflict, the reviewer picks a side.
Rights: can_* functions below, enforced by the routes (bundle_fork_routes.py).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid as uuid_mod

from flask_login import current_user

from app import db
from app.core.db_class.bundle import Bundle, BundleNode, BundleRuleAssociation
from app.core.db_class.bundle_fork import BundleForkRule, BundleMergeRequest
from app.core.db_class.rule import Rule
from app.core.db_class.tag import BundleTagAssociation, Tag
from app.core.utils.app_settings import setting

FORK_SETTINGS = setting('bundle.fork')          # app/config/bundle.fork.json
MAX_ITEM_CONTENT = 200_000                      # chars of rule / file content kept per side in an item


def _now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


def _cfg(key, default):
    try:
        return (FORK_SETTINGS.value or {}).get(key, default)
    except Exception:
        return default


def _hash(text) -> str:
    return hashlib.sha1((text or '').encode('utf-8', 'replace')).hexdigest()[:20]


# ── Snapshots ─────────────────────────────────────────────────────────────

def rule_keys(bundle_id: int) -> dict:
    """{rule_id: key} — a rule's key is its uuid, or for a copy (BundleForkRule) its original's uuid."""
    copies = dict(db.session.query(BundleForkRule.copy_rule_id, BundleForkRule.original_rule_uuid)
                  .filter(BundleForkRule.bundle_id == bundle_id).all())
    return copies


def snapshot(bundle_id: int, with_content: bool = True) -> dict | None:
    """Everything a merge compares, keyed by stable identities. Without content: hashes only
    (what is stored as a fork's common ancestor)."""
    bundle = db.session.get(Bundle, bundle_id)
    if not bundle:
        return None
    nodes = BundleNode.query.filter_by(bundle_id=bundle_id).order_by(BundleNode.id).all()
    by_id = {n.id: n for n in nodes}

    def path_of(node):
        parts, cur, guard = [], node, 0
        while cur is not None and guard < 60:
            parts.append(cur.name or '?')
            cur = by_id.get(cur.parent_id)
            guard += 1
        return '/'.join(reversed(parts))

    assoc = {rid for (rid,) in db.session.query(BundleRuleAssociation.rule_id)
             .filter(BundleRuleAssociation.bundle_id == bundle_id)}
    placed = {n.rule_id: n for n in nodes if n.rule_id}
    rule_ids = assoc | set(placed)
    rules_db = {r.id: r for r in (Rule.query.filter(Rule.id.in_(rule_ids), Rule.is_deleted == False).all()
                                  if rule_ids else [])}
    copies = rule_keys(bundle_id)

    rules, files, folders = {}, {}, []
    for rid, r in rules_db.items():
        node = placed.get(rid)
        parent = by_id.get(node.parent_id) if node else None
        entry = {'rule_id': rid, 'uuid': r.uuid, 'title': r.title, 'format': r.format or '',
                 'hash': _hash(r.to_string), 'folder': path_of(parent) if parent else '', 'owner_id': r.user_id}
        if with_content:
            entry['content'] = (r.to_string or '')[:MAX_ITEM_CONTENT]
        rules[copies.get(rid) or r.uuid] = entry
    for n in nodes:
        if n.node_type == 'folder':
            folders.append(path_of(n))
        elif not n.rule_id:
            entry = {'hash': _hash(n.custom_content)}
            if with_content:
                entry['content'] = (n.custom_content or '')[:MAX_ITEM_CONTENT]
            files[path_of(n)] = entry

    tags = sorted(name for (name,) in db.session.query(Tag.name)
                  .join(BundleTagAssociation, BundleTagAssociation.tag_id == Tag.id)
                  .filter(BundleTagAssociation.bundle_id == bundle_id))
    try:
        vulns = sorted(str(v) for v in json.loads(bundle.vulnerability_identifiers or '[]'))
    except Exception:
        vulns = []
    return {'meta': {'description': bundle.description or '', 'tags': tags, 'vulnerabilities': vulns},
            'rules': rules, 'files': files, 'folders': sorted(set(folders))}


def strip_content(snap: dict | None) -> dict | None:
    """The same snapshot, hashes only (stored as a common ancestor)."""
    if not snap:
        return snap
    out = json.loads(json.dumps(snap))
    for section in ('rules', 'files'):
        for entry in (out.get(section) or {}).values():
            entry.pop('content', None)
    return out


# ── Three-way comparison ──────────────────────────────────────────────────

def _same(a, b) -> bool:
    """Same presence and same content (hash)."""
    if a is None or b is None:
        return a is None and b is None
    return a.get('hash') == b.get('hash')


def _side(entry, keys=('rule_id', 'uuid', 'title', 'format', 'hash', 'folder', 'content')):
    return {k: entry.get(k) for k in keys if k in entry} if entry else None


def compute_changes(base: dict, source: dict, target: dict) -> list:
    """Items of the changeset source → target, against their common ancestor `base`."""
    base = base or {'meta': {}, 'rules': {}, 'files': {}, 'folders': []}
    items = []

    def add(kind, key, label, conflict=None, **extra):
        # one id per change: a rule can be both changed and moved → "rule:<uuid>" and "move:<uuid>"
        prefix = 'move' if kind == 'rule_moved' else kind.split('_')[0]
        items.append({'id': f'{prefix}:{key}', 'kind': kind, 'key': key, 'label': label,
                      'conflict': bool(conflict), 'conflict_kind': conflict,
                      'decision': None if conflict else 'accept', **extra})

    # Rules — presence + content, then folder moves
    b_r, s_r, t_r = base.get('rules') or {}, source.get('rules') or {}, target.get('rules') or {}
    for key in sorted(set(b_r) | set(s_r) | set(t_r)):
        b, s, t = b_r.get(key), s_r.get(key), t_r.get(key)
        label = (s or t or b or {}).get('title') or key
        if not _same(s, b) and not _same(s, t):
            sides = {'source': _side(s), 'target': _side(t), 'base_hash': (b or {}).get('hash')}
            if b is None and t is None:
                add('rule_added', key, label, **sides)
            elif s is None:
                if _same(t, b):
                    add('rule_removed', key, label, **sides)
                else:
                    add('rule_removed', key, label, conflict='modify_delete', **sides)
            elif t is None:
                add('rule_modified', key, label, conflict='delete_modify' if b else None, **sides)
            elif _same(t, b):
                add('rule_modified', key, label, **sides)
            else:
                add('rule_modified', key, label, conflict='content', **sides)
        if s and b and s.get('folder') != b.get('folder') and (t is None or s.get('folder') != t.get('folder')):
            if t is None:
                if _same(s, b):          # moved here, removed there (a content change is already an item above)
                    add('rule_moved', key, label, conflict='delete_move',
                        source={'folder': s.get('folder'), 'rule_id': s.get('rule_id')}, target=None, base_folder=b.get('folder'))
            else:
                conflict = 'move' if t.get('folder') != b.get('folder') else None
                add('rule_moved', key, label, conflict=conflict, source={'folder': s.get('folder'), 'rule_id': s.get('rule_id')},
                    target={'folder': t.get('folder'), 'rule_id': t.get('rule_id')}, base_folder=b.get('folder'))

    # Custom files — by path
    b_f, s_f, t_f = base.get('files') or {}, source.get('files') or {}, target.get('files') or {}
    for path in sorted(set(b_f) | set(s_f) | set(t_f)):
        b, s, t = b_f.get(path), s_f.get(path), t_f.get(path)
        if _same(s, b) or _same(s, t):
            continue
        sides = {'source': _side(s, ('hash', 'content')), 'target': _side(t, ('hash', 'content')),
                 'base_hash': (b or {}).get('hash')}
        if b is None and t is None:
            add('file_added', path, path, **sides)
        elif s is None:
            add('file_removed', path, path, conflict=None if _same(t, b) else 'modify_delete', **sides)
        elif t is None:
            add('file_modified', path, path, conflict='delete_modify' if b else None, **sides)
        else:
            add('file_modified', path, path, conflict=None if _same(t, b) else 'content', **sides)

    # Folders — added / removed (removal only empties what the merge also removed)
    b_d, s_d, t_d = set(base.get('folders') or []), set(source.get('folders') or []), set(target.get('folders') or [])
    for path in sorted((s_d - b_d) - t_d):
        add('folder_added', path, path)
    for path in sorted((b_d - s_d) & t_d):
        add('folder_removed', path, path)

    # Metadata — description (text), tags and vulnerabilities (sets: additions / removals merge)
    bm, sm, tm = base.get('meta') or {}, source.get('meta') or {}, target.get('meta') or {}
    bd, sd, td = bm.get('description', ''), sm.get('description', ''), tm.get('description', '')
    if sd != bd and sd != td:
        add('meta_description', 'description', 'Description', conflict='content' if td != bd else None,
            source={'content': sd}, target={'content': td})
    for field, label in (('tags', 'Tags'), ('vulnerabilities', 'Vulnerabilities')):
        bs, ss, ts = set(bm.get(field) or []), set(sm.get(field) or []), set(tm.get(field) or [])
        plus, minus = sorted((ss - bs) - ts), sorted((bs - ss) & ts)
        if plus or minus:
            add(f'meta_{field}', field, label, source={'add': plus, 'remove': minus}, target={'values': sorted(ts)})
    return items


def summarize_changes(items: list) -> dict:
    """conflicts: the ones still to resolve — a conflict decided (take theirs / keep mine) is 'resolved', not a
    conflict anymore."""
    out = {'rules': 0, 'files': 0, 'folders': 0, 'meta': 0, 'conflicts': 0, 'resolved': 0, 'total': len(items or [])}
    for i in items or []:
        out[{'rule': 'rules', 'file': 'files', 'folder': 'folders', 'meta': 'meta'}[i['kind'].split('_')[0]]] += 1
        if i.get('conflict'):
            out['resolved' if i.get('decision') in ('source', 'target') else 'conflicts'] += 1
    return out


# ── Rights ────────────────────────────────────────────────────────────────

def _user(user=None):
    u = user if user is not None else current_user
    return u if (u is not None and getattr(u, 'is_authenticated', False)) else None


def is_manager(bundle, user=None) -> bool:
    u = _user(user)
    return bool(u and bundle and (u.id == bundle.user_id or u.is_admin()))


def can_view(bundle, user=None) -> bool:
    if not bundle:
        return False
    if bundle.access:
        return True
    if is_manager(bundle, user):
        return True
    from app.features.bundle.bundle_core import can_view_bundle
    return user is None and can_view_bundle(bundle)


def forks_enabled() -> bool:
    return bool(_cfg('enabled', True))


def can_fork(bundle, user=None) -> tuple[bool, str]:
    u = _user(user)
    if not forks_enabled():
        return False, 'Forks are turned off on this instance.'
    if not u:
        return False, 'Sign in to fork a bundle.'
    if not bundle:
        return False, 'Bundle not found.'
    if not bundle.access and not (u.is_admin() or bundle.user_id == u.id):
        return False, 'A private bundle can only be forked by its owner or an admin.'
    limit = int(_cfg('daily_limit', 20) or 0)
    if limit and not u.is_admin():
        since = _now() - datetime.timedelta(days=1)
        made = Bundle.query.filter(Bundle.user_id == u.id, Bundle.forked_from_id.isnot(None),
                                   Bundle.created_at >= since.replace(tzinfo=None)).count()
        if made >= limit:
            return False, f'You can fork {limit} bundles a day at most.'
    return True, ''


def can_view_mr(mr, user=None) -> bool:
    u = _user(user)
    if not mr or not mr.target:
        return False
    if u and (u.is_admin() or u.id == mr.user_id or u.id == mr.target.user_id):
        return True                       # its author and the target's owner always see it
    return can_view(mr.target, user) and (mr.source is None or can_view(mr.source, user))


def can_review_mr(mr, user=None) -> bool:
    """Merge, close, decide on items: the target's owner or an admin."""
    return bool(mr and mr.target and is_manager(mr.target, user))


def can_close_mr(mr, user=None) -> bool:
    u = _user(user)
    return can_review_mr(mr, user) or bool(u and mr and u.id == mr.user_id)


# ── Fork ──────────────────────────────────────────────────────────────────

def _base_name(name: str) -> str:
    """A fork of a fork is named "X (fork)", never "X (fork) (fork)"."""
    return re.sub(r'(\s*\(fork\))+\s*$', '', name or '').strip() or (name or 'Bundle')


def fork_bundle(upstream: Bundle, user, name: str | None = None) -> Bundle:
    """A new bundle owned by `user`: same tree, same rules (shared, not copied), description, tags,
    CVEs. Not copied: votes, views, favorites, releases, notes, share link, verified badge."""
    from app.features.bundle.bundle_history_core import record_bundle_created
    snap = snapshot(upstream.id, with_content=False)
    fork = Bundle(
        uuid=str(uuid_mod.uuid4()),
        name=((name or '').strip() or f'{_base_name(upstream.name)} (fork)')[:255],
        description=upstream.description,
        user_id=user.id,
        access=bool(upstream.access),
        created_by='user',
        is_verified=False,
        view_count=0, download_count=0,
        created_at=_now(), updated_at=_now(),
        vulnerability_identifiers=upstream.vulnerability_identifiers,
        forked_from_id=upstream.id,
        forked_from_uuid=upstream.uuid,
        fork_base_snapshot=snap,
        fork_base_at=_now(),
        accepts_proposals=True,
    )
    db.session.add(fork)
    db.session.flush()

    # tree: same order (id order = display order), new ids
    nodes = BundleNode.query.filter_by(bundle_id=upstream.id).order_by(BundleNode.id).all()
    live_rules = {rid for (rid,) in db.session.query(Rule.id).filter(
        Rule.id.in_([n.rule_id for n in nodes if n.rule_id] or [0]), Rule.is_deleted == False)}
    new_ids = {}
    for n in nodes:
        if n.rule_id and n.rule_id not in live_rules:
            continue
        if n.parent_id and n.parent_id not in new_ids:
            continue                                   # parent skipped
        copy = BundleNode(bundle_id=fork.id, parent_id=new_ids.get(n.parent_id), name=n.name,
                          node_type=n.node_type, custom_content=n.custom_content, rule_id=n.rule_id)
        db.session.add(copy)
        db.session.flush()
        new_ids[n.id] = copy.id
    for a in BundleRuleAssociation.query.filter_by(bundle_id=upstream.id).all():
        if a.rule_id in live_rules or Rule.query.filter_by(id=a.rule_id, is_deleted=False).first():
            db.session.add(BundleRuleAssociation(bundle_id=fork.id, rule_id=a.rule_id, description=a.description,
                                                 added_at=_now()))
    for c in BundleForkRule.query.filter_by(bundle_id=upstream.id).all():
        db.session.add(BundleForkRule(bundle_id=fork.id, original_rule_uuid=c.original_rule_uuid,
                                      copy_rule_id=c.copy_rule_id))
    for (tag_id,) in db.session.query(BundleTagAssociation.tag_id).filter_by(bundle_id=upstream.id).all():
        db.session.add(BundleTagAssociation(uuid=str(uuid_mod.uuid4()), bundle_id=fork.id, tag_id=tag_id, user_id=user.id))
    db.session.commit()
    record_bundle_created(fork.id, user)
    return fork


def fork_chain(bundle, limit=10) -> list:
    """Upstream, its upstream… (closest first), as far as they still exist."""
    out, seen, cur = [], {bundle.id}, bundle
    while cur and cur.forked_from_id and len(out) < limit:
        up = db.session.get(Bundle, cur.forked_from_id)
        if not up or up.id in seen:
            break
        out.append(up)
        seen.add(up.id)
        cur = up
    return out


def list_forks(bundle, user=None) -> dict:
    """Forks of `bundle` the viewer may see, and how many private ones are hidden."""
    forks = Bundle.query.filter_by(forked_from_id=bundle.id).order_by(Bundle.created_at.desc()).all()
    visible = [f for f in forks if can_view(f, user)]
    return {'forks': visible, 'hidden': len(forks) - len(visible), 'total': len(forks)}


def fork_status(fork: Bundle) -> dict:
    """Changes not yet in the upstream (ahead) and upstream changes not yet in the fork (behind)."""
    up = db.session.get(Bundle, fork.forked_from_id) if fork.forked_from_id else None
    if not up:
        return {'upstream': None, 'ahead': 0, 'behind': 0}
    base = fork.fork_base_snapshot or {}
    mine, theirs = snapshot(fork.id, with_content=False), snapshot(up.id, with_content=False)
    ahead_items, behind_items = compute_changes(base, mine, theirs), compute_changes(base, theirs, mine)
    ahead, behind = summarize_changes(ahead_items), summarize_changes(behind_items)
    brief = lambda items: [{'kind': i['kind'], 'label': i['label'], 'conflict': i['conflict']} for i in items[:6]]
    return {'upstream': up, 'ahead': ahead['total'], 'behind': behind['total'],
            'ahead_detail': ahead, 'behind_detail': behind,
            'ahead_items': brief(ahead_items), 'behind_items': brief(behind_items)}


# ── Copy-on-write: edit a rule you don't own, in your fork only ───────────

def fork_rule_copy(bundle: Bundle, rule: Rule, content: str, user) -> tuple[Rule | None, str]:
    """Create a new rule (owned by `user`) with `content`, and use it instead of `rule` in `bundle`
    only. The original rule and every other bundle stay untouched."""
    from app.features.rule import rule_core as RuleModel
    from app.features.rule.rule_format.main_format import verify_syntax_rule_by_format
    content = (content or '').strip()
    if not content or content == (rule.to_string or '').strip():
        return None, 'Change the content first: the copy must differ from the original.'
    ok, err = verify_syntax_rule_by_format({'format': rule.format, 'to_string': content}, rule=rule)
    if not ok:
        return None, f'Invalid rule: {err}'
    copies = rule_keys(bundle.id)
    key = copies.get(rule.id) or rule.uuid
    copy, msg = RuleModel.add_rule_core({
        'title': rule.title, 'to_string': content, 'format': rule.format, 'license': rule.license or 'unknown',
        'description': rule.description or '', 'source': rule.source, 'author': rule.author,
        'version': rule.version or '1.0', 'tags': [a.tag_id for a in rule.rule_tags_assocs],
        'cve_id': rule.cve_id,
        '_fork_copy_of': rule.uuid,         # same rule name / id as the original is expected for a copy
    }, user)
    if not copy:
        return None, msg if isinstance(msg, str) else 'The copy could not be created.'
    _swap_rule(bundle.id, rule.id, copy.id)
    BundleForkRule.query.filter_by(bundle_id=bundle.id, copy_rule_id=rule.id).delete()
    db.session.add(BundleForkRule(bundle_id=bundle.id, original_rule_uuid=key, copy_rule_id=copy.id))
    bundle.updated_at = _now()
    db.session.commit()
    return copy, ''


def _swap_rule(bundle_id: int, old_rule_id: int, new_rule_id: int):
    """`new_rule_id` takes the place of `old_rule_id` in the bundle (association and tree node). No commit."""
    for a in BundleRuleAssociation.query.filter_by(bundle_id=bundle_id, rule_id=old_rule_id).all():
        if BundleRuleAssociation.query.filter_by(bundle_id=bundle_id, rule_id=new_rule_id).first():
            db.session.delete(a)
        else:
            a.rule_id = new_rule_id
    for n in BundleNode.query.filter_by(bundle_id=bundle_id, rule_id=old_rule_id).all():
        n.rule_id = new_rule_id
    db.session.flush()


# ── Merge requests ────────────────────────────────────────────────────────

def _pair_base(source: Bundle, target: Bundle) -> dict | None:
    """Common ancestor of two bundles that are fork and upstream of each other."""
    if source.forked_from_id == target.id:
        return source.fork_base_snapshot
    if target.forked_from_id == source.id:
        return target.fork_base_snapshot
    return None


def related(source: Bundle, target: Bundle) -> bool:
    return bool(source and target and source.id != target.id
                and (source.forked_from_id == target.id or target.forked_from_id == source.id))


def can_open_mr(source: Bundle, target: Bundle, user=None) -> tuple[bool, str]:
    u = _user(user)
    if not u:
        return False, 'Sign in first.'
    if not related(source, target):
        return False, 'A merge request goes between a fork and the bundle it was forked from.'
    if not is_manager(source, u):
        return False, 'Only the owner of the bundle the changes come from can propose them.'
    if not can_view(target, u):
        return False, 'Bundle not found.'
    if not target.accepts_proposals and not is_manager(target, u):
        return False, 'The owner of this bundle does not take merge requests.'
    if BundleMergeRequest.query.filter_by(source_bundle_id=source.id, target_bundle_id=target.id, status='open').first():
        return False, 'A merge request between these two bundles is already open — update it instead.'
    return True, ''


def open_merge_request(source: Bundle, target: Bundle, user, title: str, message: str = '',
                       kind: str = 'contribute') -> tuple[BundleMergeRequest | None, str]:
    items = compute_changes(_pair_base(source, target), snapshot(source.id), snapshot(target.id))
    if not items:
        return None, 'Nothing to propose: the two bundles already have the same content.'
    mr = BundleMergeRequest(
        uuid=str(uuid_mod.uuid4()), source_bundle_id=source.id, source_bundle_uuid=source.uuid,
        target_bundle_id=target.id, user_id=user.id, kind=kind,
        title=((title or '').strip() or f'Changes from {source.name}')[:255], message=(message or '').strip(),
        status='open', items=items, base_snapshot=_pair_base(source, target), computed_at=_now(),
    )
    db.session.add(mr)
    db.session.commit()
    return mr, ''


def refresh_merge_request(mr: BundleMergeRequest) -> BundleMergeRequest:
    """Recompute the changes (source or target moved since). A decision already taken on an item that
    is still the same change (same source and target hashes) is kept."""
    if mr.status != 'open':
        return mr
    if not mr.source or not mr.target or not related(mr.source, mr.target):
        mr.status = 'stale'
        db.session.commit()
        return mr
    old = {i['id']: i for i in (mr.items or [])}
    items = compute_changes(_pair_base(mr.source, mr.target), snapshot(mr.source.id), snapshot(mr.target.id))
    for i in items:
        prev = old.get(i['id'])
        if prev and prev.get('decision') and _fingerprint(prev) == _fingerprint(i):
            i['decision'] = prev['decision']
            if prev.get('rule_mode'):
                i['rule_mode'] = prev['rule_mode']
    mr.items = items
    mr.base_snapshot = _pair_base(mr.source, mr.target)
    mr.computed_at = _now()
    db.session.commit()
    return mr


def _fingerprint(item) -> tuple:
    s, t = item.get('source') or {}, item.get('target') or {}
    return (item.get('kind'), s.get('hash'), t.get('hash'), s.get('folder'), t.get('folder'),
            json.dumps(s.get('add')), json.dumps(s.get('remove')), s.get('content') if item['kind'] == 'meta_description' else None)


DECISIONS = {'accept', 'reject', 'source', 'target'}
RULE_MODES = {'update', 'link', 'propose'}


def set_decision(mr: BundleMergeRequest, item_id: str, decision: str, rule_mode: str | None = None) -> str:
    """'' or why not. Conflicts take 'source' / 'target'; other items 'accept' / 'reject'.
    rule_mode (changed rule): update the target's rule | link the source's rule | propose an edit."""
    items = json.loads(json.dumps(mr.items or []))     # a copy: an in-place change would not be saved
    for i in items:
        if i['id'] != item_id:
            continue
        allowed = {'source', 'target'} if i.get('conflict') else {'accept', 'reject'}
        if decision not in allowed:
            return f'Choose one of: {", ".join(sorted(allowed))}.'
        i['decision'] = decision
        if rule_mode:
            if rule_mode not in RULE_MODES or i['kind'] != 'rule_modified':
                return 'This choice is only for a changed rule.'
            i['rule_mode'] = rule_mode
        mr.items = items
        mr.updated_at = _now()
        db.session.commit()
        return ''
    return 'Item not found — refresh the merge request.'


def merge_blockers(mr: BundleMergeRequest) -> list:
    out = []
    if mr.status != 'open':
        out.append('This merge request is not open.')
    if not mr.source or not mr.target:
        out.append('One of the two bundles does not exist anymore.')
    unresolved = [i['label'] for i in (mr.items or []) if i.get('conflict') and i.get('decision') not in ('source', 'target')]
    if unresolved:
        out.append(f'{len(unresolved)} conflict(s) to resolve first.')
    return out


def merge(mr: BundleMergeRequest, user) -> tuple[dict | None, str]:
    """Apply the accepted items to the target in one transaction (all or nothing), record it in the
    target's history, move the fork's common ancestor. Returns (summary, error)."""
    from app.features.bundle.bundle_history_core import track_bundle_change
    refresh_merge_request(mr)                         # never merge a stale picture
    blockers = merge_blockers(mr)
    if blockers:
        return None, ' '.join(blockers)
    target, source = mr.target, mr.source
    done = {'applied': [], 'skipped': [], 'proposals': []}
    after = []        # what commits on its own (rule history, edit proposals): run once the merge is committed
    try:
        with track_bundle_change(target.id, 'merge', user=user):
            for item in mr.items or []:
                take = item.get('decision') in ('accept', 'source')
                if not take:
                    done['skipped'].append(item['label'])
                    continue
                note = _apply_item(target, source, item, user, after=after)
                (done['proposals'] if note and note.startswith('proposal') else done['applied']).append(
                    f"{item['label']}{' — ' + note if note else ''}")
            target.updated_at = _now()
            db.session.flush()
        # the fork's common ancestor moves to what both now share
        fork = source if source.forked_from_id == target.id else target
        up = target if fork is source else source
        fork.fork_base_snapshot = snapshot(up.id, with_content=False)
        fork.fork_base_at = _now()
        mr.status, mr.reviewed_by_id, mr.reviewed_at = 'merged', user.id, _now()
        mr.merged_summary = done
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    for action in after:              # best effort: the merge itself is done and consistent
        try:
            action()
        except Exception:
            db.session.rollback()
    return done, ''


def _ensure_folder(bundle_id: int, path: str):
    parent = None
    for name in [p for p in (path or '').split('/') if p]:
        q = BundleNode.query.filter_by(bundle_id=bundle_id, node_type='folder', name=name[:255],
                                       parent_id=parent.id if parent else None)
        folder = q.first()
        if not folder:
            folder = BundleNode(bundle_id=bundle_id, parent_id=parent.id if parent else None,
                                name=name[:255], node_type='folder')
            db.session.add(folder)
            db.session.flush()
        parent = folder
    return parent


def _file_node(bundle_id: int, path: str):
    folder, _, name = (path or '').rpartition('/')
    parent = _ensure_folder(bundle_id, folder) if folder else None
    return BundleNode.query.filter_by(bundle_id=bundle_id, parent_id=parent.id if parent else None,
                                      name=name[:255], rule_id=None).filter(BundleNode.node_type != 'folder').first(), parent, name


def _place_rule(bundle_id: int, rule_id: int, folder: str):
    if not BundleRuleAssociation.query.filter_by(bundle_id=bundle_id, rule_id=rule_id).first():
        db.session.add(BundleRuleAssociation(bundle_id=bundle_id, rule_id=rule_id, added_at=_now()))
    node = BundleNode.query.filter_by(bundle_id=bundle_id, rule_id=rule_id).first()
    parent = _ensure_folder(bundle_id, folder) if folder else None
    if node:
        node.parent_id = parent.id if parent else None
    else:
        rule = db.session.get(Rule, rule_id)
        db.session.add(BundleNode(bundle_id=bundle_id, parent_id=parent.id if parent else None,
                                  name=((rule.title if rule else '') or 'rule')[:255], node_type='file', rule_id=rule_id))
    db.session.flush()


def _remove_rule(bundle_id: int, rule_id: int):
    BundleRuleAssociation.query.filter_by(bundle_id=bundle_id, rule_id=rule_id).delete()
    for n in BundleNode.query.filter_by(bundle_id=bundle_id, rule_id=rule_id).all():
        db.session.delete(n)
    BundleForkRule.query.filter_by(bundle_id=bundle_id, copy_rule_id=rule_id).delete()
    db.session.flush()


def _link_copy(target_id: int, source_id: int, key: str, rule_id: int):
    """Keep the target matching a copy with its original (future merges line up)."""
    rule = db.session.get(Rule, rule_id)
    if rule and rule.uuid != key and not BundleForkRule.query.filter_by(bundle_id=target_id, copy_rule_id=rule_id).first():
        db.session.add(BundleForkRule(bundle_id=target_id, original_rule_uuid=key, copy_rule_id=rule_id))


def _apply_item(target: Bundle, source: Bundle, item: dict, user, after: list | None = None) -> str:
    """One accepted item → the target, flushed but never committed (the merge is one transaction).
    Side effects that commit on their own go to `after`, run once the merge is committed.
    Returns a short note ('' when plain)."""
    after = after if after is not None else []
    kind, key = item['kind'], item['key']
    s, t = item.get('source') or {}, item.get('target') or {}
    if kind == 'rule_added' or (kind == 'rule_modified' and not t):
        rule = Rule.query.filter_by(id=s.get('rule_id'), is_deleted=False).first()
        if not rule:
            return 'skipped (rule deleted meanwhile)'
        _place_rule(target.id, rule.id, s.get('folder') or '')
        _link_copy(target.id, source.id, key, rule.id)
        return ''
    if kind == 'rule_removed':
        if t.get('rule_id'):
            _remove_rule(target.id, t['rule_id'])
        return ''
    if kind == 'rule_modified':
        new = Rule.query.filter_by(id=s.get('rule_id'), is_deleted=False).first()
        old = Rule.query.filter_by(id=t.get('rule_id'), is_deleted=False).first()
        if not new:
            return 'skipped (rule deleted meanwhile)'
        if not old:
            _place_rule(target.id, new.id, s.get('folder') or '')
            return ''
        if new.id == old.id:
            return ''
        mode = item.get('rule_mode') or ('update' if (user.is_admin() or user.id == old.user_id) else 'link')
        if mode == 'update' and not (user.is_admin() or user.id == old.user_id):
            mode = 'propose'
        if mode == 'update':
            old_content = old.to_string
            old.to_string, old.last_modif = new.to_string, _now()
            db.session.flush()
            after.append(lambda rid=old.id, title=old.title, o=old_content, n=new.to_string: _rule_history(
                rid, title, o, n, user, f'Merged from bundle "{source.name}"'))
            return 'rule updated'
        if mode == 'propose':
            after.append(lambda rid=old.id, content=new.to_string: _open_proposal(rid, content, user, source.name))
            return 'proposal opened on the original rule (its owner decides)'
        _swap_rule(target.id, old.id, new.id)      # link: the target now uses the source's rule
        _link_copy(target.id, source.id, key, new.id)
        return 'now uses the copy from the fork'
    if kind == 'rule_moved':
        # the target's rule for this key; when the target removed it (delete_move conflict, source taken),
        # the source's rule comes back, in its new folder
        rid = t.get('rule_id') or _rule_id_for_key(target.id, key)
        if not rid:
            rule = Rule.query.filter_by(id=s.get('rule_id'), is_deleted=False).first()
            if not rule:
                return 'skipped (rule deleted meanwhile)'
            rid = rule.id
            _link_copy(target.id, source.id, key, rid)
        _place_rule(target.id, rid, s.get('folder') or '')
        return ''
    if kind in ('file_added', 'file_modified'):
        node, parent, name = _file_node(target.id, key)
        if node:
            node.custom_content = s.get('content') or ''
        else:
            db.session.add(BundleNode(bundle_id=target.id, parent_id=parent.id if parent else None, name=name[:255],
                                      node_type='file', custom_content=s.get('content') or ''))
        db.session.flush()
        return ''
    if kind == 'file_removed':
        node, _, _ = _file_node(target.id, key)
        if node:
            db.session.delete(node)
            db.session.flush()
        return ''
    if kind == 'folder_added':
        _ensure_folder(target.id, key)
        return ''
    if kind == 'folder_removed':
        folder = _folder_at(target.id, key)
        if folder and not BundleNode.query.filter_by(parent_id=folder.id).first():
            db.session.delete(folder)
            db.session.flush()
            return ''
        return 'kept (not empty)'
    if kind == 'meta_description':
        target.description = s.get('content') or ''
        return ''
    if kind == 'meta_tags':
        for name in s.get('add') or []:
            tag = Tag.query.filter_by(name=name).first()
            if tag and not BundleTagAssociation.query.filter_by(bundle_id=target.id, tag_id=tag.id).first():
                db.session.add(BundleTagAssociation(uuid=str(uuid_mod.uuid4()), bundle_id=target.id, tag_id=tag.id,
                                                    user_id=user.id))
        for name in s.get('remove') or []:
            tag = Tag.query.filter_by(name=name).first()
            if tag:
                BundleTagAssociation.query.filter_by(bundle_id=target.id, tag_id=tag.id).delete()
        db.session.flush()
        return ''
    if kind == 'meta_vulnerabilities':
        try:
            current = list(json.loads(target.vulnerability_identifiers or '[]'))
        except Exception:
            current = []
        current = [v for v in current if str(v) not in set(s.get('remove') or [])]
        current += [v for v in s.get('add') or [] if v not in [str(c) for c in current]]
        target.vulnerability_identifiers = json.dumps(current)
        return ''
    return 'unknown change, skipped'


def _rule_id_for_key(bundle_id: int, key: str):
    snap = snapshot(bundle_id, with_content=False) or {}
    return ((snap.get('rules') or {}).get(key) or {}).get('rule_id')


def _folder_at(bundle_id: int, path: str):
    parent = None
    for name in [p for p in (path or '').split('/') if p]:
        parent = BundleNode.query.filter_by(bundle_id=bundle_id, node_type='folder', name=name,
                                            parent_id=parent.id if parent else None).first()
        if not parent:
            return None
    return parent


def _rule_history(rule_id, title, old, new, user, message):
    """History entry of a rule a merge updated (it also notifies the users who favorited it)."""
    from app.features.rule import rule_core as RuleModel
    RuleModel.create_rule_history({'id': rule_id, 'title': title, 'success': True, 'message': message,
                                   'old_content': old, 'new_content': new, 'analyzed_by_user_id': user.id,
                                   'change_type': 'content'})


def _open_proposal(rule_id, content, user, source_name):
    """Edit proposal on a rule the merger may not edit — its owner decides, like any proposal."""
    from app.features.rule import rule_core as RuleModel
    from app.core.db_class.rule_proposal import RuleEditProposal
    ok, pid = RuleModel.propose_edit_core({'rule_id': rule_id, 'proposed_content': content,
                                          'message': f'From bundle "{source_name}" (merge request).',
                                          'edit_type': 'content_update'}, user.id)
    if ok:
        try:
            from app.features.notification.notification_core import notify_proposal_submitted
            notify_proposal_submitted(db.session.get(RuleEditProposal, pid), db.session.get(Rule, rule_id))
        except Exception:
            db.session.rollback()


def close_merge_request(mr: BundleMergeRequest, user, note: str = '') -> None:
    mr.status, mr.reviewed_by_id, mr.reviewed_at = 'closed', user.id, _now()
    mr.review_note = (note or '').strip() or None
    db.session.commit()


def reopen_merge_request(mr: BundleMergeRequest) -> str:
    if mr.status not in ('closed', 'stale'):
        return 'Only a closed merge request can be reopened.'
    if not mr.source or not mr.target or not related(mr.source, mr.target):
        return 'One of the two bundles does not exist anymore.'
    if BundleMergeRequest.query.filter(BundleMergeRequest.id != mr.id, BundleMergeRequest.status == 'open',
                                       BundleMergeRequest.source_bundle_id == mr.source_bundle_id,
                                       BundleMergeRequest.target_bundle_id == mr.target_bundle_id).first():
        return 'Another merge request between these bundles is open.'
    mr.status, mr.reviewed_by_id, mr.reviewed_at, mr.review_note = 'open', None, None, None
    db.session.commit()
    refresh_merge_request(mr)
    return ''


def sync_fork(fork: Bundle, user) -> tuple[BundleMergeRequest | None, dict | None, str]:
    """Bring the upstream's changes into the fork. Without conflict it is merged at once; with
    conflicts a 'sync' merge request is left open for the fork's owner to resolve."""
    up = db.session.get(Bundle, fork.forked_from_id) if fork.forked_from_id else None
    if not up:
        return None, None, 'The bundle this fork comes from does not exist anymore.'
    if not can_view(up, user):
        return None, None, 'You cannot see the bundle this fork comes from anymore.'
    open_sync = BundleMergeRequest.query.filter_by(source_bundle_id=up.id, target_bundle_id=fork.id, status='open').first()
    if open_sync:
        refresh_merge_request(open_sync)
        mr = open_sync
    else:
        mr, err = open_merge_request(up, fork, user, f'Sync with {up.name}', kind='sync')
        if not mr:
            fork.fork_base_snapshot, fork.fork_base_at = snapshot(up.id, with_content=False), _now()
            db.session.commit()
            return None, None, ''                 # already up to date
    if any(i.get('conflict') for i in mr.items or []):
        return mr, None, ''
    summary, err = merge(mr, user)
    return mr, summary, err


# ── Visibility / deletion side effects ────────────────────────────────────

def on_bundle_hidden_or_deleted(bundle_id: int):
    """A bundle went private or to the trash: its open merge requests as source become stale
    (their content is no longer visible to the other side)."""
    for mr in BundleMergeRequest.query.filter_by(source_bundle_id=bundle_id, status='open').all():
        mr.status = 'stale'
    db.session.commit()


def portable_fork_info(bundle: Bundle) -> dict:
    """What a .bundle.json export keeps of the fork link (bundle_portable.py)."""
    return {'forked_from_uuid': bundle.forked_from_uuid, 'fork_base_at':
            bundle.fork_base_at.strftime('%Y-%m-%dT%H:%M:%SZ') if bundle.fork_base_at else None} \
        if bundle.forked_from_uuid else {}


# ── Background job: fork of a big bundle ──────────────────────────────────

def _register_job():
    from app.features.jobs.job_worker import register_handler

    @register_handler('bundle_fork')
    def handle_bundle_fork(job, app):
        """Payload: bundle_id, user_id, name. One transaction: the fork exists whole or not at all."""
        from app.core.db_class.user import User
        from app.features.jobs.job_handlers import log_job
        payload = job.payload or {}
        upstream = db.session.get(Bundle, payload.get('bundle_id'))
        user = db.session.get(User, payload.get('user_id'))
        if not upstream or not user:
            log_job(job, 'Bundle or user not found.', level='error', event='done')
            return
        log_job(job, f'Forking "{upstream.name}"…', level='info', event='started')
        fork = fork_bundle(upstream, user, payload.get('name'))
        job.done = job.total
        db.session.commit()
        from app.core.utils.activity_log import log_activity
        log_activity('bundle.fork', f'Forked bundle "{upstream.name}" into "{fork.name}"', target_type='bundle',
                     target_uuid=fork.uuid, icon='fa-solid fa-code-fork', actor_id=user.id)
        from app.features.notification.notification_core import notify_bundle_forked
        notify_bundle_forked(upstream, fork, user.id)
        log_job(job, f'Fork ready: /bundle/detail/{fork.id}', level='success', event='done')


_register_job()
