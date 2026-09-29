"""
Tests for the admin-configurable Ollama server (AI admin → Models & Security):
InstanceConfig.ollama_url / ollama_default_model / ollama_remote_allowed, the
settings resolver in ai_core.py, and the locality guard's one admin-granted
exception for a remote host.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.core.db_class.db import InstanceConfig, User
from app.features.ai.ai_core import (
    AgentConnectionError,
    OllamaClient,
    get_ollama_settings,
    is_allowed_ollama_url,
)

REMOTE = 'http://aipitch1.circl.lu:11434'


def _login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _user(app, email):
    with app.app_context():
        return User.query.filter_by(email=email).first()


def _instance_config(**fields):
    cfg = InstanceConfig.query.first()
    if not cfg:
        cfg = InstanceConfig(uuid=str(uuid.uuid4()))
        db.session.add(cfg)
    for k, v in fields.items():
        setattr(cfg, k, v)
    db.session.commit()
    return cfg


@pytest.fixture
def admin_client(app, client):
    with app.app_context():
        _instance_config()
    _login(client, _user(app, "admin@admin.admin"))
    return client


# ── resolver + guard ─────────────────────────────────────────────────────────

def test_settings_fall_back_to_config_when_unset(app):
    with app.app_context():
        _instance_config(ollama_url=None, ollama_default_model=None, ollama_remote_allowed=False)
        s = get_ollama_settings()
        assert s['url'] == (app.config['OLLAMA_URL']).rstrip('/')
        assert s['default_model'] == app.config['OLLAMA_MODEL']
        assert s['is_local'] is True


def test_settings_prefer_instance_config(app):
    with app.app_context():
        _instance_config(ollama_url=REMOTE + '/', ollama_default_model='qwen3:27b', ollama_remote_allowed=True)
        s = get_ollama_settings()
        assert s['url'] == REMOTE
        assert s['default_model'] == 'qwen3:27b'
        assert s['is_local'] is False


def test_remote_url_refused_without_opt_in(app):
    with app.app_context():
        _instance_config(ollama_url=REMOTE, ollama_remote_allowed=False)
        assert is_allowed_ollama_url(REMOTE) is False
        with pytest.raises(AgentConnectionError):
            OllamaClient(base_url=REMOTE, model='m', timeout=5)


def test_remote_url_accepted_with_opt_in(app):
    with app.app_context():
        _instance_config(ollama_url=REMOTE, ollama_remote_allowed=True)
        assert is_allowed_ollama_url(REMOTE) is True
        OllamaClient(base_url=REMOTE, model='m', timeout=5)


def test_opt_in_only_covers_the_configured_host(app):
    with app.app_context():
        _instance_config(ollama_url=REMOTE, ollama_remote_allowed=True)
        assert is_allowed_ollama_url('http://api.openai.com') is False
        assert is_allowed_ollama_url('http://localhost:11434') is True


# ── admin routes ─────────────────────────────────────────────────────────────

def test_settings_routes_require_admin(app, client):
    assert client.get('/ai/admin/ollama_settings').status_code in (302, 401, 403)
    _login(client, _user(app, "neo@admin.admin"))
    assert client.get('/ai/admin/ollama_settings').status_code == 403
    assert client.post('/ai/admin/ollama_settings', json={'ollama_url': REMOTE}).status_code == 403


def test_save_remote_requires_explicit_opt_in(app, admin_client):
    res = admin_client.post('/ai/admin/ollama_settings', json={'ollama_url': REMOTE})
    assert res.status_code == 400
    with app.app_context():
        assert InstanceConfig.query.first().ollama_url is None


def test_save_remote_with_opt_in(app, admin_client):
    res = admin_client.post('/ai/admin/ollama_settings', json={
        'ollama_url': REMOTE, 'ollama_default_model': 'qwen3:27b', 'ollama_remote_allowed': True,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['effective']['url'] == REMOTE
    assert data['effective']['default_model'] == 'qwen3:27b'
    with app.app_context():
        cfg = InstanceConfig.query.first()
        assert cfg.ollama_url == REMOTE
        assert cfg.ollama_remote_allowed is True


def test_save_rejects_malformed_url(admin_client):
    res = admin_client.post('/ai/admin/ollama_settings', json={'ollama_url': 'aipitch1:11434'})
    assert res.status_code == 400


def test_clearing_url_falls_back_to_config(app, admin_client):
    admin_client.post('/ai/admin/ollama_settings', json={'ollama_url': REMOTE, 'ollama_remote_allowed': True})
    res = admin_client.post('/ai/admin/ollama_settings', json={'ollama_url': ''})
    assert res.status_code == 200
    assert res.get_json()['effective']['url'] == app.config['OLLAMA_URL'].rstrip('/')


def test_connection_test_refuses_remote_without_opt_in(admin_client):
    with patch('requests.get') as mock_get:
        res = admin_client.post('/ai/admin/ollama_settings/test', json={'ollama_url': REMOTE})
    assert res.status_code == 400
    mock_get.assert_not_called()


def test_connection_test_lists_models(admin_client):
    fake = MagicMock()
    fake.json.return_value = {'models': [{'name': 'qwen3:27b'}, {'name': 'llama3.2:1b'}]}
    with patch('requests.get', return_value=fake) as mock_get:
        res = admin_client.post('/ai/admin/ollama_settings/test',
                                json={'ollama_url': REMOTE, 'ollama_remote_allowed': True})
    assert res.status_code == 200
    assert res.get_json()['models'] == ['llama3.2:1b', 'qwen3:27b']
    assert mock_get.call_args[0][0] == f'{REMOTE}/api/tags'
