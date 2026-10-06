"""Database helpers for assertions."""
from app import db


def reload(obj):
    """Fresh copy of `obj` from the database — what a request actually stored —
    or None if the row is gone."""
    from sqlalchemy import inspect
    identity = inspect(obj).identity   # read without touching the (maybe deleted) row
    db.session.expire_all()
    return db.session.get(type(obj), identity)


def count(model, **filters):
    db.session.expire_all()
    return model.query.filter_by(**filters).count()
