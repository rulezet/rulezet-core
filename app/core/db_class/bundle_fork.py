"""Bundle forks and merge requests — "GitHub for bundles" (docs/future/bundle_forks.md).

A fork is an ordinary Bundle with `forked_from_id` (columns on Bundle). These tables hold:
  - BundleForkRule: in a bundle, a rule that stands for another one (a copy made to edit a rule its
    owner can't edit, "copy-on-write"), so diffs keep matching the copy with its original;
  - BundleMergeRequest: "take these changes from bundle A into bundle B" — fork → upstream
    (contribute) or upstream → fork (sync), reviewed item by item, conflicts resolved, merged.
Logic: app/features/bundle/bundle_fork_core.py.
"""
import datetime

from app import db


def _now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


class BundleForkRule(db.Model):
    """In `bundle_id`, the rule `copy_rule_id` stands for `original_rule_uuid` (made by copy-on-write
    or brought in by a merge that linked the copy)."""
    __tablename__ = 'bundle_fork_rule'
    __table_args__ = (db.UniqueConstraint('bundle_id', 'copy_rule_id', name='uq_bundle_fork_rule_copy'),)

    id                 = db.Column(db.Integer, primary_key=True)
    bundle_id          = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False, index=True)
    original_rule_uuid = db.Column(db.String(255), nullable=False, index=True)
    copy_rule_id       = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at         = db.Column(db.DateTime, default=_now)


class BundleMergeRequest(db.Model):
    """Changes of `source` proposed to `target`. `items` is the changeset computed against the common
    ancestor: one entry per rule / file / folder / metadata change, each with its own decision."""
    __tablename__ = 'bundle_merge_request'

    STATUSES = ('open', 'merged', 'closed', 'stale')

    id               = db.Column(db.Integer, primary_key=True)
    uuid             = db.Column(db.String(36), unique=True, nullable=False, index=True)
    source_bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='SET NULL'), nullable=True, index=True)
    source_bundle_uuid = db.Column(db.String(255), nullable=True)
    target_bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    kind             = db.Column(db.String(16), nullable=False, default='contribute')   # contribute | sync
    title            = db.Column(db.String(255), nullable=False)
    message          = db.Column(db.Text, nullable=True)        # markdown
    status           = db.Column(db.String(16), nullable=False, default='open', index=True)

    items            = db.Column(db.JSON, nullable=True)        # changeset (bundle_fork_core.compute_changes)
    base_snapshot    = db.Column(db.JSON, nullable=True)        # common ancestor used for `items`
    computed_at      = db.Column(db.DateTime, nullable=True)

    reviewed_by_id   = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    reviewed_at      = db.Column(db.DateTime, nullable=True)
    review_note      = db.Column(db.Text, nullable=True)
    merged_summary   = db.Column(db.JSON, nullable=True)        # what the merge did, item by item

    created_at       = db.Column(db.DateTime, default=_now, index=True)
    updated_at       = db.Column(db.DateTime, default=_now, onupdate=_now)

    source = db.relationship('Bundle', foreign_keys=[source_bundle_id])
    target = db.relationship('Bundle', foreign_keys=[target_bundle_id])
    user = db.relationship('User', foreign_keys=[user_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])

    def counts(self):
        items = self.items or []
        return {
            'total': len(items),
            'conflicts': sum(1 for i in items if i.get('conflict')),
            'unresolved': sum(1 for i in items if i.get('conflict') and i.get('decision') not in ('source', 'target')),
            'accepted': sum(1 for i in items if i.get('decision') in ('accept', 'source')),
        }

    def to_json(self, with_items=False):
        def who(u):
            return {'id': u.id, 'name': f"{u.first_name or ''} {u.last_name or ''}".strip()} if u else None

        def bundle(b, uuid=None):
            return {'id': b.id, 'uuid': b.uuid, 'name': b.name, 'user_id': b.user_id, 'access': bool(b.access)} \
                if b else ({'id': None, 'uuid': uuid, 'name': '(deleted bundle)'} if uuid else None)
        out = {
            'uuid': self.uuid, 'kind': self.kind, 'title': self.title, 'message': self.message or '',
            'status': self.status, 'source': bundle(self.source, self.source_bundle_uuid),
            'target': bundle(self.target), 'user': who(self.user), 'reviewed_by': who(self.reviewed_by),
            'review_note': self.review_note or '', 'counts': self.counts(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
            'reviewed_at': self.reviewed_at.strftime('%Y-%m-%d %H:%M') if self.reviewed_at else None,
            'computed_at': self.computed_at.strftime('%Y-%m-%d %H:%M') if self.computed_at else None,
            'merged_summary': self.merged_summary,
        }
        if with_items:
            out['items'] = self.items or []
        return out
