"""Admin → Cache: admins only, actions work and are logged, settings switch the cache off,
workflow tasks and the 'Cache maintenance' template."""
import json

from app import db
from app.core.db_class.rule import Rule
from app.core.db_class.user import User
from app.core.utils import cache_versions as cv


def _login(client, admin=False):
    email, pw = ('admin@admin.admin', 'admin') if admin else ('t@t.t', 'password1@A')
    client.post('/account/login', data={'email': email, 'password': pw, 'remember_me': False}, follow_redirects=True)
    return client


def _rid(app):
    with app.app_context():
        return Rule.query.filter_by(is_deleted=False).first().id


def test_page_is_admin_only(app):
    assert app.test_client().get('/admin/cache').status_code == 302
    c = _login(app.test_client())
    assert c.get('/admin/cache').status_code == 403
    assert c.post('/admin/cache/action', json={'action': 'clear_all'}).status_code == 403
    assert app.test_client().post('/admin/cache/action', json={'action': 'clear_all'}).status_code in (302, 400)


def test_admin_page_and_status(app, real_cache):
    c = _login(app.test_client(), admin=True)
    r = c.get('/admin/cache')
    assert r.status_code == 302 and r.headers['Location'].endswith('/admin/settings?tab=cache')
    page = c.get('/admin/settings').get_data(as_text=True)
    assert 'pane-cache' in page and '<cache-panel' in page
    s = c.get('/admin/cache/status').get_json()
    assert s['backend']['type'] == 'SimpleCache'
    assert set(s['settings']) == {'cache.enabled', 'cache.rule_page_seconds', 'cache.rule_parts_seconds', 'cache.api_seconds',
                               'cache.user_activity_seconds'}


def test_actions(app, real_cache):
    rid = _rid(app)
    c = _login(app.test_client(), admin=True)
    with app.app_context():
        before = cv.rule_key('page', rid)
    assert c.post('/admin/cache/action', json={'action': 'refresh_rule', 'rule_id': rid}).get_json()['success']
    with app.app_context():
        after = cv.rule_key('page', rid)
    assert after != before
    assert c.post('/admin/cache/action', json={'action': 'refresh_rules'}).get_json()['success']
    with app.app_context():
        assert cv.rule_key('page', rid) != after
    assert c.post('/admin/cache/action', json={'action': 'refresh_rule', 'rule_id': 999999}).status_code == 404
    assert c.post('/admin/cache/action', json={'action': 'refresh_rule', 'rule_id': 'x'}).status_code == 400
    assert c.post('/admin/cache/action', json={'action': 'nope'}).status_code == 400
    assert c.post('/admin/cache/action', json={'action': 'reset_stats'}).get_json()['success']
    assert c.post('/admin/cache/action', json={'action': 'clear_all'}).get_json()['success']
    from app.core.db_class.activity_log import ActivityLog
    with app.app_context():
        actions = {a.action for a in ActivityLog.query.filter(ActivityLog.action.like('cache.%')).all()}
    assert {'cache.refresh_rule', 'cache.refresh_rules', 'cache.clear_all', 'cache.reset_stats'} <= actions


def test_hit_ratio_counted(app, real_cache):
    rid = _rid(app)
    app.test_client().get(f'/rule/detail_rule/{rid}')
    app.test_client().get(f'/rule/detail_rule/{rid}')
    s = _login(app.test_client(), admin=True).get('/admin/cache/status').get_json()['stats']['page']
    assert s['hit'] == 1 and s['miss'] == 1 and s['ratio'] == 50


def test_setting_off_means_live_pages(app, real_cache):
    from app.core.utils.app_settings import set_setting
    rid = _rid(app)
    with app.app_context():
        admin_id = User.query.filter_by(email='admin@admin.admin').first().id
        set_setting('cache.enabled', False, admin_id)
    try:
        r1 = app.test_client().get(f'/rule/detail_rule/{rid}')
        r2 = app.test_client().get(f'/rule/detail_rule/{rid}')
        assert r1.status_code == r2.status_code == 200
        assert 'X-App-Cache' not in r2.headers
    finally:
        with app.app_context():
            set_setting('cache.enabled', True, admin_id)      # the settings are kept in the process


def test_workflow_tasks(app, real_cache):
    from app.features.jobs.jobs_core import create_job
    from app.features.jobs.job_worker import _HANDLERS
    from app.features.admin.task_scheduler.task_types import TASK_TYPES
    assert {'cache_refresh_rules', 'cache_warm_rules'} <= set(TASK_TYPES)
    rid = _rid(app)
    with app.app_context():
        admin = User.query.filter_by(email='admin@admin.admin').first()
        before = cv.rule_key('page', rid)
        job = create_job('cache_refresh_rules', {}, 'refresh', admin.id)
        _HANDLERS['cache_refresh_rules'](job, app)
        assert cv.rule_key('page', rid) != before and job.done == 1
        job = create_job('cache_warm_rules', {'limit': 5}, 'warm', admin.id)
        _HANDLERS['cache_warm_rules'](job, app)
        assert job.done >= 1
    # the warmed page is now served from the cache
    assert app.test_client().get(f'/rule/detail_rule/{rid}').headers['X-App-Cache'] == 'HIT'


def test_cache_maintenance_template():
    from app.features.admin.task_scheduler.task_types import TASK_TYPES
    t = json.load(open('app/config/workflows.templates.json'))['value']['cache_maintenance']
    tasks = t['spec']['tasks']
    refs = {x['ref'] for x in tasks}
    for x in tasks:
        assert x['task_type'] in TASK_TYPES, x['task_type']
        after = x['trigger'].get('after')
        assert after is None or after in refs
    assert tasks[0]['trigger']['trigger_mode'] == 'daily'
