"""Contributor leaderboard (issue #91): equal scores share a rank (1, 2, 2, 4) and pages never repeat or
skip a contributor — account_core.get_leaderboard_paginated."""
import uuid

import pytest

from app import db
from app.core.db_class.gamification import Gamification
from app.features.account.account_core import get_leaderboard_paginated
from tests_new.helpers.users import make_user


def _scores(app_users, values):
    """One contributor per score (in order), on top of the users the fixtures made (score 0)."""
    Gamification.query.delete()
    db.session.commit()
    for i, points in enumerate(values):
        user = make_user(f"lb{i}-{uuid.uuid4().hex[:6]}")
        db.session.add(Gamification(uuid=str(uuid.uuid4()), user_id=user.id, total_points=points))
    db.session.commit()


@pytest.mark.parametrize("direction", ["desc", "asc"])
def test_ties_share_a_rank_and_pages_are_stable(direction, clients, users):
    _scores(users, [50, 30, 30, 10] + [0] * 9)            # 13 contributors, 9 tied at zero
    seen, rows = [], []
    for page in (1, 2, 3, 4, 5):
        data = get_leaderboard_paginated(page, 3, "total_points", direction)
        rows += data["leaderboard"]
    seen = [r["user_id"] for r in rows]
    assert len(seen) == 13 and len(set(seen)) == 13          # nobody twice, nobody skipped
    ranks = {(r["total_points"], r["rank"]) for r in rows}
    if direction == "desc":
        assert ranks == {(50, 1), (30, 2), (10, 4), (0, 5)}  # competition ranking: 1, 2, 2, 4, 5…
    else:
        assert ranks == {(0, 1), (10, 10), (30, 11), (50, 13)}
    again = []
    for page in (1, 2, 3, 4, 5):
        data = get_leaderboard_paginated(page, 3, "total_points", direction)
        again += [r["user_id"] for r in data["leaderboard"]]
    assert again == seen                                      # same order on every visit
