"""
Tests for the AI providers (AI admin → Models & Security): several backends
(Ollama, Claude, ChatGPT, OpenAI-compatible), one active. Covers the default
(seeded from the old Ollama settings, so Ollama stays the default), the
locality guard, and the API-key security rules: admin-only writes, key
encrypted at rest and never returned, key dropped when the endpoint changes,
explicit consent before anything is sent outside the network.
"""

import uuid
from unittest.mock import patch

import pytest

from app import db
from app.core.db_class.db import AIProvider, InstanceConfig, User
from app.features.ai.ai_core import (
    AgentConnectionError,
    OllamaClient,
    decrypt_secret,
    get_active_provider,
    get_ollama_settings,
    is_allowed_ollama_url,
    make_client,
)

REMOTE = 'http://gpu-box.example.org:11434'
KEY = 'fake-provider-key-for-tests-0000'


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


def _create_claude(admin_client, **extra):
    body = {'name': 'Claude', 'kind': 'anthropic', 'api_key': KEY, 'default_model': 'claude-opus-5-5',
            'remote_allowed': True}
    body.update(extra)
    return admin_client.post('/ai/admin/providers', json=body)


# ── default provider = the Ollama the instance already used ──────────────────

def test_default_provider_is_seeded_ollama_from_config(app):
    with app.app_context():
        _instance_config(ollama_url=None, ollama_default_model=None, ollama_remote_allowed=False)
        p = get_active_provider()
        assert p.kind == 'ollama'
        assert p.url == app.config['OLLAMA_URL'].rstrip('/')
        assert p.default_model == app.config['OLLAMA_MODEL']
        assert AIProvider.query.filter_by(is_active=True).count() == 1


def test_default_provider_keeps_previous_instance_ollama_settings(app):
    with app.app_context():
        _instance_config(ollama_url=REMOTE + '/', ollama_default_model='qwen3:27b', ollama_remote_allowed=True)
        s = get_ollama_settings()
        assert (s['kind'], s['url'], s['default_model'], s['is_local']) == ('ollama', REMOTE, 'qwen3:27b', False)


# ── locality guard ───────────────────────────────────────────────────────────

def test_remote_ollama_refused_without_opt_in(app):
    with app.app_context():
        _instance_config(ollama_url=REMOTE, ollama_remote_allowed=False)
        assert is_allowed_ollama_url(REMOTE) is False
        with pytest.raises(AgentConnectionError):
            OllamaClient(base_url=REMOTE, model='m', timeout=5)
        with pytest.raises(AgentConnectionError):
            make_client(get_active_provider())


def test_opt_in_only_covers_the_configured_host(app):
    with app.app_context():
        _instance_config(ollama_url=REMOTE, ollama_remote_allowed=True)
        assert is_allowed_ollama_url('http://api.openai.com') is False
        assert is_allowed_ollama_url('http://localhost:11434') is True


# ── admin-only ───────────────────────────────────────────────────────────────

def test_provider_writes_require_real_admin(app, client):
    assert client.get('/ai/admin/providers').status_code in (302, 401, 403)
    _login(client, _user(app, "neo@admin.admin"))
    assert client.post('/ai/admin/providers', json={'name': 'x', 'kind': 'ollama'}).status_code == 403
    assert client.post('/ai/admin/providers/test', json={'name': 'x', 'kind': 'ollama'}).status_code == 403


# ── API key storage ──────────────────────────────────────────────────────────

def test_api_key_encrypted_at_rest_and_never_returned(app, admin_client):
    res = _create_claude(admin_client)
    assert res.status_code == 200
    assert KEY not in res.get_data(as_text=True)
    listing = admin_client.get('/ai/admin/providers').get_data(as_text=True)
    assert KEY not in listing
    with app.app_context():
        row = AIProvider.query.filter_by(kind='anthropic').first()
        assert row.api_key_enc and KEY not in row.api_key_enc
        assert decrypt_secret(row.api_key_enc) == KEY
        assert row.to_json()['api_key_hint'] == 'Stored'
        assert '0000' not in str(row.to_json())


def test_cloud_provider_needs_a_key(admin_client):
    res = admin_client.post('/ai/admin/providers', json={'name': 'Claude', 'kind': 'anthropic', 'remote_allowed': True})
    assert res.status_code == 400


def test_empty_key_on_update_keeps_the_stored_one(app, admin_client):
    pid = _create_claude(admin_client).get_json()['provider']['id']
    assert admin_client.post(f'/ai/admin/providers/{pid}', json={'name': 'Renamed'}).status_code == 200
    with app.app_context():
        assert decrypt_secret(db.session.get(AIProvider, pid).api_key_enc) == KEY


def test_changing_the_url_drops_the_stored_key(app, admin_client):
    pid = _create_claude(admin_client).get_json()['provider']['id']
    res = admin_client.post(f'/ai/admin/providers/{pid}', json={'base_url': 'https://evil.example.com'})
    assert res.status_code == 200
    assert res.get_json()['key_removed'] is True
    with app.app_context():
        assert db.session.get(AIProvider, pid).api_key_enc is None


