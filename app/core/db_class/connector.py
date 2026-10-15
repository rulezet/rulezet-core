"""Federation: connectors to other Rulezet instances, instance registry and pull logs.
"""
from app import db
import datetime


####################
#    Connector     #
####################

class Connector(db.Model):
    """
    Generic connector between this Rulezet instance and any external source.

    The connector_type field determines the protocol adapter to use.
    Currently implemented: 'rulezet'.
    Planned: 'misp', 'opencti', 'github_advisory', …

    Every user can create their own connectors — this is not admin-only.
    A shadow_user is auto-created when the connector is first saved so that
    imported content always has a valid local user_id without breaking the
    ownership model.
    """
    __tablename__ = 'connector'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True)

    # Human-readable identity
    name        = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon        = db.Column(db.String(64), nullable=True)   # FontAwesome class e.g. 'fa-solid fa-plug'

    # Protocol adapter — keep extensible
    connector_type = db.Column(db.String(64), nullable=False, default='rulezet', index=True)

    # Remote connection
    instance_url     = db.Column(db.String(512), nullable=False)
    api_key_outbound = db.Column(db.String(512), nullable=True)   # key used to auth TO the remote

    # Ownership: per user (not admin-only)
    owner_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shadow_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # What to sync
    sync_rules   = db.Column(db.Boolean, nullable=False, default=True)
    sync_bundles = db.Column(db.Boolean, nullable=False, default=False)

    # Who owns imported content: 'shadow' = ghost user | 'self' = connector owner
    owner_mode = db.Column(db.String(16), nullable=False, default='shadow')

    # System connectors (e.g. official Rulezet) are read-only and visible to all users
    is_system = db.Column(db.Boolean, nullable=False, default=False, index=True)

    # Status
    is_active   = db.Column(db.Boolean, nullable=False, default=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)  # True after first successful pull
    last_error  = db.Column(db.Text, nullable=True)

    # Sync tracking
    last_sync_at    = db.Column(db.DateTime, nullable=True)
    rules_synced    = db.Column(db.Integer, nullable=False, default=0)
    bundles_synced  = db.Column(db.Integer, nullable=False, default=0)

    # Remote instance totals — updated on each successful connection test
    remote_rules_count   = db.Column(db.Integer, nullable=True)
    remote_bundles_count = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
                           onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    owner       = db.relationship('User', foreign_keys=[owner_id],
                                  backref=db.backref('connectors', lazy='dynamic'))
    shadow_user = db.relationship('User', foreign_keys=[shadow_user_id])

    def to_json(self):
        local_rules_count   = Rule.query.filter_by(connector_id=self.id, is_deleted=False).count()
        local_bundles_count = Bundle.query.filter_by(connector_id=self.id).count()
        return {
            'id':             self.id,
            'uuid':           self.uuid,
            'name':           self.name,
            'description':    self.description or '',
            'icon':           self.icon or 'fa-solid fa-plug',
            'connector_type': self.connector_type,
            'instance_url':   self.instance_url,
            'sync_rules':     self.sync_rules,
            'sync_bundles':   self.sync_bundles,
            'owner_mode':     self.owner_mode,
            'is_system':      self.is_system,
            'is_active':      self.is_active,
            'is_verified':    self.is_verified,
            'last_error':     self.last_error,
            'last_sync_at':   self.last_sync_at.strftime('%Y-%m-%d %H:%M') if self.last_sync_at else None,
            'rules_count':    self.remote_rules_count,
            'bundles_count':  self.remote_bundles_count,
            'local_rules_count':    local_rules_count,
            'local_bundles_count':  local_bundles_count,
            'rules_synced':   self.rules_synced,
            'bundles_synced': self.bundles_synced,
            'owner_id':       self.owner_id,
            'created_at':     self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }


##########################
#   Instance Registry    #
##########################

