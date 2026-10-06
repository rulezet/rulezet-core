"""Tags — layer 3: the REST API (/api/tags/private/...), authenticated with X-API-KEY.

Both endpoints are for tag managers: an admin key or the key of a user
holding `rule.tag_any` — a plain valid key is not enough. "nobody" = no key,
"bad key" = a key that matches no account, "tagger" = a rule.tag_any user.

bulk_add is two-step: a preview (no job), then the same body with
"confirm": true queues a `bulk_add_tag_to_rules` job.
"""
import pytest

from app import db
from app.core.db_class.db import BackgroundJob, RuleEditContribution, RuleTagAssociation, RuleUpdateHistory
from app.features.jobs.job_handlers import handle_bulk_add_tag_to_rules
from tests_new.helpers.db import count
from tests_new.helpers.rules import make_rule
from tests_new.helpers.tags import default_tag, make_tag
from tests_new.helpers.users import api_headers, make_user_with_permission

API = "/api/tags/private"
BAD_KEY = {"X-API-KEY": "no-such-key"}
KEY_HOLDERS = [("nobody", 403), ("bad key", 403), ("user", 403), ("owner", 403), ("tagger", 200), ("admin", 200)]


@pytest.fixture
def tagger(app):
    return make_user_with_permission("rule.tag_any", "tagger")


def _headers(who, users, tagger):
    if who == "nobody":
        return {}
    if who == "bad key":
        return BAD_KEY
    if who == "tagger":
        return api_headers(tagger)
    return api_headers(getattr(users, who))


def _bulk_add(app, body, who):
    return app.test_client().post(f"{API}/bulk_add", json=body, headers=api_headers(who))


def _run(job, app):
    handle_bulk_add_tag_to_rules(job, app)
    db.session.expire_all()


# ── Lookup ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who, status", KEY_HOLDERS)
def test_lookup_needs_a_tag_manager_key(who, status, app, users, tagger):
    tag = default_tag()

    response = app.test_client().get(f"{API}/lookup?id={tag.id}", headers=_headers(who, users, tagger))

    assert response.status_code == status
    if status == 200:
        assert response.get_json()["tags"][0]["uuid"] == tag.uuid


def test_lookup_by_uuid(app, users):
    tag = make_tag(users.admin)

    response = app.test_client().get(f"{API}/lookup?uuid={tag.uuid}", headers=api_headers(users.admin))

    assert [t["id"] for t in response.get_json()["tags"]] == [tag.id]


def test_lookup_by_name_returns_every_match(app, users):
    make_tag(users.admin, name="tlp:red")

    response = app.test_client().get(f"{API}/lookup?name=TLP", headers=api_headers(users.admin))

    assert {t["name"] for t in response.get_json()["tags"]} == {"tlp:clear", "tlp:red"}


def test_lookup_response_shape(app, users):
    response = app.test_client().get(f"{API}/lookup?name=tlp:clear", headers=api_headers(users.admin))

    tag = response.get_json()["tags"][0]
    assert {"id", "uuid", "name", "description", "color", "icon", "visibility", "source", "rule_count"} <= set(tag)


@pytest.mark.parametrize("query", ["id=999999", "uuid=nope", "name=no-such-tag"])
def test_lookup_of_an_unknown_tag_is_not_found(query, app, users):
    response = app.test_client().get(f"{API}/lookup?{query}", headers=api_headers(users.admin))

    assert response.status_code == 404


def test_lookup_without_any_criteria_is_refused(app, users):
    response = app.test_client().get(f"{API}/lookup", headers=api_headers(users.admin))

    assert response.status_code == 400


# ── Bulk add: preview ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("who, status", KEY_HOLDERS)
def test_bulk_add_needs_a_tag_manager_key(who, status, app, users, tagger):
    rule, tag = make_rule(users.owner), make_tag(users.admin)

    response = app.test_client().post(f"{API}/bulk_add", json={"rule_ids": [rule.id], "tag_ids": [tag.id],
                                                               "confirm": True},
                                      headers=_headers(who, users, tagger))

    assert response.status_code == (202 if status == 200 else status)
    assert count(BackgroundJob) == (1 if status == 200 else 0)


def test_bulk_add_without_confirm_is_only_a_preview(app, users):
    rules, tag = [make_rule(users.owner), make_rule(users.owner)], make_tag(users.admin)

    response = _bulk_add(app, {"rule_ids": [r.id for r in rules], "tag_ids": [tag.id]}, users.admin)

    data = response.get_json()
    assert response.status_code == 200 and data["confirmed"] is False
    assert data["preview"] == {"tags": [{"id": tag.id, "name": tag.name}],
                               "requested_rule_count": 2, "matched_rule_count": 2}
    assert count(BackgroundJob) == 0 and count(RuleTagAssociation, tag_id=tag.id) == 0


@pytest.mark.parametrize("confirm", [False, "false", "true", 1, "yes", None])
def test_bulk_add_only_confirms_on_a_real_true(confirm, app, users):
    """Anything but JSON `true` is a preview — "false" must never launch the job."""
    rule, tag = make_rule(users.owner), make_tag(users.admin)

    response = _bulk_add(app, {"rule_ids": [rule.id], "tag_ids": [tag.id], "confirm": confirm}, users.admin)

    assert response.status_code == 200 and count(BackgroundJob) == 0


