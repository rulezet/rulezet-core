"""
ai.py — the 4 AI admin pages (Chatbot/Rule Analysis/Rule Generator/Rule
Fixer), the shared Models & Security page, and the shared config/history
API every one of those pages calls. See
~/Documents/Rulezet/IA-Integration-plan/AI_05_UI_UX_SPEC.md.

Per-feature trigger routes (e.g. rule analysis regeneration) are NOT here —
they live with the feature they act on (the generic POST /jobs/create, or
the rule-detail page's own routes) per AI_00 §1's "brain vs. action" split.
"""

import datetime

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.core.db_class.db import AIAgentConfig, AIExecutionLog, AIGeneration, AIModelConfig, InstanceConfig
from app.core.utils.activity_log import log_activity
from app.features.ai.ai_core import get_default_ollama_model, get_ollama_url, is_local_ollama_url

ai_blueprint = Blueprint('ai', __name__, template_folder='templates')

_KNOWN_AGENT_KEYS = {'chatbot', 'rule_analysis', 'rule_generator', 'rule_fixer', 'bundle_analysis'}


@ai_blueprint.before_request
def _require_admin():
    if not current_user.is_authenticated:
        return redirect(url_for('account.login'))
    # Full AI control (config, models, execution logs, moderation) — the
    # "AI Manager" role, in addition to real admins. "AI Operator" (ai.use
    # only) does NOT reach this section, see app/features/roles/roles_core.py.
    if not (current_user.is_admin() or current_user.has_permission('ai.manage')):
        abort(403)


# ─── Pages ───────────────────────────────────────────────────────────────────

@ai_blueprint.route('/admin/chatbot', methods=['GET'])
def admin_chatbot():
    return render_template('ai/admin_chatbot.html')


@ai_blueprint.route('/admin/rule-analysis', methods=['GET'])
def admin_rule_analysis():
    return render_template('ai/admin_rule_analysis.html')


@ai_blueprint.route('/admin/bundle-analysis', methods=['GET'])
def admin_bundle_analysis():
    return render_template('ai/admin_bundle_analysis.html')


@ai_blueprint.route('/admin/rule-generator', methods=['GET'])
def admin_rule_generator():
    return render_template('ai/admin_rule_generator.html')


@ai_blueprint.route('/admin/rule-fixer', methods=['GET'])
def admin_rule_fixer():
    return render_template('ai/admin_rule_fixer.html')


@ai_blueprint.route('/admin/models', methods=['GET'])
def admin_models():
    return render_template('ai/models_security.html')


@ai_blueprint.route('/admin/overview', methods=['GET'])
def admin_overview():
    return render_template('ai/admin_overview.html')


@ai_blueprint.route('/admin/how-it-works', methods=['GET'])
def admin_how_it_works():
    return render_template('ai/ai_how_it_works.html')


@ai_blueprint.route('/admin/<any(rule_analysis, rule_generator, rule_fixer, bundle_analysis):agent_key>/history/<string:uuid>', methods=['GET'])
def history_detail(agent_key, uuid):
    gen = AIGeneration.query.filter_by(agent_key=agent_key, uuid=uuid).first()
    if not gen:
        return render_template('404.html'), 404
    return render_template('ai/history_detail.html', agent_key=agent_key, gen=gen)


# ─── Per-agent config (feature status & configuration card) ─────────────────

@ai_blueprint.route('/admin/config', methods=['GET'])
def list_configs():
    """All 4 agents' configs in one call — feeds the Overview tab's
    per-feature toggle list without 4 round-trips. Includes the instance's
    global default model too, since a null default_model on an agent falls
    back to it (ai_core.py) — the Overview page needs it to show what model
    a feature is actually running, not just the raw (possibly empty) field."""
    configs = AIAgentConfig.query.filter(AIAgentConfig.agent_key.in_(_KNOWN_AGENT_KEYS)).all()
    by_key = {c.agent_key: c.to_json() for c in configs}
    return jsonify({
        'configs': [by_key.get(k) for k in sorted(_KNOWN_AGENT_KEYS) if by_key.get(k)],
        'global_default_model': get_default_ollama_model(),
    })


@ai_blueprint.route('/admin/config/<string:agent_key>', methods=['GET'])
def get_config(agent_key):
    if agent_key not in _KNOWN_AGENT_KEYS:
        return jsonify({"error": "Unknown agent key."}), 404
    cfg = AIAgentConfig.query.filter_by(agent_key=agent_key).first()
    if not cfg:
        return jsonify({"error": "Not configured yet."}), 404
    return jsonify(cfg.to_json())


