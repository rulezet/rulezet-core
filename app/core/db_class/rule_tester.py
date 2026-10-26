"""Rule tests and their results.
"""
from app import db
import datetime


########################################
#   Rule Tester                        #
########################################

class RuleTest(db.Model):
    """A single test session: one input tested against one or many rules."""
    __tablename__ = 'rule_test'

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid         = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # single-rule tests set this; bulk tests leave it null
    rule_id      = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='SET NULL'),
                             nullable=True, index=True)

    test_type    = db.Column(db.String(16), nullable=False)   # 'single' | 'bulk'
    format       = db.Column(db.String(32), nullable=False)   # yara | sigma | suricata | …

    input_type   = db.Column(db.String(32), nullable=False)   # string | hex | file_b64 | json | http
    input_data   = db.Column(db.Text, nullable=True)
    input_label  = db.Column(db.String(255), nullable=True)

    # Flags the sample under test as a real malicious/dangerous artifact, so
    # anyone viewing this test later is warned before handling it.
    is_dangerous       = db.Column(db.Boolean, nullable=False, default=False, index=True)
    danger_description = db.Column(db.Text, nullable=True)

    bulk_filters = db.Column(db.JSON, nullable=True)

    job_id       = db.Column(db.Integer, db.ForeignKey('background_job.id', ondelete='SET NULL'),
                             nullable=True)

    # pending | running | done | failed
    status       = db.Column(db.String(16), nullable=False, default='pending', index=True)
    matched_count = db.Column(db.Integer, nullable=True)
    total_rules   = db.Column(db.Integer, nullable=True)
    error         = db.Column(db.Text, nullable=True)

    is_public    = db.Column(db.Boolean, nullable=False, default=False, index=True)
    label        = db.Column(db.String(255), nullable=True)
    notes        = db.Column(db.Text, nullable=True)

    created_at   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.datetime.now(datetime.timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    user    = db.relationship('User', backref=db.backref('rule_tests', lazy='dynamic'))
    rule    = db.relationship('Rule', backref=db.backref('tests', lazy='dynamic'),
                              foreign_keys=[rule_id])
    job     = db.relationship('BackgroundJob', foreign_keys=[job_id])
    results = db.relationship('RuleTestResult', backref='test', lazy='dynamic',
                              cascade='all, delete-orphan')

    def to_json(self):
        user_obj = User.query.get(self.user_id)
        return {
            'id':            self.id,
            'uuid':          self.uuid,
            'user_id':       self.user_id,
            'user':          {'id': user_obj.id, 'username': user_obj.get_username(),
                              'avatar': user_obj.get_avatar_url()} if user_obj else None,
            'rule_id':       self.rule_id,
            'test_type':     self.test_type,
            'format':        self.format,
            'input_type':    self.input_type,
            'input_label':   self.input_label,
            'is_dangerous':       self.is_dangerous,
            'danger_description': self.danger_description,
            'status':        self.status,
            'matched_count': self.matched_count,
            'total_rules':   self.total_rules,
            'is_public':     self.is_public,
            'label':         self.label,
            'notes':         self.notes,
            'job_uuid':      self.job.uuid if self.job else None,
            'created_at':    self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at':  self.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.completed_at else None,
        }

    def to_json_summary(self):
        """Compact representation for list views (no input_data)."""
        return {
            'uuid':          self.uuid,
            'user_id':       self.user_id,
            'rule_id':       self.rule_id,
            'test_type':     self.test_type,
            'format':        self.format,
            'input_type':    self.input_type,
            'input_label':   self.input_label,
            'is_dangerous':  self.is_dangerous,
            'status':        self.status,
            'matched_count': self.matched_count,
            'total_rules':   self.total_rules,
            'is_public':     self.is_public,
            'label':         self.label,
            'created_at':    self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at':  self.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.completed_at else None,
        }


class RuleTestResult(db.Model):
    """One rule's outcome inside a RuleTest session."""
    __tablename__ = 'rule_test_result'

    id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_id = db.Column(db.Integer, db.ForeignKey('rule_test.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='SET NULL'),
                        nullable=True, index=True)

    matched           = db.Column(db.Boolean, nullable=False, default=False)
    score             = db.Column(db.Float, nullable=True)
    details           = db.Column(db.JSON, nullable=True)
    quality_hints     = db.Column(db.JSON, nullable=True)
    error             = db.Column(db.Text, nullable=True)
    execution_time_ms = db.Column(db.Integer, nullable=True)

    # snapshot so history stays stable even when rule is edited later
    rule_title  = db.Column(db.String(255), nullable=True)
    rule_uuid   = db.Column(db.String(36), nullable=True)
    rule_format = db.Column(db.String(32), nullable=True)

    rule = db.relationship('Rule', foreign_keys=[rule_id])

    def to_json(self):
        return {
            'id':               self.id,
            'test_id':          self.test_id,
            'rule_id':          self.rule_id,
            'rule_uuid':        self.rule_uuid,
            'rule_title':       self.rule_title,
            'rule_format':      self.rule_format,
            'matched':          self.matched,
            'score':            self.score,
            'details':          self.details,
            'quality_hints':    self.quality_hints,
            'error':            self.error,
            'execution_time_ms': self.execution_time_ms,
        }



########################################
#   Tests on sample sets               #
########################################

class SampleTestRun(db.Model):
    """One run of rulezet-tester (a document of rules × sample sets): the run state it reports,
    kept here so every web process sees it (DbRunRegistry) and the result outlives the page.
    origin: 'editor' (Test button) or 'create' (the YARA editor's Create job)."""
    __tablename__ = 'sample_test_run'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id      = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    format      = db.Column(db.String(32), nullable=False)
    origin      = db.Column(db.String(16), nullable=False, default='editor')
    status      = db.Column(db.String(16), nullable=False, default='queued', index=True)
    state       = db.Column(db.JSON, nullable=False)
    created_at  = db.Column(db.DateTime, nullable=False,
                            default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    finished_at = db.Column(db.DateTime, nullable=True)


class RuleSampleResult(db.Model):
    """What one run said about one rule, for the version of the rule that was tested
    (content_hash = sha256 of its text): the "tested on N samples" badge of the rule page."""
    __tablename__ = 'rule_sample_result'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rule_id         = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=False, index=True)
    run_id          = db.Column(db.Integer, db.ForeignKey('sample_test_run.id', ondelete='CASCADE'), nullable=False, index=True)
    content_hash    = db.Column(db.String(64), nullable=False)
    total           = db.Column(db.Integer, nullable=False, default=0)
    detected        = db.Column(db.Integer, nullable=False, default=0)
    missed          = db.Column(db.Integer, nullable=False, default=0)
    false_positives = db.Column(db.Integer, nullable=False, default=0)
    errors          = db.Column(db.Integer, nullable=False, default=0)
    sets            = db.Column(db.JSON, nullable=True)       # [{id, name, kind}]
    created_at      = db.Column(db.DateTime, nullable=False,
                                default=lambda: datetime.datetime.now(datetime.timezone.utc))

    run = db.relationship('SampleTestRun')

    def to_json(self):
        return {
            'total': self.total, 'detected': self.detected, 'missed': self.missed,
            'false_positives': self.false_positives, 'errors': self.errors, 'sets': self.sets or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

# Imported last: these models are only used inside methods, and importing them
# at the top would be circular.
from app.core.db_class.user import User  # noqa: E402