def test_bulk_add_accepts_uuids_and_ids_mixed(app, users):
    by_id, by_uuid, tag = make_rule(users.owner), make_rule(users.owner), make_tag(users.admin)

    response = _bulk_add(app, {"rule_ids": [by_id.id], "rule_uuids": [by_uuid.uuid], "tag_uuids": [tag.uuid]},
                         users.admin)

    assert response.get_json()["preview"]["matched_rule_count"] == 2


def test_bulk_add_does_not_count_unknown_or_deleted_rules(app, users):
    rule, deleted, tag = make_rule(users.owner), make_rule(users.owner, is_deleted=True), make_tag(users.admin)

    response = _bulk_add(app, {"rule_ids": [rule.id, deleted.id, 999999], "tag_ids": [tag.id]}, users.admin)

    assert response.get_json()["preview"]["matched_rule_count"] == 1


@pytest.mark.parametrize("body", [
    {"tag_ids": [1]},
    {"rule_ids": [1]},
    {"rule_ids": [999999], "tag_ids": "TAG"},
    {"rule_ids": [], "rule_uuids": [], "tag_ids": [1]},
])
def test_bulk_add_without_rules_or_tags_is_refused(body, app, users):
    response = _bulk_add(app, body, users.admin)

    assert response.status_code == 400 and count(BackgroundJob) == 0


def test_bulk_add_with_only_unknown_tags_is_refused(app, users):
    rule = make_rule(users.owner)

    response = _bulk_add(app, {"rule_ids": [rule.id], "tag_ids": [999999], "tag_uuids": ["nope"]}, users.admin)

    assert response.status_code == 400 and count(BackgroundJob) == 0


def test_bulk_add_with_only_unknown_or_deleted_rules_is_refused(app, users):
    deleted, tag = make_rule(users.owner, is_deleted=True), make_tag(users.admin)

    response = _bulk_add(app, {"rule_ids": [999999, deleted.id], "rule_uuids": ["nope"], "tag_ids": [tag.id],
                               "confirm": True}, users.admin)

    assert response.status_code == 400 and count(BackgroundJob) == 0


def test_bulk_add_ignores_a_rules_original_uuid(app, users):
    """Only Rulezet's own uuid identifies a rule, not the GitHub-import one."""
    rule, tag = make_rule(users.owner, original_uuid="original-uuid-1"), make_tag(users.admin)

    response = _bulk_add(app, {"rule_uuids": ["original-uuid-1"], "tag_ids": [tag.id]}, users.admin)

    assert response.status_code == 400


# ── Bulk add: confirmed job ───────────────────────────────────────────────────

def test_bulk_add_confirmed_queues_a_job_for_the_caller(app, users, tagger):
    rule, tag = make_rule(users.owner), make_tag(users.admin)

    response = _bulk_add(app, {"rule_ids": [rule.id], "tag_ids": [tag.id], "confirm": True}, tagger)

    data = response.get_json()
    job = BackgroundJob.query.one()
    assert response.status_code == 202 and data["confirmed"] is True
    assert data["job_uuid"] == job.uuid and data["job_url"] == f"/jobs/detail/{job.uuid}"
    assert job.job_type == "bulk_add_tag_to_rules" and job.created_by == tagger.id


def test_bulk_add_job_tags_the_rules_and_records_history(app, users, tagger):
    rules, tag = [make_rule(users.owner), make_rule(users.owner)], make_tag(users.admin)
    _bulk_add(app, {"rule_ids": [r.id for r in rules], "tag_ids": [tag.id], "confirm": True}, tagger)

    _run(BackgroundJob.query.one(), app)

    for rule in rules:
        assert count(RuleTagAssociation, rule_id=rule.id, tag_id=tag.id) == 1
        assert count(RuleUpdateHistory, rule_id=rule.id, change_type="metadata") == 1


def test_bulk_add_job_credits_the_tagger_as_a_contributor(app, users, tagger):
    rule, tag = make_rule(users.owner), make_tag(users.admin)
    _bulk_add(app, {"rule_ids": [rule.id], "tag_ids": [tag.id], "confirm": True}, tagger)

    _run(BackgroundJob.query.one(), app)

    assert count(RuleEditContribution, rule_id=rule.id, user_id=tagger.id) == 1


def test_bulk_add_job_only_touches_existing_active_rules_and_tags(app, users):
    """Unknown ids / deleted rules mixed into the request are dropped, never
    linked (PostgreSQL would refuse a link to a tag that doesn't exist)."""
    rule, deleted, tag = make_rule(users.owner), make_rule(users.owner, is_deleted=True), make_tag(users.admin)
    _bulk_add(app, {"rule_ids": [rule.id, deleted.id, 999999], "tag_ids": [tag.id, 999999], "confirm": True},
              users.admin)

    _run(BackgroundJob.query.one(), app)

    assert {(a.rule_id, a.tag_id) for a in RuleTagAssociation.query.all()} == {(rule.id, tag.id)}


def test_bulk_add_job_skips_rules_already_tagged(app, users):
    rule, tag = make_rule(users.owner), make_tag(users.admin)
    db.session.add(RuleTagAssociation(uuid="existing-link", rule_id=rule.id, tag_id=tag.id, user_id=users.owner.id))
    db.session.commit()
    _bulk_add(app, {"rule_ids": [rule.id], "tag_ids": [tag.id], "confirm": True}, users.admin)

    _run(BackgroundJob.query.one(), app)

    assert count(RuleTagAssociation, rule_id=rule.id, tag_id=tag.id) == 1
    assert count(RuleUpdateHistory, rule_id=rule.id) == 0
