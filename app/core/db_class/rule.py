"""Detection rules and what hangs directly off a rule (votes, favorites, ownership requests, history, bad rules).
"""
from app import db
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy import func
import datetime
import hashlib


#############
#   Rule    #
#############

class Rule(db.Model):
    """Rule model to store and describe various rules."""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer) # the user who import the rule
    version = db.Column(db.String)
    format = db.Column(db.String)
    title = db.Column(db.String)
    license = db.Column(db.String)
    description = db.Column(db.String)
    uuid = db.Column(db.String(36), index=True)
    original_uuid = db.Column(db.String , nullable=True)
    source = db.Column(db.String)
    author = db.Column(db.String) # the reel author of the rule
    creation_date = db.Column(db.DateTime, index=True)
    last_modif = db.Column(db.DateTime, index=True)
    vote_up = db.Column(db.Integer)
    vote_down = db.Column(db.Integer)
    to_string = db.Column(db.String)
    cve_id = db.Column(db.String , nullable=True)

    github_path = db.Column(db.String , nullable=True)
    # Git host the item comes from: github | gitlab | gitea | bitbucket | generic
    # (None = not from a git repository). Kept up to date by the listeners at
    # the end of this file — see git_provider.detect_provider().
    git_provider = db.Column(db.String(20), nullable=True, index=True)
    # Git branch this rule was imported from (e.g. "main", "dev") — set at
    # import time from the branch picked in the import UI. NULL for rules
    # imported before this column existed, or not imported from GitHub at
    # all; backfilled best-effort from the source repo's own default
    # branch rather than assumed to be "main".
    branch = db.Column(db.String(255), nullable=True)

    # MD5 of the whitespace-normalized, lowercased to_string — kept in sync by the
    # `set` event below. Lets duplicate-content lookups use an index instead of a
    # full-table scan through nested REPLACE()/LOWER() SQL functions.
    content_hash = db.Column(db.String(32), nullable=True, index=True)

    # Format-specific identifier that must be unique within its format's corpus
    # (Suricata SID, YARA rule name, Wazuh rule ID) — NULL for formats with no
    # such identifier. Kept in sync by the `set` events below. Lets
    # check_identifier_uniqueness() do an indexed lookup instead of re-parsing
    # every existing rule of the same format on every new submission — see
    # rule_core.py:check_identifier_uniqueness.
    corpus_identifier = db.Column(db.String(191), nullable=True, index=True)

    # Soft delete
    is_deleted        = db.Column(db.Boolean, nullable=False, default=False, index=True)
    deleted_at        = db.Column(db.DateTime, nullable=True)
    deleted_by_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    delete_batch_uuid = db.Column(db.String(36), nullable=True, index=True)

    # Connector origin — set when a rule is imported via a connector
    connector_id       = db.Column(db.Integer, db.ForeignKey('connector.id', ondelete='SET NULL'), nullable=True, index=True)
    remote_rule_uuid   = db.Column(db.String(36), nullable=True, index=True)  # UUID on the remote instance
    sync_instance_url  = db.Column(db.String(255), nullable=True)             # Instance URL the rule was pulled from (persisted even if connector deleted)

    # Rule lifecycle status (personal management)
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)

    # Quality score — objective documentation/traceability/validity signal, kept
    # separate from vote_up/vote_down/favorites (popularity). NULL = never analyzed
    # yet, distinct from a real low score of 0. See app/features/rule/rule_quality/.
    quality_score             = db.Column(db.Float, nullable=True, index=True)
    quality_score_breakdown   = db.Column(db.JSON, nullable=True)
    quality_score_computed_at = db.Column(db.DateTime, nullable=True)

    # Read from the rule's own text (app/features/rule/rule_metadata_core.py), kept in sync by the
    # `set` events below: references (list of strings) and every other metadata key the rule
    # carries that Rulezet has no field for (dates, hashes, status, level…: {key: value | [values]}).
    # NULL when the text has none. Never edited by hand: change the rule's text instead.
    rule_references = db.Column(db.JSON, nullable=True)
    extra_metadata  = db.Column(db.JSON, nullable=True)
    # References added by hand (create / edit form), on top of the ones in the text — never
    # overwritten by the events below. all_references = both, the rule's own first.
    manual_references = db.Column(db.JSON, nullable=True)

    @property
    def all_references(self):
        refs = list(self.rule_references or [])
        return refs + [r for r in (self.manual_references or []) if r not in refs]

    #edit
    def get_rule_user_first_name_by_id(self):
        user = User.query.get(self.user_id)  
        return user.first_name + " " + user.last_name if user else None

    def get_rule_name_by_id(id):
        rule = Rule.query.get(id)
        return rule.title if rule else None
    
    def to_json(self, submitter=None, is_favorited=None):
        """submitter/is_favorited let a caller serialising many rules at
        once (a rule list page) batch-fetch both up front — one query for
        every submitter, one for the current user's favorites among the
        whole page — instead of this method re-querying User and
        RuleFavoriteUser once per rule (was 1-2 extra round trips per row,
        e.g. ~20 queries for a 10-rule page). See rule.py's
        get_rules_page_filter for the batched caller. Left None (the
        default) for every other call site, which keeps the original
        per-call lookups."""
        if is_favorited is None:
            is_favorited = False
            if not current_user.is_anonymous():
                is_favorited = RuleFavoriteUser.query.filter_by(user_id=current_user.id, rule_id=self.id).first() is not None

        if submitter is None:
            submitter = User.query.get(self.user_id)
        submitter_avatar = submitter.get_avatar_url() if submitter else None
        editor_name = (submitter.first_name + " " + submitter.last_name) if submitter else None
        return {
            "id": self.id,
            "format": self.format,
            "extension": self.get_extension(),
            "title": self.title,
            "license": self.license,
            "description": self.description,
            "uuid": self.uuid,
            "original_uuid": self.original_uuid,
            "source": self.source,
            "author": self.author,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M'),
            "vote_up": self.vote_up,
            "vote_down": self.vote_down,
            "user_id": self.user_id,
            "version": self.version,
            "to_string": self.to_string,
            "is_favorited": is_favorited,
            "cve_id": self.cve_id if self.cve_id is not None else [],
            "editor": editor_name,
            "github_path": self.github_path if self.github_path else None,
            "git_provider": self.git_provider,
            "branch": self.branch if self.branch else None,
            "editor_avatar": submitter_avatar,
            "sync_instance_url": self.sync_instance_url,
            "status": self.status or 'draft',
            "is_code_format": self.is_code_format(),
            "quality_score": self.quality_score,
            "quality_score_breakdown": self.quality_score_breakdown,
            "quality_score_computed_at": self.quality_score_computed_at.strftime('%Y-%m-%d %H:%M') if self.quality_score_computed_at else None,
            "references": self.all_references,
            "references_from_rule": self.rule_references or [],
            "references_manual": self.manual_references or [],
            "extra_metadata": self.extra_metadata or {},
        }

    def get_extension(self):
        """ Get the file extension for each format """
        format_name = self.format.lower() if self.format else ""
        
        extensions = {
            'yara': 'yar',
            'sigma': 'yml',
            'suricata': 'rules',
            'sagan': 'rules',
            'snort': 'rules',
            'zeek': 'zeek',
            'wazuh': 'xml',
            'nse': 'nse',
            'crs': 'conf',
            'nova': 'nov',
            'splunk': 'yml',
            'elastic': 'toml',
            'kql': 'kql',
            'kunai': 'kun',
            'atr': 'yaml',
            'plum': 'yaml',
        }

        return extensions.get(format_name, 'txt')

    # ref A8: Zeek and NSE (Lua-based Nmap scripts) submissions are arbitrary
    # executable code, not declarative detection rules, and used to be shown
    # in the same undifferentiated list as YARA/Sigma/Suricata/CRS.
    CODE_FORMATS = {'zeek', 'nse'}

    def is_code_format(self) -> bool:
        """True for formats that are executable code rather than a declarative rule."""
        return (self.format or '').lower() in self.CODE_FORMATS


    def to_json_detail(self):
        """ Return a detailed JSON representation of the rule, including all fields. This is used for the rule detail page. """
        
        # votes
        total_votes = (self.vote_up or 0) + (self.vote_down or 0)
        vote_ratio = round((self.vote_up or 0) / total_votes * 100) if total_votes > 0 else 0

        # favorites count
        favorites_count = self.favorited_by_users_assocs.count()

        # is favorited by current user
        is_favorited = False
        if not current_user.is_anonymous():
            is_favorited = RuleFavoriteUser.query.filter_by(user_id=current_user.id, rule_id=self.id).first() is not None

        # submitter
        submitter = User.query.get(self.user_id)
        submitter_info = None
        if submitter:
            gamification = submitter.gamification_stats
            submitter_info = {
                "id": submitter.id,
                "username": submitter.first_name + " " + submitter.last_name,
                "level": gamification.current_level if gamification else 1,
                "total_points": gamification.total_points if gamification else 0,
            }

        # tags
        tags = [assoc.to_json() for assoc in self.rule_tags_assocs]

        # comments
        comments = [c.to_json() for c in self.comments_rule.order_by(Comment.created_at.desc()).limit(20)]

        # edit proposals
        proposals = self.edit_proposals.order_by(RuleEditProposal.timestamp.desc()).limit(10).all()
        proposals_summary = [p.to_json_for_discuss() for p in proposals]

        # bundles containing this rule
        bundles = [
            {
                "id": assoc.bundle.id,
                "name": assoc.bundle.name,
                "uuid": assoc.bundle.uuid,
                "is_verified": assoc.bundle.is_verified,
            }
            for assoc in self.bundles_assoc.all()
            if assoc.bundle and assoc.bundle.access
        ]

        # update history
        history = self.rule_update_history.order_by(RuleUpdateHistory.analyzed_at.desc()).limit(5).all()
        update_history = [h.to_json() for h in history]

        # similar rules
        similar = RuleSimilarity.query.filter_by(rule_id=self.id).order_by(RuleSimilarity.score.desc()).limit(5).all()
        similar_rules = []
        for s in similar:
            r = Rule.query.get(s.similar_rule_id)
            if r:
                similar_rules.append({
                    "id": r.id,
                    "title": r.title,
                    "format": r.format,
                    "score": round(s.score * 100),
                })

        return {
            # --- identity ---
            "identity": {
                "id": self.id,
                "uuid": self.uuid,
                "original_uuid": self.original_uuid,
                "title": self.title,
                "version": self.version,
                "format": self.format,
                "is_code_format": self.is_code_format(),
            },

            # --- content ---
            "content": {
                "to_string": self.to_string,
                "description": self.description,
                "source": self.source,
                "github_path": self.github_path,
                "git_provider": self.git_provider,
                "extension": self.get_extension(),
            },

            # --- quality ---
            "quality": {
                "score": self.quality_score,
                "breakdown": self.quality_score_breakdown,
                "computed_at": self.quality_score_computed_at.strftime('%Y-%m-%d %H:%M') if self.quality_score_computed_at else None,
            },

            # --- authorship ---
            "authorship": {
                "author": self.author,
                "license": self.license,
                "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
                "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M'),
                "submitter": submitter_info,
            },

            # --- community ---
            "community": {
                "votes": {
                    "up": self.vote_up or 0,
                    "down": self.vote_down or 0,
                    "total": total_votes,
                    "ratio_percent": vote_ratio,
                },
                "favorites": {
                    "count": favorites_count,
                    "is_favorited": is_favorited,
                },
                "comments": {
                    "count": self.comments_rule.count(),
                    "latest": comments,
                },
            },

            # --- relations ---
            "relations": {
                "tags": tags,
                "attacks": [a.technique_id for a in self.attack_assocs],
                "bundles": bundles,
                "similar_rules": similar_rules,
            },

            # --- vulnerability ---
            "vulnerability": {
                "cve_ids": self.cve_id if self.cve_id is not None else [],
            },

            # --- history ---
            "history": {
                "edit_proposals": {
                    "count": self.edit_proposals.count(),
                    "latest": proposals_summary,
                },
                "update_history": update_history,
            },
        }


