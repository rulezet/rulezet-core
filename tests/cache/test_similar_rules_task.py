"""Workflow task 'similar_rules_scan' (same analysis as Admin → Similar rules) + who may launch it."""
from app.core.db_class.rule import Rule
from app.core.db_class.user import User


def _login(client, admin=False):
    email, pw = ('admin@admin.admin', 'admin') if admin else ('t@t.t', 'password1@A')
    client.post('/account/login', data={'email': email, 'password': pw, 'remember_me': False}, follow_redirects=True)
    return client


def test_task_type_registered():
    from app.features.admin.task_scheduler.task_types import TASK_TYPES
    import app.features.jobs.job_handlers  # noqa: F401 — registers the handlers
    from app.features.jobs.job_worker import _HANDLERS
    t = TASK_TYPES['similar_rules_scan']
    assert t['job_type'] in _HANDLERS
    assert [o['value'] for o in t['extra_options'][0]['options']] == ['new_only', 'all']


class _FakeSession:
    """Stands for Similarity_class (the real one runs threads on the whole database)."""
    made = []

    def __init__(self, user, info, mode=None, params=None, **kw):
        self.user, self.mode, self.params = user, mode, params
        self.stopped, self.status_message, self.uuid, self.calls = False, 'ok', 'fake-uuid', 0
        _FakeSession.made.append(self)

    def start(self):
        pass

    def status(self):
        self.calls += 1
        done = self.calls >= 2
        return {'stopped': done, 'total_jobs': 2, 'complete': 2 if done else 1, 'total': 5, 'similar_pairs_found': 3}

    def stop(self):
        self.stopped = True


def test_handler_runs_the_same_analysis_as_the_page(app, monkeypatch):
    from app.features.jobs.jobs_core import create_job
    from app.features.jobs.job_worker import _HANDLERS
    from app.features.rule.utils.similar_rules import similarity_class as SM
    monkeypatch.setattr(SM, 'Similarity_class', _FakeSession)
    monkeypatch.setattr('time.sleep', lambda s: None)
    _FakeSession.made.clear()
    with app.app_context():
        admin_id = User.query.filter_by(email='admin@admin.admin').first().id
        for scope, params in (('new_only', {'mode': 'new_only'}), ('all', {'mode': 'all', 'selected_ids': []})):
            job = create_job('similar_rules_scan', {'scope': scope}, 'similar', admin_id)
            _HANDLERS['similar_rules_scan'](job, app)
            s = _FakeSession.made[-1]
            assert s.mode == 'filter' and s.params == params          # exactly what the page's buttons send
            assert s.user.id == admin_id and job.status != 'failed'


def test_handler_does_not_wait_for_a_run_that_ended(app, monkeypatch):
    from app.features.jobs.jobs_core import create_job
    from app.features.jobs.job_worker import _HANDLERS
    from app.features.rule.utils.similar_rules import similarity_class as SM

    class Ended(_FakeSession):
        def status(self):
            # finished early (_finish_early): stopped, out of the sessions list, never "stopped" in status
            self.stopped = True
            if self in SM.sessions:
                SM.sessions.remove(self)
            return {'stopped': False}
    monkeypatch.setattr(SM, 'Similarity_class', Ended)
    monkeypatch.setattr('time.sleep', lambda s: None)
    with app.app_context():
        admin_id = User.query.filter_by(email='admin@admin.admin').first().id
        job = create_job('similar_rules_scan', {'scope': 'new_only'}, 'similar', admin_id)
        _HANDLERS['similar_rules_scan'](job, app)                    # returns at once


def test_bad_scope_fails(app):
    from app.features.jobs.jobs_core import create_job
    from app.features.jobs.job_worker import _HANDLERS
    with app.app_context():
        admin_id = User.query.filter_by(email='admin@admin.admin').first().id
        job = create_job('similar_rules_scan', {'scope': 'everything!'}, 'similar', admin_id)
        _HANDLERS['similar_rules_scan'](job, app)
        assert job.status == 'failed'


def test_only_admins_run_whole_instance_scans(app):
    c = _login(app.test_client())
    assert c.get('/rule/similar_rules/update').status_code == 403                  # GET wipes every pair
    assert c.post('/rule/similar_rules/update', json={'mode': 'all', 'selected_ids': []}).status_code == 403
    assert c.post('/rule/similar_rules/update', json={'mode': 'new_only'}).status_code == 403
    assert c.post('/rule/similar_rules/update', json={'mode': 'partial', 'selected_ids': [1, 2]}).status_code == 403
    with app.app_context():
        rid = Rule.query.filter_by(is_deleted=False).first().id
    from app.features.rule.utils.similar_rules import similarity_class as SM
    import pytest
    mp = pytest.MonkeyPatch()
    mp.setattr(SM, 'Similarity_class', _FakeSession)
    try:
        assert c.post('/rule/similar_rules/update', json={'mode': 'partial', 'selected_ids': [rid]}).status_code == 201
    finally:
        mp.undo()
    assert app.test_client().get('/rule/similar_rules/update').status_code in (302, 401)
