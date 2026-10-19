"""Server side of the rule editor, mounted on /editor-api (validation, rule lookup, editor JS/CSS).
Logged-in users only, like the pages that show the editor."""
from flask import jsonify
from flask_login import current_user
from rulezet_editor import create_blueprint

from . import editor_core as EditorModel

editor_blueprint = create_blueprint(EditorModel.backend, name='editor_api')


@editor_blueprint.before_request
def _login_required():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Log in to use the editor.'}), 401
    return None
