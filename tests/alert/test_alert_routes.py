"""
Tests for app/features/alert/alert.py — pages, JSON endpoints, permissions,
search / filters and the no-login email unsubscribe link.
"""

import uuid

import pytest

from app import db
from app.core.db_class.db import Alert, InstanceConfig, User
from app.features.alert import alert_core as A


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def _user_id(app, email):
    with app.app_context():
        return User.query.filter_by(email=email).first().id


@pytest.fixture
def owner_client(app, client):
    app.config.update(MAIL_DEFAULT_SENDER='noreply@rulezet.test')
    with app.app_context():
        if not InstanceConfig.query.first():
            db.session.add(InstanceConfig(uuid=str(uuid.uuid4())))
            db.session.commit()
    _login(client, _user_id(app, "t@t.t"))
    return client


PAYLOAD = {'name': 'NetScaler', 'targets': ['rule'], 'events': ['created'],
           'criteria': {'cves': ['CVE-2026-19490'], 'keywords': ['netscaler']}, 'email_mode': 'daily'}


def _create(client, **overrides):
    res = client.post('/alert/create', json={**PAYLOAD, **overrides})
    assert res.status_code == 200, res.get_json()
    return res.get_json()['alert']['uuid']


def test_pages_require_login(client):
    for path in ('/alert/', '/alert/new', '/alert/data'):
        assert client.get(path).status_code in (302, 401)


def test_pages_render(app, owner_client):
    alert_uuid = _create(owner_client)
    for path in ('/alert/', '/alert/new?cves=CVE-2026-1&attacks=T1190&target=both',
                 f'/alert/{alert_uuid}', f'/alert/{alert_uuid}/edit'):
        assert owner_client.get(path).status_code == 200, path


def test_crud(app, owner_client):
    alert_uuid = _create(owner_client)
    res = owner_client.post(f'/alert/{alert_uuid}/update', json={**PAYLOAD, 'name': 'Renamed'})
    assert res.get_json()['alert']['name'] == 'Renamed'
    assert owner_client.post(f'/alert/{alert_uuid}/toggle', json={'is_active': False}).get_json()['is_active'] is False
    assert owner_client.post(f'/alert/{alert_uuid}/delete').get_json()['success'] is True
    with app.app_context():
        assert A.get_alert_by_uuid(alert_uuid) is None


def test_invalid_payload_is_rejected(owner_client):
    res = owner_client.post('/alert/create', json={**PAYLOAD, 'criteria': {}})
    assert res.status_code == 400


def test_other_users_cannot_touch_an_alert(app, owner_client):
    alert_uuid = _create(owner_client)
    other = app.test_client()
    _login(other, _user_id(app, "neo@admin.admin"))
    assert other.get(f'/alert/{alert_uuid}').status_code == 403
    assert other.post(f'/alert/{alert_uuid}/update', json=PAYLOAD).status_code == 403
    assert other.post(f'/alert/{alert_uuid}/delete').status_code == 403
    assert other.get(f'/alert/{alert_uuid}/matches').status_code == 403


def test_admin_can_open_any_alert(app, owner_client):
    alert_uuid = _create(owner_client)
    admin = app.test_client()
    _login(admin, _user_id(app, "admin@admin.admin"))
    assert admin.get(f'/alert/{alert_uuid}').status_code == 200


def test_search_matches_values_not_json_keys(owner_client):
    _create(owner_client, name='CVE watch')
    _create(owner_client, name='Phishing', criteria={'keywords': ['phishing']})
    data = owner_client.get('/alert/data?q=cve').get_json()
    assert [a['name'] for a in data['items']] == ['CVE watch']
    data = owner_client.get('/alert/data?q=phish').get_json()
    assert [a['name'] for a in data['items']] == ['Phishing']


def test_filters_and_pagination(owner_client):
    for i in range(5):
        _create(owner_client, name=f'Alert {i}', email_mode='off' if i % 2 else 'daily')
    paused = _create(owner_client, name='Paused one')
    owner_client.post(f'/alert/{paused}/toggle', json={'is_active': False})

    assert owner_client.get('/alert/data?status=paused').get_json()['total'] == 1
    assert owner_client.get('/alert/data?email=off').get_json()['total'] == 2
    page2 = owner_client.get('/alert/data?per_page=4&page=2').get_json()
    assert page2['total'] == 6 and page2['total_pages'] == 2 and len(page2['items']) == 2
    kpis = owner_client.get('/alert/data?status=paused').get_json()['kpis']
    assert kpis['total'] == 6 and kpis['active'] == 5          # KPIs ignore the filters


def test_email_mode_refused_when_email_disabled(app, owner_client):
    with app.app_context():
        InstanceConfig.query.first().email_enabled = False
        db.session.commit()
    alert_uuid = _create(owner_client, email_mode='instant')
    with app.app_context():
        assert A.get_alert_by_uuid(alert_uuid).email_mode == 'off'


def test_unsubscribe_link_works_without_login(app, owner_client):
    alert_uuid = _create(owner_client, email_mode='instant')
    with app.app_context():
        token = A.make_unsubscribe_token(A.get_alert_by_uuid(alert_uuid))
    anonymous = app.test_client()
    assert anonymous.get(f'/alert/unsubscribe/{token}').status_code == 200
    with app.app_context():
        assert A.get_alert_by_uuid(alert_uuid).email_mode == 'off'
    assert anonymous.get('/alert/unsubscribe/forged').status_code == 200   # friendly page, no change


def test_preview_endpoint(owner_client):
    res = owner_client.post('/alert/preview', json={'criteria': {'keywords': ['netscaler']}, 'targets': ['rule']})
    assert res.status_code == 200 and res.get_json()['preview']['days'] == 30


def test_user_actions_are_logged(app, owner_client):
    from app.core.db_class.db import ActivityLog
    alert_uuid = _create(owner_client)
    owner_client.post(f'/alert/{alert_uuid}/update', json={**PAYLOAD, 'name': 'Renamed'})
    owner_client.post(f'/alert/{alert_uuid}/toggle', json={'is_active': False})
    owner_client.post(f'/alert/{alert_uuid}/delete')
    with app.app_context():
        actions = [l.action for l in ActivityLog.query.filter(ActivityLog.action.like('alert.%'))
                                                      .order_by(ActivityLog.id).all()]
    assert actions == ['alert.create', 'alert.update', 'alert.toggle', 'alert.delete']
