"""Messages: page /messages/ and its JSON routes (logic and rights in messages_core.py, references in refs_core.py)."""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file
from flask_login import current_user, login_required

from app.core.db_class.message import ChannelMessage
from app.core.utils.activity_log import log_activity
from . import messages_core as M
from . import refs_core as R

messages_blueprint = Blueprint('messages', __name__)

# ── Per-account limit on the messages API (setting messages.limits.api_per_minute; admins not limited) ──
# An open page asks about 25 times a minute (new messages every 3-30 s, the list every 12 s); a bot looping on the
# API gets 429 past the limit, logged once per minute. Counted in the shared cache (Redis in production: all
# workers count together), in this process when there is no real cache.
_RL_LOCAL = {}


def _rate_count(key):
    from app import memory_cache
    backend = getattr(memory_cache, 'cache', None)
    if backend is not None and type(backend).__name__ != 'NullCache':
        try:
            n = memory_cache.inc(key) if hasattr(memory_cache, 'inc') else None
            if n is None:
                n = (memory_cache.get(key) or 0) + 1
                memory_cache.set(key, n, timeout=120)
            elif n == 1:
                memory_cache.set(key, 1, timeout=120)
            return int(n)
        except Exception:
            pass
    for k in [k for k in _RL_LOCAL if k.rsplit(':', 1)[1] < key.rsplit(':', 1)[1]]:
        _RL_LOCAL.pop(k, None)                      # older minutes
    _RL_LOCAL[key] = _RL_LOCAL.get(key, 0) + 1
    return _RL_LOCAL[key]


@messages_blueprint.before_request
def _api_rate_limit():
    import time
    from flask import current_app
    if not request.path.startswith('/messages/api/') or not current_user.is_authenticated or current_user.is_admin() \
            or not current_app.config.get('MESSAGES_RATE_LIMIT', True):      # off in tests (config.py TestingConfig)
        return None
    limit = M._limit('api_per_minute', 120)
    n = _rate_count(f'msgapi:{current_user.id}:{int(time.time() // 60)}')
    if n <= limit:
        return None
    if n == limit + 1:                               # once a minute in the activity log
        log_activity('messages.rate_limited', f'{current_user.get_username()} went over {limit} requests a minute '
                     f'on the messages API', target_type='user', target_id=current_user.id, is_public=False, level='warning')
    resp = jsonify({'ok': False, 'message': 'Too many requests — slow down a little.'})
    resp.status_code = 429
    resp.headers['Retry-After'] = '60'
    return resp


def _err(msg, code=400):
    return jsonify({'ok': False, 'message': msg}), code


def _channel_or_404(uuid, need='view'):
    c = M.get_channel(uuid)
    check = {'view': M.can_view, 'post': M.can_post, 'manage': M.can_manage, 'own': M.can_own,
             'invite': M.can_invite}[need]
    if not c or not M.can_view(c, current_user):
        abort(404)
    if not check(c, current_user):
        abort(403)
    return c


def _message_or_404(c, message_id):
    m = ChannelMessage.query.filter_by(id=message_id, channel_id=c.id).first()
    if not m:
        abort(404)
    return m


# ── Pages ──────────────────────────────────────────────────────────────────

@messages_blueprint.get('/')
@login_required
def page_messages():
    return render_template('messages/messages.html', open_uuid=None, start=_start_args())


@messages_blueprint.get('/c/<string:uuid>')
@login_required
def page_channel(uuid):
    c = M.get_channel(uuid)
    if not c or not M.can_view(c, current_user):
        abort(404)
    return render_template('messages/messages.html', open_uuid=c.uuid, start=None)


@messages_blueprint.get('/new')
@login_required
def page_new():
    """/messages/new?ref=rule:12 — start a conversation about something; ?to=<user id> — write to someone."""
    if request.args.get('to', '').isdigit():
        c, err = M.direct_with(current_user, int(request.args['to']))
        if c:
            start = _start_args()
            return render_template('messages/messages.html', open_uuid=c.uuid,
                                   start={'prefill': start['ref']} if start else None)
    return render_template('messages/messages.html', open_uuid=None, start=_start_args())


@messages_blueprint.get('/ref/<string:kind>/<path:key>')
@login_required
def open_ref(kind, key):
    """Where a #reference chip in a message leads — only to what the reader may see."""
    hit = R.resolve(kind, key)
    if not hit:
        abort(404)
    return redirect(hit['url'])


