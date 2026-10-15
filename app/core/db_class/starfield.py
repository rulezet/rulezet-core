"""Starfield (the hidden game at /starfield): one row per finished run, so
admins can follow who plays and how well.
"""
import datetime
import uuid as uuid_mod

from app import db


class StarfieldRun(db.Model):
    __tablename__ = 'starfield_run'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid_mod.uuid4()))
    # Logged-in player, or None; player_id is a random id kept in the browser,
    # which groups the runs of one anonymous player (and of a user's browser).
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    player_id   = db.Column(db.String(36), nullable=False, index=True)

    mode        = db.Column(db.String(10), nullable=False, index=True)    # level | endless
    world       = db.Column(db.Integer, nullable=True)
    level_index = db.Column(db.Integer, nullable=True)                    # 0-3 levels, 4 boss, 5 honeypot
    level_name  = db.Column(db.String(80), nullable=True)
    level_kind  = db.Column(db.String(20), nullable=True)                 # waves, survive, beacons, protect, boss, honeypot…
    won         = db.Column(db.Boolean, nullable=False, default=False)
    reason      = db.Column(db.String(120), nullable=True)                # why the run was lost

    score       = db.Column(db.Integer, nullable=False, default=0, index=True)
    stars       = db.Column(db.Integer, nullable=False, default=0)
    wave        = db.Column(db.Integer, nullable=True)
    kills       = db.Column(db.Integer, nullable=False, default=0)
    hits        = db.Column(db.Integer, nullable=False, default=0)
    max_combo   = db.Column(db.Integer, nullable=False, default=0)
    bytes       = db.Column(db.Integer, nullable=False, default=0)
    time_s      = db.Column(db.Integer, nullable=False, default=0)

    ship        = db.Column(db.String(20), nullable=True, index=True)     # yara | suricata | sigma | zeek
    difficulty  = db.Column(db.String(20), nullable=True)                 # analyst | hunter | redteam
    controls    = db.Column(db.String(10), nullable=True)                 # classic | twin
    # Everything else: criteria met, upgrades, unlocked weapons, shots per
    # weapon, dashes, bombs, ship power, pickups, kills per malware, hp left…
    details     = db.Column(db.JSON, nullable=True)

    created_at  = db.Column(db.DateTime, nullable=False, index=True,
                            default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    def to_json(self):
        return {
            'uuid': self.uuid, 'user_id': self.user_id, 'player_id': self.player_id,
            'mode': self.mode, 'world': self.world, 'level_index': self.level_index,
            'level_name': self.level_name, 'level_kind': self.level_kind,
            'won': self.won, 'reason': self.reason, 'score': self.score, 'stars': self.stars, 'wave': self.wave,
            'kills': self.kills, 'hits': self.hits, 'max_combo': self.max_combo, 'bytes': self.bytes,
            'time_s': self.time_s, 'ship': self.ship, 'difficulty': self.difficulty, 'controls': self.controls,
            'details': self.details or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
