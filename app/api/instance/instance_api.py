from flask_restx import Namespace, Resource
from flask import request, current_app
from datetime import datetime, timedelta
from app import db
from app.core.db_class.db import RegisteredInstance

instance_ns = Namespace('instance', description='Instance registry — phone-home endpoint')


@instance_ns.route('/register')
class InstanceRegister(Resource):
    def post(self):
        # Only the official instance accepts registrations.
        # On any other self-hosted instance this endpoint is silent.
        if not current_app.config.get('IS_OFFICIAL_INSTANCE'):
            return {'message': 'Not found'}, 404

        data = request.get_json(silent=True) or {}
        uuid = (data.get('uuid') or '').strip()
        if not uuid or len(uuid) > 36:
            return {'message': 'uuid required'}, 400

        now  = datetime.utcnow()
        inst = RegisteredInstance.query.filter_by(uuid=uuid).first()

        if inst:
            # Rate-limit: accept at most one real update per hour per UUID
            if now - inst.last_seen < timedelta(hours=1):
                return {'message': 'ok', 'status': 'rate_limited'}, 200
            inst.last_seen     = now
            inst.ping_count   += 1
            url = (data.get('url') or '').strip()
            if url:
                inst.public_url = url
            ver = (data.get('version') or '').strip()
            if ver:
                inst.version = ver
            if data.get('rules_count') is not None:
                inst.rules_count   = data['rules_count']
            if data.get('bundles_count') is not None:
                inst.bundles_count = data['bundles_count']
        else:
            inst = RegisteredInstance(
                uuid          = uuid,
                public_url    = (data.get('url') or '').strip() or None,
                version       = (data.get('version') or '').strip() or None,
                rules_count   = data.get('rules_count'),
                bundles_count = data.get('bundles_count'),
                ping_count    = 1,
                first_seen    = now,
                last_seen     = now,
            )
            db.session.add(inst)

        db.session.commit()
        return {'message': 'ok', 'status': 'registered'}, 200
