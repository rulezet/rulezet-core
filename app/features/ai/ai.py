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


# ─── AI providers (Models & Security page) ───────────────────────────────────
# Every backend an admin registered — Ollama (local/remote), Claude, ChatGPT,
# internal OpenAI-compatible servers. Exactly one is active; every agent
# goes through it (ai_core.get_active_provider). Security rules:
#  - writes are real-admin only (they hold API keys and decide where rule
#    content is sent), not just the "AI Manager" role;
#  - the API key is write-only: encrypted at rest, never returned (only a
#    ••••last4 hint), never logged;
#  - changing a provider's URL drops its stored key unless a new one is given
#    in the same request — a key can't be silently redirected to another host;
#  - a non-local endpoint needs explicit consent (remote_allowed), always
#    true for a cloud API, before it can be activated or tested.

from app.core.db_class.db import AIProvider
from app.features.ai.ai_core import PROVIDER_KINDS, ProviderConfig, decrypt_secret, encrypt_secret


def _require_real_admin():
    if not current_user.is_admin():
        return jsonify({"error": "Only administrators can manage AI providers and their API keys."}), 403
    return None


def _validate_provider_url(raw, kind):
    from urllib.parse import urlparse

    url = (raw or '').strip().rstrip('/') or PROVIDER_KINDS[kind]['default_url']
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return None, "The URL must look like https://host[:port][/path]."
    if parsed.username or parsed.password:
        return None, "Don't put credentials in the URL — use the API key field."
    if parsed.scheme == 'http' and PROVIDER_KINDS[kind]['cloud']:
        return None, "A cloud API must be reached over https://."
    # Plain http to a remote Ollama / internal server stays allowed (e.g. a GPU
    # box on the institution network) behind the explicit remote consent; only
    # an API key is never sent over it — see _key_over_plain_http.
    return url, None


def _key_over_plain_http(url, has_key):
    from urllib.parse import urlparse
    return has_key and urlparse(url).scheme == 'http' and not is_local_ollama_url(url)


def _provider_payload(data, existing=None):
    """Validated field dict from a create/update body, or (None, error)."""
    kind = (data.get('kind') or (existing.kind if existing else '')).strip()
    if kind not in PROVIDER_KINDS:
        return None, "Unknown provider type."
    name = (data.get('name') or (existing.name if existing else '')).strip()[:128]
    if not name:
        return None, "A name is required."
    url, err = _validate_provider_url(data.get('base_url') if 'base_url' in data
                                      else (existing.base_url if existing else ''), kind)
    if err:
        return None, err
    api_key = (data.get('api_key') or '').strip()
    if len(api_key) > 512 or any(c.isspace() for c in api_key):
        return None, "That doesn't look like a valid API key."
    import re as _re
    workspace_id = (data.get('workspace_id') if 'workspace_id' in data
                    else (existing.workspace_id if existing else '')) or ''
    workspace_id = workspace_id.strip() if kind == 'anthropic' else ''
    if workspace_id and not _re.fullmatch(r'[A-Za-z0-9_-]{1,128}', workspace_id):
        return None, "The workspace ID should look like wrkspc_… (letters, digits, _ and - only)."
    money = {}
    for key in ('monthly_budget_usd', 'price_input_per_mtok', 'price_output_per_mtok'):
        raw = data.get(key) if key in data else (getattr(existing, key) if existing else None)
        if raw in (None, ''):
            money[key] = None
            continue
        try:
            money[key] = float(raw)
        except (TypeError, ValueError):
            return None, "Budget and prices must be numbers."
        if not (0 <= money[key] <= 1_000_000):
            return None, "Budget and prices must be between 0 and 1,000,000."
    if (money['price_input_per_mtok'] is None) != (money['price_output_per_mtok'] is None):
        return None, "Give both the input and the output price, or neither."
    return {
        **money,
        'block_over_budget': bool(data.get('block_over_budget') if 'block_over_budget' in data
                                  else (existing.block_over_budget if existing else False)),
        'workspace_id': workspace_id or None,
        'kind': kind, 'name': name, 'base_url': url, 'api_key': api_key,
        'clear_api_key': bool(data.get('clear_api_key')),
        'default_model': (data.get('default_model') or '').strip()[:128] or None,
        'remote_allowed': bool(data.get('remote_allowed')),
    }, None


