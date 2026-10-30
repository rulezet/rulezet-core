"""
bundle_fork_routes.py — forks and merge requests of bundles (bundle_fork_core.py), on the bundle
blueprint. Every route checks its rights with the can_* functions of the core.

    GET  /bundle/<id>/fork_info                 forked from, ahead / behind, what the viewer may do
    POST /bundle/<id>/fork                      fork it (a background job for big bundles)
    GET  /bundle/<id>/forks                     its forks (private ones counted, not shown)
    GET  /bundle/<id>/merge_requests            merge requests to it and from it
    POST /bundle/<id>/merge_requests            propose this fork's changes to its upstream
    POST /bundle/<id>/sync                      bring the upstream's changes into this fork
    POST /bundle/<id>/accepts_proposals         owner: open / close the bundle to merge requests
    POST /bundle/<id>/fork_rule/<rule_id>       edit a rule you don't own, in your fork only
    GET  /bundle/merge_request/<uuid>           the merge request page
    GET  /bundle/merge_request/<uuid>/json      its changes (?refresh=1 recomputes them)
    POST /bundle/merge_request/<uuid>/decision  accept / reject an item, pick a side for a conflict
    POST /bundle/merge_request/<uuid>/merge|close|reopen|edit
"""
from flask import abort, jsonify, render_template, request
from flask_login import current_user, login_required

from app import db
from app.core.db_class.bundle import Bundle
from app.core.db_class.bundle_fork import BundleMergeRequest
from app.core.db_class.rule import Rule
from app.core.utils.activity_log import log_activity
from app.core.utils.utils import internal_error, json_object
from app.features.bundle import bundle_fork_core as Fork
from app.features.bundle.bundle import bundle_blueprint
from app.features.rule.rule_core import _active


def _bundle_or_404(bundle_id):
    bundle = db.session.get(Bundle, bundle_id)
    if not bundle or not Fork.can_view(bundle):
        abort(404)
    return bundle


def _mr_or_404(mr_uuid):
    mr = BundleMergeRequest.query.filter_by(uuid=mr_uuid).first()
    if not mr or not Fork.can_view_mr(mr):
        abort(404)
    return mr


def _err(message, status=400):
    return jsonify({'success': False, 'message': message, 'toast_class': 'danger-subtle'}), status


def _ok(message, **extra):
    return jsonify({'success': True, 'message': message, 'toast_class': 'success-subtle', **extra}), 200


def _bundle_json(b):
    if not b:
        return None
    owner = b.user
    return {'id': b.id, 'uuid': b.uuid, 'name': b.name, 'access': bool(b.access), 'user_id': b.user_id,
            'owner': f"{owner.first_name or ''} {owner.last_name or ''}".strip() if owner else None,
            'created_at': b.created_at.strftime('%Y-%m-%d') if b.created_at else None}


def _log(action, description, mr=None, bundle=None, **extra):
    log_activity(action, description, target_type='bundle_merge_request' if mr else 'bundle',
                 target_uuid=(mr.uuid if mr else bundle.uuid if bundle else None),
                 icon='fa-solid fa-code-fork' if action.startswith('bundle.fork') else 'fa-solid fa-code-pull-request',
                 extra=extra or None)


# ── Bundle side ───────────────────────────────────────────────────────────

@bundle_blueprint.route('/<int:bundle_id>/fork_info', methods=['GET'])
def fork_info(bundle_id):
    bundle = _bundle_or_404(bundle_id)
    chain = [b for b in Fork.fork_chain(bundle) if Fork.can_view(b)]
    upstream = db.session.get(Bundle, bundle.forked_from_id) if bundle.forked_from_id else None
    status = {'ahead': 0, 'behind': 0, 'ahead_items': [], 'behind_items': []}
    if upstream and Fork.can_view(upstream):
        st = Fork.fork_status(bundle)
        status = {k: st[k] for k in status}
    forks = Fork.list_forks(bundle)
    can_fork, why_not = Fork.can_fork(bundle)
    can_mr, why_no_mr = (Fork.can_open_mr(bundle, upstream) if upstream else (False, ''))
    open_in = BundleMergeRequest.query.filter_by(target_bundle_id=bundle.id, status='open').count()
    open_out = BundleMergeRequest.query.filter_by(source_bundle_id=bundle.id, status='open').count()
    open_mr = None
    if upstream:
        m = BundleMergeRequest.query.filter_by(source_bundle_id=bundle.id, target_bundle_id=upstream.id, status='open').first()
        if m:
            open_mr = {'uuid': m.uuid, 'title': m.title, 'counts': m.counts(), 'created_at': m.to_json()['created_at']}
    my_fork = None
    if current_user.is_authenticated:
        mine = Bundle.query.filter_by(forked_from_id=bundle.id, user_id=current_user.id).first()
        my_fork = _bundle_json(mine)
    return jsonify({
        'enabled': Fork.forks_enabled(),
        'is_fork': bool(bundle.forked_from_uuid),
        'upstream': _bundle_json(upstream) if upstream and Fork.can_view(upstream) else None,
        'upstream_gone': bool(bundle.forked_from_uuid and not upstream),
        'upstream_hidden': bool(upstream and not Fork.can_view(upstream)),
        'chain': [_bundle_json(b) for b in chain],
        'ahead': status['ahead'], 'behind': status['behind'],
        'ahead_items': status['ahead_items'], 'behind_items': status['behind_items'],
        'owner_name': _bundle_json(bundle)['owner'],
        'fork_base_at': bundle.fork_base_at.strftime('%Y-%m-%d %H:%M') if bundle.fork_base_at else None,
        'forks_count': forks['total'],
        'can_fork': can_fork, 'why_not_fork': why_not,
        'can_open_mr': can_mr, 'why_not_mr': why_no_mr,
        'is_manager': Fork.is_manager(bundle),
        'accepts_proposals': bool(bundle.accepts_proposals),
        'open_incoming': open_in, 'open_outgoing': open_out,
        'my_fork': my_fork,
        'open_mr': open_mr,          # this fork's merge request to its original, when one is open
    }), 200


@bundle_blueprint.route('/<int:bundle_id>/fork', methods=['POST'])
@login_required
def fork(bundle_id):
    bundle = _bundle_or_404(bundle_id)
    data = json_object()
    if data.get('reuse'):                  # "Suggest changes": continue in your fork when you have one
        mine = Bundle.query.filter_by(forked_from_id=bundle.id, user_id=current_user.id).order_by(Bundle.created_at).first()
        if mine:
            return _ok('Your fork of this bundle — change it, then propose your changes.', bundle_id=mine.id,
                       url=f'/bundle/detail/{mine.id}', existing=True)
    ok, why = Fork.can_fork(bundle)
    if not ok:
        return _err(why, 403)
    name = (data.get('name') or '').strip()
    from app.core.db_class.bundle import BundleRuleAssociation
    size = BundleRuleAssociation.query.filter_by(bundle_id=bundle.id).count()
    if size > int(Fork._cfg('job_threshold', 400) or 400):
        from app.features.jobs.jobs_core import create_job
        job = create_job('bundle_fork', {'bundle_id': bundle.id, 'user_id': current_user.id, 'name': name},
                         f'Fork of "{bundle.name}"', current_user.id, total=size)
        return _ok('Big bundle: the fork is being made in the background — you will get a notification.',
                   job_uuid=job.uuid if job else None)
    try:
        new = Fork.fork_bundle(bundle, current_user, name)
    except Exception as e:
        db.session.rollback()
        return _err(internal_error(e, 'The fork could not be made.'), 500)
    _after_fork(bundle, new, current_user.id)
    return _ok('Bundle forked — it is yours to change.', bundle_id=new.id, url=f'/bundle/detail/{new.id}')


def _after_fork(upstream, fork, actor_id):
    _log('bundle.fork', f'Forked bundle "{upstream.name}" into "{fork.name}"', bundle=fork,
         upstream_uuid=upstream.uuid)
    from app.features.notification.notification_core import notify_bundle_forked
    notify_bundle_forked(upstream, fork, actor_id)


@bundle_blueprint.route('/<int:bundle_id>/forks', methods=['GET'])
def forks(bundle_id):
    bundle = _bundle_or_404(bundle_id)
    data = Fork.list_forks(bundle)
    out = []
    for f in data['forks']:
        row = _bundle_json(f)
        open_mr = BundleMergeRequest.query.filter_by(source_bundle_id=f.id, target_bundle_id=bundle.id, status='open').first()
        row['open_merge_request'] = open_mr.uuid if open_mr else None
        row['updated_at'] = f.updated_at.strftime('%Y-%m-%d') if f.updated_at else None
        out.append(row)
    return jsonify({'forks': out, 'hidden': data['hidden'], 'total': data['total']}), 200