@ai_blueprint.route('/admin/config/<string:agent_key>', methods=['POST'])
def save_config(agent_key):
    if agent_key not in _KNOWN_AGENT_KEYS:
        return jsonify({"error": "Unknown agent key."}), 404
    cfg = AIAgentConfig.query.filter_by(agent_key=agent_key).first()
    if not cfg:
        return jsonify({"error": "Not configured yet."}), 404

    data = request.get_json(force=True) or {}
    if 'enabled' in data:
        cfg.enabled = bool(data['enabled'])
    if 'default_model' in data:
        cfg.default_model = (data['default_model'] or None)
    if 'timeout_s' in data and data['timeout_s']:
        cfg.timeout_s = max(1, int(data['timeout_s']))
    if 'num_predict' in data and data['num_predict']:
        cfg.num_predict = max(1, int(data['num_predict']))
    if 'max_per_hour' in data and cfg.max_per_hour is not None:
        # Only agents that already have rate limiting (max_per_hour is not
        # NULL) can have it tuned — rule_analysis (batch/admin-triggered)
        # has no per-user limit by design (AI_00 §4.1) and stays that way.
        raw = data['max_per_hour']
        cfg.max_per_hour = max(0, int(raw)) if raw not in (None, '') else cfg.max_per_hour

    cfg.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()
    log_activity('ai.config_update', f'Updated AI agent config for "{agent_key}"',
                 target_type='ai_agent_config', target_id=cfg.id, is_public=False)
    return jsonify({"success": True, "config": cfg.to_json()})


# ─── Mascot display toggle (cosmetic only — never touches agent.enabled) ────
# Site-wide: whether Rulezy's avatar renders anywhere at all (chatbot, rule
# list filter, thinking-steps badges, 404, home...). Independent of whether
# the underlying AI agents are enabled — this only hides the character.

@ai_blueprint.route('/admin/mascot_toggle', methods=['POST'])
def mascot_toggle():
    data = request.get_json(force=True) or {}
    cfg = InstanceConfig.query.first()
    if not cfg:
        return jsonify({"error": "Instance not configured yet."}), 404
    cfg.mascot_enabled = bool(data.get('mascot_enabled'))
    db.session.commit()
    log_activity('ai.mascot_toggle',
                 f'{"Enabled" if cfg.mascot_enabled else "Disabled"} Rulezy mascot display',
                 target_type='instance_config', target_id=cfg.id, is_public=False)
    return jsonify({'success': True, 'mascot_enabled': cfg.mascot_enabled})


# ─── Ollama server (Models & Security page) ──────────────────────────────────
# Which Ollama every agent talks to. Stored on InstanceConfig; an empty field
# falls back to config.py's OLLAMA_URL / OLLAMA_MODEL. Pointing at a remote
# host (e.g. a shared GPU box) needs the explicit remote_allowed opt-in —
# otherwise ai_core's locality guard keeps refusing it.

def _validate_ollama_url(raw):
    from urllib.parse import urlparse

    url = (raw or '').strip().rstrip('/')
    if not url:
        return None, None
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return None, "Ollama URL must look like http://host:11434."
    return url, None


def _ollama_settings_json():
    from app.features.ai.ai_core import get_ollama_settings

    cfg = InstanceConfig.query.first()
    effective = get_ollama_settings()
    return {
        'ollama_url':            cfg.ollama_url if cfg else None,
        'ollama_default_model':  cfg.ollama_default_model if cfg else None,
        'ollama_remote_allowed': bool(cfg.ollama_remote_allowed) if cfg else False,
        'effective':             effective,
        'config_fallback': {
            'url':           current_app.config.get('OLLAMA_URL'),
            'default_model': current_app.config.get('OLLAMA_MODEL'),
        },
    }


@ai_blueprint.route('/admin/ollama_settings', methods=['GET'])
def get_ollama_server_settings():
    return jsonify(_ollama_settings_json())


