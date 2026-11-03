"""Rule feeds for tools (feature app/features/feed/): GET /api/feed/ lists them, GET /api/feed/<format>
returns every shareable rule of the format, ready for the tool. A free account's API key is needed,
in the X-API-KEY header or as ?apikey= (for tools that only take a URL, e.g. suricata-update)."""
from flask import Response, current_app, request
from flask_restx import Namespace, Resource

from app.core.utils.utils import get_user_api
from app.features.feed import feed_core as FeedModel

feed_ns = Namespace('feed', description='Rule feeds for tools (a free account\'s API key: X-API-KEY header or ?apikey=)')


def _key_user():
    return get_user_api(request.headers.get('X-API-KEY') or request.args.get('apikey'))


def _base_url():
    return (current_app.config.get('INSTANCE_PUBLIC_URL') or request.host_url).rstrip('/')


@feed_ns.route('/')
class FeedList(Resource):
    @feed_ns.doc(description='The feeds offered: format, number of rules, URL.')
    def get(self):
        if not _key_user():
            return {'success': False, 'message': 'An API key is needed (free account: /register, key on your profile).'}, 403
        base = _base_url()
        return {'success': True, 'feeds': [{**f, 'url': f"{base}/api/feed/{f['format']}"} for f in FeedModel.summary()]}


@feed_ns.route('/<string:fmt>')
@feed_ns.param('fmt', 'Rule format: yara, sigma, suricata…')
class FeedFormat(Resource):
    @feed_ns.doc(params={
        'since': 'Only rules created or changed since this date (YYYY-MM-DD)',
        'tag': 'Only rules with this tag (e.g. attack.t1059, tlp:clear)',
        'source': 'Only rules whose source contains this text (a repository…)',
        'output': '"json" for JSON lines whatever the format',
        'apikey': 'Your API key, when the tool cannot send the X-API-KEY header',
    }, description='Every shareable rule of the format, as the tool loads it (YARA .yar, Suricata .rules, Sigma YAML, '
                   'else JSON lines). Rules tagged TLP:RED / AMBER are never included.')
    def get(self, fmt):
        user = _key_user()
        if not user:
            return {'success': False, 'message': 'An API key is needed (free account: /register, key on your profile).'}, 403
        try:
            body, mime, filename, etag, count = FeedModel.build(
                fmt, _base_url(), since=request.args.get('since'), tag=request.args.get('tag'),
                source=request.args.get('source'), as_json=request.args.get('output') == 'json')
        except LookupError:
            return {'success': False, 'message': f'No feed for {fmt}: see GET /api/feed/'}, 404
        except ValueError as e:
            return {'success': False, 'message': str(e)}, 400
        if request.if_none_match and etag in request.if_none_match:
            return Response(status=304, headers={'ETag': etag})
        return Response(body, mimetype=mime, headers={
            'ETag': etag, 'Content-Disposition': f'inline; filename="{filename}"', 'X-Rulezet-Rules': str(count),
            'Cache-Control': 'private, max-age=300'})