@bundle_blueprint.route('/<int:bundle_id>/merge_requests', methods=['GET'])
def merge_requests(bundle_id):
    bundle = _bundle_or_404(bundle_id)
    status = request.args.get('status', 'open')
    base = BundleMergeRequest.query.filter((BundleMergeRequest.target_bundle_id == bundle.id)
                                           | (BundleMergeRequest.source_bundle_id == bundle.id))
    q = base.filter(BundleMergeRequest.status == status) if status in BundleMergeRequest.STATUSES else base
    rows = [m for m in q.order_by(BundleMergeRequest.created_at.desc()).limit(200).all() if Fork.can_view_mr(m)]
    counts = {s: base.filter(BundleMergeRequest.status == s).count() for s in BundleMergeRequest.STATUSES}
    return jsonify({'merge_requests': [m.to_json() for m in rows], 'counts': counts}), 200


@bundle_blueprint.route('/<int:bundle_id>/merge_requests', methods=['POST'])
@login_required
def open_merge_request(bundle_id):
    source = _bundle_or_404(bundle_id)
    target = db.session.get(Bundle, source.forked_from_id) if source.forked_from_id else None
    ok, why = Fork.can_open_mr(source, target)
    if not ok:
        return _err(why, 403)
    data = json_object()
    mr, err = Fork.open_merge_request(source, target, current_user, data.get('title'), data.get('message'))
    if not mr:
        return _err(err)
    _log('bundle.mr_open', f'Opened merge request "{mr.title}" ({source.name} → {target.name})', mr=mr)
    from app.features.notification.notification_core import notify_bundle_merge_request
    notify_bundle_merge_request(mr, 'opened', current_user.id)
    return _ok('Merge request opened.', uuid=mr.uuid, url=f'/bundle/merge_request/{mr.uuid}')


@bundle_blueprint.route('/<int:bundle_id>/sync', methods=['POST'])
@login_required
def sync(bundle_id):
    fork = _bundle_or_404(bundle_id)
    if not Fork.is_manager(fork):
        return _err('Only the owner of this fork can sync it.', 403)
    if not fork.forked_from_id:
        return _err('This bundle is not a fork.')
    try:
        mr, summary, err = Fork.sync_fork(fork, current_user)
    except Exception as e:
        db.session.rollback()
        return _err(internal_error(e, 'The sync failed — nothing was changed.'), 500)
    if err:
        return _err(err)
    if mr is None:
        return _ok('Already up to date.')
    if summary is None:
        return _ok('The upstream changed the same things as you: resolve the conflicts to finish the sync.',
                   uuid=mr.uuid, url=f'/bundle/merge_request/{mr.uuid}', conflicts=True)
    _log('bundle.sync', f'Synced fork "{fork.name}" with its upstream', mr=mr, applied=len(summary['applied']))
    return _ok(f"Synced: {len(summary['applied'])} change(s) brought in.", uuid=mr.uuid)


@bundle_blueprint.route('/<int:bundle_id>/accepts_proposals', methods=['POST'])
@login_required
def set_accepts_proposals(bundle_id):
    bundle = _bundle_or_404(bundle_id)
    if not Fork.is_manager(bundle):
        return _err('Only the owner or an admin can change this.', 403)
    bundle.accepts_proposals = bool(json_object().get('value'))
    db.session.commit()
    _log('bundle.mr_settings', f'Merge requests {"open" if bundle.accepts_proposals else "closed"} on "{bundle.name}"', bundle=bundle)
    return _ok('Saved.', accepts_proposals=bundle.accepts_proposals)


@bundle_blueprint.route('/<int:bundle_id>/fork_rule/<int:rule_id>', methods=['POST'])
@login_required
def fork_rule(bundle_id, rule_id):
    bundle = _bundle_or_404(bundle_id)
    if not Fork.is_manager(bundle):
        return _err('Only the owner of this bundle can change its rules.', 403)
    if not bundle.forked_from_uuid:
        return _err('Rule copies are for forks: edit the rule itself, or fork the bundle first.')
    rule = _active().filter(Rule.id == rule_id).first()
    snap_ids = {e['rule_id'] for e in (Fork.snapshot(bundle.id, with_content=False) or {}).get('rules', {}).values()}
    if not rule or rule.id not in snap_ids:
        return _err('This rule is not in the bundle.', 404)
    if rule.user_id == current_user.id:
        return _err('This rule is yours: edit it directly (the change shows in every bundle that uses it).')
    copy, err = Fork.fork_rule_copy(bundle, rule, json_object().get('content'), current_user)
    if not copy:
        return _err(err)
    _log('bundle.fork_rule', f'Edited a copy of rule "{rule.title}" in fork "{bundle.name}"', bundle=bundle,
         original_rule_id=rule.id, copy_rule_id=copy.id)
    return _ok('Your copy of the rule is now used in this fork; the original is untouched.', rule_id=copy.id)


# ── Merge request side ────────────────────────────────────────────────────

_EVENTS = {   # activity-log action → how it reads in the discussion timeline (like rule proposals)
    'bundle.mr_open':     ('fa-solid fa-code-pull-request', 'opened this merge request'),
    'bundle.mr_edit':     ('fa-solid fa-pen', 'edited the title and description'),
    'bundle.mr_decision': ('fa-solid fa-list-check', None),
    'bundle.mr_merge':    ('fa-solid fa-code-merge', 'merged this merge request'),
    'bundle.mr_close':    ('fa-solid fa-circle-xmark', 'closed this merge request'),
    'bundle.mr_reopen':   ('fa-solid fa-rotate-left', 'reopened this merge request'),
    'bundle.sync':        ('fa-solid fa-rotate', 'synced the fork'),
}


def _mr_system_events(mr) -> list:
    """What happened to a merge request, for the comment thread's timeline: opened, edited, each
    decision on a change, merged / closed / reopened — from the activity log."""
    from app.core.db_class.activity_log import ActivityLog
    rows = (ActivityLog.query.filter(ActivityLog.target_type == 'bundle_merge_request', ActivityLog.target_uuid == mr.uuid,
                                     ActivityLog.action.in_(list(_EVENTS)))
            .order_by(ActivityLog.created_at.asc()).limit(300).all())
    out = []
    for log in rows:
        icon, text = _EVENTS[log.action]
        u = log.user
        out.append({'type': log.action.split('.')[-1], 'icon': icon, 'text': text or (log.description or ''),
                    'actor_id': log.user_id, 'actor_name': f"{u.first_name} {u.last_name}".strip() if u else 'Someone',
                    'actor_avatar': u.get_avatar_url() if u else None,
                    'created_at': log.created_at.isoformat() if log.created_at else None})
    if not any(e['type'] == 'mr_open' for e in out) and mr.created_at:     # opened by a job / before logging
        u = mr.user
        out.insert(0, {'type': 'mr_open', 'icon': _EVENTS['bundle.mr_open'][0], 'text': _EVENTS['bundle.mr_open'][1],
                       'actor_id': mr.user_id, 'actor_name': f"{u.first_name} {u.last_name}".strip() if u else 'Someone',
                       'actor_avatar': u.get_avatar_url() if u else None, 'created_at': mr.created_at.isoformat()})
    return out


@bundle_blueprint.route('/merge_request/<string:mr_uuid>', methods=['GET'])
def merge_request_page(mr_uuid):
    mr = _mr_or_404(mr_uuid)
    return render_template('bundle/merge_request.html', mr=mr)


@bundle_blueprint.route('/merge_request/<string:mr_uuid>/json', methods=['GET'])
def merge_request_json(mr_uuid):
    mr = _mr_or_404(mr_uuid)
    if request.args.get('refresh') and mr.status == 'open':
        Fork.refresh_merge_request(mr)
    data = mr.to_json(with_items=True)
    data.update({
        'id': mr.id,
        'system_events': _mr_system_events(mr),
        'can_review': Fork.can_review_mr(mr),
        'can_close': Fork.can_close_mr(mr),
        'is_author': current_user.is_authenticated and current_user.id == mr.user_id,
        'blockers': Fork.merge_blockers(mr) if mr.status == 'open' else [],
        'summary': Fork.summarize_changes(mr.items),
    })
    return jsonify(data), 200


