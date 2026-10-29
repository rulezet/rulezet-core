"""Users, their follows, personal settings and custom themes.
"""
from app import db
from app import login_manager
from flask_login import AnonymousUserMixin
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
import datetime
from app.core.db_class.common import _gen_uuid


#############
#   User    #
#############

@login_manager.user_loader
def load_user(user_id):
    """Loads the user from the session."""
    return User.query.get(int(user_id))


# ============================================================
# CHANGES TO APPLY IN app/db_class/db.py — User model only
# Replace the existing User class with this one.
# ============================================================

# Sentinel value for User.profile_picture — the one exception to "profile_picture
# is a bare filename under static/uploads/avatars/": the official Rulezet
# connector's shadow user (app/features/connector/connector_core.py) uses this
# to point straight at the app logo under static/image/ instead.
OFFICIAL_LOGO_AVATAR_SENTINEL = '__official_rulezet_logo__'


class User(UserMixin, db.Model):
    """User model for authentication and authorization."""

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(64), index=True)
    last_name = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    admin = db.Column(db.Boolean, default=False, index=True)
    password_hash = db.Column(db.String(165))
    api_key = db.Column(db.String(128), index=True)
    is_connected = db.Column(db.Boolean, default=False, index=True)
    auth_provider = db.Column(db.String(32), default='local', nullable=False, server_default='local')
    auth_data = db.Column(db.String(128), unique=True, index=True)

    is_verified = db.Column(db.Boolean, default=False)
    # an admin checked that the person really is who they claim to be ("Verified by an admin" badge);
    # each decision, with its justification, in UserIdentityVerification
    identity_verified = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    # the organisation an admin assigned (informative: shown on the profile and the UserChip)
    organisation_id = db.Column(db.Integer, db.ForeignKey('organisation.id', ondelete='SET NULL'), nullable=True, index=True)
    organisation = db.relationship('Organisation', foreign_keys=[organisation_id])
    # the first admin of a new instance (app.py -i) gets a generated password: changed before anything else
    must_change_password = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    verification_code = db.Column(db.String(6), nullable=True)
    verification_expiration = db.Column(db.DateTime, nullable=True)
    password_reset_token = db.Column(db.String(64), nullable=True, index=True)
    password_reset_expiration = db.Column(db.DateTime, nullable=True)
    pending_email = db.Column(db.String(64), nullable=True)
    email_change_token = db.Column(db.String(64), nullable=True, index=True)
    email_change_expiration = db.Column(db.DateTime, nullable=True)

    # --- NEW FIELDS ---

    # Profile
    username = db.Column(db.String(64), unique=True, nullable=True, index=True)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(256), nullable=True)  # relative path under /static/uploads/avatars/
    location = db.Column(db.String(128), nullable=True)

    # External links
    website_url = db.Column(db.String(256), nullable=True)
    github_url = db.Column(db.String(256), nullable=True)
    twitter_url = db.Column(db.String(256), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)

    # --- END NEW FIELDS ---

    def is_admin(self):
        """Check if the user has admin privileges."""
        return self.admin

    def has_permission(self, key: str) -> bool:
        """Check a granular permission grant via the Role/Permission system.

        Admins bypass every check here by design — this is a purely additive
        layer for the middle tier between "any logged-in user" and "admin",
        never a replacement for the existing is_admin() gates scattered
        across the app. A permission only ever narrows what a non-admin can
        do beyond their own resources; it never restricts an admin.
        """
        if self.is_admin():
            return True
        role_ids = [ur.role_id for ur in UserRole.query.filter_by(user_id=self.id).all()]
        if not role_ids:
            return False
        return (
            db.session.query(RolePermission)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role_id.in_(role_ids), Permission.key == key)
            .first()
            is not None
        )

    def get_username(self):
        return self.username if self.username else (self.first_name + " " + self.last_name)

    def get_first_name(self):
        return self.first_name

    def get_avatar_url(self):
        """Return the profile picture URL or a default gravatar-style fallback."""
        # Exception: the official Rulezet connector's shadow user points
        # straight at the app logo under static/image/ instead of a copy in
        # the user-uploaded avatars folder — see OFFICIAL_LOGO_AVATAR_SENTINEL
        # in connector_core.py.
        if self.profile_picture == OFFICIAL_LOGO_AVATAR_SENTINEL:
            return "/static/image/pp_Rulezet.png"
        if self.profile_picture:
            return "/static/uploads/avatars/" + self.profile_picture
        return None

    @property
    def password(self):
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_anonymous(self):
        return False

    def to_json(self, include_private=True):
        """Serialize the user object to JSON.

        include_private=False strips email and admin status — use this
        whenever the result reaches a viewer who isn't the user themselves
        or an admin (e.g. rendered into a page any logged-in user can open).
        """

        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email if include_private else None,
            "admin": self.admin if include_private else False,
            "username": self.get_username(),
            "is_connected": self.is_connected,
            "is_verified": self.is_verified,
            "identity_verified": bool(self.identity_verified),
            "organisation": self.organisation.to_json() if self.organisation else None,
            "is_admin": self.is_admin() if include_private else False,
            # new
            "bio": self.bio,
            "profile_picture": self.get_avatar_url(),
            "location": self.location,
            "website_url": self.website_url,
            "github_url": self.github_url,
            "twitter_url": self.twitter_url,
            "created_at": self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            "last_seen": self.last_seen.strftime('%Y-%m-%d %H:%M') if self.last_seen else None,
            "auth_provider": self.auth_provider,
        }


