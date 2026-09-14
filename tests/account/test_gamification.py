import datetime

from app import db
from app.core.db_class.db import Rule, Bundle, User, Gamification, UserBadge
from app.features.account import account_core as AccountModel


def _make_user(email):
    u = User(first_name="T", last_name="U", email=email, password="x", is_verified=True)
    db.session.add(u)
    db.session.commit()
    return u


def test_rules_owned_excludes_soft_deleted(app):
    with app.app_context():
        user = _make_user("owner1@test.local")
        db.session.add(Rule(user_id=user.id, format="yara", title="r1", is_deleted=False))
        db.session.add(Rule(user_id=user.id, format="yara", title="r2", is_deleted=True))
        db.session.commit()

        from app.features.rule.rule_core import get_count_rules_by_user_id
        assert get_count_rules_by_user_id(user.id) == 1


def test_record_contribution_streak(app):
    with app.app_context():
        user = _make_user("streak@test.local")
        g = Gamification(user_id=user.id, uuid="g-streak")
        db.session.add(g)
        db.session.commit()

        AccountModel._record_contribution(g)
        assert g.consecutive_days_active == 1
        first_date = g.last_contribution_date

        # same-day repeat leaves the streak unchanged
        AccountModel._record_contribution(g)
        assert g.consecutive_days_active == 1

        # exactly one day later bumps it
        g.last_contribution_date = first_date - datetime.timedelta(days=1)
        AccountModel._record_contribution(g)
        assert g.consecutive_days_active == 2

        # a multi-day gap resets it to 1
        g.last_contribution_date = first_date - datetime.timedelta(days=5)
        AccountModel._record_contribution(g)
        assert g.consecutive_days_active == 1


def test_evaluate_badges_is_idempotent(app):
    with app.app_context():
        user = _make_user("badge@test.local")
        g = Gamification(user_id=user.id, uuid="g-badge", total_points=1500)
        db.session.add(g)
        db.session.commit()

        new_badges = AccountModel.evaluate_badges(g)
        assert 'bronze_contributor' in new_badges

        # running again against the same state must not re-flag it
        assert AccountModel.evaluate_badges(g) == []
        assert UserBadge.query.filter_by(user_id=user.id, badge_key='bronze_contributor').count() == 1


def test_leaderboard_accepts_new_sort_keys():
    for key in ('bundles_owned', 'rule_tests_contributed', 'attack_mappings_contributed'):
        assert key in AccountModel._LEADERBOARD_SORT_COLUMNS


def test_recompute_gamification_batch(app):
    with app.app_context():
        user = _make_user("batch@test.local")
        db.session.add(Rule(user_id=user.id, format="yara", title="r1", is_deleted=False, vote_up=3, vote_down=1))
        db.session.add(Bundle(uuid="bundle-batch", name="bundle1", user_id=user.id, vote_up=2, vote_down=0))
        db.session.commit()

        touched = AccountModel.recompute_gamification_batch([user.id])
        assert touched == 1

        profile = Gamification.query.filter_by(user_id=user.id).first()
        assert profile.rules_owned == 1
        assert profile.bundles_owned == 1
        assert profile.rules_popular_score == 4  # (3 rule + 2 bundle) - (1 rule + 0 bundle)


def _login_admin(client):
    return client.post("/account/login", data={"email": "admin@admin.admin", "password": "admin"},
                        follow_redirects=True)


def test_contributor_and_how_to_earn_points_pages_render(client):
    _login_admin(client)

    resp = client.get("/account/contributor")
    assert resp.status_code == 200

    resp2 = client.get("/account/how_to_earn_points")
    assert resp2.status_code == 200
    assert b"Bronze Contributor" in resp2.data
