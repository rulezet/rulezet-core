"""Rules — layer 4: inputs meant to break Rulezet.

Expected every time: a clean answer (< 500), and either nothing stored or the
value stored as plain text — escaped when it is displayed, never executed.
"""
import pytest

from app.core.db_class.db import Rule, RuleEditProposal, RuleVote
from tests_new.helpers.db import count, reload
from tests_new.helpers.inputs import BAD_IDS, BLANK, EMPTY, INJECTIONS, ODD_CHARACTERS, TOO_LONG, WRONG_TYPES
from tests_new.helpers.rules import edit_form, make_proposal, make_rule, new_rule_form, yara_rule
from tests_new.helpers.users import api_headers

BAD_TEXT = [TOO_LONG, *INJECTIONS, *ODD_CHARACTERS]


# ── Create (web form) ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("title", [EMPTY, BLANK])
def test_create_rule_with_an_empty_title_stores_nothing(title, clients):
    response = clients["owner"].post("/rule/create_rule", data=new_rule_form(title=title))

    assert response.status_code == 200
    assert count(Rule) == 0


@pytest.mark.parametrize("title", BAD_TEXT)
def test_create_rule_with_a_hostile_title_never_errors(title, clients):
    response = clients["owner"].post("/rule/create_rule", data=new_rule_form(title=title))

    assert response.status_code < 500


@pytest.mark.parametrize("content", [EMPTY, TOO_LONG, *INJECTIONS, *ODD_CHARACTERS])
def test_create_rule_with_hostile_content_stores_nothing(content, clients):
    response = clients["owner"].post("/rule/create_rule", data=new_rule_form(to_string=content))

    assert response.status_code < 500
    assert count(Rule) == 0


@pytest.mark.parametrize("fmt", ["not-a-format", "", "<script>", "yara; DROP TABLE rule"])
def test_create_rule_with_an_unknown_format_stores_nothing(fmt, clients):
    response = clients["owner"].post("/rule/create_rule", data=new_rule_form(format=fmt))

    assert response.status_code < 500
    assert count(Rule) == 0


@pytest.mark.parametrize("field", ["tags", "vulnerabilities"])
@pytest.mark.parametrize("value", ["not json", "{}", "[1, 2", '[{"id": "x"}]', "null"])
def test_create_rule_with_malformed_json_fields_never_errors(field, value, clients):
    form = new_rule_form()
    form[field] = value

    response = clients["owner"].post("/rule/create_rule", data=form)

    assert response.status_code < 500


def test_hostile_title_is_escaped_on_the_rule_page(clients, users):
    rule = make_rule(users.owner, title="<script>alert('pwned')</script>")

    page = clients["anonymous"].get(f"/rule/detail_rule/{rule.id}").get_data(as_text=True)

    assert "<script>alert('pwned')</script>" not in page


# ── Edit ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value", BAD_TEXT)
def test_edit_rule_with_hostile_fields_never_errors(value, clients, users):
    rule = make_rule(users.owner)

    response = clients["owner"].post(f"/rule/edit_rule/{rule.id}",
                                     data=edit_form(rule, title=value, description=value, source=value))

    assert response.status_code < 500


def test_edit_rule_with_hostile_content_keeps_the_old_content(clients, users):
    rule = make_rule(users.owner)
    old = rule.to_string

    response = clients["owner"].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, to_string=TOO_LONG))

    assert response.status_code < 500
    assert reload(rule).to_string == old


# ── JSON endpoints: bad ids, wrong types, broken bodies ──────────────────────

@pytest.mark.parametrize("rule_id", [*BAD_IDS, *WRONG_TYPES])
def test_delete_rule_with_a_bad_id_deletes_nothing(rule_id, clients, users):
    rule = make_rule(users.owner)

    response = clients["admin"].post("/rule/delete_rule", json={"id": rule_id})

    assert response.status_code < 500
    assert reload(rule).is_deleted is False


@pytest.mark.parametrize("body", [None, "not json", [1, 2], 42])
def test_delete_rule_with_a_broken_body_never_errors(body, clients, users):
    make_rule(users.owner)

    if body is None:
        response = clients["admin"].post("/rule/delete_rule")
    elif isinstance(body, str):
        response = clients["admin"].post("/rule/delete_rule", data=body, content_type="application/json")
    else:
        response = clients["admin"].post("/rule/delete_rule", json=body)

    assert response.status_code < 500