def _start_args():
    ref = request.args.get('ref', '')
    if ':' not in ref:
        return None
    kind, key = ref.split(':', 1)
    hit = R.resolve(kind, key)
    if not hit:
        return None
    start = {'ref': hit}
    # "Discuss in a channel" from a comment: its author is added, the comment quoted (only a comment of that object)
    if request.args.get('quote'):
        from app.core.db_class.comment import UnifiedComment
        c = UnifiedComment.query.filter_by(uuid=request.args['quote'], is_active=True).first()
        if c and c.object_type == kind and str(c.object_id) == str(key):
            author = c.author
            start['quote'] = {'content': c.content[:2000], 'author': M.user_json(author)}
            if author and author.id != current_user.id:
                start['members'] = [{**M.user_json(author), 'username': author.get_username()}]
    return start


# ── Lists ──────────────────────────────────────────────────────────────────

@messages_blueprint.get('/api/conversations')
@login_required
def api_conversations():
    return jsonify({'conversations': M.conversations(current_user), 'unread': M.unread_total(current_user)})


@messages_blueprint.get('/api/unread')
@login_required
def api_unread():
    return jsonify({'unread': M.unread_total(current_user)})


@messages_blueprint.get('/api/browse')
@login_required
def api_browse():
    return jsonify({'channels': M.browse(current_user, request.args.get('q'))})


@messages_blueprint.get('/api/about/<string:kind>/<path:key>')
@login_required
def api_about(kind, key):
    """Channels about this rule / bundle / CVE…, for its page."""
    if not R.resolve(kind, key):
        return jsonify({'channels': []})
    return jsonify({'channels': M.for_ref(current_user, kind, key)})


@messages_blueprint.get('/api/refs')
@login_required
def api_refs():
    kinds = [k for k in (request.args.get('kinds') or '').split(',') if k] or None
    return jsonify({'items': R.search(request.args.get('q'), kinds), 'kinds': R.KINDS})


@messages_blueprint.post('/api/previews')
@login_required
def api_previews():
    """Cards of the Rulezet links in messages (previews_core.py) — {url: card or null}, only this instance's pages."""
    from . import previews_core as P
    urls = [u for u in ((request.get_json(silent=True) or {}).get('urls') or []) if isinstance(u, str)][:P.MAX_PER_REQUEST]
    return jsonify({'previews': {u: P.preview(u, current_user) for u in urls}})


@messages_blueprint.get('/api/search')
@login_required
def api_search():
    c = _channel_or_404(request.args['channel']) if request.args.get('channel') else None
    return jsonify({'results': M.search(current_user, request.args.get('q'), c)})


# ── Channels ───────────────────────────────────────────────────────────────

@messages_blueprint.post('/api/channels')
@login_required
def api_create():
    data = request.get_json(silent=True) or {}
    c, err = M.create_channel(current_user, data.get('name'), data.get('topic'), data.get('is_private'),
                              data.get('member_ids'), data.get('ref_type'), data.get('ref_key'))
    if not c:
        return _err(err)
    return jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)}), 201


@messages_blueprint.post('/api/direct/<int:user_id>')
@login_required
def api_direct(user_id):
    c, err = M.direct_with(current_user, user_id)
    if not c:
        return _err(err, 429 if 'Too many' in err else 404)
    return jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.get('/api/channels/<string:uuid>')
