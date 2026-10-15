"""Git sources: imports, update checks, sync schedules, repository proposals, the repository registry and the Rulesets mirror.

The listeners at the end keep `git_provider` in sync with each row's repository URL.
"""
from app import db
from sqlalchemy import event
import datetime
import json
import uuid as _uuid_mod
from app.core.db_class.rule import InvalidRuleModel, Rule


class ImporterResult(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, unique=True)
    info = db.Column(db.String)
    bad_rules = db.Column(db.Integer, index=True)
    imported = db.Column(db.Integer, index=True)
    skipped = db.Column(db.Integer, index=True)
    total = db.Column(db.Integer, index=True)
    query_date = db.Column(db.DateTime, index=True)
    user_id = db.Column(db.Integer, index=True)
    count_per_format = db.Column(db.String)
    # Git host the item comes from: github | gitlab | gitea | bitbucket | generic
    # (None = not from a git repository). Kept up to date by the listeners at
    # the end of this file — see git_provider.detect_provider().
    git_provider = db.Column(db.String(20), nullable=True, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "info": json.loads(self.info),
            "bad_rules": self.bad_rules,
            "imported": self.imported,
            "skipped": self.skipped,
            "total": self.total,
            "query_date": self.query_date.strftime('%Y-%m-%d %H:%M'),
            "user_id": self.user_id,
            "count_per_format": json.loads(self.count_per_format),
            "git_provider": self.git_provider
        }
        return json_dict


    
