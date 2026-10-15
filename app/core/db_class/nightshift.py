"""Night shift (the hidden investigation game at /nightshift): one row per case
a player opens, one row per rule they test or deploy on it. Everything that
counts — pinned evidence, hints, tests, the score — is decided server-side.
"""
import datetime
import uuid as uuid_mod

from app import db


def _now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


class NightshiftCaseRun(db.Model):
    __tablename__ = 'nightshift_case_run'

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid           = db.Column(db.String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid_mod.uuid4()))
    # Logged-in player, or None; player_id is a random id kept in the browser
    # (groups an anonymous player's runs, as in Starfield).
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    player_id      = db.Column(db.String(36), nullable=False, index=True)
    case_id        = db.Column(db.String(40), nullable=False, index=True)

    evidence       = db.Column(db.JSON, nullable=True)                      # pinned keys, in order
    hints_used     = db.Column(db.Integer, nullable=False, default=0)
    tests          = db.Column(db.Integer, nullable=False, default=0)
    failed_deploys = db.Column(db.Integer, nullable=False, default=0)

    closed         = db.Column(db.Boolean, nullable=False, default=False, index=True)
    score          = db.Column(db.Integer, nullable=False, default=0, index=True)
    stars          = db.Column(db.Integer, nullable=False, default=0)
    score_details  = db.Column(db.JSON, nullable=True)
    rule           = db.Column(db.Text, nullable=True)                      # the deployed rule

    created_at     = db.Column(db.DateTime, nullable=False, default=_now, index=True)
    last_test_at   = db.Column(db.DateTime, nullable=True)
    closed_at      = db.Column(db.DateTime, nullable=True)

    attempts = db.relationship('NightshiftAttempt', backref='run', cascade='all, delete-orphan',
                               order_by='NightshiftAttempt.id')

    def to_json(self):
        return {
            'uuid': self.uuid, 'case_id': self.case_id, 'evidence': self.evidence or [],
            'hints_used': self.hints_used, 'tests': self.tests, 'failed_deploys': self.failed_deploys,
            'closed': self.closed, 'score': self.score, 'stars': self.stars,
            'score_details': self.score_details or {}, 'rule': self.rule,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
        }


class NightshiftAttempt(db.Model):
    __tablename__ = 'nightshift_attempt'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id      = db.Column(db.Integer, db.ForeignKey('nightshift_case_run.id', ondelete='CASCADE'), nullable=False, index=True)
    kind        = db.Column(db.String(10), nullable=False)                   # test | deploy
    rule        = db.Column(db.Text, nullable=False)
    error       = db.Column(db.String(300), nullable=True)                   # compile error, if any
    tp          = db.Column(db.Integer, nullable=False, default=0)
    fp          = db.Column(db.Integer, nullable=False, default=0)
    fn          = db.Column(db.Integer, nullable=False, default=0)
    created_at  = db.Column(db.DateTime, nullable=False, default=_now)
