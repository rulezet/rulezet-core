"""Admin oversight of messages: /admin/messages (oversight_core.py) — who writes where, never what, unless an
admin reveals one message (logged)."""
from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from app.core.db_class.message import ChannelMessage
from . import messages_core as M
from . import oversight_core as O

messages_admin_blueprint = Blueprint('messages_admin', __name__)


@messages_admin_blueprint.before_request
@login_required
def _admins_only():
    if not current_user.is_admin():
        abort(403)


@messages_admin_blueprint.get('/')
def page():
    return render_template('messages/admin_oversight.html')


@messages_admin_blueprint.get('/api/conversations')
def api_conversations():
    return jsonify(O.conversations(request.args.get('q'), request.args.get('kind'), request.args.get('page', 1, type=int)))


@messages_admin_blueprint.get('/api/conversations/<string:uuid>')
def api_messages(uuid):
    c = M.get_channel(uuid)
    if not c:
        abort(404)
    return jsonify(O.messages_meta(c, request.args.get('before', type=int)))


@messages_admin_blueprint.post('/api/messages/<int:message_id>/reveal')
def api_reveal(message_id):
    m = ChannelMessage.query.get_or_404(message_id)
    return jsonify(O.reveal(m, current_user))