@bundle_blueprint.route('/merge_request/<string:mr_uuid>/decision', methods=['POST'])
@login_required
def merge_request_decision(mr_uuid):
    mr = _mr_or_404(mr_uuid)
    if not Fork.can_review_mr(mr):
        return _err('Only the owner of the target bundle or an admin decides.', 403)
    if mr.status != 'open':
        return _err('This merge request is not open.')
    data = json_object()
    item_id, decision = str(data.get('item_id') or ''), str(data.get('decision') or '')
    err = Fork.set_decision(mr, item_id, decision, data.get('rule_mode'))
    if err:
        return _err(err)
    item = next((i for i in mr.items or [] if i['id'] == item_id), {})
    verb = {'accept': 'accepted', 'reject': 'left out', 'source': 'took the fork\'s side for',
            'target': 'kept this bundle\'s side for'}.get(decision, decision)
    _log('bundle.mr_decision', f'{verb} "{item.get("label", item_id)}"', mr=mr)
    return _ok('Saved.', blockers=Fork.merge_blockers(mr), counts=mr.counts())


@bundle_blueprint.route('/merge_request/<string:mr_uuid>/merge', methods=['POST'])
@login_required
def merge_request_merge(mr_uuid):
    mr = _mr_or_404(mr_uuid)
    if not Fork.can_review_mr(mr):
        return _err('Only the owner of the target bundle or an admin can merge.', 403)
    mr.review_note = (json_object().get('note') or '').strip() or None
    try:
        summary, err = Fork.merge(mr, current_user)
    except Exception as e:
        db.session.rollback()
        return _err(internal_error(e, 'The merge failed — nothing was changed.'), 500)
    if err:
        return _err(err)
    _log('bundle.mr_merge', f'Merged "{mr.title}" into "{mr.target.name}"', mr=mr,
         applied=len(summary['applied']), skipped=len(summary['skipped']))
    from app.features.notification.notification_core import notify_bundle_merge_request
    notify_bundle_merge_request(mr, 'merged', current_user.id)
    return _ok(f"Merged: {len(summary['applied'])} change(s) applied, {len(summary['skipped'])} left out.",
               summary=summary)


@bundle_blueprint.route('/merge_request/<string:mr_uuid>/close', methods=['POST'])
@login_required
def merge_request_close(mr_uuid):
    mr = _mr_or_404(mr_uuid)
    if not Fork.can_close_mr(mr):
        return _err('Only its author, the owner of the target bundle or an admin can close it.', 403)
    if mr.status != 'open':
        return _err('This merge request is not open.')
    Fork.close_merge_request(mr, current_user, json_object().get('note'))
    _log('bundle.mr_close', f'Closed merge request "{mr.title}"', mr=mr)
    from app.features.notification.notification_core import notify_bundle_merge_request
    notify_bundle_merge_request(mr, 'closed', current_user.id)
    return _ok('Merge request closed.')


@bundle_blueprint.route('/merge_request/<string:mr_uuid>/reopen', methods=['POST'])
@login_required
def merge_request_reopen(mr_uuid):
    mr = _mr_or_404(mr_uuid)
    if not Fork.can_close_mr(mr):
        return _err('Only its author, the owner of the target bundle or an admin can reopen it.', 403)
    err = Fork.reopen_merge_request(mr)
    if err:
        return _err(err)
    _log('bundle.mr_reopen', f'Reopened merge request "{mr.title}"', mr=mr)
    return _ok('Merge request reopened.')


@bundle_blueprint.route('/merge_request/<string:mr_uuid>/edit', methods=['POST'])
@login_required
def merge_request_edit(mr_uuid):
    mr = _mr_or_404(mr_uuid)
    if not (current_user.id == mr.user_id or current_user.is_admin()):
        return _err('Only its author can edit it.', 403)
    data = json_object()
    title = (data.get('title') or '').strip()
    if not title:
        return _err('A title is needed.')
    mr.title, mr.message = title[:255], (data.get('message') or '').strip()
    db.session.commit()
    _log('bundle.mr_edit', 'edited the title and description', mr=mr)
    from app.features.notification.notification_core import notify_bundle_merge_request
    if mr.status == 'open':
        notify_bundle_merge_request(mr, 'updated', current_user.id)
    return _ok('Saved.')


@bundle_blueprint.route('/<int:bundle_id>/fork_rules', methods=['GET'])
@login_required
def fork_rules(bundle_id):
    """The fork's rules, for "Edit a rule in this fork": which are copies, which belong to someone else."""
    bundle = _bundle_or_404(bundle_id)
    if not Fork.is_manager(bundle):
        return _err('Only the owner of this bundle.', 403)
    snap = Fork.snapshot(bundle.id, with_content=False) or {}
    copies = set(Fork.rule_keys(bundle.id))
    rows = [{'id': e['rule_id'], 'title': e['title'], 'format': e['format'], 'folder': e['folder'],
             'is_copy': e['rule_id'] in copies, 'is_mine': e.get('owner_id') == current_user.id}
            for e in (snap.get('rules') or {}).values()]
    rows.sort(key=lambda r: (r['folder'], (r['title'] or '').lower()))
    return jsonify({'rules': rows}), 200