def test_test_endpoint_never_sends_stored_key_to_a_new_url(app, admin_client):
    pid = _create_claude(admin_client).get_json()['provider']['id']
    seen = {}

    def _fake_list(self):
        seen['key'] = self.provider.api_key
        seen['url'] = self.provider.url
        return ['claude-opus-5-5']

    with patch('app.features.ai.ai_core.AnthropicClient.list_models', _fake_list):
        res = admin_client.post('/ai/admin/providers/test', json={
            'id': pid, 'name': 'Claude', 'kind': 'anthropic', 'base_url': 'https://evil.example.com',
            'remote_allowed': True})
    # No key may reach the new host: the client refuses before any call.
    assert res.status_code == 502
    assert 'key' not in seen

    with patch('app.features.ai.ai_core.AnthropicClient.list_models', _fake_list):
        res = admin_client.post('/ai/admin/providers/test', json={
            'id': pid, 'name': 'Claude', 'kind': 'anthropic', 'remote_allowed': True})
    assert res.status_code == 200
    assert seen == {'key': KEY, 'url': 'https://api.anthropic.com'}


def test_api_key_never_sent_over_plain_http_outside_the_network(admin_client):
    res = admin_client.post('/ai/admin/providers', json={
        'name': 'gw', 'kind': 'openai_compatible', 'base_url': 'http://gateway.example.com/v1',
        'api_key': KEY, 'remote_allowed': True})
    assert res.status_code == 400


def test_cloud_api_must_use_https(admin_client):
    res = _create_claude(admin_client, base_url='http://api.anthropic.com')
    assert res.status_code == 400


# ── remote Ollama (e.g. a GPU box on the institution network) ────────────────

def test_save_remote_ollama_over_http_with_opt_in(app, admin_client):
    res = admin_client.post('/ai/admin/providers', json={
        'name': 'GPU box', 'kind': 'ollama', 'base_url': REMOTE, 'default_model': 'qwen3:27b',
        'remote_allowed': True})
    assert res.status_code == 200
    pid = res.get_json()['provider']['id']
    assert admin_client.post(f'/ai/admin/providers/{pid}/activate').status_code == 200
    with app.app_context():
        s = get_ollama_settings()
        assert (s['kind'], s['url'], s['default_model'], s['is_local']) == ('ollama', REMOTE, 'qwen3:27b', False)
        assert is_allowed_ollama_url(REMOTE) is True
        make_client(get_active_provider())


def test_remote_ollama_cannot_be_activated_without_opt_in(admin_client):
    res = admin_client.post('/ai/admin/providers', json={'name': 'GPU box', 'kind': 'ollama', 'base_url': REMOTE})
    assert res.status_code == 200
    pid = res.get_json()['provider']['id']
    assert admin_client.post(f'/ai/admin/providers/{pid}/activate').status_code == 400


def test_save_rejects_malformed_url(admin_client):
    res = admin_client.post('/ai/admin/providers', json={'name': 'x', 'kind': 'ollama', 'base_url': 'gpu-box:11434'})
    assert res.status_code == 400


def test_connection_test_refuses_remote_without_opt_in(admin_client):
    with patch('requests.get') as mock_get:
        res = admin_client.post('/ai/admin/providers/test', json={'name': 'GPU box', 'kind': 'ollama', 'base_url': REMOTE})
    assert res.status_code == 400
    mock_get.assert_not_called()


def test_connection_test_lists_remote_ollama_models(admin_client):
    from unittest.mock import MagicMock
    fake = MagicMock()
    fake.json.return_value = {'models': [{'name': 'qwen3:27b'}, {'name': 'llama3.2:1b'}]}
    with patch('requests.get', return_value=fake) as mock_get:
        res = admin_client.post('/ai/admin/providers/test', json={
            'name': 'GPU box', 'kind': 'ollama', 'base_url': REMOTE, 'remote_allowed': True})
    assert res.status_code == 200
    assert res.get_json()['models'] == ['llama3.2:1b', 'qwen3:27b']
    assert mock_get.call_args[0][0] == f'{REMOTE}/api/tags'


def test_credentials_in_url_refused(admin_client):
    res = admin_client.post('/ai/admin/providers', json={
        'name': 'gw', 'kind': 'openai_compatible', 'base_url': 'https://user:pass@gw.example.com/v1',
        'remote_allowed': True})
    assert res.status_code == 400


# ── activation ───────────────────────────────────────────────────────────────

def test_activation_needs_consent_for_external_provider(app, admin_client):
    pid = _create_claude(admin_client, remote_allowed=False).get_json()['provider']['id']
    assert admin_client.post(f'/ai/admin/providers/{pid}/activate').status_code == 400
    admin_client.post(f'/ai/admin/providers/{pid}', json={'remote_allowed': True})
    assert admin_client.post(f'/ai/admin/providers/{pid}/activate').status_code == 200
    with app.app_context():
        assert AIProvider.query.filter_by(is_active=True).count() == 1
        p = get_active_provider()
        assert (p.kind, p.api_key) == ('anthropic', KEY)