_PLAIN_HTTP_KEY_ERROR = ("An API key is never sent over plain http:// to a server outside this network — "
                         "use https://, or leave the key empty.")


def _is_local_kind_url(kind, url):
    return not PROVIDER_KINDS[kind]['cloud'] and is_local_ollama_url(url)


@ai_blueprint.route('/admin/providers', methods=['GET'])
def providers_list():
    rows = AIProvider.query.order_by(AIProvider.id).all()
    if not rows:
        from app.features.ai.ai_core import get_active_provider
        get_active_provider()   # seeds the default Ollama provider
        rows = AIProvider.query.order_by(AIProvider.id).all()
    items = []
    for r in rows:
        row = r.to_json()
        row['is_local'] = _is_local_kind_url(r.kind, r.base_url or PROVIDER_KINDS.get(r.kind, {}).get('default_url', ''))
        items.append(row)
    return jsonify({
        'providers': items,
        'kinds': {k: {'label': v['label'], 'default_url': v['default_url'],
                      'needs_key': v['needs_key'], 'cloud': v['cloud']} for k, v in PROVIDER_KINDS.items()},
        'can_edit': current_user.is_admin(),
    })


@ai_blueprint.route('/admin/providers/data', methods=['GET'])
def providers_data():
    """DataTable feed: search (name / URL / model), sort, type and
    last-test filters, pagination."""
    from sqlalchemy import or_

    if AIProvider.query.count() == 0:
        from app.features.ai.ai_core import get_active_provider
        get_active_provider()   # seeds the default Ollama provider

    page      = request.args.get('page', 1, type=int)
    per_page  = min(request.args.get('per_page', 10, type=int), 100)
    search    = (request.args.get('search') or '').strip()
    kind      = request.args.get('kind') or ''
    test      = request.args.get('test') or ''
    sort      = request.args.get('sort') or 'created_at'
    direction = request.args.get('dir') or 'asc'

    q = AIProvider.query
    if search:
        like = f"%{search}%"
        q = q.filter(or_(AIProvider.name.ilike(like), AIProvider.base_url.ilike(like),
                         AIProvider.default_model.ilike(like)))
    if kind in PROVIDER_KINDS:
        q = q.filter(AIProvider.kind == kind)
    if test == 'ok':
        q = q.filter(AIProvider.last_test_ok.is_(True))
    elif test == 'failed':
        q = q.filter(AIProvider.last_test_ok.is_(False))
    elif test == 'never':
        q = q.filter(AIProvider.last_test_ok.is_(None))

    sort_col = {
        'is_active':     AIProvider.is_active,
        'name':          AIProvider.name,
        'kind':          AIProvider.kind,
        'base_url':      AIProvider.base_url,
        'default_model': AIProvider.default_model,
        'monthly_budget_usd': AIProvider.monthly_budget_usd,
        'last_test_at':  AIProvider.last_test_at,
        'created_at':    AIProvider.created_at,
    }.get(sort, AIProvider.created_at)
    q = q.order_by(sort_col.desc() if direction == 'desc' else sort_col.asc(), AIProvider.id.asc())

    pagination = q.paginate(page=page, per_page=per_page, max_per_page=100)
    items = []
    for r in pagination.items:
        row = r.to_json()
        row['is_local'] = _is_local_kind_url(r.kind, r.base_url or PROVIDER_KINDS.get(r.kind, {}).get('default_url', ''))
        items.append(row)
    return jsonify({'items': items, 'total': pagination.total, 'total_pages': pagination.pages})


@ai_blueprint.route('/admin/providers', methods=['POST'])
def providers_create():
    denied = _require_real_admin()
    if denied:
        return denied
    fields, err = _provider_payload(request.get_json(force=True) or {})
    if err:
        return jsonify({"error": err}), 400
    if PROVIDER_KINDS[fields['kind']]['needs_key'] and not fields['api_key']:
        return jsonify({"error": "This provider needs an API key."}), 400
    if _key_over_plain_http(fields['base_url'], bool(fields['api_key'])):
        return jsonify({"error": _PLAIN_HTTP_KEY_ERROR}), 400
    import uuid as _uuid
    row = AIProvider(
        uuid=str(_uuid.uuid4()), name=fields['name'], kind=fields['kind'], base_url=fields['base_url'],
        api_key_enc=encrypt_secret(fields['api_key']) if fields['api_key'] else None,
        workspace_id=fields['workspace_id'],
        monthly_budget_usd=fields['monthly_budget_usd'],
        price_input_per_mtok=fields['price_input_per_mtok'],
        price_output_per_mtok=fields['price_output_per_mtok'],
        block_over_budget=fields['block_over_budget'],
        default_model=fields['default_model'], remote_allowed=fields['remote_allowed'], is_active=False,
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.session.add(row)
    db.session.commit()
    log_activity('ai.provider_create', f'Added AI provider "{row.name}" ({row.kind}, {row.base_url})',
                 target_type='ai_provider', target_id=row.id, is_public=False)
    return jsonify({'success': True, 'provider': row.to_json()})


@ai_blueprint.route('/admin/providers/<int:provider_id>', methods=['POST'])
def providers_update(provider_id):
    denied = _require_real_admin()
    if denied:
        return denied
    row = db.session.get(AIProvider, provider_id)
    if not row:
        return jsonify({"error": "Not found."}), 404
    fields, err = _provider_payload(request.get_json(force=True) or {}, existing=row)
    if err:
        return jsonify({"error": err}), 400

    key_note = ''
    target_changed = fields['base_url'] != (row.base_url or '') or fields['kind'] != row.kind
    if fields['api_key']:
        row.api_key_enc = encrypt_secret(fields['api_key'])
        key_note = ', API key replaced'
    elif fields['clear_api_key'] or (target_changed and row.api_key_enc):
        # Never let a stored key follow a provider to a different host.
        row.api_key_enc = None
        key_note = ', API key removed' + (' (URL changed — enter it again)' if target_changed else '')
    if _key_over_plain_http(fields['base_url'], bool(row.api_key_enc)):
        db.session.rollback()
        return jsonify({"error": _PLAIN_HTTP_KEY_ERROR}), 400
    if row.is_active and PROVIDER_KINDS[fields['kind']]['needs_key'] and not row.api_key_enc:
        db.session.rollback()
        return jsonify({"error": "This is the active provider — it can't be left without an API key."}), 400
    if row.is_active and not _is_local_kind_url(fields['kind'], fields['base_url']) and not fields['remote_allowed']:
        db.session.rollback()
        return jsonify({"error": "This is the active provider and it is not local — keep \"Allow sending content\" ticked, or activate another provider first."}), 400

    if target_changed or fields['api_key'] or 'removed' in key_note or fields['workspace_id'] != row.workspace_id:
        _reset_test_status(row)
    row.workspace_id = fields['workspace_id']
    row.monthly_budget_usd    = fields['monthly_budget_usd']
    row.price_input_per_mtok  = fields['price_input_per_mtok']
    row.price_output_per_mtok = fields['price_output_per_mtok']
    row.block_over_budget     = fields['block_over_budget']
    row.name, row.kind, row.base_url = fields['name'], fields['kind'], fields['base_url']
    row.default_model, row.remote_allowed = fields['default_model'], fields['remote_allowed']
    row.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()
    log_activity('ai.provider_update', f'Updated AI provider "{row.name}" ({row.kind}, {row.base_url}){key_note}',
                 target_type='ai_provider', target_id=row.id, is_public=False)
    return jsonify({'success': True, 'provider': row.to_json(),
                    'key_removed': bool(target_changed and not fields['api_key'] and 'removed' in key_note)})


@ai_blueprint.route('/admin/providers/<int:provider_id>', methods=['DELETE'])
def providers_delete(provider_id):
    denied = _require_real_admin()
    if denied:
        return denied
    row = db.session.get(AIProvider, provider_id)
    if not row:
        return jsonify({"error": "Not found."}), 404
    if row.is_active:
        return jsonify({"error": "Activate another provider before deleting the active one."}), 400
    name = row.name
    db.session.delete(row)
    db.session.commit()
    log_activity('ai.provider_delete', f'Deleted AI provider "{name}"', target_type='ai_provider',
                 target_id=provider_id, is_public=False)
    return jsonify({'success': True})


@ai_blueprint.route('/admin/providers/<int:provider_id>/activate', methods=['POST'])
def providers_activate(provider_id):
    denied = _require_real_admin()
    if denied:
        return denied
    row = db.session.get(AIProvider, provider_id)
    if not row:
        return jsonify({"error": "Not found."}), 404
    url = row.base_url or PROVIDER_KINDS[row.kind]['default_url']
    if not _is_local_kind_url(row.kind, url) and not row.remote_allowed:
        return jsonify({"error": "This provider is outside this server's network — edit it and tick "
                                 "\"Allow sending content\" first."}), 400
    if PROVIDER_KINDS[row.kind]['needs_key'] and not decrypt_secret(row.api_key_enc):
        return jsonify({"error": "This provider has no usable API key — edit it and enter the key."}), 400
    AIProvider.query.filter(AIProvider.id != row.id).update({'is_active': False}, synchronize_session=False)
    row.is_active = True
    db.session.commit()
    log_activity('ai.provider_activate', f'Active AI provider is now "{row.name}" ({row.kind})',
                 target_type='ai_provider', target_id=row.id, is_public=False)
    return jsonify({'success': True, 'provider': row.to_json()})


def _reset_test_status(row):
    row.last_test_at = row.last_test_ok = row.last_test_message = None


def _run_provider_test(provider):
    """(ok, models, error) — connects and lists the models, nothing else."""
    from app.features.ai.ai_core import AgentBusy, AgentConnectionError, make_client
    try:
        return True, make_client(provider, timeout=15).list_models(), None
    except (AgentConnectionError, AgentBusy) as e:
        return False, [], str(e)
    except Exception as e:
        current_app.logger.warning(f'AI provider test failed ({provider.kind}, {provider.url}): {type(e).__name__}')
        return False, [], f"Connection failed ({type(e).__name__})."


def _record_test(row, ok, models, error):
    row.last_test_at = datetime.datetime.now(datetime.timezone.utc)
    row.last_test_ok = ok
    row.last_test_message = (f"{len(models)} model(s) available" if ok else (error or 'Failed'))[:300]
    db.session.commit()


def _test_response(ok, models, error, row=None):
    body = {'success': ok, 'models': models} if ok else {'success': False, 'error': error}
    if row is not None:
        body['provider'] = row.to_json()
    return jsonify(body), (200 if ok else 502)


@ai_blueprint.route('/admin/providers/test', methods=['POST'])
def providers_test():
    """Connect + list models for a provider form, before or after saving.
    An empty api_key with an `id` uses the stored key — but only if the URL
    and type are unchanged, so a stored key can't be sent to a new host.
    The result is recorded on the row only when it describes the saved
    settings (same type, URL and key)."""
    denied = _require_real_admin()
    if denied:
        return denied
    data = request.get_json(force=True) or {}
    existing = db.session.get(AIProvider, int(data['id'])) if str(data.get('id') or '').isdigit() else None
    fields, err = _provider_payload(data, existing=existing)
    if err:
        return jsonify({"error": err}), 400
    if not _is_local_kind_url(fields['kind'], fields['base_url']) and not fields['remote_allowed']:
        return jsonify({"error": "Tick \"Allow sending content\" to contact a server outside this network."}), 400

    api_key = fields['api_key']
    if _key_over_plain_http(fields['base_url'], bool(api_key)):
        return jsonify({"error": _PLAIN_HTTP_KEY_ERROR}), 400
    same_target = bool(existing and existing.kind == fields['kind'] and existing.base_url == fields['base_url'])
    if not api_key and same_target:
        api_key = decrypt_secret(existing.api_key_enc)
    provider = ProviderConfig(kind=fields['kind'], url=fields['base_url'], name=fields['name'],
                              api_key=api_key or None, default_model=fields['default_model'],
                              remote_allowed=fields['remote_allowed'], workspace_id=fields['workspace_id'])
    ok, models, error = _run_provider_test(provider)
    if same_target and not fields['api_key'] and fields['workspace_id'] == existing.workspace_id:
        _record_test(existing, ok, models, error)
        return _test_response(ok, models, error, existing)
    return _test_response(ok, models, error)


@ai_blueprint.route('/admin/providers/<int:provider_id>/test', methods=['POST'])
def providers_test_saved(provider_id):
    """Test a provider exactly as saved (table "Test" button) and record it."""
    from app.features.ai.ai_core import _provider_from_row

    denied = _require_real_admin()
    if denied:
        return denied
    row = db.session.get(AIProvider, provider_id)
    if not row:
        return jsonify({"error": "Not found."}), 404
    provider = _provider_from_row(row)
    if not provider.is_local and not provider.remote_allowed:
        return jsonify({"error": "This provider is outside this server's network — edit it and tick "
                                 "\"Allow sending content\" first."}), 400
    ok, models, error = _run_provider_test(provider)
    _record_test(row, ok, models, error)
    return _test_response(ok, models, error, row)


@ai_blueprint.route('/admin/providers/<int:provider_id>/budget', methods=['GET'])
def providers_budget(provider_id):
    """This month's spending through this provider, as tracked by Rulezet
    (the providers expose no remaining-credit API), against its budget."""
    from app.features.ai.ai_core import _provider_from_row, month_spend, price_for

    row = db.session.get(AIProvider, provider_id)
    if not row:
        return jsonify({"error": "Not found."}), 404
    provider = _provider_from_row(row)
    spend = month_spend(row.id)
    budget = row.monthly_budget_usd
    remaining_pct = None
    if budget:
        remaining_pct = max(0.0, round(100 * (1 - spend['spent'] / budget), 1))
    return jsonify({
        **spend,
        'free':          provider.kind == 'ollama' and price_for(provider, row.default_model) == (0.0, 0.0),
        'priced':        price_for(provider, row.default_model) is not None,
        'budget':        budget,
        'remaining_usd': round(max(0.0, budget - spend['spent']), 4) if budget else None,
        'remaining_pct': remaining_pct,
        'blocking':      bool(row.block_over_budget),
    })


@ai_blueprint.route('/admin/providers/active/models', methods=['GET'])
def providers_active_models():
    from app.features.ai.ai_core import AgentConnectionError, list_active_models
    try:
        provider, models = list_active_models(force=bool(request.args.get('refresh')))
    except AgentConnectionError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({'provider': {'id': provider.id, 'name': provider.name, 'kind': provider.kind},
                    'models': models})


# ─── Shared model allowlist (Models & Security page) ─────────────────────────

def _sync_models_from_ollama():
    """Idempotent upsert of AIModelConfig rows from the ACTIVE provider's
    model list — newly discovered models are added enabled by default;
    never removes a row (an admin's explicit disable of a since-uninstalled
    model should survive). Name kept from the Ollama-only days."""
    from app.features.ai.ai_core import list_active_models

    _, names = list_active_models(force=True)
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
    from app.features.ai.ai_core import list_active_models
    try:
        live = set(list_active_models()[1])
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

    log_activity('ai.models_sync', f'Synced model allowlist from the active AI provider ({added} new)',
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
    from app.features.ai.ai_core import get_active_provider
    provider = get_active_provider()
    if provider.kind == 'ollama':
        ollama_reachable, loaded_models = _get_ollama_loaded_models()
    else:
        # Not an Ollama: no /api/ps to read, and pinging a cloud API every
        # few seconds would cost money — reachability shows on "Test".
        ollama_reachable, loaded_models = True, []

    available_gb = round(vmem.available / (1024 ** 3), 2)
    # A remote Ollama (or any other provider) loads models into its own RAM,
    # not this box's — local memory pressure says nothing about it.
    ollama_remote = provider.kind != 'ollama' or not provider.is_local
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
        'provider': {'name': provider.name, 'kind': provider.kind},
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

    from app.features.ai.ai_core import get_active_provider
    if get_active_provider().kind != 'ollama':
        return jsonify({"error": "The active AI provider is not an Ollama server."}), 400
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
