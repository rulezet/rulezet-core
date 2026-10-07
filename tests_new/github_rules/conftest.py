"""GitHub for rules: every test runs against the fake GitHub of
tests_new/helpers/github.py — nothing here can reach the network — and with the
live Sync Schedule scheduler paused (triggers are registered, never fired)."""
from unittest import mock

import pytest

from tests_new.helpers.github import FakeGitHub
from tests_new.helpers.users import make_user_with_permission


@pytest.fixture(autouse=True)
def github(app, tmp_path, monkeypatch):
    return FakeGitHub(tmp_path, monkeypatch)


@pytest.fixture(autouse=True)
def _paused_scheduler(monkeypatch):
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.features.rule.rule_from_github.sync_schedule import scheduler_engine

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.start(paused=True)
    monkeypatch.setattr(scheduler_engine, "_scheduler", scheduler)
    yield scheduler
    scheduler.shutdown(wait=False)


@pytest.fixture(autouse=True)
def _no_job_notifications():
    with mock.patch("app.features.notification.notification_core.create_job_notification"):
        yield


@pytest.fixture
def manager(users):
    """A non-admin holding `github.manage` (the GitHub Manager role)."""
    return make_user_with_permission("github.manage", name="github-manager")


@pytest.fixture
def clients_and_manager(clients, client_as, manager):
    """The four standard clients plus "manager"."""
    return {**clients, "manager": client_as(manager)}
