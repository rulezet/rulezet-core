"""ATT&CK — layer 3: the REST API.

The only ATT&CK endpoint of /api/ is the public rule search by technique
(/api/rule/public/search_rules_by_attack): no key needed, and a key — valid
or not — changes nothing. Mapping techniques is not exposed through the API.
"""
import pytest

from tests_new.helpers.attack import link_technique, make_technique, trash
from tests_new.helpers.rules import make_rule
from tests_new.helpers.users import api_headers

SEARCH = "/api/rule/public/search_rules_by_attack"


def _headers(who, users):
    if who == "nobody":
        return {}
    if who == "bad key":
        return {"X-API-KEY": "no-such-key"}
    return api_headers(getattr(users, who))


@pytest.mark.parametrize("who", ["nobody", "bad key", "user", "admin"])
def test_search_by_technique_is_public(who, app, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059"))

    response = app.test_client().get(f"{SEARCH}?technique_ids=T1059", headers=_headers(who, users))

    assert response.status_code == 200
    assert [r["id"] for r in response.get_json()["results"]] == [rule.id]


def test_search_by_technique_returns_the_mapped_rules(app, users):
    t1059, t1105 = make_technique("T1059"), make_technique("T1105")
    both = make_rule(users.owner)
    link_technique(both, t1059)
    link_technique(both, t1105)
    one = make_rule(users.owner)
    link_technique(one, t1105)
    make_rule(users.owner)

    data = app.test_client().get(f"{SEARCH}?technique_ids=t1059,T1105").get_json()

    assert data["detected_patterns"] == ["T1059", "T1105"]
    assert data["total_matches"] == 2
    matched = {r["id"]: r["matched_techniques"] for r in data["results"]}
    assert matched == {both.id: ["T1059", "T1105"], one.id: ["T1105"]}
    assert all(r["detail_url"].endswith(f"/rule/detail_rule/{r['id']}") for r in data["results"])


def test_search_by_technique_hides_trashed_rules(app, users):
    technique = make_technique("T1059")
    active = make_rule(users.owner)
    link_technique(active, technique)
    link_technique(trash(make_rule(users.owner), users.admin), technique)

    data = app.test_client().get(f"{SEARCH}?technique_ids=T1059").get_json()

    assert [r["id"] for r in data["results"]] == [active.id] and data["total_matches"] == 1


def test_search_by_technique_reads_ids_out_of_free_text(app, users):
    rule = make_rule(users.owner)
    link_technique(rule, make_technique("T1059.001"))

    data = app.test_client().get(f"{SEARCH}?technique_ids=see t1059.001 please").get_json()

    assert data["detected_patterns"] == ["T1059.001"]
    assert [r["id"] for r in data["results"]] == [rule.id]


def test_search_by_technique_without_ids_is_refused(app):
    response = app.test_client().get(SEARCH)

    assert response.status_code == 400


def test_search_by_technique_without_a_valid_id_is_not_found(app):
    response = app.test_client().get(f"{SEARCH}?technique_ids=not-a-technique")

    assert response.status_code == 404


def test_search_by_an_unmapped_technique_finds_nothing(app, users):
    make_rule(users.owner)

    data = app.test_client().get(f"{SEARCH}?technique_ids=T1059").get_json()

    assert data["results"] == [] and data["total_matches"] == 0
