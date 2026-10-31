"""Daily clean-up of unverified, never-used accounts (unverified_cleanup_core.py, job purge_unverified_users,
template unverified_accounts_cleanup): only bots / abandoned sign-ups go, never a real user."""
import datetime

from app import db
from app.core.db_class.activity_log import ActivityLog
from app.core.db_class.job import BackgroundJob
from app.core.db_class.user import User
from app.core.utils.activity_log import log_activity
from app.features.account import unverified_cleanup_core as C
from tests_new.helpers.account import captured_mails, register_form
from tests_new.helpers.rules import make_rule

OLD = datetime.datetime.utcnow() - datetime.timedelta(days=3)


def _signup(client, **form_overrides):
    """A real sign-up through the public API (what a bot does), made 3 days old."""
    form = register_form(**form_overrides) if form_overrides else register_form()
    with captured_mails():
        client.post("/api/account/public/register", json=form)
    user = User.query.filter_by(email=form["email"]).one()
    log_activity("user.register", "New user registered", target_type="user", target_id=user.id, actor_id=user.id)
    user.created_at = OLD
    db.session.commit()
    return user


def test_only_unused_unverified_local_accounts_are_candidates(app, users):
    client = app.test_client()
    bot = _signup(client)
    recent = _signup(client)
    recent.created_at = datetime.datetime.utcnow()                    # signed up 1 minute ago: grace period
    sso = _signup(client)
    sso.auth_provider = "oidc"                                         # vouched for by its identity provider
    checked = _signup(client)
    checked.identity_verified = True
    with_rule = _signup(client)                                        # used Rulezet (e.g. through its API key)
    make_rule(with_rule)
    acted = _signup(client)
    log_activity("rule.create", "x", actor_id=acted.id)
    db.session.commit()
    found = C.find_candidates(24)
    assert [u.id for u in found["delete"]] == [bot.id]
    assert found["kept_used"] == 2                                     # with_rule and acted
    assert all(u.is_verified for u in (users.owner, users.user, users.admin))   # verified users never looked at


def test_purge_deletes_and_makes_the_signup_logs_private(app, users):
    bot = _signup(app.test_client())
    log_id = ActivityLog.query.filter_by(action="user.register", target_id=bot.id).one().id
    report = C.purge(24, 200, dry_run=True)
    assert report["candidates"] == 1 and db.session.get(User, bot.id) is not None   # dry run: nothing changes
    report = C.purge(24, 200, dry_run=False)
    db.session.expire_all()
    assert report["deleted"] == 1 and db.session.get(User, bot.id) is None
    assert db.session.get(ActivityLog, log_id).is_public is False


def test_too_many_at_once_deletes_nothing(app, users):
    client = app.test_client()
    bots = [_signup(client) for _ in range(3)]
    report = C.purge(24, max_per_run=2, dry_run=False)
    assert report["aborted"] and report["deleted"] == 0
    assert all(db.session.get(User, b.id) for b in bots)


def test_job_and_template(app, users):
    from app.features.jobs.job_handlers import handle_purge_unverified_users
    bot = _signup(app.test_client())
    job = BackgroundJob(uuid="purge-1", job_type="purge_unverified_users", status="running", total=0, done=0,
                        created_by=users.admin.id, payload={"dry_run": False, "grace_hours": "24", "max_per_run": "200"})
    db.session.add(job)
    db.session.commit()
    handle_purge_unverified_users(job, app)
    db.session.expire_all()
    assert db.session.get(User, bot.id) is None
    from app.core.utils.app_settings import get_setting
    spec = get_setting("workflows.templates")["unverified_accounts_cleanup"]["spec"]
    assert spec["tasks"][0]["task_type"] == "purge_unverified_users"
    assert spec["tasks"][0]["target_payload"]["max_per_run"] == 200