class InstanceConfig(db.Model):
    """Single-row: this instance's persistent UUID and telemetry settings."""
    __tablename__ = 'instance_config'
    id                = db.Column(db.Integer, primary_key=True)
    uuid              = db.Column(db.String(36), unique=True, nullable=False)
    telemetry_enabled = db.Column(db.Boolean, default=True, nullable=False)
    chatbot_enabled   = db.Column(db.Boolean, default=True, nullable=False)
    mascot_enabled    = db.Column(db.Boolean, default=True, nullable=False)
    # Instance-wide switch for every user-facing email feature (alert emails,
    # digests...). Even when on, emails only go out if SMTP is actually
    # configured — see app/core/utils/mail_status.py.
    email_enabled     = db.Column(db.Boolean, default=True, nullable=False)
    # Ollama server the AI agents talk to — set from the AI admin (Models &
    # Security). NULL falls back to config.py's OLLAMA_URL / OLLAMA_MODEL.
    # A non-local URL is refused by ai_core's locality guard unless
    # ollama_remote_allowed is explicitly turned on by an admin.
    ollama_url            = db.Column(db.String(512), nullable=True)
    ollama_default_model  = db.Column(db.String(128), nullable=True)
    ollama_remote_allowed = db.Column(db.Boolean, default=False, nullable=False)
    public_url        = db.Column(db.String(512), nullable=True)
    version           = db.Column(db.String(64), nullable=True)
    last_started_at   = db.Column(db.DateTime, nullable=True)
    created_at        = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_json(self):
        return {
            'uuid':              self.uuid,
            'telemetry_enabled': self.telemetry_enabled,
            'chatbot_enabled':   self.chatbot_enabled,
            'mascot_enabled':    self.mascot_enabled,
            'email_enabled':     self.email_enabled,
            'public_url':        self.public_url,
            'version':           self.version,
            'last_started_at':   self.last_started_at.strftime('%Y-%m-%d %H:%M') if self.last_started_at else None,
            'created_at':        self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }


class RegisteredInstance(db.Model):
    """Remote Rulezet instances that have phoned home to this instance."""
    __tablename__ = 'registered_instance'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid          = db.Column(db.String(36), unique=True, nullable=False, index=True)
    public_url    = db.Column(db.String(512), nullable=True)
    ip_address    = db.Column(db.String(45),  nullable=True)
    version       = db.Column(db.String(64),  nullable=True)
    rules_count   = db.Column(db.Integer,     nullable=True)
    bundles_count = db.Column(db.Integer,     nullable=True)
    ping_count    = db.Column(db.Integer,     default=1, nullable=False)
    first_seen    = db.Column(db.DateTime,    nullable=False)
    last_seen     = db.Column(db.DateTime,    nullable=False, index=True)

    def to_json(self):
        return {
            'uuid':          self.uuid,
            'public_url':    self.public_url,
            'ip_address':    self.ip_address,
            'version':       self.version,
            'rules_count':   self.rules_count,
            'bundles_count': self.bundles_count,
            'ping_count':    self.ping_count,
            'first_seen':    self.first_seen.strftime('%Y-%m-%d %H:%M'),
            'last_seen':     self.last_seen.strftime('%Y-%m-%d %H:%M'),
        }


class RemotePullLog(db.Model):
    """One row per pull session initiated by a remote instance against this instance's sync API.
    Logged when a remote connector fetches page 1 of /api/sync/rules."""
    __tablename__ = 'remote_pull_log'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    instance_uuid = db.Column(db.String(36),  nullable=True, index=True)
    instance_url  = db.Column(db.String(512), nullable=True)
    ip_address    = db.Column(db.String(64),  nullable=True)
    rules_total   = db.Column(db.Integer,     nullable=True)
    created_at    = db.Column(db.DateTime,    nullable=False,
                              default=datetime.datetime.utcnow, index=True)

    def to_json(self):
        return {
            'id':            self.id,
            'instance_uuid': self.instance_uuid,
            'instance_url':  self.instance_url,
            'ip_address':    self.ip_address,
            'rules_total':   self.rules_total,
            'created_at':    self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }


# Imported last: these models are only used inside methods, and importing them
# at the top would be circular.
from app.core.db_class.bundle import Bundle  # noqa: E402
from app.core.db_class.rule import Rule  # noqa: E402