@login_required
def api_channel(uuid):
    c = _channel_or_404(uuid)
    return jsonify({'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.post('/api/channels/<string:uuid>')
@login_required
def api_update(uuid):
    c = _channel_or_404(uuid, 'manage')
    data = request.get_json(silent=True) or {}
    err = M.update_channel(c, current_user, data.get('name'), data.get('topic'), data.get('is_private'),
                           data.get('is_archived'), data.get('members_can_invite'))
    if err:
        return _err(err)
    return jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.delete('/api/channels/<string:uuid>')
@login_required
def api_delete(uuid):
    c = _channel_or_404(uuid, 'own')
    name = c.name
    M.delete_channel(c)
    log_activity('channel.delete', f'Channel "{name}" deleted', target_type='channel', is_public=False)
    return jsonify({'ok': True})


@messages_blueprint.post('/api/channels/<string:uuid>/images')
@login_required
def api_image(uuid):
    """Upload an image for a message (the message box inserts it as Markdown)."""
    c = _channel_or_404(uuid, 'post')
    url, name, err = M.save_image(c, current_user, request.files.get('image'))
    if err:
        return _err(err)
    return jsonify({'ok': True, 'url': url, 'name': name}), 201


@messages_blueprint.get('/files/<string:uuid>/<string:name>')
@login_required
def file(uuid, name):
    """A message image — only for who can read the conversation."""
    c = M.get_channel(uuid)
    if not c or not M.can_view(c, current_user):
        abort(404)
    path = M.file_path(c, name)
    if not path:
        abort(404)
    resp = send_file(path, mimetype='image/jpeg' if name.endswith('.jpg') else 'image/png', max_age=86400)
    resp.headers['Cache-Control'] = 'private, max-age=86400'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp


@messages_blueprint.post('/api/channels/<string:uuid>/avatar')
@login_required
def api_avatar(uuid):
    c = _channel_or_404(uuid, 'manage')
    err = M.set_avatar(c, current_user, request.files.get('avatar'))
    return _err(err) if err else jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.delete('/api/channels/<string:uuid>/avatar')
@login_required
def api_avatar_remove(uuid):
    c = _channel_or_404(uuid, 'manage')
    M.remove_avatar(c, current_user)
    return jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.post('/api/channels/<string:uuid>/invite')
@login_required
def api_invite(uuid):
    """Make or renew the invite link."""
    c = _channel_or_404(uuid, 'manage')
    M.set_invite(c, current_user, True)
    return jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.delete('/api/channels/<string:uuid>/invite')
@login_required
def api_invite_off(uuid):
    c = _channel_or_404(uuid, 'manage')
    M.set_invite(c, current_user, False)
    return jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.get('/join/<string:code>')
@login_required
def page_join(code):
    """An invite link: shows the channel and asks — joining is a POST (a link loaded by another site, e.g. as an
    image, must not add the visitor to a channel nor show its owner who came)."""
    c = M.channel_by_code(code)
    if not c:
        return render_template('messages/messages.html', open_uuid=None, start=None,
                               invite_error='This invite link is not valid anymore.'), 404
    if M.member(c, current_user.id):
        return redirect(f'/messages/c/{c.uuid}')
    invite = {'code': code, 'name': c.name, 'topic': c.topic, 'avatar': M.avatar_url(c), 'is_private': c.is_private,
              'member_count': c.members.count()}
    return render_template('messages/messages.html', open_uuid=None, start={'invite': invite})


@messages_blueprint.post('/join/<string:code>')
@login_required
def api_join_by_code(code):
    c, err = M.join_by_code(current_user, code)
    if not c:
        return _err(err, 404)
    return jsonify({'ok': True, 'uuid': c.uuid})


@messages_blueprint.get('/api/people')
@login_required
def api_people():
    c = M.get_channel(request.args.get('channel')) if request.args.get('channel') else None
    if c and not M.can_view(c, current_user):
        c = None
    if request.args.get('ids_only'):
        return jsonify({'ids': M.people(current_user, request.args.get('q'), request.args.get('org'), ids_only=True)})
    return jsonify(M.people(current_user, request.args.get('q'), request.args.get('org'), c,
                            request.args.get('page', 1, type=int)))


# ── Automations (feeds_core.py) ────────────────────────────────────────────

@messages_blueprint.get('/api/channels/<string:uuid>/feeds')
@login_required
def api_feeds(uuid):
    from . import feeds_core as F
    c = _channel_or_404(uuid)
    out = {'feeds': F.feeds(c), 'kinds': F.KINDS}
    if M.can_manage(c, current_user):                       # what can be chosen: your alerts
        from app.core.db_class.alert import Alert
        out['my_alerts'] = [{'id': a.id, 'name': a.name} for a in
                            Alert.query.filter_by(user_id=current_user.id).order_by(Alert.name).limit(200)]
    return jsonify(out)


@messages_blueprint.post('/api/channels/<string:uuid>/feeds')
@login_required
def api_add_feed(uuid):
    from . import feeds_core as F
    c = _channel_or_404(uuid, 'manage')
    data = request.get_json(silent=True) or {}
    f, err = F.add_feed(c, current_user, data.get('kind'), data.get('target_id'))
    if not f:
        return _err(err)
    return jsonify({'ok': True, 'feeds': F.feeds(c)}), 201


@messages_blueprint.delete('/api/channels/<string:uuid>/feeds/<int:feed_id>')
@login_required
def api_delete_feed(uuid, feed_id):
    from . import feeds_core as F
    c = _channel_or_404(uuid, 'manage')
    if not F.delete_feed(c, current_user, feed_id):
        return _err('Not found.', 404)
    return jsonify({'ok': True, 'feeds': F.feeds(c)})


@messages_blueprint.post('/api/channels/<string:uuid>/join')
@login_required
def api_join(uuid):
    c = _channel_or_404(uuid)
    if not M.join(c, current_user):
        return _err('This channel can\'t be joined.', 403)
    return jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.post('/api/channels/<string:uuid>/leave')
@login_required
def api_leave(uuid):
    c = _channel_or_404(uuid)
    err = M.leave(c, current_user)
    return _err(err) if err else jsonify({'ok': True})


@messages_blueprint.post('/api/channels/<string:uuid>/clear')
@login_required
def api_clear(uuid):
    c = _channel_or_404(uuid)
    err = M.clear_for_me(c, current_user)
    return _err(err) if err else jsonify({'ok': True})


@messages_blueprint.post('/api/channels/<string:uuid>/me')
@login_required
def api_me(uuid):
    c = _channel_or_404(uuid)
    data = request.get_json(silent=True) or {}
    if not M.set_member_flags(c, current_user, data.get('muted'), data.get('starred'), data.get('email_mode')):
        return _err('You are not in this conversation.')
    return jsonify({'ok': True})


@messages_blueprint.post('/api/channels/<string:uuid>/members')
@login_required
def api_add_members(uuid):
    c = _channel_or_404(uuid, 'invite')
    added, err = M.add_members(c, current_user, (request.get_json(silent=True) or {}).get('user_ids'))
    if err:
        return _err(err)
    return jsonify({'ok': True, 'added': len(added), 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.delete('/api/channels/<string:uuid>/members/<int:user_id>')
@login_required
def api_remove_member(uuid, user_id):
    c = _channel_or_404(uuid, 'manage')
    err = M.remove_member(c, current_user, user_id)
    return _err(err) if err else jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


@messages_blueprint.post('/api/channels/<string:uuid>/members/<int:user_id>/role')
@login_required
def api_role(uuid, user_id):
    c = _channel_or_404(uuid, 'own')
    err = M.set_role(c, current_user, user_id, (request.get_json(silent=True) or {}).get('role'))
    return _err(err) if err else jsonify({'ok': True, 'channel': M.channel_json(c, current_user, full=True)})


# ── Messages ───────────────────────────────────────────────────────────────

@messages_blueprint.get('/api/channels/<string:uuid>/messages')
@login_required
def api_messages(uuid):
    c = _channel_or_404(uuid)
    rows, more = M.messages(c, current_user, request.args.get('before', type=int),
                            request.args.get('after', type=int), request.args.get('limit', type=int))
    return jsonify({'messages': rows, 'has_more': more, 'reads': M.reads(c, current_user)})


@messages_blueprint.post('/api/channels/<string:uuid>/messages')
@login_required
def api_post(uuid):
    c = _channel_or_404(uuid, 'post')
    data = request.get_json(silent=True) or {}
    m, err = M.post_message(c, current_user, data.get('content'), data.get('reply_to_id'))
    if not m:
        return _err(err)
    return jsonify({'ok': True, 'message': M.message_json(m, current_user)}), 201


@messages_blueprint.post('/api/channels/<string:uuid>/messages/<int:message_id>')
@login_required
def api_edit(uuid, message_id):
    c = _channel_or_404(uuid)
    m = _message_or_404(c, message_id)
    err = M.edit_message(m, current_user, (request.get_json(silent=True) or {}).get('content'))
    return _err(err, 403) if err else jsonify({'ok': True, 'message': M.message_json(m, current_user)})


@messages_blueprint.delete('/api/channels/<string:uuid>/messages/<int:message_id>')
@login_required
def api_delete_message(uuid, message_id):
    c = _channel_or_404(uuid)
    m = _message_or_404(c, message_id)
    err = M.delete_message(m, current_user)
    return _err(err, 403) if err else jsonify({'ok': True, 'message': M.message_json(m, current_user)})


@messages_blueprint.post('/api/channels/<string:uuid>/messages/<int:message_id>/react')
@login_required
def api_react(uuid, message_id):
    c = _channel_or_404(uuid, 'post')
    m = _message_or_404(c, message_id)
    err = M.toggle_reaction(m, current_user, (request.get_json(silent=True) or {}).get('emoji'))
    return _err(err) if err else jsonify({'ok': True, 'message': M.message_json(m, current_user)})


@messages_blueprint.get('/api/channels/<string:uuid>/messages/<int:message_id>/reactors')
@login_required
def api_reactors(uuid, message_id):
    """Who added this emoji — the hover pop-up of a reaction (components/VoterPopover.js)."""
    from app.core.db_class.message import ChannelReaction
    c = _channel_or_404(uuid)
    m = _message_or_404(c, message_id)
    rows = ChannelReaction.query.filter_by(message_id=m.id, emoji=request.args.get('emoji', '')).all()
    from app.core.db_class.user import User
    users = [u for u in (M.db.session.get(User, r.user_id) for r in rows) if u]
    return jsonify({'users': [{'id': u.id, 'username': u.get_username(), 'avatar': u.get_avatar_url()} for u in users[:50]],
                    'total': len(rows)})


@messages_blueprint.post('/api/channels/<string:uuid>/messages/<int:message_id>/pin')
@login_required
def api_pin(uuid, message_id):
    c = _channel_or_404(uuid)
    m = _message_or_404(c, message_id)
    err = M.toggle_pin(m, current_user)
    return _err(err, 403) if err else jsonify({'ok': True, 'message': M.message_json(m, current_user)})


@messages_blueprint.post('/api/channels/<string:uuid>/read')
@login_required
def api_read(uuid):
    c = _channel_or_404(uuid)
    M.mark_read(c, current_user, (request.get_json(silent=True) or {}).get('upto'))
    return jsonify({'ok': True})
