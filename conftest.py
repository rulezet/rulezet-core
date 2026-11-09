"""Database infrastructure shared by the legacy and replacement test suites."""
from contextlib import contextmanager
from copy import deepcopy
import sqlite3

import pytest


@pytest.fixture(scope="session")
def _test_app_factory(tmp_path_factory):
    """Build each suite's schema and baseline once, in a private SQLite file."""
    from app import create_app, db
    from config import TestingConfig

    apps = []

    def build(seed):
        directory = tmp_path_factory.mktemp("rulezet-db")
        # Override before init_app: changing the URI afterwards cannot change
        # SQLAlchemy's engine. Separate paths also isolate concurrent pytest runs.
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("FLASKENV", "testing")
            patch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI",
                          f"sqlite:///{directory / 'test.sqlite'}")
            patch.setattr(TestingConfig, "SESSION_FILE_DIR", str(directory / "sessions"), raising=False)
            app = create_app(start_worker=False)
        apps.append(app)
        app.config.update(
            TESTING=True,
            SERVER_NAME=f"{app.config.get('FLASK_URL')}:{app.config.get('FLASK_PORT')}",
        )
        with app.app_context():
            db.create_all()
            seed()
            db.session.remove()
        return app

    yield build

    for app in apps:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


@pytest.fixture
def _test_state():
    """Reset process-local state alongside the database."""
    from app.core.utils.app_settings import clear_cache
    from app.features.account import account

    @contextmanager
    def reset(app):
        # SESSION_SQLALCHEMY contains the live extension, not copyable data.
        config = {key: deepcopy(value) if isinstance(value, (dict, list, set)) else value
                  for key, value in app.config.items()}
        clear_cache()
        account._login_failures.clear()
        try:
            yield
        finally:
            app.config.clear()
            app.config.update(config)
            clear_cache()
            account._login_failures.clear()

    return reset


@pytest.fixture
def _db_transaction(request, _test_state, _db_snapshot):
    """Keep real ORM commits/request visibility, then discard all test writes."""
    from app import db

    if request.node.get_closest_marker("independent_db"):
        return _db_snapshot

    @contextmanager
    def isolate(app):
        with app.app_context():
            db.session.remove()
            engines = dict(db.engines)
            connection = db.engine.connect()
            # SQLite's legacy transaction mode doesn't BEGIN for a SAVEPOINT.
            # An explicit outer transaction keeps released savepoints rollbackable.
            connection.exec_driver_sql("BEGIN")
            transaction = connection.get_transaction()
            session_options = dict(db.session.session_factory.kw)
            db.session.configure(join_transaction_mode="create_savepoint")
            db.engines[None] = connection
        try:
            with _test_state(app):
                yield app
        finally:
            with app.app_context():
                try:
                    db.session.remove()
                finally:
                    db.engines.clear()
                    db.engines.update(engines)
                    db.session.session_factory.kw.clear()
                    db.session.session_factory.kw.update(session_options)
                    try:
                        transaction.rollback()
                    finally:
                        connection.close()

    return isolate


@pytest.fixture
def _db_snapshot(_test_state):
    """For worker tests needing independent commits across nested app contexts.

    Releasing a worker's savepoint cannot commit past an enclosing context's
    rollback. These tests use normal connections and restore the baseline with
    SQLite's backup API instead, without rebuilding tables or rerunning seeds.
    """
    from app import db

    @contextmanager
    def isolate(app):
        snapshot = sqlite3.connect(":memory:")
        try:
            with app.app_context():
                db.session.remove()
                engine = db.engine
                with engine.connect() as connection:
                    connection.connection.driver_connection.backup(snapshot)
            try:
                with _test_state(app):
                    yield app
            finally:
                with app.app_context():
                    db.session.remove()
                    engine.dispose()
                    with engine.connect() as connection:
                        snapshot.backup(connection.connection.driver_connection)
        finally:
            snapshot.close()

    return isolate