@ai_blueprint.route('/admin/ollama_settings', methods=['POST'])
def save_ollama_server_settings():
    cfg = InstanceConfig.query.first()
    if not cfg:
        return jsonify({"error": "Instance not configured yet."}), 404

    data = request.get_json(force=True) or {}
    url, err = _validate_ollama_url(data.get('ollama_url'))
    if err:
        return jsonify({"error": err}), 400
    remote_allowed = bool(data.get('ollama_remote_allowed'))
    if url and not is_local_ollama_url(url) and not remote_allowed:
        return jsonify({"error": "This is a remote server — tick \"Allow remote server\" to confirm "
                                 "rule/user content may be sent to it."}), 400

    cfg.ollama_url            = url
    cfg.ollama_default_model  = (data.get('ollama_default_model') or '').strip() or None
    cfg.ollama_remote_allowed = remote_allowed
    db.session.commit()
    log_activity('ai.ollama_settings_update',
                 f'Ollama server set to {url or "config default"}'
                 f'{" (remote allowed)" if remote_allowed else ""}',
                 target_type='instance_config', target_id=cfg.id, is_public=False)
    return jsonify({'success': True, **_ollama_settings_json()})


@ai_blueprint.route('/admin/ollama_settings/test', methods=['POST'])
def test_ollama_server_settings():
    """Reach a candidate URL's /api/tags before saving it. Same rule as the
    save: a remote host is only contacted when remote is explicitly allowed."""
    import requests as http_requests

    data = request.get_json(force=True) or {}
    url, err = _validate_ollama_url(data.get('ollama_url'))
    if err:
        return jsonify({"error": err}), 400
    url = url or get_ollama_url()
    if not is_local_ollama_url(url) and not data.get('ollama_remote_allowed'):
        return jsonify({"error": "Remote server — tick \"Allow remote server\" first."}), 400

    try:
        resp = http_requests.get(f"{url}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m.get('name') for m in resp.json().get('models', []) if m.get('name')]
    except (http_requests.RequestException, ValueError) as e:
        return jsonify({"success": False, "error": f"Could not reach Ollama at {url}: {e}"}), 502
    return jsonify({'success': True, 'url': url, 'models': sorted(models)})


# ─── Shared model allowlist (Models & Security page) ─────────────────────────

def _sync_models_from_ollama():
    """Idempotent upsert of AIModelConfig rows from Ollama's own /api/tags —
    newly discovered models are added enabled by default; never removes a
    row for a model that's since been removed from Ollama (an admin's
    explicit disable of a since-uninstalled model should survive)."""
    from app.features.ai.ai_core import AgentConnectionError, OllamaClient
    from flask import current_app

    client = OllamaClient(
        base_url=get_ollama_url(),
        model='', timeout=5,
    )
    names = client.list_models()
    added = 0
    for name in names:
        if not AIModelConfig.query.filter_by(model_name=name).first():
            db.session.add(AIModelConfig(model_name=name, is_enabled=True))
            added += 1
    db.session.commit()
    return added


@ai_blueprint.route('/admin/models/list', methods=['GET'])
def models_list():
    from app.features.ai.ai_core import AgentConnectionError

    # Lazy first-sync — nothing to show on a fresh install otherwise, and
    # nothing forces an admin to remember to click "sync" before ever
    # seeing a model in any of the 4 pages' dropdowns.
    if AIModelConfig.query.count() == 0:
        try:
            _sync_models_from_ollama()
        except AgentConnectionError:
            pass

    # Flag which allowlisted models the *current* Ollama server actually has —
    # rows are never deleted on sync, so after switching servers the list
    # still holds the old server's models. None = server unreachable, unknown.
    from app.features.ai.ai_core import OllamaClient
    try:
        live = set(OllamaClient(base_url=get_ollama_url(), model='', timeout=5).list_models())
    except AgentConnectionError:
        live = None

    models = AIModelConfig.query.order_by(AIModelConfig.model_name).all()
    rows = []
    for m in models:
        row = m.to_json()
        row['available'] = None if live is None else m.model_name in live
        rows.append(row)
    return jsonify({'models': rows, 'server_reachable': live is not None})


@ai_blueprint.route('/admin/models/sync', methods=['POST'])
def models_sync():
    from app.features.ai.ai_core import AgentConnectionError

    try:
        added = _sync_models_from_ollama()
    except AgentConnectionError as e:
        return jsonify({"error": str(e)}), 502

    log_activity('ai.models_sync', f'Synced model allowlist from Ollama ({added} new)',
                 target_type='ai_model_config', is_public=False)
    models = AIModelConfig.query.order_by(AIModelConfig.model_name).all()
    return jsonify({'success': True, 'added': added, 'models': [m.to_json() for m in models]})


@ai_blueprint.route('/admin/models/<int:model_id>/toggle', methods=['POST'])
def models_toggle(model_id):
    model = AIModelConfig.query.get(model_id)
    if not model:
        return jsonify({"error": "Not found."}), 404
    data = request.get_json(force=True) or {}
    model.is_enabled = bool(data.get('is_enabled'))
    db.session.commit()
    log_activity('ai.model_toggle',
                 f'{"Enabled" if model.is_enabled else "Disabled"} model "{model.model_name}"',
                 target_type='ai_model_config', target_id=model.id, is_public=False)
    return jsonify({'success': True, 'model': model.to_json()})


# ─── Cross-agent execution log (Models & Security page) ─────────────────────

@ai_blueprint.route('/admin/execution_log/data', methods=['GET'])
def execution_log_data():
    page     = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    search   = (request.args.get('search') or '').strip()
    agent_filter = request.args.get('agent_key') or None
    sort     = request.args.get('sort') or 'created_at'
    direction = request.args.get('dir') or 'desc'

    q = AIExecutionLog.query
    if agent_filter:
        q = q.filter(AIExecutionLog.agent_key == agent_filter)
    if search:
        q = q.filter(AIExecutionLog.input_summary.ilike(f"%{search}%"))

    sort_col = {
        'created_at': AIExecutionLog.created_at,
        'agent_key':  AIExecutionLog.agent_key,
        'status':     AIExecutionLog.status,
        'latency_ms': AIExecutionLog.latency_ms,
    }.get(sort, AIExecutionLog.created_at)
    q = q.order_by(sort_col.desc() if direction == 'desc' else sort_col.asc())

    pagination = q.paginate(page=page, per_page=per_page, max_per_page=100)
    items = []
    for entry in pagination.items:
        row = entry.to_json()
        row['username'] = (
            (f"{entry.user.first_name} {entry.user.last_name}".strip() or entry.user.email)
            if entry.user else None
        )
        items.append(row)
    return jsonify({'items': items, 'total': pagination.total, 'total_pages': pagination.pages})


# ─── Per-agent history (AIGeneration) — Rule Analysis/Generator/Fixer ────────

@ai_blueprint.route('/admin/history/<string:agent_key>/data', methods=['GET'])
def history_data(agent_key):
    if agent_key not in _KNOWN_AGENT_KEYS or agent_key == 'chatbot':
        # Chatbot keeps its own existing conversation list/API (AI_05 §7.4) —
        # this generic AIGeneration-backed endpoint doesn't apply to it.
        return jsonify({"error": "Unknown agent key."}), 404

    page     = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    search   = (request.args.get('search') or '').strip()
    sort     = request.args.get('sort') or 'created_at'
    direction = request.args.get('dir') or 'desc'

    q = AIGeneration.query.filter_by(agent_key=agent_key)
    if search:
        q = q.filter(AIGeneration.model.ilike(f"%{search}%"))

    sort_col = {
        'created_at': AIGeneration.created_at,
        'model':      AIGeneration.model,
    }.get(sort, AIGeneration.created_at)
    q = q.order_by(sort_col.desc() if direction == 'desc' else sort_col.asc())

    pagination = q.paginate(page=page, per_page=per_page, max_per_page=100)
    items = []
    for gen in pagination.items:
        row = gen.to_json()
        row['rule_id']    = gen.rule_id
        row['rule_title'] = gen.rule.title if gen.rule else None
        row['bundle_title'] = gen.bundle.name if gen.bundle else None
        row['verdict_label'] = (gen.meta or {}).get('verdict_label')
        # Rows written before failures were recorded have no status — they
        # were only ever kept on success.
        row['status']     = (gen.meta or {}).get('status') or 'success'
        row['error']      = (gen.meta or {}).get('error')
        row['username']   = (
            (f"{gen.user.first_name} {gen.user.last_name}".strip() or gen.user.email)
            if gen.user else None
        )
        items.append(row)
    return jsonify({'items': items, 'total': pagination.total, 'total_pages': pagination.pages})


@ai_blueprint.route('/admin/history/<string:agent_key>/bulk', methods=['POST'])
def history_bulk(agent_key):
    if agent_key not in _KNOWN_AGENT_KEYS or agent_key == 'chatbot':
        return jsonify({"error": "Unknown agent key."}), 404

    data = request.get_json(force=True) or {}
    if data.get('action') != 'delete':
        return jsonify({"error": "Unknown bulk action."}), 400

    ids = data.get('ids')
    q = AIGeneration.query.filter_by(agent_key=agent_key)
    if ids != 'ALL':
        if not ids:
            return jsonify({"error": "No ids given."}), 400
        q = q.filter(AIGeneration.id.in_(ids))

    deleted = q.delete(synchronize_session=False)
    db.session.commit()
    log_activity('ai.history_bulk_delete', f'Deleted {deleted} "{agent_key}" history entr(y/ies)',
                 target_type='ai_generation', is_public=False)
    return jsonify({'success': True, 'deleted': deleted})


@ai_blueprint.route('/admin/history/<string:agent_key>/toggle_visibility/<int:gen_id>', methods=['POST'])
def history_toggle_visibility(agent_key, gen_id):
    if agent_key not in _KNOWN_AGENT_KEYS or agent_key == 'chatbot':
        return jsonify({"error": "Unknown agent key."}), 404
    gen = AIGeneration.query.filter_by(id=gen_id, agent_key=agent_key).first()
    if not gen:
        return jsonify({"error": "Not found."}), 404
    data = request.get_json(force=True) or {}
    gen.is_public = bool(data.get('is_public'))
    db.session.commit()
    return jsonify({'success': True, 'entry': gen.to_json()})


# ─── System status (CPU/RAM/Ollama) — "is now a good time to run this?" ──────
# Answers the question every admin actually has before clicking "Generate":
# is the box under enough load that this is going to be slow/fail? Not a
# precise capacity-planning tool — a fast, honest snapshot.

def _get_ollama_loaded_models():
    """Ollama's own /api/ps — which models are currently resident in memory,
    how big, and when they'll auto-unload. Returns (reachable, models)."""
    import requests as http_requests

    base = get_ollama_url()
    try:
        resp = http_requests.get(f"{base}/api/ps", timeout=3)
        resp.raise_for_status()
    except http_requests.RequestException:
        return False, []

    models = []
    for m in resp.json().get('models', []):
        models.append({
            'name':       m.get('name') or m.get('model'),
            'size_gb':    round((m.get('size') or 0) / (1024 ** 3), 2),
            'expires_at': m.get('expires_at'),
            'gpu':        bool(m.get('size_vram')),
        })
    return True, models


@ai_blueprint.route('/admin/system_status', methods=['GET'])
def system_status():
    import psutil

    # interval=0.2 blocks briefly for a real (not cumulative-since-boot)
    # reading — acceptable for an admin dashboard poll, not a hot path.
    cpu_percent = psutil.cpu_percent(interval=0.2)
    vmem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    ollama_reachable, loaded_models = _get_ollama_loaded_models()

    available_gb = round(vmem.available / (1024 ** 3), 2)
    # A remote Ollama loads models into its own RAM, not this box's — local
    # memory pressure says nothing about whether a model will fit there.
    ollama_remote = not is_local_ollama_url(get_ollama_url())
    if not ollama_reachable:
        level = 'critical'
    elif ollama_remote:
        level = 'ok'
    elif available_gb < 2:
        level = 'critical'
    elif available_gb < 6 or swap.percent > 60:
        level = 'warning'
    else:
        level = 'ok'

    try:
        load_avg = list(psutil.getloadavg())
    except (AttributeError, OSError):
        load_avg = None

    return jsonify({
        'level': level,
        'cpu_percent': cpu_percent,
        'cpu_count': psutil.cpu_count(),
        'load_avg': load_avg,
        'memory': {
            'total_gb':     round(vmem.total / (1024 ** 3), 2),
            'used_gb':      round(vmem.used / (1024 ** 3), 2),
            'available_gb': available_gb,
            'percent':      vmem.percent,
        },
        'swap': {
            'total_gb': round(swap.total / (1024 ** 3), 2),
            'used_gb':  round(swap.used / (1024 ** 3), 2),
            'percent':  swap.percent,
        },
        'ollama_reachable': ollama_reachable,
        'ollama_remote': ollama_remote,
        'loaded_models': loaded_models,
    })


@ai_blueprint.route('/admin/system_status/unload', methods=['POST'])
def system_status_unload():
    """Force-unload one model from Ollama's memory right now, instead of
    waiting out its keep_alive — the direct lever for "free up RAM before
    running something bigger" that §RAM-pressure findings this session
    called for."""
    import requests as http_requests

    data = request.get_json(force=True) or {}
    model_name = (data.get('model') or '').strip()
    if not model_name:
        return jsonify({"error": "model is required."}), 400

    base = get_ollama_url()
    try:
        resp = http_requests.post(
            f"{base}/api/generate",
            json={"model": model_name, "keep_alive": 0},
            timeout=10,
        )
        resp.raise_for_status()
    except http_requests.RequestException as e:
        return jsonify({"error": str(e)}), 502

    log_activity('ai.model_unload', f'Unloaded model "{model_name}" from memory', is_public=False)
    return jsonify({"success": True})
