"""Database helpers for assertions."""
from app import db


def reload(obj):
    """Fresh copy of `obj` from the database — what a request actually stored."""
    db.session.expire_all()
    return db.session.get(type(obj), obj.id)


def count(model, **filters):
    db.session.expire_all()
    return model.query.filter_by(**filters).count()
