import datetime
import uuid as uuid_mod

from flask_login import current_user
from sqlalchemy import or_, select

from app import db
from app.core.db_class.db import RuleTest, RuleTestResult


# ── Visibility helpers ────────────────────────────────────────────────────────

def _test_query_for_viewer(viewer):
    """Base RuleTest query scoped to what viewer is allowed to see."""
    q = RuleTest.query
    if viewer.is_anonymous():
        return q.filter_by(is_public=True)
    if viewer.is_admin():
        return q
    return q.filter(or_(RuleTest.is_public == True, RuleTest.user_id == viewer.id))


def assert_test_readable(test, viewer):
    """Abort 403 if viewer cannot read this test."""
    from flask import abort
    if not test.is_public:
        if viewer.is_anonymous() or (viewer.id != test.user_id and not viewer.is_admin()):
            abort(403)


def assert_test_writable(test, viewer):
    """Abort 403 if viewer cannot modify/delete this test."""
    from flask import abort
    if viewer.id != test.user_id and not viewer.is_admin():
        abort(403)


# ── Queries ───────────────────────────────────────────────────────────────────

def get_test_by_uuid(uuid: str, viewer=None) -> RuleTest | None:
    test = RuleTest.query.filter_by(uuid=uuid).first()
    if test and viewer:
        assert_test_readable(test, viewer)
    return test


def get_tests_for_rule(rule_id: int, viewer, page: int = 1, per_page: int = 20, min_score: float = 0.01):
    # Include single tests targeting this rule directly (always relevant) AND bulk
    # tests where this rule actually scored something (>= min_score or matched) —
    # a bulk sweep where this rule barely registered isn't meaningful history for it.
    bulk_test_ids = select(RuleTestResult.test_id).where(
        RuleTestResult.rule_id == rule_id,
        or_(RuleTestResult.score >= min_score, RuleTestResult.matched == True)
    ).scalar_subquery()
    q = _test_query_for_viewer(viewer).filter(
        or_(RuleTest.rule_id == rule_id, RuleTest.id.in_(bulk_test_ids))
    )
    return q.order_by(RuleTest.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)


def get_my_tests(user_id: int, page: int = 1, per_page: int = 20, test_type: str = None):
    q = RuleTest.query.filter_by(user_id=user_id)
    if test_type:
        q = q.filter_by(test_type=test_type)
    return q.order_by(RuleTest.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)


def count_visible_tests_for_rule(rule_id: int, viewer, min_score: float = 0.01) -> int:
    bulk_test_ids = select(RuleTestResult.test_id).where(
        RuleTestResult.rule_id == rule_id,
        or_(RuleTestResult.score >= min_score, RuleTestResult.matched == True)
    ).scalar_subquery()
    return _test_query_for_viewer(viewer).filter(
        or_(RuleTest.rule_id == rule_id, RuleTest.id.in_(bulk_test_ids))
    ).count()


# ── Create ────────────────────────────────────────────────────────────────────

def create_test(
    user_id: int,
    test_type: str,
    fmt: str,
    input_type: str,
    input_data: str,
    input_label: str = None,
    rule_id: int = None,
    bulk_filters: dict = None,
    label: str = None,
    notes: str = None,
    is_public: bool = False,
    is_dangerous: bool = False,
    danger_description: str = None,
) -> RuleTest:
    test = RuleTest(
        uuid         = str(uuid_mod.uuid4()),
        user_id      = user_id,
        rule_id      = rule_id,
        test_type    = test_type,
        format       = fmt,
        input_type   = input_type,
        input_data   = input_data,
        input_label  = input_label,
        bulk_filters = bulk_filters,
        label        = label,
        notes        = notes,
        is_public    = is_public,
        is_dangerous       = bool(is_dangerous),
        danger_description = danger_description if is_dangerous else None,
        status       = 'pending',
    )
    db.session.add(test)
    db.session.commit()
    return test


def create_result(
    test_id: int,
    rule_id: int,
    rule_title: str,
    rule_uuid: str,
    rule_format: str,
    matched: bool,
    score: float,
    details: dict,
    quality_hints: list,
    execution_time_ms: int,
    error: str = None,
) -> RuleTestResult:
    result = RuleTestResult(
        test_id           = test_id,
        rule_id           = rule_id,
        rule_title        = rule_title,
        rule_uuid         = rule_uuid,
        rule_format       = rule_format,
        matched           = matched,
        score             = score,
        details           = details,
        quality_hints     = quality_hints,
        execution_time_ms = execution_time_ms,
        error             = error,
    )
    db.session.add(result)
    db.session.commit()
    return result


# ── Update ────────────────────────────────────────────────────────────────────

def count_matched_results(test_id: int) -> int:
    from app.core.db_class.db import RuleTestResult
    return RuleTestResult.query.filter_by(test_id=test_id, matched=True).count()


def mark_test_done(test: RuleTest, matched_count: int, total_rules: int = None):
    test.status        = 'done'
    test.matched_count = matched_count
    test.total_rules   = total_rules
    test.completed_at  = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()


def mark_test_failed(test: RuleTest, error: str):
    test.status       = 'failed'
    test.error        = error
    test.completed_at = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()


def mark_test_running(test: RuleTest):
    test.status = 'running'
    db.session.commit()


def toggle_visibility(test: RuleTest) -> bool:
    test.is_public = not test.is_public
    db.session.commit()
    return test.is_public


def delete_test(test: RuleTest):
    db.session.delete(test)
    db.session.commit()


def update_notes(test: RuleTest, notes: str):
    test.notes = notes
    db.session.commit()
