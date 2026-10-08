"""Rules — layer 2: create / read / edit / delete, checked in the database."""
import json

from app import db
from app.core.db_class.db import (
    Rule, RuleEditProposal, RuleFavoriteUser, RuleTagAssociation, RuleUpdateHistory, RuleVote, Tag,
)
from tests_new.helpers.db import count, reload
from tests_new.helpers.rules import edit_form, make_proposal, make_rule, new_rule_form, yara_rule


def _tag_names(rule):
    return {Tag.query.get(a.tag_id).name for a in RuleTagAssociation.query.filter_by(rule_id=rule.id)}


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_rule_stores_it_owned_by_the_creator(clients, users):
    form = new_rule_form()

    response = clients["owner"].post("/rule/create_rule", data=form)

    rule = Rule.query.filter_by(title=form["title"]).one()
    assert response.status_code == 302 and f"/rule/detail_rule/{rule.id}" in response.headers["Location"]
    assert rule.user_id == users.owner.id
    assert rule.format == "yara" and rule.to_string == form["to_string"]
    assert rule.is_deleted is False


def test_create_rule_attaches_the_default_tags(clients):
    form = new_rule_form()

    clients["owner"].post("/rule/create_rule", data=form)

    assert _tag_names(Rule.query.filter_by(title=form["title"]).one()) == {"tlp:clear", "PAP:CLEAR"}


def test_create_rule_records_a_creation_history_entry(clients):
    form = new_rule_form()

    clients["owner"].post("/rule/create_rule", data=form)

    rule = Rule.query.filter_by(title=form["title"]).one()
    assert count(RuleUpdateHistory, rule_id=rule.id, change_type="created") == 1


def test_create_rule_with_a_cve_links_the_vulnerability(clients):
    form = new_rule_form(cve_id="CVE-2024-12345")

    clients["owner"].post("/rule/create_rule", data=form)

    rule = Rule.query.filter_by(title=form["title"]).one()
    assert "CVE-2024-12345" in json.loads(rule.cve_id or "[]")


def test_create_rule_with_invalid_syntax_stores_nothing(clients):
    form = new_rule_form(to_string="rule broken { condition: }")

    response = clients["owner"].post("/rule/create_rule", data=form)

    assert response.status_code == 200
    assert count(Rule, title=form["title"]) == 0


def test_create_rule_with_existing_content_creates_no_duplicate(clients, users):
    existing = make_rule(users.user)
    form = new_rule_form(to_string=existing.to_string)

    response = clients["owner"].post("/rule/create_rule", data=form)

    assert count(Rule, title=form["title"]) == 0
    assert f"/rule/detail_rule/{existing.id}" in response.headers.get("Location", "")


def test_create_rule_with_a_title_already_used_is_refused(clients, users):
    existing = make_rule(users.user)

    clients["owner"].post("/rule/create_rule", data=new_rule_form(title=existing.title))

    assert count(Rule, title=existing.title) == 1


# ── Read ──────────────────────────────────────────────────────────────────────

def test_rule_list_shows_active_rules_only(clients, users):
    active = make_rule(users.owner)
    trashed = make_rule(users.owner, is_deleted=True)

    titles = [r["title"] for r in clients["anonymous"].get("/rule/data_table?per_page=50").get_json()["items"]]

    assert active.title in titles and trashed.title not in titles


def test_paginated_rule_list_hides_trashed_rules(clients, users):
    make_rule(users.owner)
    trashed = make_rule(users.owner, is_deleted=True)

    titles = [r["title"] for r in clients["anonymous"].get("/rule/get_rules_page?page=1").get_json()["rule"]]

    assert trashed.title not in titles


def test_rules_of_a_user_hide_trashed_rules(clients, users):
    make_rule(users.owner)
    trashed = make_rule(users.owner, is_deleted=True)

    response = clients["anonymous"].get(f"/rule/get_rules_page_filter_with_id?userId={users.owner.id}&page=1")

    assert trashed.title not in [r["title"] for r in response.get_json()["rule"]]


def test_my_rules_hide_my_trashed_rules(clients, users):
    make_rule(users.owner)
    trashed = make_rule(users.owner, is_deleted=True)

    response = clients["owner"].get("/rule/get_rules_page_owner?page=1").get_json()

    assert trashed.title not in [r["title"] for r in response["owner_rules"]]
    assert response["total_rules"] == 1


