"""MISP servers.
"""
from app import db
import datetime


class MispServer(db.Model):
    """
    Admin-configured MISP instance connection, used to push a rule's generated
    MISP Object or MISP Event (see app/features/misp/rule/misp_object.py)
    directly into a live MISP deployment via PyMISP's ExpandedPyMISP REST
    client.

    A MISP API key grants full API access to that instance — genuinely
    sensitive, unlike Connector.api_key_outbound — so api_key_encrypted here
    is Fernet-encrypted at rest (see misp_connector_core.py's _encrypt/_decrypt),
    the same departure from this codebase's plaintext-credential precedent
    already established for VelociraptorServer.
    """
    __tablename__ = 'misp_server'

    id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)

    # Human-readable identity
    name        = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Remote connection
    url               = db.Column(db.String(255), nullable=False)   # e.g. https://misp.example.org
    api_key_encrypted = db.Column(db.Text, nullable=False)          # Fernet-encrypted
    verify_tls        = db.Column(db.Boolean, nullable=False, default=True)

    # Ownership / status
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active   = db.Column(db.Boolean, nullable=False, default=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)   # True after first successful test
    last_error  = db.Column(db.Text, nullable=True)

    last_test_at  = db.Column(db.DateTime, nullable=True)
    last_push_at  = db.Column(db.DateTime, nullable=True)
    pushes_count  = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
                           onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    added_by = db.relationship('User', foreign_keys=[added_by_id],
                               backref=db.backref('misp_servers', lazy='dynamic'))

    def to_json(self):
        # Never expose the API key, even encrypted.
        return {
            'id':             self.id,
            'uuid':           self.uuid,
            'name':           self.name,
            'description':    self.description or '',
            'url':            self.url,
            'verify_tls':     self.verify_tls,
            'is_active':      self.is_active,
            'is_verified':    self.is_verified,
            'last_error':     self.last_error,
            'last_test_at':   self.last_test_at.strftime('%Y-%m-%d %H:%M') if self.last_test_at else None,
            'last_push_at':   self.last_push_at.strftime('%Y-%m-%d %H:%M') if self.last_push_at else None,
            'pushes_count':   self.pushes_count,
            'added_by_id':    self.added_by_id,
            'created_at':     self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }
