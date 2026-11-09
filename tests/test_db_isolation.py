"""The shared database baseline survives commits, rollbacks and failed tests."""
import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.core.db_class.user import User


@pytest.fixture(params=["_db_transaction", "_db_snapshot"])
def isolate_database(request):
    return request.getfixturevalue(request.param)


def test_commits_are_visible_across_contexts_and_then_discarded(_app, isolate_database):
    with _app.app_context():
        baseline = [(u.id, u.first_name) for u in User.query.order_by(User.id)]

    with isolate_database(_app):
        with _app.app_context():
            User.query.filter_by(email="t@t.t").one().first_name = "Changed"
            db.session.delete(User.query.filter_by(email="neo@admin.admin").one())
            db.session.add(User(email="isolation@tests.rulezet", first_name="Added"))
            db.session.commit()
        with _app.app_context():
            assert User.query.filter_by(email="t@t.t").one().first_name == "Changed"
            assert User.query.filter_by(email="neo@admin.admin").first() is None
            assert User.query.filter_by(email="isolation@tests.rulezet").one()
        # A later request must see the committed account, even after the
        # previous app context removed its SQLAlchemy session.
        client = _app.test_client()
        with _app.app_context():
            user_id = User.query.filter_by(email="t@t.t").one().id
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        assert client.get("/account/").status_code == 200

    with isolate_database(_app), _app.app_context():
        assert [(u.id, u.first_name) for u in User.query.order_by(User.id)] == baseline


def test_session_rollback_preserves_prior_commits(_app, isolate_database):
    with isolate_database(_app), _app.app_context():
        user = User.query.filter_by(email="t@t.t").one()
        user.first_name = "Committed"
        db.session.commit()
        user.first_name = "Rolled back"
        db.session.flush()
        db.session.rollback()
        assert user.first_name == "Committed"

        # A failed flush must also leave the outer transaction usable.
        db.session.add(User(email="t@t.t"))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
        user.last_name = "Still usable"
        db.session.commit()

    with isolate_database(_app), _app.app_context():
        user = User.query.filter_by(email="t@t.t").one()
        assert (user.first_name, user.last_name) == ("theo", "theo")


def test_failed_test_restores_database_and_config(_app, isolate_database):
    original_secret = _app.config["SECRET_KEY"]
    try:
        with isolate_database(_app), _app.app_context():
            _app.config["SECRET_KEY"] = "changed"
            _app.config["TEST_ONLY_SETTING"] = True
            User.query.filter_by(email="t@t.t").one().first_name = "Changed"
            db.session.commit()
            raise RuntimeError("simulated test failure")
    except RuntimeError as error:
        assert str(error) == "simulated test failure"
    else:
        pytest.fail("Database isolation must propagate the test failure")

    with isolate_database(_app), _app.app_context():
        assert _app.config["SECRET_KEY"] == original_secret
        assert "TEST_ONLY_SETTING" not in _app.config
        assert User.query.filter_by(email="t@t.t").one().first_name == "theo"


def test_worker_commit_survives_parent_context_teardown(_app, _db_snapshot):
    with _db_snapshot(_app):
        with _app.app_context():
            User.query.count()  # The parent context has an active ORM session.
            with _app.app_context():
                User.query.filter_by(email="t@t.t").one().first_name = "Worker commit"
                db.session.commit()
        with _app.app_context():
            assert User.query.filter_by(email="t@t.t").one().first_name == "Worker commit"

    with _app.app_context():
        assert User.query.filter_by(email="t@t.t").one().first_name == "theo"
