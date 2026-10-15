"""Velociraptor servers.
"""
from app import db
import datetime


##########################
#   Velociraptor         #
##########################

class VelociraptorServer(db.Model):
    """
    Admin-configured Velociraptor server connection, used to push generated
    detection artifacts (see app/features/rule/exporters/velociraptor_exporter.py)
    directly into a live Velociraptor deployment.

    Velociraptor authenticates API clients via mutual TLS (a client cert/key
    pair issued by the server's own CA, distributed as an "API client config"
    YAML) rather than a bearer token — so client_cert/client_key here are
    genuinely sensitive (impersonation-capable against production endpoint
    infrastructure), unlike Connector.api_key_outbound. Encrypted at rest with
    Fernet (see velociraptor_core.py's _encrypt/_decrypt) — a deliberate
    departure from the plaintext-credential precedent used elsewhere in this
    codebase, given the much larger blast radius of a leaked private key.
    """
    __tablename__ = 'velociraptor_server'

    id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)

    # Human-readable identity
    name        = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Remote connection — from the Velociraptor "API client config" YAML
    api_connection_string = db.Column(db.String(255), nullable=False)   # host:port
    ca_certificate         = db.Column(db.Text, nullable=False)          # PEM, public — not encrypted
    client_cert_encrypted  = db.Column(db.Text, nullable=False)          # PEM, Fernet-encrypted
    client_key_encrypted   = db.Column(db.Text, nullable=False)          # PEM private key, Fernet-encrypted

    # Ownership / status
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active   = db.Column(db.Boolean, nullable=False, default=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)   # True after first successful test
    last_error  = db.Column(db.Text, nullable=True)

    last_test_at     = db.Column(db.DateTime, nullable=True)
    last_push_at     = db.Column(db.DateTime, nullable=True)
    artifacts_pushed = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
                           onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    added_by = db.relationship('User', foreign_keys=[added_by_id],
                               backref=db.backref('velociraptor_servers', lazy='dynamic'))

    def to_json(self):
        # Never expose cert/key material, even encrypted.
        return {
            'id':                    self.id,
            'uuid':                  self.uuid,
            'name':                  self.name,
            'description':           self.description or '',
            'api_connection_string': self.api_connection_string,
            'is_active':             self.is_active,
            'is_verified':           self.is_verified,
            'last_error':            self.last_error,
            'last_test_at':          self.last_test_at.strftime('%Y-%m-%d %H:%M') if self.last_test_at else None,
            'last_push_at':          self.last_push_at.strftime('%Y-%m-%d %H:%M') if self.last_push_at else None,
            'artifacts_pushed':      self.artifacts_pushed,
            'added_by_id':           self.added_by_id,
            'created_at':            self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }
