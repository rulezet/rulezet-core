"""feed.py — the /feeds page: the rule feeds Rulezet serves to tools (feed_core.py, GET /api/feed/<format>),
how to plug them into YARA, Suricata, Sigma…, and a download button per feed for logged-in users
(a free account is needed; its API key is on My account)."""
from flask import Blueprint, Response, abort, current_app, render_template, request
from flask_login import current_user, login_required

from app.core.utils.app_settings import get_setting
from app.features.feed import feed_core as FeedModel

feed_blueprint = Blueprint('feed', __name__)


def _base_url():
    return (current_app.config.get('INSTANCE_PUBLIC_URL') or request.host_url).rstrip('/')


@feed_blueprint.route('/feeds')
def feeds():
    catalog = get_setting('formats.catalog') or {}
    items = []
    for f in FeedModel.summary():
        info = catalog.get(f['format'], {}) if isinstance(catalog, dict) else {}
        items.append({**f, 'logo': info.get('logo'), 'color': info.get('color') or '#0d6efd',
                      'description': info.get('description') or '', 'title': info.get('title') or f.get('label')})
    return render_template('feed/feeds.html', feeds=items, base_url=_base_url(),
                           logged_in=current_user.is_authenticated,
                           has_key=bool(current_user.is_authenticated and current_user.api_key))


@feed_blueprint.route('/feeds/download/<string:fmt>')
@login_required
def download(fmt):
    """The feed as a file, for the page's Download buttons (the session stands for the API key)."""
    try:
        body, mime, filename, _etag, _count = FeedModel.build(fmt, _base_url(), since=request.args.get('since'),
                                                              tag=request.args.get('tag'),
                                                              as_json=request.args.get('output') == 'json')
    except LookupError:
        abort(404)
    except ValueError as e:
        return Response(str(e), status=400, mimetype='text/plain')
    return Response(body, mimetype=mime, headers={'Content-Disposition': f'attachment; filename="{filename}"'})