def test_active_provider_cannot_be_deleted(app, admin_client):
    admin_client.get('/ai/admin/providers')   # seeds the default Ollama
    with app.app_context():
        active_id = AIProvider.query.filter_by(is_active=True).first().id
    assert admin_client.delete(f'/ai/admin/providers/{active_id}').status_code == 400


# ── table (DataTable feed) and test status ───────────────────────────────────

def test_added_providers_show_in_table_with_filters(admin_client):
    _create_claude(admin_client)
    admin_client.post('/ai/admin/providers', json={'name': 'GPU box', 'kind': 'ollama', 'base_url': REMOTE,
                                                   'remote_allowed': True})
    data = admin_client.get('/ai/admin/providers/data').get_json()
    names = {i['name'] for i in data['items']}
    assert {'Ollama (default)', 'Claude', 'GPU box'} <= names
    assert all(i['last_test_ok'] is None for i in data['items'])
    only_claude = admin_client.get('/ai/admin/providers/data?kind=anthropic').get_json()['items']
    assert [i['name'] for i in only_claude] == ['Claude']
    assert admin_client.get('/ai/admin/providers/data?search=GPU').get_json()['total'] == 1
    assert admin_client.get('/ai/admin/providers/data?test=never').get_json()['total'] == data['total']


def test_test_status_recorded_and_reset_when_url_changes(app, admin_client):
    pid = _create_claude(admin_client).get_json()['provider']['id']
    with patch('app.features.ai.ai_core.AnthropicClient.list_models', lambda self: ['claude-opus-5-5']):
        res = admin_client.post(f'/ai/admin/providers/{pid}/test')
    assert res.status_code == 200
    assert res.get_json()['provider']['last_test_ok'] is True
    assert admin_client.get('/ai/admin/providers/data?test=ok').get_json()['total'] == 1

    admin_client.post(f'/ai/admin/providers/{pid}', json={'base_url': 'https://other.example.com', 'api_key': KEY})
    with app.app_context():
        row = db.session.get(AIProvider, pid)
        assert row.last_test_ok is None and row.last_test_at is None


# ── monthly budget (spending tracked by Rulezet) ─────────────────────────────

def test_claude_cost_from_builtin_price_list(app):
    from app.features.ai.ai_core import ProviderConfig, estimate_cost
    p = ProviderConfig(kind='anthropic', url='https://api.anthropic.com', name='Claude')
    usage = {'input_tokens': 1_000_000, 'output_tokens': 100_000, 'cache_write_tokens': 0, 'cache_read_tokens': 0}
    assert estimate_cost(p, 'claude-opus-5-5', usage) == 6.0          # 4 + 0.1 * 20
    assert estimate_cost(p, 'claude-haiku-4-5-20251001', usage) == 1.5
    p_custom = ProviderConfig(kind='openai', url='https://api.openai.com/v1', name='GPT')
    assert estimate_cost(p_custom, 'gpt-x', usage) is None            # unknown price → not counted


def test_budget_shown_and_enforced(app, admin_client):
    import json
    pid = _create_claude(admin_client, monthly_budget_usd=10, block_over_budget=True).get_json()['provider']['id']
    admin_client.post(f'/ai/admin/providers/{pid}/activate')

    def _fake_call(self, messages, json_schema):
        self.usage['input_tokens'] += 1_000_000      # $4 on claude-opus-5-5
        self.usage['output_tokens'] += 150_000       # $3
        return json.dumps({"reply": "hi"})

    with app.app_context():
        from app.features.ai.ai_core import get_agent
        with patch('app.features.ai.ai_core.AnthropicClient._call', _fake_call), \
             patch('app.features.ai.ai_core.list_active_models', return_value=(None, ['claude-opus-5-5'])):
            agent = get_agent('chatbot')
            assert agent.run(user=None, history=[], message='hi').ok
            b = admin_client.get(f'/ai/admin/providers/{pid}/budget').get_json()
            assert (b['spent'], b['remaining_pct']) == (7.0, 30.0)
            assert agent.run(user=None, history=[], message='hi').ok     # $14 now, over budget
            blocked = agent.run(user=None, history=[], message='hi')
    assert not blocked.ok and blocked.meta['status'] == 'budget'


# ── missing SDK: the page is told to install it, only from the fixed list ────

def test_test_reports_missing_sdk_instead_of_failing(admin_client):
    with patch('app.features.ai.ai_core.missing_sdk', return_value=('anthropic', 'anthropic==0.67.0')):
        res = admin_client.post('/ai/admin/providers/test', json={
            'name': 'Claude', 'kind': 'anthropic', 'api_key': KEY, 'remote_allowed': True})
    assert res.status_code == 409
    assert res.get_json()['needs_install'] is True and res.get_json()['package'] == 'anthropic'


def test_install_sdk_only_for_known_provider_types(admin_client):
    with patch('subprocess.run') as run:
        assert admin_client.post('/ai/admin/providers/install_sdk', json={'kind': 'ollama'}).status_code == 400
        assert admin_client.post('/ai/admin/providers/install_sdk', json={'kind': 'requests; rm -rf /'}).status_code == 400
    run.assert_not_called()