@pytest.mark.parametrize("ids", ["1", 1, {"a": 1}, [None], ["x"], [2**63]])
def test_bulk_delete_with_bad_ids_never_errors(ids, clients, users):
    rule = make_rule(users.owner)

    response = clients["admin"].post("/rule/delete_rule_list", json={"ids": ids})

    assert response.status_code < 500
    assert reload(rule).is_deleted is False


@pytest.mark.parametrize("rule_id", [*BAD_IDS, *WRONG_TYPES])
def test_vote_with_a_bad_rule_id_never_errors(rule_id, clients, users):
    make_rule(users.owner)

    response = clients["user"].post("/rule/vote_rule", json={"id": rule_id, "vote_type": "up"})

    assert response.status_code < 500
    assert count(RuleVote) == 0


@pytest.mark.parametrize("vote_type", ["sideways", "", None, 1, ["up"]])
def test_vote_with_a_bad_type_is_refused(vote_type, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post("/rule/vote_rule", json={"id": rule.id, "vote_type": vote_type})

    assert response.status_code == 400
    assert count(RuleVote) == 0


@pytest.mark.parametrize("status", ["published", "", None, 1, ["draft"], TOO_LONG])
def test_status_with_a_bad_value_is_refused(status, clients, users):
    rule = make_rule(users.owner, status="draft")

    response = clients["owner"].patch(f"/rule/{rule.id}/status", json={"status": status})

    assert response.status_code == 400
    assert reload(rule).status == "draft"


@pytest.mark.parametrize("body", [[1, 2], "draft", 42])
def test_status_with_a_non_object_body_never_errors(body, clients, users):
    rule = make_rule(users.owner)

    response = clients["owner"].patch(f"/rule/{rule.id}/status", json=body)

    assert response.status_code < 500


@pytest.mark.parametrize("payload", [{"tag_ids": "1"}, {"tag_ids": [None]}, {"tag_ids": ["x"]},
                                     {"cve_ids": "CVE-2024-1"}, {"technique_ids": 5}, [1], "x"])
def test_quick_meta_with_wrong_types_never_errors(payload, clients, users):
    rule = make_rule(users.owner)

    response = clients["owner"].patch(f"/rule/{rule.id}/quick_meta", json=payload)

    assert response.status_code < 500


@pytest.mark.parametrize("fmt", ["unknown", "", "../../etc/passwd", TOO_LONG])
def test_download_with_a_bad_format_never_errors(fmt, clients, users):
    rule = make_rule(users.owner)

    response = clients["anonymous"].get(f"/rule/download_rule?rule_id={rule.id}&format={fmt[:2000]}")

    assert response.status_code < 500


@pytest.mark.parametrize("rule_id", ["abc", "-1", str(2**63), "1 OR 1=1"])
def test_download_with_a_bad_id_never_errors(rule_id, clients):
    response = clients["anonymous"].get(f"/rule/download_rule?rule_id={rule_id}&format=txt")

    assert response.status_code < 500


@pytest.mark.parametrize("rule_uuid", ["not-a-uuid", "<script>", "' OR 1=1 --", "a" * 5000])
def test_rule_page_by_bad_uuid_never_errors(rule_uuid, clients):
    response = clients["anonymous"].get(f"/rule/detail_rule/{rule_uuid}")

    assert response.status_code < 500


# ── Edit proposals ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("content", [EMPTY, BLANK, TOO_LONG, *INJECTIONS])
def test_proposal_with_hostile_content_stores_nothing(content, clients, users):
    rule = make_rule(users.owner)

    response = clients["user"].post(f"/rule/propose_edit/{rule.id}", data={"rule_content": content})

    assert response.status_code < 500
    assert count(RuleEditProposal) == 0


@pytest.mark.parametrize("query", ["", "ruleId=1", "decision=accepted", "ruleId=1&decision=accepted",
                                   "ruleId=1&decision=maybe&ruleproposalId=1", "ruleId=x&decision=accepted&ruleproposalId=y"])
def test_validate_proposal_with_missing_or_bad_parameters_never_errors(query, clients, users):
    make_rule(users.owner)

    response = clients["admin"].get(f"/rule/validate_proposal?{query}")

    assert response.status_code < 500


@pytest.mark.parametrize("body", [None, "not json", [1], {"decision": "rejected"},
                                  {"ruleId": [1], "ruleproposalId": {}, "decision": "rejected"}])
def test_validate_proposal_with_a_broken_body_never_errors(body, clients, users):
    rule = make_rule(users.owner)
    proposal = make_proposal(rule, users.user)

    if isinstance(body, str):
        response = clients["owner"].post("/rule/validate_proposal", data=body, content_type="application/json")
    else:
        response = clients["owner"].post("/rule/validate_proposal", json=body)

    assert 400 <= response.status_code < 500
    assert reload(proposal).status == "pending"


@pytest.mark.parametrize("reason", [TOO_LONG, 5, ["why"], {"a": 1}])
def test_reject_with_a_reason_too_long_or_not_a_text_is_refused(reason, clients, users):
    rule = make_rule(users.owner)
    proposal = make_proposal(rule, users.user)

    response = clients["owner"].post("/rule/validate_proposal", json={
        "ruleId": rule.id, "ruleproposalId": proposal.id, "decision": "rejected", "reason": reason})

    assert response.status_code == 400
    assert reload(proposal).status == "pending"


@pytest.mark.parametrize("reason", INJECTIONS)
def test_reject_reason_is_stored_verbatim(reason, clients, users):
    rule = make_rule(users.owner)
    proposal = make_proposal(rule, users.user)

    clients["owner"].post("/rule/validate_proposal", json={
        "ruleId": rule.id, "ruleproposalId": proposal.id, "decision": "rejected", "reason": reason})

    assert reload(proposal).rejection_reason == reason.strip()


@pytest.mark.parametrize("proposal_id", ["", "999999", "abc"])
def test_get_unknown_proposal_never_errors(proposal_id, clients):
    response = clients["user"].get(f"/rule/get_proposal?id={proposal_id}")

    assert response.status_code < 500


# ── Trash (admin) ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", [None, "not json", [1], {"action": "keep_trash"}, {"action": "keep_trash", "trash_id": "x", "active_id": []}])
def test_resolve_conflict_with_a_broken_body_never_errors(body, clients, users):
    active = make_rule(users.owner)

    if body is None:
        response = clients["admin"].post("/rule/resolve_conflict")
    elif isinstance(body, str):
        response = clients["admin"].post("/rule/resolve_conflict", data=body, content_type="application/json")
    else:
        response = clients["admin"].post("/rule/resolve_conflict", json=body)

    assert response.status_code < 500
    assert reload(active) is not None and reload(active).is_deleted is False


@pytest.mark.parametrize("body", [{"ids": "1"}, {"ids": [None, "x"]}, {"restore_all": "yes"}, [1], {"batch_uuid": ["x"]}])
def test_restore_bulk_with_bad_values_never_errors(body, clients, users):
    response = clients["admin"].post("/rule/restore_bulk", json=body)

    assert response.status_code < 500


@pytest.mark.parametrize("params", ["page=-1", "page=abc", "deleted_from=yesterday", "deleted_to=2024-13-45", "search=" + "%27" * 50])
def test_trash_listing_with_bad_filters_never_errors(params, clients):
    response = clients["admin"].get(f"/rule/get_trash_rules?{params}")

    assert response.status_code < 500


# ── API ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["title", "format", "to_string", "version", "license", "description", "source", "cve_id"])
@pytest.mark.parametrize("value", [12345, 1.5, True, [], ["a"], {"x": 1}])
def test_api_create_with_a_wrong_type_never_errors(field, value, app, users):
    payload = {"title": "API rule", "format": "yara", "license": "MIT", "version": "1",
               "to_string": yara_rule("api_types")}
    payload[field] = value

    response = app.test_client().post("/api/rule/private/create", json=payload, headers=api_headers(users.owner))

    assert response.status_code < 500


@pytest.mark.parametrize("value", BAD_TEXT)
def test_api_create_with_hostile_text_never_errors(value, app, users):
    payload = {"title": value, "format": "yara", "license": "MIT", "version": "1",
               "to_string": yara_rule("api_text"), "description": value, "source": value}

    response = app.test_client().post("/api/rule/private/create", json=payload, headers=api_headers(users.owner))

    assert response.status_code < 500


@pytest.mark.parametrize("rule_id", [*BAD_IDS, *WRONG_TYPES])
def test_api_delete_with_a_bad_id_deletes_nothing(rule_id, app, users):
    rule = make_rule(users.owner)

    response = app.test_client().post("/api/rule/private/delete", json={"rule_id": rule_id},
                                      headers=api_headers(users.admin))

    assert response.status_code < 500
    assert reload(rule).is_deleted is False


@pytest.mark.parametrize("payload", [{"page": 0}, {"page": "x"}, {"per_page": 1000}, {"per_page": -5},
                                     {"search_field": "password"}, {"sort_by": "random"}, {"vulnerabilities": ["nope"]},
                                     {"fields": ["password_hash"]}, {"search": TOO_LONG}, [1, 2]])
def test_api_search_with_bad_parameters_is_refused_cleanly(payload, app, users):
    response = app.test_client().post("/api/rule/private/search", json=payload, headers=api_headers(users.user))

    assert response.status_code < 500


@pytest.mark.parametrize("query", ["page=0", "page=abc", "per_page=1000", "rule_type=nope", "sort_by=random",
                                   "search=" + "A" * 300, "author=" + "A" * 300])
def test_public_search_with_bad_parameters_is_refused_cleanly(query, app):
    response = app.test_client().get(f"/api/rule/public/searchPage?{query}")

    assert response.status_code < 500


def test_edit_rule_to_a_blank_title_keeps_the_old_title(clients, users):
    rule = make_rule(users.owner)

    clients["owner"].post(f"/rule/edit_rule/{rule.id}", data=edit_form(rule, title=BLANK))

    assert reload(rule).title.strip() != ""


def test_create_rule_with_an_unknown_tag_id_links_no_tag(clients):
    from app.core.db_class.db import RuleTagAssociation
    form = new_rule_form(tags='[{"id": 999999}]')

    response = clients["owner"].post("/rule/create_rule", data=form)

    assert response.status_code < 500
    rule = Rule.query.filter_by(title=form["title"]).one()
    assert count(RuleTagAssociation, rule_id=rule.id, tag_id=999999) == 0


@pytest.mark.parametrize("query", ["99999999999999999999", "0", "²", "1"])
def test_global_search_with_an_odd_number_never_errors(query, clients, users):
    make_rule(users.owner)

    response = clients["anonymous"].get(f"/global_search?q={query}")

    assert response.status_code == 200


@pytest.mark.parametrize("body", [{"message": BLANK}, {"message": 5}, {"message": None}, {}, [], "text"])
def test_edit_a_proposal_justification_with_a_bad_message_keeps_it(body, clients, users):
    rule = make_rule(users.user)
    proposal = RuleEditProposal(rule_id=rule.id, user_id=users.owner.id, proposed_content=yara_rule("p"),
                                old_content=rule.to_string, message="Why this change", status="pending")
    from app import db
    db.session.add(proposal)
    db.session.commit()

    response = clients["owner"].post(f"/rule/edit_proposal_message/{proposal.id}", json=body)

    assert response.status_code == 400
    assert reload(proposal).message == "Why this change"


@pytest.mark.parametrize("method", ["post", "delete"])
def test_justification_of_an_unknown_proposal_is_not_found(method, clients):
    response = getattr(clients["owner"], method)("/rule/edit_proposal_message/999999", json={"message": "x"})

    assert response.status_code == 404


@pytest.mark.parametrize("query", ["", "rule_id=abc", "rule_id=99999999999999999999", "rule_id=²", "rule_id=1&page=abc",
                                   "rule_id=1&page=99999999999999999999", "rule_id=1&page=-3",
                                   "rule_id=1&status=merged", "rule_id=1&sort=random", "rule_id=1&q=%25_%00",
                                   "rule_id=1&edit_type=" + "x" * 5000, "rule_id=1&q=" + "y" * 100000])
def test_proposal_threads_with_odd_parameters_never_errors(query, clients, users):
    make_rule(users.owner)

    response = clients["anonymous"].get(f"/rule/get_proposal_threads?{query}")

    assert response.status_code in (200, 400, 404)