class UpdateResult(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, unique=True)

    user_id = db.Column(db.String, index=True)        # user that triggered the update
    mode = db.Column(db.String, nullable=False)        # update mode: url / rule / repo

    info = db.Column(db.Text, nullable=True)           # optional info (json encoded string)
    repo_sources = db.Column(db.Text, nullable=True)   # json list or dict encoded as text

    not_found = db.Column(db.Integer, default=0)
    found = db.Column(db.Integer, default=0)
    updated = db.Column(db.Integer, default=0)
    skipped = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, index=True)

    thread_count = db.Column(db.Integer, default=4)
    query_date = db.Column(db.DateTime, index=True)
    # Git host the item comes from: github | gitlab | gitea | bitbucket | generic
    # (None = not from a git repository). Kept up to date by the listeners at
    # the end of this file — see git_provider.detect_provider().
    git_provider = db.Column(db.String(20), nullable=True, index=True)

    # Relationships
    rule_statuses = db.relationship(
        "RuleStatus",
        backref="update_result",
        cascade="all, delete-orphan",
        lazy=True
    )

    new_rules = db.relationship(
        "NewRule",
        backref="update_result",
        cascade="all, delete-orphan",
        lazy=True
    )


    def _get_rule_name_by_mode(self):
        if self.mode != "by_rule":
            return None

        try:
            repo_data = json.loads(self.repo_sources) if self.repo_sources else None
            if not repo_data:
                return None

            rule_ids = repo_data if isinstance(repo_data, list) else [repo_data]

            rule_names = []
            for rid in rule_ids:
                rule = Rule.get_rule_name_by_id(rid)
                if rule:
                    rule_names.append(rule if isinstance(rule, str) else getattr(rule, "title", str(rule)))
                else:
                    rule_names.append(f"Rule {rid} not found")

            return rule_names if len(rule_names) > 1 else rule_names[0]

        except Exception as e:
            return None


    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "mode": self.mode,
            "info": json.loads(self.info) if self.info else None,
            "repo_sources": json.loads(self.repo_sources) if self.repo_sources else None,
            "not_found": self.not_found,
            "found": self.found,
            "updated": self.updated,
            "skipped": self.skipped,
            "total": self.total,
            "thread_count": self.thread_count,
            "git_provider": self.git_provider,
            "query_date": self.query_date.strftime('%Y-%m-%d %H:%M') if self.query_date else None,
            "rules": [rule.to_json() for rule in self.rule_statuses] if self.rule_statuses else [],
            "new_rules": [nr.to_json() for nr in self.new_rules] if self.new_rules else []
        }
    
    def to_json_list(self):
        """Lean summary — aggregate counts + metadata only, no per-rule content.
        Used by the update-status polling endpoint and the update-history list;
        neither needs individual rules (those load through their own paginated
        get_rules()/get_news_rules() endpoints). Building the full to_json()
        here would mean loading and serializing every RuleStatus/NewRule row
        — up to thousands, each carrying full rule content — just to discard
        them a line later."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "mode": self.mode,
            "info": json.loads(self.info) if self.info else None,
            "repo_sources": json.loads(self.repo_sources) if self.repo_sources else None,
            "not_found": self.not_found,
            "found": self.found,
            "updated": self.updated,
            "skipped": self.skipped,
            "total": self.total,
            "thread_count": self.thread_count,
            "query_date": self.query_date.strftime('%Y-%m-%d %H:%M') if self.query_date else None,
            "rule_name_by_rule_mode": self._get_rule_name_by_mode(),
            # A count, not the array itself — see the docstring above.
            "new_rules_count": NewRule.query.filter_by(update_result_id=self.id).count(),
        }


class RuleStatus(db.Model):
    __tablename__ = "rule_status"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, unique=True)

    update_result_id = db.Column(
        db.Integer,
        db.ForeignKey("update_result.id", ondelete="CASCADE"),
        nullable=False
    )

    date = db.Column(db.DateTime, index=True)
    name_rule = db.Column(db.String, nullable=False)
    rule_id = db.Column(db.String, nullable=True)

    # delete !

    message = db.Column(db.Text, nullable=True)

    found = db.Column(db.Boolean, default=False)
    update_available = db.Column(db.Boolean, default=False)
    rule_syntax_valid = db.Column(db.Boolean, default=True)
    error = db.Column(db.Boolean, default=False)

    history_id = db.Column(db.String, nullable=True)
    def _get_rule(self):
        if not self.rule_id:
            return None
        try:
            return Rule.query.filter_by(id=int(self.rule_id)).first()
        except (ValueError, TypeError):
            return None

    def get_format(self):
        r = self._get_rule()
        return r.format if r else None

    def get_title(self):
        r = self._get_rule()
        return r.title if r else None

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "update_result_id": self.update_result_id,
            "date": self.date.strftime('%Y-%m-%d %H:%M') if self.date else None,
            "name_rule": self.name_rule,
            "rule_title": self.get_title(),
            "rule_id": self.rule_id,
            "message": self.message,
            "found": self.found,
            "update_available": self.update_available,
            "rule_syntax_valid": self.rule_syntax_valid,
            "error": self.error,
            "history_id": self.history_id,
            "format": self.get_format()
        }


class NewRule(db.Model):
    __tablename__ = "new_rule"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, unique=True)

    update_result_id = db.Column(
        db.Integer,
        db.ForeignKey("update_result.id", ondelete="CASCADE"),
        nullable=False
    )
    format = db.Column(db.String(50), nullable=True)
    date = db.Column(db.DateTime, index=True)
    name_rule = db.Column(db.String, nullable=False)
    rule_content = db.Column(db.Text, nullable=False)

    message = db.Column(db.Text, nullable=True)

    rule_syntax_valid = db.Column(db.Boolean, default=True)
    error = db.Column(db.Boolean, default=False)
    accept = db.Column(db.Boolean, default=False)
    github_path = db.Column(db.String, nullable=True)


    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "update_result_id": self.update_result_id,
            "date": self.date.strftime('%Y-%m-%d %H:%M') if self.date else None,
            "name_rule": self.name_rule,
            "rule_content": self.rule_content,
            "message": self.message,
            "format": self.format,
            "rule_syntax_valid": self.rule_syntax_valid,
            "error": self.error,
            "accept": self.accept,
            "github_path": self.github_path
        }


############################################
#    Recurring GitHub sync schedules       #
############################################

class GithubSyncSchedule(db.Model):
    __tablename__ = "github_sync_schedule"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), index=True, unique=True)
    title       = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    editor_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    is_active   = db.Column(db.Boolean, default=True, index=True)

    # Recurrence — explicit fields (not a raw cron string) so the UI can
    # round-trip a schedule back into its picker widgets for editing.
    frequency    = db.Column(db.String(20), nullable=False)   # 'daily' | 'weekly' | 'monthly' | 'cron'
    days_of_week = db.Column(db.String(20), nullable=True)    # '0,2,4' (APScheduler day_of_week ints, Mon=0) — 'weekly' only
    day_of_month = db.Column(db.Integer, nullable=True)       # 1-31, or -1 for "last day" — 'monthly' only
    hour         = db.Column(db.Integer, nullable=False, default=3)
    minute       = db.Column(db.Integer, nullable=False, default=0)
    cron_expr    = db.Column(db.String(120), nullable=True)   # only used when frequency == 'cron'
    timezone     = db.Column(db.String(60), nullable=False, default="UTC")

    next_run_at  = db.Column(db.DateTime, index=True, nullable=True)
    last_run_at  = db.Column(db.DateTime, nullable=True)

    created_at   = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    editor = db.relationship("User")
    repos  = db.relationship("GithubSyncScheduleRepo", backref="schedule", cascade="all, delete-orphan", lazy=True)
    runs   = db.relationship("GithubSyncRun", backref="schedule", cascade="all, delete-orphan", lazy=True,
                              order_by="desc(GithubSyncRun.started_at)")

    def days_of_week_list(self):
        if not self.days_of_week:
            return []
        return [int(d) for d in self.days_of_week.split(',') if d != '']

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "editor": {
                "id": self.editor.id,
                "name": f"{self.editor.first_name} {self.editor.last_name}".strip(),
                "avatar": self.editor.get_avatar_url(),
            } if self.editor else None,
            "is_active": self.is_active,
            "frequency": self.frequency,
            "days_of_week": self.days_of_week_list(),
            "day_of_month": self.day_of_month,
            "hour": self.hour,
            "minute": self.minute,
            "cron_expr": self.cron_expr,
            "timezone": self.timezone,
            "next_run_at": self.next_run_at.strftime('%Y-%m-%d %H:%M') if self.next_run_at else None,
            "last_run_at": self.last_run_at.strftime('%Y-%m-%d %H:%M') if self.last_run_at else None,
            "repo_count": len(self.repos),
            "repos": [r.to_json() for r in self.repos],
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }


class GithubSyncScheduleRepo(db.Model):
    __tablename__ = "github_sync_schedule_repo"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("github_sync_schedule.id", ondelete="CASCADE"), nullable=False)
    repo_url    = db.Column(db.String(500), nullable=False)

    auto_accept_update = db.Column(db.Boolean, default=False)
    auto_add_new_rule  = db.Column(db.Boolean, default=False)
    is_generic_source  = db.Column(db.Boolean, default=False, nullable=False)
    # Git host the item comes from: github | gitlab | gitea | bitbucket | generic
    # (None = not from a git repository). Kept up to date by the listeners at
    # the end of this file — see git_provider.detect_provider().
    git_provider = db.Column(db.String(20), nullable=True, index=True)

    __table_args__ = (db.UniqueConstraint('schedule_id', 'repo_url', name='uq_schedule_repo'),)

    def to_json(self):
        return {
            "id": self.id,
            "repo_url": self.repo_url,
            "auto_accept_update": self.auto_accept_update,
            "auto_add_new_rule": self.auto_add_new_rule,
            "is_generic_source": self.is_generic_source,
            "git_provider": self.git_provider,
        }


class GithubSyncRun(db.Model):
    """One firing of a GithubSyncSchedule. Wraps N per-repo results — it does
    not duplicate UpdateResult data, only groups it for the report page."""
    __tablename__ = "github_sync_run"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid        = db.Column(db.String(36), index=True, unique=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("github_sync_schedule.id", ondelete="CASCADE"), nullable=False)
    job_uuid    = db.Column(db.String(36), nullable=True)

    status      = db.Column(db.String(20), default="pending")  # pending | running | done | failed
    started_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    repo_results = db.relationship("GithubSyncRunRepo", backref="run", cascade="all, delete-orphan", lazy=True)

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "schedule_id": self.schedule_id,
            "schedule_title": self.schedule.title if self.schedule else None,
            "job_uuid": self.job_uuid,
            "status": self.status,
            "started_at": self.started_at.strftime('%Y-%m-%d %H:%M') if self.started_at else None,
            "finished_at": self.finished_at.strftime('%Y-%m-%d %H:%M') if self.finished_at else None,
            "repos": [r.to_json() for r in self.repo_results],
        }


class GithubSyncRunRepo(db.Model):
    """Per-repo outcome within one run. Points at the real UpdateResult (by
    uuid) where found/updated/not_found/skipped already live — this table
    only records what the automation decided to do with that repo."""
    __tablename__ = "github_sync_run_repo"

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id              = db.Column(db.Integer, db.ForeignKey("github_sync_run.id", ondelete="CASCADE"), nullable=False)
    repo_url            = db.Column(db.String(500), nullable=False)
    update_result_uuid  = db.Column(db.String(36), nullable=True)

    status         = db.Column(db.String(20), default="pending")  # pending | running | done | error
    error_message  = db.Column(db.Text, nullable=True)
    auto_accepted  = db.Column(db.Integer, default=0)
    auto_rejected  = db.Column(db.Integer, default=0)
    auto_added     = db.Column(db.Integer, default=0)

    def to_json(self):
        return {
            "id": self.id,
            "repo_url": self.repo_url,
            "update_result_uuid": self.update_result_uuid,
            "status": self.status,
            "error_message": self.error_message,
            "auto_accepted": self.auto_accepted,
            "auto_rejected": self.auto_rejected,
            "auto_added": self.auto_added,
        }


def _gen_github_proposal_uuid():
    return str(_uuid_mod.uuid4())


class GithubProposal(db.Model):
    """A non-admin user's request to import a GitHub repository. Reviewed by
    admins (accept/reject, bulk), accepted proposals are imported one after
    another by the 'github_proposal_bulk_import' background job."""
    __tablename__ = "github_proposal"

    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid     = db.Column(db.String(36), unique=True, nullable=False, index=True, default=_gen_github_proposal_uuid)
    user_id  = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)

    repo_url = db.Column(db.String(512), nullable=False)
    branch   = db.Column(db.String(255), nullable=True)
    license  = db.Column(db.String(128), nullable=True)
    message  = db.Column(db.Text, nullable=True)
    is_generic_source = db.Column(db.Boolean, default=False, nullable=False)
    # Git host the item comes from: github | gitlab | gitea | bitbucket | generic
    # (None = not from a git repository). Kept up to date by the listeners at
    # the end of this file — see git_provider.detect_provider().
    git_provider = db.Column(db.String(20), nullable=True, index=True)

    # pending | accepted | rejected | imported | failed
    # ('transferred' is a legacy value from before accepting always imported
    # — see decide_proposals in proposal_core.py — kept as a valid string for
    # any old row, no longer produced by current code.)
    status         = db.Column(db.String(32), default="pending", index=True)
    ownership_mode = db.Column(db.String(16), nullable=True)  # 'requester' | 'admin'

    decided_by_id  = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    decided_at     = db.Column(db.DateTime, nullable=True)
    decision_note  = db.Column(db.Text, nullable=True)

    job_uuid              = db.Column(db.String(36), nullable=True, index=True)
    importer_result_uuid  = db.Column(db.String(36), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    requester  = db.relationship("User", foreign_keys=[user_id])
    decided_by = db.relationship("User", foreign_keys=[decided_by_id])

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "requester_username": self.requester.get_username() if self.requester else None,
            "requester_avatar": self.requester.get_avatar_url() if self.requester else None,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "license": self.license,
            "message": self.message,
            "is_generic_source": self.is_generic_source,
            "git_provider": self.git_provider,
            "status": self.status,
            "ownership_mode": self.ownership_mode,
            "decided_by_id": self.decided_by_id,
            "decided_by_username": self.decided_by.get_username() if self.decided_by else None,
            "decided_at": self.decided_at.strftime('%Y-%m-%d %H:%M') if self.decided_at else None,
            "decision_note": self.decision_note,
            "job_uuid": self.job_uuid,
            "importer_result_uuid": self.importer_result_uuid,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
        }


class RuleMirrorConfig(db.Model):
    """One "Rulesets" mirror target (see docs/design/rule_git_mirror.md) —
    an instance can have several, each pushing the same active/public rule
    set to a different repo. Off by default, admin-configured, per-instance
    — deliberately NOT tied to GITHUB_TOKEN/IS_OFFICIAL_INSTANCE so a
    self-hosted instance can point this at its own repo(s) with its own
    token(s), independent of rulezet.org's own official mirror config.

    github_token is stored the same way Connector.api_key_outbound already
    is (a plain column — this app's existing trust boundary is DB access,
    not per-field encryption) but is never re-sent to the browser once
    saved; the admin UI only ever shows a masked placeholder."""
    __tablename__ = 'rule_mirror_config'
    id              = db.Column(db.Integer, primary_key=True)
    uuid            = db.Column(db.String(36), unique=True, nullable=False)
    name            = db.Column(db.String(255), nullable=False, default='Rulesets mirror')
    enabled         = db.Column(db.Boolean, default=False, nullable=False)
    repo_url        = db.Column(db.String(512), nullable=True)
    # Git host the item comes from: github | gitlab | gitea | bitbucket | generic
    # (None = not from a git repository). Kept up to date by the listeners at
    # the end of this file — see git_provider.detect_provider().
    git_provider = db.Column(db.String(20), nullable=True, index=True)
    github_token    = db.Column(db.String(512), nullable=True)
    branch          = db.Column(db.String(128), default='main', nullable=False)
    last_synced_at  = db.Column(db.DateTime, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at      = db.Column(db.DateTime, nullable=True)
    updated_by_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Set only by a successful "Test connection" call (rule_mirror_core.test_config)
    # — reset to False whenever repo_url/branch/github_token change. "Run now"
    # is refused, both in the UI and server-side, until this is True: a
    # mandatory check before ever attempting to push, not just an optional one.
    is_verified     = db.Column(db.Boolean, default=False, nullable=False)
    last_error      = db.Column(db.Text, nullable=True)
    last_tested_at  = db.Column(db.DateTime, nullable=True)

    def to_json(self):
        return {
            "git_provider": self.git_provider,
            'id':             self.id,
            'uuid':           self.uuid,
            'name':           self.name,
            'enabled':        self.enabled,
            'repo_url':       self.repo_url,
            'has_token':      bool(self.github_token),
            'branch':         self.branch,
            'is_verified':    self.is_verified,
            'last_error':     self.last_error,
            'last_tested_at': self.last_tested_at.strftime('%Y-%m-%d %H:%M') if self.last_tested_at else None,
            'last_synced_at': self.last_synced_at.strftime('%Y-%m-%d %H:%M') if self.last_synced_at else None,
            'updated_at':     self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
        }


class GithubRepo(db.Model):
    """Cached registry of distinct GitHub repo URLs referenced by active
    (non-deleted) rules — powers the GitHub Sources list
    (/rule/github/list_github_url) without a live GROUP BY over the whole
    Rule table (that query took 1.3-1.4s per page load on a ~368k-row
    corpus with no caching at all). rule_count is kept in sync incrementally
    from every place that changes rule counts per source — see
    app/features/rule/github_repo_core.py for the write-side helpers and
    the full list of call sites this depends on staying correct at.

    format_counts/license_counts are {name: count} dicts of this repo's
    active rules, kept in sync incrementally at the same write sites as
    rule_count (see github_repo_core.py) — the filter/sort/search logic on
    the GitHub Sources list reads them (and cve_count/conflict_count)
    directly off this table, never a live Rule scan.

    conflict_count (distinct rules in this repo with a RuleSimilarity row
    scoring > 0.99) is the one exception to "same write sites as
    rule_count": RuleSimilarity itself is produced by a separate, full
    corpus-wide recompute job (app/features/rule/utils/similar_rules/
    similarity_class.py wipes and rebuilds the whole table), so
    conflict_count is instead resynced in one batched pass right after that
    job finishes — see github_repo_core.sync_conflict_counts().
    """
    __tablename__ = 'github_repo'

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid           = db.Column(db.String(36), unique=True, nullable=False, index=True)
    url            = db.Column(db.String(500), unique=True, nullable=False, index=True)
    # Git host the item comes from: github | gitlab | gitea | bitbucket | generic
    # (None = not from a git repository). Kept up to date by the listeners at
    # the end of this file — see git_provider.detect_provider().
    git_provider = db.Column(db.String(20), nullable=True, index=True)
    author         = db.Column(db.String(255), nullable=True, index=True)
    rule_count     = db.Column(db.Integer, nullable=False, default=0)
    format_counts  = db.Column(db.JSON, nullable=False, default=dict)
    license_counts = db.Column(db.JSON, nullable=False, default=dict)
    # {branch_name: active-rule-count} — same incremental-sync convention as
    # format_counts/license_counts (see github_repo_core.py). A rule with no
    # recorded branch (imported before this column existed) simply doesn't
    # contribute an entry here, same as a rule with no format/license.
    branch_counts  = db.Column(db.JSON, nullable=False, default=dict)
    cve_count      = db.Column(db.Integer, nullable=False, default=0)
    conflict_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc),
                           onupdate=datetime.datetime.now(tz=datetime.timezone.utc))
    last_synced_at = db.Column(db.DateTime, nullable=True)  # set by a full rebuild, not by incremental deltas

    def to_json(self):
        return {
            "git_provider": self.git_provider,
            'id':         self.id,
            'uuid':       self.uuid,
            'url':        self.url,
            'author':     self.author,
            'rule_count': self.rule_count,
            'formats':    sorted((self.format_counts or {}).keys()),
            'licenses':   sorted((self.license_counts or {}).keys()),
            'branches':   sorted(b for b in (self.branch_counts or {}).keys() if b),
            'cve_count':  self.cve_count,
            'has_conflicts': self.conflict_count > 0,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
        }


# ─── git_provider, kept in sync with each item's repository URL ──────────────

def _detect_git_provider(url):
    from app.features.rule.rule_format.utils_format.git_provider import detect_provider
    if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return None
    return detect_provider(url)


def _git_url_of(target):
    if isinstance(target, Rule):
        if not target.github_path:
            from app.features.rule.rule_format.utils_format.git_provider import is_git_repo_url
            return target.source if is_git_repo_url(target.source) else None
        return target.source
    if isinstance(target, InvalidRuleModel):
        return target.url
    if isinstance(target, (GithubRepo, GithubProposal, GithubSyncScheduleRepo, RuleMirrorConfig)):
        return target.url if isinstance(target, GithubRepo) else target.repo_url
    if isinstance(target, ImporterResult):
        try:
            return (json.loads(target.info or '{}') or {}).get('repo_url')
        except (ValueError, AttributeError):
            return None
    if isinstance(target, UpdateResult):
        if target.mode == 'by_rule':
            return None
        try:
            sources = json.loads(target.repo_sources) if target.repo_sources else None
        except ValueError:
            return None
        if isinstance(sources, list):
            sources = next((x for x in sources if isinstance(x, str)), None)
        return sources if isinstance(sources, str) else None
    return None


def _set_git_provider(_mapper, _connection, target):
    target.git_provider = _detect_git_provider(_git_url_of(target))


for _model in (Rule, InvalidRuleModel, ImporterResult, UpdateResult, GithubSyncScheduleRepo,
               GithubProposal, RuleMirrorConfig, GithubRepo):
    event.listen(_model, 'before_insert', _set_git_provider)
    event.listen(_model, 'before_update', _set_git_provider)
