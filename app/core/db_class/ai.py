"""AI features: chatbot conversations, providers, agents, generations and analysis requests.
"""
from app import db
import datetime
import uuid as _uuid_mod


########################################
#   Chatbot Conversation History       #
########################################

class ChatbotConversation(db.Model):
    """One chatbot widget session — groups every message exchanged while it was open
    so admins can review, on /chatbot/admin/conversations, what the assistant was
    asked and how it responded."""
    __tablename__ = 'chatbot_conversation'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid            = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    started_at      = db.Column(db.DateTime, nullable=False,
                                default=lambda: datetime.datetime.now(datetime.timezone.utc))
    last_message_at = db.Column(db.DateTime, nullable=False,
                                default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    message_count   = db.Column(db.Integer, nullable=False, default=0)
    # How many assistant replies in this conversation had success=False (a
    # syntax error, an unresolvable format, etc.) — denormalized so the list
    # view can flag problem conversations without an extra query per row.
    error_count     = db.Column(db.Integer, nullable=False, default=0, index=True)

    user     = db.relationship('User', backref=db.backref('chatbot_conversations', lazy='dynamic'))
    messages = db.relationship('ChatbotMessage', backref='conversation', lazy='dynamic',
                               order_by='ChatbotMessage.id', cascade='all, delete-orphan')

    def to_json(self):
        username = "Unknown"
        avatar = None
        try:
            if self.user:
                username = self.user.get_username()
                avatar = self.user.get_avatar_url()
        except Exception:
            pass
        return {
            "id":              self.id,
            "uuid":            self.uuid,
            "user_id":         self.user_id,
            "username":        username,
            "avatar":          avatar,
            "started_at":      self.started_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
            "last_message_at": self.last_message_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
            "message_count":   self.message_count,
            "error_count":     self.error_count,
        }


class ChatbotMessage(db.Model):
    """Single message row — one per user message AND one per assistant reply,
    so a full back-and-forth transcript can be replayed in order."""
    __tablename__ = 'chatbot_message'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('chatbot_conversation.id', ondelete='CASCADE'),
                                nullable=False, index=True)

    role    = db.Column(db.String(16), nullable=False)   # "user" | "assistant"
    content = db.Column(db.Text, nullable=False)

    # assistant-only: which action the model (or a deterministic shortcut) picked,
    # and whether it succeeded — NULL for user messages
    action  = db.Column(db.String(32), nullable=True)
    success = db.Column(db.Boolean, nullable=True)

    # whatever extra payload the reply carried — redirect/link/links
    meta = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)

    def to_json(self):
        return {
            "id":         self.id,
            "role":       self.role,
            "content":    self.content,
            "action":     self.action,
            "success":    self.success,
            "meta":       self.meta,
            "created_at": self.created_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
        }


# ─── AI foundation (app/features/ai/) ───────────────────────────────────────
# Shared across every AI agent (chatbot, rule analysis, rule generator, rule
# fixer) — see ~/Documents/Rulezet/IA-Integration-plan/AI_00_FOUNDATION.md §5.

class AIAgentConfig(db.Model):
    """One row per agent key. The admin kill-switch + tunables live here,
    not scattered across InstanceConfig booleans."""
    __tablename__ = 'ai_agent_config'

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    agent_key     = db.Column(db.String(50), unique=True, nullable=False, index=True)
    enabled       = db.Column(db.Boolean, nullable=False, default=True)
    default_model = db.Column(db.String(128), nullable=True)  # falls back to global OLLAMA_MODEL if null
    max_per_hour  = db.Column(db.Integer, nullable=True)       # null = no per-user rate limit (batch agents)
    timeout_s     = db.Column(db.Integer, nullable=False, default=120)
    num_predict   = db.Column(db.Integer, nullable=False, default=2048)
    updated_at    = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
                               onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    def to_json(self):
        return {
            'id':            self.id,
            'agent_key':     self.agent_key,
            'enabled':       self.enabled,
            'default_model': self.default_model,
            'max_per_hour':  self.max_per_hour,
            'timeout_s':     self.timeout_s,
            'num_predict':   self.num_predict,
            'updated_at':    self.updated_at.isoformat() if self.updated_at else None,
        }


class AIModelConfig(db.Model):
    """Global model allowlist, synced from Ollama's own /api/tags — shared
    across all agents, a model disabled here is unavailable everywhere."""
    __tablename__ = 'ai_model_config'

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model_name = db.Column(db.String(128), unique=True, nullable=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    added_at   = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    def to_json(self):
        return {
            'id':         self.id,
            'model_name': self.model_name,
            'is_enabled': self.is_enabled,
            'added_at':   self.added_at.isoformat() if self.added_at else None,
        }


class AIProvider(db.Model):
    """One AI backend an admin registered on AI admin → Models & Security:
    a local or remote Ollama, Claude (Anthropic API), ChatGPT (OpenAI API),
    or any internal OpenAI-compatible server (vLLM, LM Studio, LiteLLM…).
    Exactly one is active — every agent goes through it (ai_core.py
    get_active_provider). The first one is seeded from the old Ollama
    settings, so an instance that never touches this keeps running on
    Ollama. The API key is stored encrypted (ai_core.encrypt_secret)."""
    __tablename__ = 'ai_provider'

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid           = db.Column(db.String(36), unique=True, nullable=False, index=True)
    name           = db.Column(db.String(128), nullable=False)
    kind           = db.Column(db.String(32), nullable=False)   # ollama | anthropic | openai | openai_compatible
    base_url       = db.Column(db.String(512), nullable=True)
    api_key_enc    = db.Column(db.Text, nullable=True)
    # Claude only: sent as the anthropic-workspace-id header, needed when the
    # API key is organization-level rather than scoped to one workspace.
    workspace_id   = db.Column(db.String(128), nullable=True)
    default_model  = db.Column(db.String(128), nullable=True)
    # Explicit admin consent that rule/user content may be sent to this
    # endpoint when it is not on the local network (cloud APIs always are).
    remote_allowed = db.Column(db.Boolean, nullable=False, default=False)
    is_active      = db.Column(db.Boolean, nullable=False, default=False, index=True)
    # Spending tracked by Rulezet itself (AIExecutionLog.cost_usd) against a
    # monthly budget — the providers expose no "remaining credit" API. Prices
    # in USD per million tokens; empty = built-in Claude price list
    # (ai_core.CLAUDE_PRICES), unknown for other providers.
    monthly_budget_usd     = db.Column(db.Float, nullable=True)
    price_input_per_mtok   = db.Column(db.Float, nullable=True)
    price_output_per_mtok  = db.Column(db.Float, nullable=True)
    block_over_budget      = db.Column(db.Boolean, nullable=False, default=False)
    # Last "Test connection" of the SAVED settings — reset whenever the type,
    # URL or key change, so a green badge always describes what's stored.
    last_test_at      = db.Column(db.DateTime, nullable=True)
    last_test_ok      = db.Column(db.Boolean, nullable=True)
    last_test_message = db.Column(db.String(300), nullable=True)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at     = db.Column(db.DateTime, nullable=True)

    def to_json(self):
        from app.features.ai.ai_core import describe_secret
        return {
            'id':             self.id,
            'uuid':           self.uuid,
            'name':           self.name,
            'kind':           self.kind,
            'base_url':       self.base_url,
            'has_api_key':    bool(self.api_key_enc),
            'api_key_hint':   describe_secret(self.api_key_enc),
            'workspace_id':   self.workspace_id,
            'monthly_budget_usd':    self.monthly_budget_usd,
            'price_input_per_mtok':  self.price_input_per_mtok,
            'price_output_per_mtok': self.price_output_per_mtok,
            'block_over_budget':     bool(self.block_over_budget),
            'default_model':  self.default_model,
            'remote_allowed': self.remote_allowed,
            'is_active':      self.is_active,
            'last_test_at':      self.last_test_at.isoformat() if self.last_test_at else None,
            'last_test_ok':      self.last_test_ok,
            'last_test_message': self.last_test_message,
            'created_at':     self.created_at.isoformat() if self.created_at else None,
            'updated_at':     self.updated_at.isoformat() if self.updated_at else None,
        }


class AIExecutionLog(db.Model):
    """One row per agent invocation, every agent, success or failure — the
    unified history + security-visibility surface the admin AI hub reads
    from. Chatbot additionally writes its own ChatbotMessage row per turn;
    this row is the lightweight cross-agent summary, not a replacement."""
    __tablename__ = 'ai_execution_log'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid            = db.Column(db.String(36), unique=True, nullable=False, index=True)
    agent_key       = db.Column(db.String(50), nullable=False, index=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    rule_id         = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=True, index=True)
    input_summary   = db.Column(db.String(300), nullable=True)  # short, truncated — never full rule content
    content         = db.Column(db.Text, nullable=True)          # the agent's output (report / rule / fix / reply)
    model_used      = db.Column(db.String(128), nullable=True)
    status          = db.Column(db.String(20), nullable=False)   # success | failed | rate_limited | disabled | busy | budget
    error_message   = db.Column(db.Text, nullable=True)
    is_public       = db.Column(db.Boolean, nullable=False, default=True)  # admin moderation lever
    flagged_reason  = db.Column(db.String(200), nullable=True)   # e.g. 'possible_prompt_injection'
    iteration_count = db.Column(db.Integer, nullable=True)       # for the repair loop (rule generator/fixer)
    latency_ms      = db.Column(db.Integer, nullable=True)
    # Which AI provider ran it and what it consumed (all calls of the run
    # summed) — feeds the per-provider monthly budget on Models & Security.
    provider_id     = db.Column(db.Integer, db.ForeignKey('ai_provider.id', ondelete='SET NULL'), nullable=True, index=True)
    input_tokens    = db.Column(db.Integer, nullable=True)
    output_tokens   = db.Column(db.Integer, nullable=True)
    cost_usd        = db.Column(db.Float, nullable=True)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)

    user = db.relationship('User', foreign_keys=[user_id])
    rule = db.relationship('Rule', foreign_keys=[rule_id])

    def to_json(self):
        return {
            'id':              self.id,
            'uuid':            self.uuid,
            'agent_key':       self.agent_key,
            'user_id':         self.user_id,
            'rule_id':         self.rule_id,
            'input_summary':   self.input_summary,
            'content':         self.content if self.is_public else None,
            'model_used':      self.model_used,
            'status':          self.status,
            'error_message':   self.error_message,
            'is_public':       self.is_public,
            'flagged_reason':  self.flagged_reason,
            'iteration_count': self.iteration_count,
            'latency_ms':      self.latency_ms,
            'input_tokens':    self.input_tokens,
            'output_tokens':   self.output_tokens,
            'cost_usd':        self.cost_usd,
            'created_at':      self.created_at.isoformat() if self.created_at else None,
        }


