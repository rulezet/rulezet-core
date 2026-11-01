"""Daily clean-up of the accounts whose email was never verified (unverified_cleanup_core.py, job purge_unverified_users,
template unverified_accounts_cleanup): never an admin, a system account or the account running it."""
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


def test_every_unverified_local_account_is_a_candidate_except_protected(app, users):
    client = app.test_client()
    bot = _signup(client)
    recent = _signup(client)
    recent.created_at = datetime.datetime.utcnow()                    # signed up 1 minute ago: grace period
    sso = _signup(client)
    sso.auth_provider = "oidc"                                         # verified by its identity provider
    with_rule = _signup(client)                                        # used Rulezet: still deleted (email never verified)
    rule = make_rule(with_rule)
    unverified_admin = _signup(client)
    unverified_admin.admin = True                                      # never an admin
    runner = _signup(client)                                           # never the account running the clean-up
    db.session.commit()
    found = C.find_candidates(24, protect_ids=[runner.id])
    assert sorted(u.id for u in found["delete"]) == sorted([bot.id, with_rule.id])
    assert found["kept_protected"] == 2
    assert all(u.is_verified for u in (users.owner, users.user, users.admin))   # verified users never looked at
    C.purge(24, 200, dry_run=False, protect_ids=[runner.id])
    db.session.expire_all()
    from app.core.db_class.rule import Rule
    assert db.session.get(User, with_rule.id) is None
    assert db.session.get(Rule, rule.id).user_id != with_rule.id                  # its rule goes to the admin


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
    backup, purge_task = spec["tasks"]
    assert backup["task_type"] == "db_backup_rotate"                                  # a checked backup first,
    assert purge_task["trigger"] == {"after": "backup", "condition": "success"}       # the purge only if it worked
    assert purge_task["task_type"] == "purge_unverified_users" and purge_task["target_payload"]["max_per_run"] == 200