@bundle_blueprint.route('/<int:bundle_id>/fork_network', methods=['GET'])
def fork_network(bundle_id):
    """The family of this bundle for the fork graph: the oldest visible ancestor, its forks (and theirs,
    a few levels down), and the events between them — fork, merge request opened / merged / closed,
    sync — oldest first. Bundles the viewer can't see are left out."""
    bundle = _bundle_or_404(bundle_id)
    chain = [b for b in Fork.fork_chain(bundle) if Fork.can_view(b)]
    root = chain[-1] if chain else bundle
    nodes, frontier, seen = [root], [root], {root.id}
    for _ in range(4):                                   # depth: root → forks → forks of forks …
        nxt = []
        for b in frontier:
            for f in Bundle.query.filter_by(forked_from_id=b.id).order_by(Bundle.created_at).limit(40).all():
                if f.id not in seen and Fork.can_view(f):
                    seen.add(f.id)
                    nodes.append(f)
                    nxt.append(f)
        frontier = nxt
        if len(nodes) >= 60:
            break
    ids = [n.id for n in nodes]
    events = []
    for n in nodes:
        if n.forked_from_id in seen:
            events.append({'type': 'fork', 'at': n.created_at, 'bundle_id': n.id, 'from_id': n.forked_from_id,
                           'label': f'Forked by {_bundle_json(n)["owner"] or "someone"}'})
    mrs = BundleMergeRequest.query.filter(BundleMergeRequest.source_bundle_id.in_(ids),
                                          BundleMergeRequest.target_bundle_id.in_(ids)).all()
    for m in mrs:
        if not Fork.can_view_mr(m):
            continue
        events.append({'type': 'mr_open', 'at': m.created_at, 'bundle_id': m.source_bundle_id, 'to_id': m.target_bundle_id,
                       'label': ('Sync requested' if m.kind == 'sync' else 'Merge request') + f': {m.title}',
                       'uuid': m.uuid, 'status': m.status})
        if m.status in ('merged', 'closed') and m.reviewed_at:
            events.append({'type': 'mr_' + m.status, 'at': m.reviewed_at, 'bundle_id': m.target_bundle_id,
                           'from_id': m.source_bundle_id, 'uuid': m.uuid,
                           'label': ('Synced' if m.kind == 'sync' else 'Merged') if m.status == 'merged' else f'Closed: {m.title}'})

    def ts(e):
        at = e['at']
        return at.replace(tzinfo=None).isoformat() if at else ''
    events.sort(key=ts)
    for e in events:
        e['at'] = e['at'].strftime('%Y-%m-%d %H:%M') if e['at'] else None
    return jsonify({
        'current_id': bundle.id,
        'bundles': [{**_bundle_json(n), 'forked_from_id': n.forked_from_id if n.forked_from_id in seen else None} for n in nodes],
        'events': events,
    }), 200


@bundle_blueprint.route('/<int:bundle_id>/compare_upstream', methods=['GET'])
def compare_upstream(bundle_id):
    """A fork compared with the bundle it comes from, like the "Files changed" of a pull request.
    ?side=mine (default): what this fork changed — what a merge request would propose;
    ?side=theirs: what changed in the original since — what Sync would bring."""
    fork = _bundle_or_404(bundle_id)
    upstream = db.session.get(Bundle, fork.forked_from_id) if fork.forked_from_id else None
    if not upstream or not Fork.can_view(upstream):
        return _err('This bundle is not a fork of a bundle you can see.', 404)
    mine, theirs = Fork.snapshot(fork.id), Fork.snapshot(upstream.id)
    base = fork.fork_base_snapshot
    if request.args.get('side') == 'theirs':
        items = Fork.compute_changes(base, theirs, mine)
    else:
        items = Fork.compute_changes(base, mine, theirs)
    return jsonify({'items': items, 'summary': Fork.summarize_changes(items),
                    'upstream': _bundle_json(upstream), 'fork': _bundle_json(fork)}), 200