class AIAnalysisRequest(db.Model):
    """A user's request for an AI analysis of a rule or a bundle, made from
    its AI Analysis section by someone who can't launch one (not an admin /
    AI Operator for a rule, not an admin / AI Manager for a bundle). AI
    managers review them on the Rule / Bundle Analysis admin pages — an
    accepted request queues the analysis job (see ai_request_core)."""
    __tablename__ = 'ai_analysis_request'

    id            = db.Column(db.Integer, primary_key=True)
    uuid          = db.Column(db.String(36), unique=True, nullable=False, index=True,
                              default=lambda: str(_uuid_mod.uuid4()))
    target_type   = db.Column(db.String(10), nullable=False, index=True)     # rule | bundle
    rule_id       = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=True, index=True)
    bundle_id     = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=True, index=True)
    script        = db.Column(db.String(20), nullable=False, default='standard')  # standard | deep (rule), full (bundle)
    message       = db.Column(db.Text, nullable=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    status        = db.Column(db.String(16), nullable=False, default='pending', index=True)  # pending | accepted | rejected
    created_at    = db.Column(db.DateTime, nullable=False, index=True,
                              default=lambda: datetime.datetime.now(datetime.timezone.utc))
    decided_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    decided_at    = db.Column(db.DateTime, nullable=True)
    decision_note = db.Column(db.Text, nullable=True)
    job_uuid      = db.Column(db.String(36), nullable=True)
    # The exact input asked about (issues #88 / #89): the rule's content when the request was made and
    # its hash — the job analyses THIS, never a newer version (ai_provenance.py).
    input_content    = db.Column(db.Text, nullable=True)
    content_hash     = db.Column(db.String(64), nullable=True, index=True)
    # Execution, separate from the approval (status): not_started | queued | running | completed | failed
    execution_status = db.Column(db.String(16), nullable=False, default='not_started', server_default='not_started')
    executed_at      = db.Column(db.DateTime, nullable=True)
    generation_id    = db.Column(db.Integer, db.ForeignKey('ai_generation.id', ondelete='SET NULL', use_alter=True,
                                                       name='fk_ai_analysis_request_generation'), nullable=True)

    user       = db.relationship('User', foreign_keys=[user_id])
    decided_by = db.relationship('User', foreign_keys=[decided_by_id])
    rule       = db.relationship('Rule', foreign_keys=[rule_id])
    bundle     = db.relationship('Bundle', foreign_keys=[bundle_id])

    def to_json(self):
        name = lambda u: (f"{u.first_name} {u.last_name}".strip() or u.email) if u else None
        target = self.rule if self.target_type == 'rule' else self.bundle
        return {
            'id': self.id,
            'uuid': self.uuid,
            'target_type': self.target_type,
            'target_id': self.rule_id if self.target_type == 'rule' else self.bundle_id,
            'target_title': (target.title if self.target_type == 'rule' else target.name) if target else None,
            'target_format': target.format if self.target_type == 'rule' and target else None,
            'target_url': (f"/rule/detail_rule/{self.rule_id}/ai_analysis" if self.target_type == 'rule'
                           else f"/bundle/detail/{self.bundle_id}#ai"),
            'script': self.script,
            'message': self.message,
            'user_id': self.user_id,
            'user_name': name(self.user),
            'user_avatar': self.user.get_avatar_url() if self.user else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'decided_by_id': self.decided_by_id,
            'decided_by_name': name(self.decided_by),
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'decision_note': self.decision_note,
            'job_uuid': self.job_uuid,
            'content_hash': self.content_hash,
            'execution_status': self.execution_status,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'generation_id': self.generation_id,
        }


class AIGeneration(db.Model):
    """Display history for agents whose output is meant to be browsed/
    regenerated/compared per rule (rule analysis reports now, generator/
    fixer output later — see AI_02_RULE_ANALYSIS.md §3). Distinct from
    AIExecutionLog: this is the actual kept output, one row per generation,
    forever; AIExecutionLog is the lightweight per-call audit trail written
    alongside it on every run."""
    __tablename__ = 'ai_generation'

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid       = db.Column(db.String(36), unique=True, nullable=False, index=True)
    agent_key  = db.Column(db.String(50), nullable=False, index=True)
    # Nullable: a rule_fixer generation is attached to an InvalidRuleModel row
    # (not a Rule) until a human accepts it and it gets imported — there's no
    # rule_id yet at the time it's recorded.
    rule_id    = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=True, index=True)
    # Set for bundle-scoped agents (bundle_analysis) — a report about a whole
    # bundle, not one rule. Deleted with the bundle.
    bundle_id  = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=True, index=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    content    = db.Column(db.Text, nullable=False)
    # Structured extras alongside `content` (e.g. rule_analysis's severity/
    # confidence/recommendations/etc — see rule_analysis_agent.py) — optional,
    # agent-specific, never required so other agents and old rows are unaffected.
    meta       = db.Column(db.JSON, nullable=True)
    model      = db.Column(db.String(128), nullable=True)
    is_public  = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    # Provenance (issue #88) — NULL on reports made before it was recorded ("not recorded", never guessed):
    # the hash of the exact rule content analysed, the request and job it came from, and who asked,
    # approved and started it. user_id stays "who the job ran as" (the approver, for a request).
    content_hash     = db.Column(db.String(64), nullable=True)
    request_id       = db.Column(db.Integer, db.ForeignKey('ai_analysis_request.id', ondelete='SET NULL'), nullable=True)
    job_uuid         = db.Column(db.String(36), nullable=True)
    requested_by_id  = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    approved_by_id   = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    initiated_by_id  = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    user = db.relationship('User', foreign_keys=[user_id])
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    initiated_by = db.relationship('User', foreign_keys=[initiated_by_id])
    rule = db.relationship('Rule', foreign_keys=[rule_id])
    bundle = db.relationship('Bundle', foreign_keys=[bundle_id],
                             backref=db.backref('ai_generations', cascade='all, delete-orphan', passive_deletes=True))

    def to_json(self):
        return {
            'id':         self.id,
            'uuid':       self.uuid,
            'agent_key':  self.agent_key,
            'rule_id':    self.rule_id,
            'bundle_id':  self.bundle_id,
            'user_id':    self.user_id,
            'content':    self.content if self.is_public else None,
            'meta':       self.meta if self.is_public else None,
            'model':      self.model,
            'is_public':  self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