class Organisation(db.Model):
    """An organisation created by an admin; admins assign users to it (one per user).
    Informative only: shown on the profile and the UserChip, gives no right."""
    __tablename__ = 'organisation'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)
    website     = db.Column(db.String(256), nullable=True)
    # the badge's look, like a tag: colour (hex), Font Awesome icon, text (the name when empty)
    color       = db.Column(db.String(20), nullable=True)
    icon        = db.Column(db.String(50), nullable=True)
    label       = db.Column(db.String(40), nullable=True)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    created_by  = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    def to_json(self):
        return {'id': self.id, 'name': self.name, 'website': self.website,
                'color': self.color or '#6f42c1', 'icon': self.icon or 'fa-building',
                'label': self.label or '', 'text': self.label or self.name}


class UserIdentityVerification(db.Model):
    """One admin decision on a user's identity: verified (really who they claim to be) or
    withdrawn, with the admin's justification. The history of a user is all their rows."""
    __tablename__ = 'user_identity_verification'

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    verified      = db.Column(db.Boolean, nullable=False)
    justification = db.Column(db.Text, nullable=False)
    by_user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    by_user = db.relationship('User', foreign_keys=[by_user_id])

    def to_json(self):
        return {
            'id': self.id,
            'verified': self.verified,
            'justification': self.justification,
            'by': self.by_user.to_json(include_private=False) if self.by_user else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }


class AnonymousUser(AnonymousUserMixin):
    """Defines behavior for anonymous users (not logged in)."""
    
    def is_admin(self):
        return False

    def has_permission(self, key):
        return False

    def is_anonymous(self):
        return True


# Register AnonymousUser as the default for anonymous visitors
login_manager.anonymous_user = AnonymousUser


########################################
#   User Follow                        #
########################################

class UserFollow(db.Model):
    """One row per follower → followed relationship."""
    __tablename__ = 'user_follow'
    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='uq_user_follow'),)

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
                            nullable=False, index=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
                            nullable=False, index=True)
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    follower = db.relationship('User', foreign_keys=[follower_id],
                               backref=db.backref('following', lazy='dynamic', cascade='all, delete-orphan'))
    followed = db.relationship('User', foreign_keys=[followed_id],
                               backref=db.backref('followers', lazy='dynamic', cascade='all, delete-orphan'))


THEME_CHOICES = ('system', 'light', 'dark')


class UserConfig(db.Model):
    __tablename__ = 'user_config'

    id         = db.Column(db.Integer, primary_key=True)
    uuid       = db.Column(db.String(36), unique=True, nullable=False, default=_gen_uuid)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active  = db.Column(db.Boolean, default=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    meta       = db.Column(db.JSON, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    theme   = db.Column(db.String(64), default='system')

    def to_json(self):
        return {
            'id':      self.id,
            'uuid':    self.uuid,
            'user_id': self.user_id,
            'theme':   self.theme,
        }


class CustomTheme(db.Model):
    __tablename__ = 'custom_theme'

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid       = db.Column(db.String(36), unique=True, nullable=False, default=_gen_uuid)
    name       = db.Column(db.String(64), nullable=False)
    css_key    = db.Column(db.String(64), unique=True, nullable=False)
    icon       = db.Column(db.String(64), nullable=False, default='fa-palette')
    is_dark    = db.Column(db.Boolean, default=False, nullable=False)
    is_builtin = db.Column(db.Boolean, default=False, nullable=False)
    is_public  = db.Column(db.Boolean, default=False, nullable=False)
    css_vars   = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, nullable=True)
    meta       = db.Column(db.JSON, nullable=True)

    def to_json(self):
        return {
            'id':         self.id,
            'uuid':       self.uuid,
            'name':       self.name,
            'css_key':    self.css_key,
            'icon':       self.icon,
            'is_dark':    self.is_dark,
            'is_builtin': self.is_builtin,
            'css_vars':   self.css_vars or {},
            'is_public':  self.is_public,
            'is_active':  self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# Imported last: these models are only used inside methods, and importing them
# at the top would be circular.
from app.core.db_class.role import Permission, RolePermission, UserRole  # noqa: E402
