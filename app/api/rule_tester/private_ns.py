import datetime

from flask import request
from flask_login import current_user
from flask_restx import Namespace, Resource

from app.core.utils.activity_log import log_activity
from app.features.rule import rule_core as RuleModel
from app.features.rule_tester import rule_tester_core as TesterModel
from app.features.rule_tester.drivers import registry

rule_tester_private_ns = Namespace(
    'Rule Tester — Private 🔑',
    description='Authenticated rule testing endpoints',
)


def _get_actor():
    """Return current user from session or API key."""
    from app.core.utils.utils import get_user_from_api
    u = get_user_from_api(request.headers)
    if u:
        return u
    if current_user.is_authenticated:
        return current_user
    return None


# ── Capabilities ──────────────────────────────────────────────────────────────

@rule_tester_private_ns.route('/capabilities')
class Capabilities(Resource):
    def get(self):
        """List all supported formats and their input types."""
        return {'capabilities': registry.get_all_capabilities()}


# ── Create / run a test ───────────────────────────────────────────────────────

@rule_tester_private_ns.route('/test')
class TestCreate(Resource):
    def post(self):
        """Create and (for single tests) immediately run a rule test."""
        actor = _get_actor()
        if not actor:
            return {'message': 'Authentication required'}, 401

        data = request.get_json(force=True, silent=True) or {}

        test_type   = data.get('test_type', 'single')
        fmt         = (data.get('format') or '').lower()
        input_type  = data.get('input_type', 'string')
        input_data  = data.get('input_data', '')
        input_label = data.get('input_label')
        label       = data.get('label')
        notes       = data.get('notes')
        is_public   = bool(data.get('is_public', False))
        rule_uuid   = data.get('rule_uuid')
        bulk_filters = data.get('bulk_filters')

        if not fmt:
            return {'message': 'format is required'}, 400
        if not input_type or input_data is None:
            return {'message': 'input_type and input_data are required'}, 400

        _ENABLED_FORMATS = {'yara'}
        if fmt not in _ENABLED_FORMATS:
            return {'message': f'Testing for {fmt.upper()} is not yet available. Only YARA is currently supported.'}, 400

        driver = registry.get_driver(fmt)
        if not driver:
            return {'message': f'Unsupported format: {fmt}'}, 400

        rule_id = None
        rule    = None
        if rule_uuid:
            rule = RuleModel.get_rule_by_uuid(rule_uuid)
            if not rule:
                return {'message': 'Rule not found'}, 404
            rule_id = rule.id

        # ── Single test: run synchronously ────────────────────────────────────
        if test_type == 'single':
            if not rule:
                return {'message': 'rule_uuid is required for single tests'}, 400

            rule_content = rule.to_string or ''
            logs = []

            def log_fn(level, message):
                logs.append({'level': level, 'message': message})

            test = TesterModel.create_test(
                user_id     = actor.id,
                test_type   = 'single',
                fmt         = fmt,
                input_type  = input_type,
                input_data  = input_data,
                input_label = input_label,
                rule_id     = rule_id,
                label       = label,
                notes       = notes,
                is_public   = is_public,
            )
            TesterModel.mark_test_running(test)

            try:
                detail = driver.run_test(rule_content, {'type': input_type, 'value': input_data}, log_fn)
            except Exception as e:
                TesterModel.mark_test_failed(test, str(e))
                return {
                    'test_uuid': test.uuid,
                    'status':    'failed',
                    'error':     str(e),
                }, 200

            TesterModel.create_result(
                test_id           = test.id,
                rule_id           = rule_id,
                rule_title        = rule.title,
                rule_uuid         = rule.uuid,
                rule_format       = rule.format,
                matched           = detail.matched,
                score             = detail.score,
                details           = detail.details,
                quality_hints     = detail.quality_hints,
                execution_time_ms = detail.execution_time_ms,
                error             = detail.error,
            )

            TesterModel.mark_test_done(test, matched_count=1 if detail.matched else 0,
                                       total_rules=1)

            log_activity(
                'rule_test.complete',
                f'Test on rule "{rule.title}" — {"matched" if detail.matched else "no match"} '
                f'(score {detail.score:.2f})',
                target_type='rule', target_id=rule.id, target_uuid=rule.uuid,
            )

            return {
                'test_uuid': test.uuid,
                'status':    'done',
                'matched':   detail.matched,
                'score':     detail.score,
                'details':   detail.details,
                'quality_hints': detail.quality_hints,
                'execution_time_ms': detail.execution_time_ms,
                'error':     detail.error,
                'logs':      logs,
            }, 200

        # ── Bulk test: create background job ──────────────────────────────────
        if test_type == 'bulk':
            if not bulk_filters and not fmt:
                return {'message': 'bulk_filters is required for bulk tests'}, 400

            test = TesterModel.create_test(
                user_id      = actor.id,
                test_type    = 'bulk',
                fmt          = fmt,
                input_type   = input_type,
                input_data   = input_data,
                input_label  = input_label,
                bulk_filters = bulk_filters or {},
                label        = label,
                notes        = notes,
                is_public    = is_public,
            )

            from app import db
            from app.core.db_class.db import BackgroundJob
            import uuid as _uuid

            job = BackgroundJob(
                uuid     = str(_uuid.uuid4()),
                created_by = actor.id,
                job_type = 'rule_test_bulk',
                status   = 'pending',
                label    = label or f'Bulk {fmt.upper()} test',
                payload  = {
                    'test_uuid':    test.uuid,
                    'format':       fmt,
                    'input_type':   input_type,
                    'input_data':   input_data,
                    'bulk_filters': bulk_filters or {},
                },
            )
            db.session.add(job)
            db.session.flush()
            test.job_id = job.id
            db.session.commit()

            log_activity(
                'rule_test.bulk_launch',
                f'Bulk {fmt.upper()} test launched',
                target_type=None, target_id=None, target_uuid=None,
            )

            return {
                'test_uuid': test.uuid,
                'job_uuid':  job.uuid,
                'status':    'pending',
            }, 202

        return {'message': f'Unknown test_type: {test_type}'}, 400


# ── Get test details + result ─────────────────────────────────────────────────

@rule_tester_private_ns.route('/test/<string:test_uuid>')
class TestDetail(Resource):
    def get(self, test_uuid):
        actor = _get_actor()
        test  = TesterModel.get_test_by_uuid(test_uuid, viewer=actor)
        if not test:
            return {'message': 'Test not found'}, 404

        result = test.results.order_by(None).first()
        return {
            'test':   test.to_json(),
            'result': result.to_json() if result else None,
        }

    def delete(self, test_uuid):
        actor = _get_actor()
        test  = TesterModel.get_test_by_uuid(test_uuid, viewer=actor)
        if not test:
            return {'message': 'Test not found'}, 404
        TesterModel.assert_test_writable(test, actor)
        TesterModel.delete_test(test)
        return {'message': 'Deleted'}, 200


# ── Paginated results (for bulk) ──────────────────────────────────────────────

@rule_tester_private_ns.route('/test/<string:test_uuid>/results')
class TestResults(Resource):
    def get(self, test_uuid):
        actor    = _get_actor()
        test     = TesterModel.get_test_by_uuid(test_uuid, viewer=actor)
        if not test:
            return {'message': 'Test not found'}, 404

        page        = int(request.args.get('page', 1))
        per_page    = min(int(request.args.get('per_page', 20)), 100)
        matched_only = request.args.get('matched') == '1'
        errors_only  = request.args.get('errors_only') == '1'

        from app.core.db_class.db import RuleTestResult
        q = RuleTestResult.query.filter_by(test_id=test.id)
        if matched_only:
            q = q.filter(RuleTestResult.matched == True)
        elif errors_only:
            q = q.filter(RuleTestResult.error.isnot(None))
        pagination = (q.order_by(RuleTestResult.matched.desc(),
                                 RuleTestResult.score.desc().nullslast())
                       .paginate(page=page, per_page=per_page, error_out=False))

        return {
            'results':  [r.to_json() for r in pagination.items],
            'total':    pagination.total,
            'pages':    pagination.pages,
            'page':     page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        }


# ── Toggle visibility ─────────────────────────────────────────────────────────

@rule_tester_private_ns.route('/test/<string:test_uuid>/visibility')
class TestVisibility(Resource):
    def put(self, test_uuid):
        actor = _get_actor()
        test  = TesterModel.get_test_by_uuid(test_uuid, viewer=actor)
        if not test:
            return {'message': 'Test not found'}, 404
        TesterModel.assert_test_writable(test, actor)
        new_val = TesterModel.toggle_visibility(test)
        log_activity('rule_test.visibility_change',
                     f'Test made {"public" if new_val else "private"}',
                     target_type=None, target_id=None, target_uuid=test.uuid)
        return {'is_public': new_val}


# ── Update notes ──────────────────────────────────────────────────────────────

@rule_tester_private_ns.route('/test/<string:test_uuid>/notes')
class TestNotes(Resource):
    def put(self, test_uuid):
        actor = _get_actor()
        test  = TesterModel.get_test_by_uuid(test_uuid, viewer=actor)
        if not test:
            return {'message': 'Test not found'}, 404
        TesterModel.assert_test_writable(test, actor)
        data  = request.get_json(force=True, silent=True) or {}
        TesterModel.update_notes(test, data.get('notes', ''))
        return {'notes': test.notes}


# ── My tests ──────────────────────────────────────────────────────────────────

@rule_tester_private_ns.route('/my-tests')
class MyTests(Resource):
    def get(self):
        actor    = _get_actor()
        page     = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 50)
        pagination = TesterModel.get_my_tests(actor.id, page=page, per_page=per_page)
        return {
            'tests':    [t.to_json_summary() for t in pagination.items],
            'total':    pagination.total,
            'pages':    pagination.pages,
            'page':     page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        }