def test_trashed_rule_page_shows_the_trash_notice_not_the_rule(clients, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}")

    assert rule.to_string.encode() not in response.data


# ── Edit ──────────────────────────────────────────────────────────────────────

def test_edit_rule_content_bumps_the_version_and_records_history(clients, users):
    rule = make_rule(users.owner, version="1")
    new_content = yara_rule("edited_content")

    clients["owner"].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, to_string=new_content))

    edited = reload(rule)
    assert edited.to_string == new_content
    assert edited.version != "1"
    assert count(RuleUpdateHistory, rule_id=rule.id) >= 1


def test_edit_rule_with_invalid_syntax_keeps_the_old_content(clients, users):
    rule = make_rule(users.owner)
    old_content = rule.to_string

    clients["owner"].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, to_string="rule broken { condition: }"))

    assert reload(rule).to_string == old_content


def test_edit_rule_to_a_title_already_used_is_refused(clients, users):
    other = make_rule(users.user)
    rule = make_rule(users.owner)

    clients["owner"].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, title=other.title))

    assert reload(rule).title != other.title


def test_admin_editing_a_missing_rule_gets_not_found(clients):
    response = clients["admin"].get("/rule/edit_rule/999999")

    assert response.status_code == 404


# ── Delete, trash, restore ────────────────────────────────────────────────────

def test_delete_rule_moves_it_to_the_trash(clients, users):
    rule = make_rule(users.owner)

    clients["owner"].post("/rule/delete_rule", json={"id": rule.id})

    trashed = reload(rule)
    assert trashed.is_deleted is True
    assert trashed.deleted_at is not None and trashed.deleted_by_id == users.owner.id


def test_bulk_delete_groups_the_rules_in_one_batch(clients, users):
    rules = [make_rule(users.owner), make_rule(users.owner)]

    clients["owner"].post("/rule/delete_rule_list", json={"ids": [r.id for r in rules]})

    batches = {reload(r).delete_batch_uuid for r in rules}
    assert len(batches) == 1 and None not in batches


def test_restore_rule_clears_the_trash_fields(clients, users):
    rule = make_rule(users.owner, is_deleted=True, deleted_by_id=users.admin.id)

    clients["admin"].post(f"/rule/restore/{rule.id}")

    restored = reload(rule)
    assert restored.is_deleted is False
    assert restored.deleted_at is None and restored.deleted_by_id is None and restored.delete_batch_uuid is None


def test_restore_rule_whose_content_is_active_again_reports_a_conflict(clients, users):
    trashed = make_rule(users.owner, is_deleted=True)
    make_rule(users.user, to_string=trashed.to_string)

    response = clients["admin"].post(f"/rule/restore/{trashed.id}")

    assert response.status_code == 409
    assert reload(trashed).is_deleted is True


def test_resolve_conflict_keeping_the_trashed_rule_restores_it(clients, users):
    trashed = make_rule(users.owner, is_deleted=True)
    active = make_rule(users.user, to_string=trashed.to_string)

    response = clients["admin"].post("/rule/resolve_conflict",
                                     json={"action": "keep_trash", "trash_id": trashed.id, "active_id": active.id})

    assert response.status_code == 200
    assert reload(trashed).is_deleted is False


def test_resolve_conflict_keeping_the_active_rule_deletes_the_trashed_one(clients, users):
    trashed = make_rule(users.owner, is_deleted=True)
    active = make_rule(users.user, to_string=trashed.to_string)

    clients["admin"].post("/rule/resolve_conflict",
                          json={"action": "keep_active", "trash_id": trashed.id, "active_id": active.id})

    assert reload(trashed) is None and reload(active).is_deleted is False


def test_permanent_delete_removes_the_rule_and_what_hangs_off_it(clients, users):
    rule = make_rule(users.owner, is_deleted=True)
    db.session.add(RuleVote(rule_id=rule.id, user_id=users.user.id, vote_type="up"))
    db.session.add(RuleFavoriteUser(rule_id=rule.id, user_id=users.user.id))
    db.session.commit()

    clients["admin"].post(f"/rule/permanent_delete/{rule.id}")

    assert reload(rule) is None
    assert count(RuleVote, rule_id=rule.id) == 0 and count(RuleFavoriteUser, rule_id=rule.id) == 0


