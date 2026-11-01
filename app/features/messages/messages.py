"""Messages: page /messages/ and its JSON routes (logic and rights in messages_core.py, references in refs_core.py)."""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file
from flask_login import current_user, login_required

from app.core.db_class.message import ChannelMessage
from app.core.utils.activity_log import log_activity
from . import messages_core as M
from . import refs_core as R

messages_blueprint = Blueprint('messages', __name__)


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
    return {'ref': hit} if hit else None


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
        return _err(err, 404)
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
    """An invite link: joins the channel (even private), then opens it."""
    c, err = M.join_by_code(current_user, code)
    if not c:
        return render_template('messages/messages.html', open_uuid=None, start=None, invite_error=err), 404
    return redirect(f'/messages/c/{c.uuid}')


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
    if not M.set_member_flags(c, current_user, data.get('muted'), data.get('starred')):
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
    return jsonify({'messages': rows, 'has_more': more})


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
