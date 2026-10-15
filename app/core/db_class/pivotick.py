"""Pivotick graph backgrounds and styles.
"""
from app import db
import datetime


class PivotickBackground(db.Model):
    """Admin-uploaded background image for PivoTick graph canvases.

    Uploaded by an admin, but selectable by ANY user on /settings as their
    personal PivoTick canvas background (choice stored client-side, see
    rz-pivotick-bg-image in localStorage — this table is just the shared gallery).
    """
    __tablename__ = 'pivotick_background'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    filename    = db.Column(db.String(256), nullable=False)
    name        = db.Column(db.String(128), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at  = db.Column(db.DateTime, nullable=False,
                            default=lambda: datetime.datetime.now(datetime.timezone.utc))

    def get_url(self):
        return "/static/uploads/pivotick_backgrounds/" + self.filename

    def to_json(self):
        return {
            "id":         self.id,
            "uuid":       self.uuid,
            "name":       self.name or self.filename,
            "url":        self.get_url(),
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M'),
        }


class PivotickGraphStyle(db.Model):
    """Admin-defined node/edge render config (icon/color/shape/size) for a PivoTick graph.

    One row per graph_type ('rule', 'bundle', 'attack'). Lives entirely outside the
    app/modules/pivotick submodule and its bundled JS/CSS, so bumping the PivoTick
    version never touches this table or overwrites an admin's customization.
    A NULL config means "use the built-in default" (see PIVOTICK_DEFAULT_STYLES
    in app/features/pivotick/pivotick_core.py).
    """
    __tablename__ = 'pivotick_graph_style'

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    graph_type = db.Column(db.String(20), unique=True, nullable=False, index=True)
    config     = db.Column(db.JSON, nullable=True)
    # Admin switch (/admin/pivotick): when off, the graph isn't offered at all —
    # rule/bundle pages show only the MISP event JSON, the ATT&CK page drops
    # its Graph view. No row = enabled.
    enabled    = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    # rule/bundle only: which MISP → graph mapping draws it — 'converters'
    # (pivotick-converters, the default) or 'rulezet' (Rulezet's own mapping,
    # styled by `config` above). NULL = default.
    renderer   = db.Column(db.String(20), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True,
                           default=lambda: datetime.datetime.now(datetime.timezone.utc),
                           onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    def to_json(self):
        return {
            "graph_type":  self.graph_type,
            "config":      self.config,
            "updated_at":  self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
        }