def compute_rule_content_hash(content):
    """MD5 of a rule's content, normalized the same way get_rule_by_content()
    used to normalize it for its SQL comparison (strip space/\\n/\\r/\\t, lowercase)."""
    if not content:
        return None
    clean = content.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '').lower()
    return hashlib.md5(clean.encode('utf-8')).hexdigest()


def compute_rule_corpus_identifier(rule_format, content):
    """Format-specific identifier that must be unique within its format's
    corpus (Suricata SID, YARA rule name, Wazuh rule ID). Lazy import — this
    module is imported by rule_core, not the other way around."""
    from app.features.rule.rule_core import _extract_corpus_identifier
    return _extract_corpus_identifier(rule_format, content)


def compute_rule_metadata(rule_format, content):
    """(references, extra_metadata) read from the rule's text — None for each when empty, so a
    rule with nothing keeps NULL columns. Lazy import, same reason as above."""
    from app.features.rule.rule_metadata_core import extract_rule_metadata
    found = extract_rule_metadata(rule_format, content)
    return found['references'] or None, found['extra'] or None


@event.listens_for(Rule.to_string, 'set')
def _rule_to_string_set(target, value, oldvalue, initiator):
    target.content_hash = compute_rule_content_hash(value)
    target.corpus_identifier = compute_rule_corpus_identifier(target.format, value)
    target.rule_references, target.extra_metadata = compute_rule_metadata(target.format, value)


@event.listens_for(Rule.format, 'set')
def _rule_format_set(target, value, oldvalue, initiator):
    # Order-independent safety: recompute if to_string was already set before
    # format (add_rule_core sets format first today, but nothing enforces that).
    if target.to_string:
        target.corpus_identifier = compute_rule_corpus_identifier(value, target.to_string)
        target.rule_references, target.extra_metadata = compute_rule_metadata(value, target.to_string)


class FormatRule(db.Model):
    """Table for all the formats of the rules"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    creation_date = db.Column(db.DateTime, index=True)
    can_be_execute = db.Column(db.Boolean, nullable=False)

    user = db.relationship('User', backref=db.backref('user_format', lazy='dynamic', cascade='all, delete-orphan'))

    def get_count_rule_with_this_format(self):
        """Return the number of rules with this format, ignoring leading/trailing spaces and case."""
        return Rule.query.filter(
            func.lower(func.trim(Rule.format)) == self.name.lower()
        ).count()

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "user_id": self.user_id,
            "can_be_execute": self.can_be_execute,
            "number_of_rule_with_this_format": self.get_count_rule_with_this_format()
        }
    
    def to_json_light(self):
        return {
            "id": self.id,
            "name": self.name,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "user_id": self.user_id,
            "can_be_execute": self.can_be_execute,
        }


class RuleFavoriteUser(db.Model):
    """Association table for User and Rule favorites."""
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    # Define the relationships with cascade option
    user = db.relationship('User', backref=db.backref('favorite_rules_assocs', lazy='dynamic', cascade='all, delete-orphan'))
    rule = db.relationship('Rule', backref=db.backref('favorited_by_users_assocs', lazy='dynamic', cascade='all, delete-orphan'))


    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "rule_id": self.rule_id,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class RequestOwnerRule(db.Model):
    """Model for user-submitted requests visible by admins or rule owners."""
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)

    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=True, index=True)
    rule_source = db.Column(db.String, nullable=True)
    # Snapshot of every rule id covered by this entry — only set for manual
    # bulk ownership grants (bulk_transfer_ownership), which span many rules
    # across possibly-different sources with no single rule_id/rule_source
    # to point to, and can't be reconstructed after the fact by filtering
    # (the rules now belong to the new owner, not whoever "concerned rules"
    # lookups would otherwise search by).
    rule_ids = db.Column(db.JSON, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Request creator
    user_id_to_send = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Owner targeted by the request

    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="pending")

    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.now(tz=datetime.timezone.utc),
        index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.now(tz=datetime.timezone.utc),
        onupdate=datetime.datetime.now(tz=datetime.timezone.utc),
        index=True
    )

    # Relationships
    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('requests', lazy='dynamic', cascade='all, delete-orphan')
    )

    user_owner_rule = db.relationship(
        'User',
        foreign_keys=[user_id_to_send],
        backref=db.backref('owned_requests', lazy='dynamic', cascade='all, delete-orphan')
    )

    rule = db.relationship(
        'Rule',
        foreign_keys=[rule_id],
        backref=db.backref('requests', lazy='dynamic', cascade='all, delete-orphan')
    )
    def get_user_name(self, user_id: int) -> str:
        user = User.query.get(user_id)
        return user.first_name if user else "Unknown"


    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "user_who_made_request": self.user.first_name if self.user else "Unknown",
            "user_id_to_send": self.user_id_to_send,
            "user_who_owns_rule": self.user_owner_rule.get_username() if self.user_owner_rule else None,
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M'),
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M'),
            "rule_id": self.rule_id,
            "rule_source": self.rule_source,
            "rule_ids": self.rule_ids,
            "rule_count": len(self.rule_ids) if self.rule_ids else None,
        }


class RuleVote(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    vote_type = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))

    user = db.relationship('User', backref=db.backref('rule_votes', lazy='dynamic', cascade='all, delete-orphan'))
    rule = db.relationship('Rule', backref=db.backref('votes', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "rule_id": self.rule_id,
            "vote_type": self.vote_type,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class InvalidRuleModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(512), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    raw_content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(tz=datetime.timezone.utc))
    rule_type = db.Column(db.String(50), default="Sigma") 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    url = db.Column(db.Text, nullable=False)
    license = db.Column(db.Text)

    github_path = db.Column(db.String , nullable=True)
    # Git host the item comes from: github | gitlab | gitea | bitbucket | generic
    # (None = not from a git repository). Kept up to date by the listeners at
    # the end of this file — see git_provider.detect_provider().
    git_provider = db.Column(db.String(20), nullable=True, index=True)

    user = db.relationship('User', backref=db.backref('user', lazy='dynamic', cascade='all, delete-orphan'))

    def to_json(self):
        return {
            'id': self.id,
            'file_name': self.file_name,
            'error_message': self.error_message,
            'raw_content': self.raw_content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'rule_type': self.rule_type,
            "user_id": self.user_id,
            "url": self.url,
            "license": self.license,
            "github_path": self.github_path if self.github_path else None,
            "git_provider": self.git_provider,
            # Sent eagerly (not just user_id) so the UI can show the editor's
            # name right away instead of a "?" placeholder until a UserChip
            # hover triggers its own lazy /account/user_mini/<id> fetch.
            "editor_name": (f"{self.user.first_name} {self.user.last_name}".strip() if self.user else None),
            "editor_avatar": (self.user.get_avatar_url() if self.user else None),
        }


class RuleUpdateHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'), nullable=False, index=True)
    rule_title = db.Column(db.String(255), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    message = db.Column(db.Text, nullable=True)
    new_content = db.Column(db.Text, nullable=True)
    old_content = db.Column(db.Text, nullable=True)
    analyzed_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    analyzed_at = db.Column(db.DateTime, index=True)
    manuel_submit = db.Column(db.Boolean, default=False, nullable=True)

    # Metadata snapshot (title/author/owner/tags/status/...) before and after this
    # version — lets the history UI show field-level changes (e.g. "Owner: X -> Y")
    # for edits that don't touch the rule content at all. NULL on rows created
    # before this was introduced; only new/edited rows going forward carry it.
    old_snapshot = db.Column(db.JSON, nullable=True)
    new_snapshot = db.Column(db.JSON, nullable=True)
    # 'created' | 'content' | 'metadata' | 'ownership' | 'mixed' — NULL on legacy rows.
    change_type = db.Column(db.String(20), nullable=True)

    analyzed_by = db.relationship("User", backref=db.backref("rule_updates", lazy='dynamic', cascade='all, delete-orphan'))
    rule = db.relationship("Rule", backref=db.backref("rule_update_history", lazy='dynamic', cascade='all, delete-orphan'))

    def get_rule_format(self):
        """
        Returns the format of the rule with rule_id
        """
        rule = Rule.query.get(self.rule_id)
        if rule:
            return rule.format
        return None
    def get_rule_source(self):
        """
        Returns the source of the rule with rule_id
        """
        rule = Rule.query.get(self.rule_id)
        if rule:
            return rule.source
        return None
    
    def to_json(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_title": self.rule_title,
            "success": self.success,
            "message": self.message,
            "new_content": self.new_content,
            "old_content": self.old_content,
            "analyzed_by_user_id": self.analyzed_by_user_id,
            "analyzed_at": self.analyzed_at.strftime('%Y-%m-%d %H:%M'),
            "analyzed_by_user_name": self.analyzed_by.first_name,
            "analyzed_by_avatar": self.analyzed_by.get_avatar_url() if self.analyzed_by else None,
            "rule_format": self.get_rule_format(),
            "rule_source": self.get_rule_source(),
            "manuel_submit": self.manuel_submit if self.manuel_submit else False,
            "old_snapshot": self.old_snapshot,
            "new_snapshot": self.new_snapshot,
            "change_type": self.change_type,
        }


class RuleScope(db.Model):
    """A user's declaration of the environment where a rule works (or not). A user
    can declare several per rule, never twice exactly the same one
    (rule_core.save_scope / scope_signature)."""
    __tablename__ = 'rule_scope'

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid       = db.Column(db.String(36), unique=True, nullable=False, index=True)
    rule_id    = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id',  ondelete='CASCADE'), nullable=False, index=True)

    works      = db.Column(db.Boolean, nullable=False, default=True)   # True = "works for me"
    entries    = db.Column(db.JSON,    nullable=False, default=list)    # [{"key": "os", "value": "linux"}, …]
    comment    = db.Column(db.Text,    nullable=True)
    # Callables: evaluated on each insert / update (a bare datetime.now(...)
    # here would be computed once at import, giving every row the same date).
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc),
                           onupdate=lambda: datetime.datetime.now(tz=datetime.timezone.utc))

    rule = db.relationship('Rule', backref=db.backref('scope_declarations', lazy='dynamic',
                                                       cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('scope_declarations', lazy='dynamic'))

    def to_json(self):
        return {
            'id':         self.id,
            'uuid':       self.uuid,
            'user_id':    self.user_id,
            'username':   self.user.get_username() if self.user else 'Unknown',
            'avatar':     self.user.get_avatar_url() if self.user else None,
            'works':      self.works,
            'entries':    self.entries or [],
            'comment':    self.comment or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
        }


class FieldParserConfig(db.Model):
    """Saved configurations for the bulk admin parser tools.

    config_type discriminates which tool a row belongs to:
      - 'field_parser'   — the base license/author/... field extractor (original use)
      - 'platform_tags'  — the OS/platform tag-detection pattern list
    Both just store a named, admin-authored JSON blob; a single generic table is
    enough since neither has its own relations, and this keeps the saved-config
    CRUD (list/save/update/delete) identical for every future admin parser tool.
    """
    __tablename__ = 'field_parser_config'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    config      = db.Column(db.JSON, nullable=False, default=dict)
    config_type = db.Column(db.String(50), nullable=False, default='field_parser', server_default='field_parser')
    created_at  = db.Column(db.DateTime, default=lambda: datetime.datetime.now(tz=datetime.timezone.utc))
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    user = db.relationship('User', backref=db.backref('field_parser_configs', lazy='dynamic'))

    def to_json(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'config':      self.config,
            'config_type': self.config_type,
            'created_at':  self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'user_id':     self.user_id,
        }


# Imported last: these models are only used inside methods, and importing them
# at the top would be circular.
from app.core.db_class.comment import Comment  # noqa: E402
from app.core.db_class.rule_proposal import RuleEditProposal  # noqa: E402
from app.core.db_class.similarity import RuleSimilarity  # noqa: E402
from app.core.db_class.user import User  # noqa: E402
