"""Legacy seed data, reused with per-test transaction isolation."""
import sys
import os


sys.path.append(os.getcwd())

from app.core.utils.init_db import create_admin_test, create_default_user, create_rule_test, create_user_test
import pytest


@pytest.fixture(scope="session")
def _legacy_seed():
    def seed():
        create_user_test()
        create_admin_test()
        create_rule_test()
        create_default_user()  # for the rule with no author

    return seed


@pytest.fixture(scope="session")
def _app(_test_app_factory, _legacy_seed):
    return _test_app_factory(_legacy_seed)


@pytest.fixture
def app(_app, _db_transaction):
    with _db_transaction(_app):
        yield _app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