def test_permanent_delete_never_touches_an_active_rule(clients, users):
    rule = make_rule(users.owner)

    response = clients["admin"].post(f"/rule/permanent_delete/{rule.id}")

    assert response.status_code == 404
    assert reload(rule) is not None


# ── Votes and favorites ───────────────────────────────────────────────────────

def test_voting_twice_the_same_way_removes_the_vote(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post("/rule/vote_rule", json={"id": rule.id, "vote_type": "up"})
    clients["user"].post("/rule/vote_rule", json={"id": rule.id, "vote_type": "up"})

    assert count(RuleVote, rule_id=rule.id) == 0 and reload(rule).vote_up == 0


def test_voting_the_other_way_switches_the_vote(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post("/rule/vote_rule", json={"id": rule.id, "vote_type": "up"})
    clients["user"].post("/rule/vote_rule", json={"id": rule.id, "vote_type": "down"})

    voted = reload(rule)
    assert (voted.vote_up, voted.vote_down) == (0, 1)


def test_favorite_toggles(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post(f"/rule/favorite/{rule.id}")
    assert count(RuleFavoriteUser, rule_id=rule.id) == 1
    clients["user"].post(f"/rule/favorite/{rule.id}")
    assert count(RuleFavoriteUser, rule_id=rule.id) == 0


def test_favoriting_a_trashed_rule_is_refused(clients, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = clients["user"].post(f"/rule/favorite/{rule.id}")

    assert response.status_code == 404
    assert count(RuleFavoriteUser, rule_id=rule.id) == 0


# ── Status ────────────────────────────────────────────────────────────────────

def test_status_change_is_stored(clients, users):
    rule = make_rule(users.owner, status="draft")

    response = clients["owner"].patch(f"/rule/{rule.id}/status", json={"status": "deprecated"})

    assert response.status_code == 200 and reload(rule).status == "deprecated"


# ── Edit proposals ────────────────────────────────────────────────────────────

def _propose(clients, rule, content):
    clients["user"].post(f"/rule/propose_edit/{rule.id}", data={"rule_content": content, "message": "please"})
    return RuleEditProposal.query.filter_by(rule_id=rule.id).order_by(RuleEditProposal.id.desc()).first()


def test_proposal_is_stored_pending_and_leaves_the_rule_unchanged(clients, users):
    rule = make_rule(users.owner)
    old_content = rule.to_string

    proposal = _propose(clients, rule, yara_rule("proposed"))

    assert proposal.status == "pending" and proposal.user_id == users.user.id
    assert reload(rule).to_string == old_content


def test_accepting_a_proposal_applies_its_content(clients, users):
    rule = make_rule(users.owner)
    content = yara_rule("accepted")
    proposal = _propose(clients, rule, content)

    clients["owner"].get(f"/rule/validate_proposal?ruleId={rule.id}&decision=accepted&ruleproposalId={proposal.id}")

    assert reload(rule).to_string == content
    assert reload(proposal).status == "accepted"


def test_rejecting_a_proposal_keeps_the_rule(clients, users):
    rule = make_rule(users.owner)
    old_content = rule.to_string
    proposal = _propose(clients, rule, yara_rule("rejected"))

    clients["owner"].get(f"/rule/validate_proposal?ruleId={rule.id}&decision=rejected&ruleproposalId={proposal.id}")

    assert reload(rule).to_string == old_content
    assert reload(proposal).status == "rejected"


def test_proposal_identical_to_the_rule_is_refused(clients, users):
    rule = make_rule(users.owner)

    clients["user"].post(f"/rule/propose_edit/{rule.id}", data={"rule_content": rule.to_string})

    assert count(RuleEditProposal, rule_id=rule.id) == 0


def test_proposal_cannot_be_validated_through_another_rule(clients, users):
    """A rule's owner can't accept a proposal that belongs to someone else's rule."""
    victim = make_rule(users.user)
    mine = make_rule(users.owner)
    proposal = _propose(clients, victim, yara_rule("hijack"))

    response = clients["owner"].get(
        f"/rule/validate_proposal?ruleId={mine.id}&decision=accepted&ruleproposalId={proposal.id}")

    assert response.status_code == 404
    assert reload(victim).to_string != proposal.proposed_content


def test_resolve_conflict_with_unrelated_ids_deletes_nothing(clients, users):
    trashed = make_rule(users.owner, is_deleted=True)
    unrelated = make_rule(users.user)

    response = clients["admin"].post("/rule/resolve_conflict",
                                     json={"action": "keep_trash", "trash_id": trashed.id, "active_id": unrelated.id})

    assert response.status_code == 400
    assert reload(unrelated) is not None and reload(trashed).is_deleted is True


def test_editing_a_trashed_rule_gets_not_found(clients, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = clients["owner"].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, title="Edited in the trash"))

    assert response.status_code == 404
    assert reload(rule).title != "Edited in the trash"


def test_create_rule_with_the_vulnerability_picker_links_them(clients):
    form = new_rule_form(vulnerabilities='["CVE-2023-1111", "CVE-2023-2222"]')

    clients["owner"].post("/rule/create_rule", data=form)

    rule = Rule.query.filter_by(title=form["title"]).one()
    assert set(json.loads(rule.cve_id)) == {"CVE-2023-1111", "CVE-2023-2222"}


def test_bulk_restore_without_an_explicit_choice_restores_nothing(clients, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = clients["admin"].post("/rule/restore_bulk", json={"ids": []})

    assert response.status_code == 400
    assert reload(rule).is_deleted is True


def test_bulk_restore_of_everything_needs_restore_all(clients, users):
    rules = [make_rule(users.owner, is_deleted=True), make_rule(users.owner, is_deleted=True)]

    clients["admin"].post("/rule/restore_bulk", json={"restore_all": True})

    assert all(reload(r).is_deleted is False for r in rules)


def test_permanent_delete_of_a_batch_deletes_that_batch_only(clients, users):
    batch = [make_rule(users.owner, is_deleted=True, delete_batch_uuid="batch-1") for _ in range(2)]
    other = make_rule(users.owner, is_deleted=True, delete_batch_uuid="batch-2")

    clients["admin"].post("/rule/permanent_delete_bulk", json={"batch_uuid": "batch-1"})

    assert all(reload(r) is None for r in batch)
    assert reload(other) is not None


# ── Proposals grouped into threads (the rule's "Proposals" page) ─────────────

def _proposal(rule, author, *, previous=None, status="pending", minutes=0):
    import datetime
    from app import db
    proposal = RuleEditProposal(
        rule_id=rule.id, user_id=author.id, proposed_content=yara_rule(f"p{minutes}"), old_content=rule.to_string,
        status=status, previous_proposal_id=previous.id if previous else None,
        timestamp=datetime.datetime(2026, 1, 1) + datetime.timedelta(minutes=minutes))
    db.session.add(proposal)
    db.session.commit()
    return proposal


def test_proposals_are_grouped_into_threads_in_reading_order(clients, users):
    rule = make_rule(users.owner)
    first = _proposal(rule, users.user, status="rejected", minutes=0)
    alone = _proposal(rule, users.admin, minutes=5)
    revision = _proposal(rule, users.user, previous=first, status="rejected", minutes=10)
    branch = _proposal(rule, users.admin, previous=first, status="accepted", minutes=20)
    of_revision = _proposal(rule, users.user, previous=revision, minutes=30)

    data = clients["anonymous"].get(f"/rule/get_proposal_threads?rule_id={rule.id}").get_json()

    # latest activity first: the thread of `first` (30 min) before `alone` (5 min)
    assert [t["id"] for t in data["threads"]] == [first.id, alone.id]
    thread = data["threads"][0]
    # depth-first, oldest revision first; version numbers follow the dates
    assert [(p["id"], p["depth"], p["version"]) for p in thread["proposals"]] == [
        (first.id, 0, 1), (revision.id, 1, 2), (of_revision.id, 2, 4), (branch.id, 1, 3)]
    assert thread["status"] == "accepted" and data["threads"][1]["status"] == "open"
    assert (data["total_proposals"], data["total_threads"]) == (5, 2)


def test_proposal_threads_are_never_split_across_pages(clients, users):
    from app.features.rule.rule_core import PROPOSAL_THREADS_PER_PAGE
    rule = make_rule(users.owner)
    for n in range(PROPOSAL_THREADS_PER_PAGE + 1):
        root = _proposal(rule, users.user, minutes=n * 10)
        _proposal(rule, users.user, previous=root, minutes=n * 10 + 1)

    first = clients["anonymous"].get(f"/rule/get_proposal_threads?rule_id={rule.id}&page=1").get_json()
    second = clients["anonymous"].get(f"/rule/get_proposal_threads?rule_id={rule.id}&page=2").get_json()

    assert first["total_pages"] == 2
    assert len(first["threads"]) == PROPOSAL_THREADS_PER_PAGE and len(second["threads"]) == 1
    assert all(len(t["proposals"]) == 2 for t in first["threads"] + second["threads"])


def test_proposal_threads_of_a_trashed_rule_are_not_found(clients, users):
    rule = make_rule(users.owner, is_deleted=True)

    response = clients["anonymous"].get(f"/rule/get_proposal_threads?rule_id={rule.id}")

    assert response.status_code == 404


def test_proposal_threads_filters_and_sort(clients, users):
    from app import db
    rule = make_rule(users.owner)
    merged = _proposal(rule, users.user, status="rejected", minutes=0)
    _proposal(rule, users.user, previous=merged, status="accepted", minutes=1)
    open_one = _proposal(rule, users.admin, minutes=10)
    open_one.edit_type, open_one.message = "security", "Fixes a bypass"
    closed = _proposal(rule, users.user, status="rejected", minutes=20)
    db.session.commit()

    def ids(**params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        data = clients["anonymous"].get(f"/rule/get_proposal_threads?rule_id={rule.id}&{query}").get_json()
        return [t["id"] for t in data["threads"]], data["status_counts"]

    assert ids(status="accepted")[0] == [merged.id]
    assert ids(status="open")[0] == [open_one.id]
    assert ids(status="closed")[0] == [closed.id]
    assert ids(status="open")[1] == {"open": 1, "accepted": 1, "closed": 1}   # counts ignore the filter
    assert ids(edit_type="security")[0] == [open_one.id]
    assert ids(q="bypass")[0] == [open_one.id]
    assert ids(q=f"%23{closed.id}")[0] == [closed.id]                           # "#<id>"
    assert ids(sort="oldest")[0] == [merged.id, open_one.id, closed.id]
    assert ids(sort="versions")[0][0] == merged.id


# ── Deciding a thread (accept supersedes the other versions, reasons) ────────

def _decide(client, proposal, decision, reason=None):
    return client.post("/rule/validate_proposal", json={
        "ruleId": proposal.rule_id, "ruleproposalId": proposal.id, "decision": decision, "reason": reason})


def test_accepting_a_version_supersedes_the_rest_of_its_thread(clients, users):
    rule = make_rule(users.owner)
    v1 = make_proposal(rule, users.user, status="rejected", minutes=0)
    v2 = make_proposal(rule, users.user, previous=v1, minutes=1)
    v3 = make_proposal(rule, users.admin, previous=v1, minutes=2)
    other_thread = make_proposal(rule, users.admin, minutes=3)

    response = _decide(clients["owner"], v2, "accepted")

    assert response.status_code == 200
    assert sorted(response.get_json()["superseded_ids"]) == sorted([v1.id, v3.id])
    assert [reload(p).status for p in (v1, v2, v3, other_thread)] == ["superseded", "accepted", "superseded", "pending"]
    assert reload(rule).to_string == v2.proposed_content


def test_a_decided_or_superseded_version_cannot_be_decided_again(clients, users):
    rule = make_rule(users.owner)
    original = rule.to_string
    v1 = make_proposal(rule, users.user, status="superseded")
    accepted = make_proposal(rule, users.user, status="accepted", minutes=1)

    responses = [_decide(clients["owner"], p, "accepted") for p in (v1, accepted)]

    assert [r.status_code for r in responses] == [409, 409]
    assert reload(rule).to_string == original
    assert reload(v1).status == "superseded"


def test_a_superseded_version_cannot_be_revised(clients, users):
    rule = make_rule(users.owner)
    v1 = make_proposal(rule, users.user, status="superseded")

    response = clients["user"].post(f"/rule/propose_revision/{v1.id}", headers={"Accept": "application/json"},
                                    data={"rule_content": yara_rule("late"), "message": "too late"})

    assert response.status_code == 400
    assert count(RuleEditProposal, previous_proposal_id=v1.id) == 0


def test_rejection_reason_is_stored_returned_and_notified(clients, users):
    from app.core.db_class.db import Notification
    rule = make_rule(users.owner)
    proposal = make_proposal(rule, users.user)

    _decide(clients["owner"], proposal, "rejected", reason="  Breaks the condition  ")

    assert reload(proposal).rejection_reason == "Breaks the condition"
    data = clients["user"].get(f"/rule/get_proposal?id={proposal.id}").get_json()["proposal"]
    assert data["rejection_reason"] == "Breaks the condition"
    notification = Notification.query.filter_by(user_id=users.user.id, notif_type="proposal_rejected").one()
    assert "Breaks the condition" in notification.body


def test_accepting_a_revision_records_the_rule_s_real_previous_content(clients, users):
    """The history entry diffs the rule as it was, not the version the revision started from."""
    rule = make_rule(users.owner)
    original = rule.to_string
    v1 = make_proposal(rule, users.user)
    v2 = make_proposal(rule, users.user, previous=v1, minutes=1)

    _decide(clients["owner"], v2, "accepted")

    history = RuleUpdateHistory.query.filter_by(rule_id=rule.id).order_by(RuleUpdateHistory.id.desc()).first()
    assert (history.old_content, history.new_content) == (original, v2.proposed_content)


def test_bulk_accept_keeps_one_version_per_thread(clients, users):
    rule = make_rule(users.owner)
    v1 = make_proposal(rule, users.user, minutes=0)
    v2 = make_proposal(rule, users.user, previous=v1, minutes=1)

    clients["owner"].post("/rule/manage_proposals", json={"action": "accept", "mode": "partial",
                                                           "selected_ids": [v1.id, v2.id]})

    assert (reload(v1).status, reload(v2).status) == ("accepted", "superseded")
    assert reload(rule).to_string == v1.proposed_content


def test_thread_participants_are_notified_of_a_decision(clients, users):
    from app.core.db_class.db import Notification, UnifiedComment
    rule = make_rule(users.owner)
    v1 = make_proposal(rule, users.admin)
    v2 = make_proposal(rule, users.user, previous=v1, minutes=1)
    db.session.add(UnifiedComment(content="looks good", object_type="proposal", object_id=v1.id,
                                  created_by=users.user.id))
    db.session.commit()

    _decide(clients["owner"], v1, "accepted")

    notified = {n.user_id for n in Notification.query.filter_by(notif_type="proposal_thread")}
    assert users.user.id in notified          # author of v2 and commenter
    assert users.owner.id not in notified     # the one deciding
    assert reload(v2).status == "superseded"


def test_get_proposal_returns_its_thread_and_what_the_viewer_may_do(clients, users):
    rule = make_rule(users.owner)
    v1 = make_proposal(rule, users.user, status="rejected", minutes=0)
    v2 = make_proposal(rule, users.user, previous=v1, minutes=1)

    as_owner = clients["owner"].get(f"/rule/get_proposal?id={v2.id}").get_json()["proposal"]
    as_stranger = clients["admin"].get(f"/rule/get_proposal?id={v1.id}").get_json()["proposal"]

    assert [(v["id"], v["version"]) for v in as_owner["thread"]] == [(v1.id, 1), (v2.id, 2)]
    assert as_owner["version"] == 2 and as_owner["rule_content"] == rule.to_string
    assert (as_owner["can_decide"], as_owner["can_revise"]) == (True, True)
    assert (as_stranger["can_decide"], as_stranger["can_revise"]) == (False, True)   # admin; v1 is not pending


def test_review_queue_lists_each_version_with_its_place_in_the_thread(clients, users):
    rule = make_rule(users.owner)
    v1 = make_proposal(rule, users.user, minutes=0)
    v2 = make_proposal(rule, users.user, previous=v1, minutes=1)

    rows = clients["owner"].get("/rule/get_rules_propose_edit_history_page").get_json()["rules_list"]

    positions = {r["id"]: (r["thread_root_id"], r["thread_version"], r["thread_size"]) for r in rows}
    assert positions == {v1.id: (v1.id, 1, 2), v2.id: (v1.id, 2, 2)}
