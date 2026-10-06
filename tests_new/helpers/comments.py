"""Comment factories — the unified comment thread (/api/comments, table
comment_v2) on rules and bundles, and the legacy rule comments (/rule/...,
table comment).

A thread hangs on an object, named by (object_type, object_id); the objects
used here are rules (helpers/rules.py) and bundles (below).
"""
import datetime
import itertools
import uuid

from app import db
from app.core.db_class.db import Bundle, Comment, UnifiedComment

API = "/api/comments"

_counter = itertools.count(1)


def _now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


def make_bundle(owner, *, public=True, **overrides):
    """A bundle owned by `owner` — public (everyone can read it) or private
    (only its owner and admins can)."""
    n = next(_counter)
    fields = dict(uuid=str(uuid.uuid4()), name=f"Test bundle {n}", description=f"Bundle {n}",
                  user_id=owner.id, access=public, created_at=_now(), updated_at=_now())
    fields.update(overrides)
    bundle = Bundle(**fields)
    db.session.add(bundle)
    db.session.commit()
    return bundle


def trash(rule):
    """Soft-delete `rule` (what "delete" does): it disappears for everyone."""
    rule.is_deleted = True
    rule.deleted_at = _now()
    db.session.commit()
    return rule


def target(obj):
    """(object_type, object_id) of a rule or a bundle."""
    return ("bundle" if isinstance(obj, Bundle) else "rule"), obj.id


def make_comment(author, on, *, parent=None, content=None, active=True):
    """A comment by `author` on `on` (a rule or a bundle), optionally a reply
    to `parent`."""
    object_type, object_id = target(on)
    comment = UnifiedComment(
        uuid=str(uuid.uuid4()),
        content=content or f"Comment {next(_counter)}",
        object_type=object_type,
        object_id=object_id,
        parent_id=parent.id if parent else None,
        depth=parent.depth + 1 if parent else 0,
        root_id=(parent.root_id or parent.id) if parent else None,
        created_by=author.id,
        created_at=_now(),
        updated_at=_now(),
        is_active=active,
    )
    if not active:
        comment.deleted_at = _now()
        comment.deleted_by = author.id
    db.session.add(comment)
    db.session.commit()
    return comment


def new_comment(on, content="A new comment", **extra):
    """What the comment box posts to POST /api/comments/."""
    object_type, object_id = target(on)
    payload = {"object_type": object_type, "object_id": object_id, "content": content}
    payload.update(extra)
    return payload


def list_url(on, **params):
    object_type, object_id = target(on)
    query = "&".join(f"{k}={v}" for k, v in {"object_type": object_type, "object_id": object_id, **params}.items())
    return f"{API}/?{query}"


def mention(user):
    """The token the @mention picker inserts for `user`."""
    return f"@[{user.first_name} {user.last_name}]({user.id})"


def make_legacy_comment(author, rule, *, parent=None, content=None):
    """A comment of the legacy rule comment system (/rule/get_comments…)."""
    comment = Comment(
        uuid=str(uuid.uuid4()),
        rule_id=rule.id,
        user_id=author.id,
        user_name=f"{author.first_name} {author.last_name}",
        content=content or f"Legacy comment {next(_counter)}",
        created_at=_now(),
        updated_at=_now(),
        parent_comment_id=parent.id if parent else None,
    )
    db.session.add(comment)
    db.session.commit()
    return comment
