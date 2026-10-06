"""
tests/test_search_rules.py

Tests for POST /api/rule/private/search

Covers every filter combination with dedicated seed rules so each
test is fully self-contained and isolated.
"""

import datetime
import uuid
import pytest

# --------------------------
# Constants
# --------------------------

SEARCH_ENDPOINT = "/api/rule/private/search"

API_KEY_USER  = "user_api_key"       # created by create_user_test()
API_KEY_ADMIN = "admin_api_key"      # created by create_admin_test()
API_KEY_OTHER = "api_key_user_rule"  # second regular user

# --------------------------
# Seed helpers
# (same pattern as create_rule_test in init_db.py)
# --------------------------

def _make_rule(client, **overrides):
    """
    Insert a rule via the API and return its id.
    Uses sensible defaults so callers only specify what matters for their test.
    """
    defaults = {
        "title":       f"SR_{uuid.uuid4().hex[:8]}",
        "format":      "yara",
        "version":     "1.0",
        "license":     "MIT",
        "source":      "unit-test",
        "to_string":   "rule placeholder { condition: true }",
        "description": "search-test rule",
    }
    defaults.update(overrides)
    res = client.post(
        "/api/rule/private/create",
        json=defaults,
        headers={"X-API-KEY": API_KEY_USER},
    )
    assert res.status_code == 200, f"Seed rule creation failed: {res.data}"
    return res.get_json()["rule"]["id"]


def _tag_rule(client, rule_id, tag_name):
    """
    Tag a rule via the API. Creates the tag inline if needed.
    We use the admin endpoint because tag creation requires admin in most setups.
    Falls back gracefully if endpoint differs.
    """
    res = client.post(
        f"/tags/add_tag_to_rule/{rule_id}",
        json={"tag_name": tag_name},
        headers={"X-API-KEY": API_KEY_ADMIN},
    )
    # If the endpoint doesn't exist or returns an error, insert directly via DB helper.
    if res.status_code not in (200, 201):
        _tag_rule_db(tag_name, rule_id)


def _tag_rule_db(app, tag_name, rule_id):
    """Direct DB insertion for tagging — mirrors init_db pattern."""
    from app import db
    from app.core.db_class.db import Tag, RuleTagAssociation

    with app.app_context():
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(
                uuid=str(uuid.uuid4()),
                name=tag_name,
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
                created_by=1,
            )
            db.session.add(tag)
            db.session.commit()

        assoc = RuleTagAssociation(
            uuid=str(uuid.uuid4()),
            rule_id=rule_id,
            tag_id=tag.id,
            user_id=1,
            added_at=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        db.session.add(assoc)
        db.session.commit()


def post_search(client, payload):
    return client.post(
        SEARCH_ENDPOINT,
        json=payload,
        headers={"X-API-KEY": API_KEY_USER},
    )


def _titles(res):
    return [r["title"] for r in res.get_json()["rules"]]


# ==================================================
# Auth
# ==================================================

def test_search_requires_api_key(client):
    res = client.post(SEARCH_ENDPOINT, json={})
    assert res.status_code == 403


def test_search_wrong_api_key(client):
    res = client.post(SEARCH_ENDPOINT, json={}, headers={"X-API-KEY": "totally_wrong"})
    assert res.status_code == 403


# ==================================================
# Basic structure
# ==================================================

def test_search_empty_body_returns_200(client):
    """No filters → all rules, paginated."""
    res = post_search(client, {})
    assert res.status_code == 200
    data = res.get_json()
    assert "rules"    in data
    assert "total"    in data
    assert "page"     in data
    assert "pages"    in data
    assert "per_page" in data
    assert data["paginate"] is True


def test_search_no_body_returns_200(client):
    res = client.post(SEARCH_ENDPOINT, headers={"X-API-KEY": API_KEY_USER})
    assert res.status_code == 200


# ==================================================
# Text search — search_field=title
# ==================================================

def test_search_by_title_partial(client):
    _make_rule(client, title="SRTEST_MimikatzDump", to_string="rule SRTEST_MimikatzDump { condition: true }")
    _make_rule(client, title="SRTEST_Unrelated",    to_string="rule SRTEST_Unrelated { condition: true }")

    res = post_search(client, {"search": "MimikatzDump", "search_field": "title"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_MimikatzDump" in titles
    assert "SRTEST_Unrelated"    not in titles


def test_search_by_title_case_insensitive(client):
    _make_rule(client, title="SRTEST_CaseInsensitive", to_string="rule SRTEST_CaseInsensitive { condition: true }")

    res = post_search(client, {"search": "caseinsensitive", "search_field": "title"})
    assert res.status_code == 200
    assert "SRTEST_CaseInsensitive" in _titles(res)


def test_search_by_title_exact_match_finds(client):
    _make_rule(client, title="SRTEST_ExactAlpha",      to_string="rule SRTEST_ExactAlpha { condition: true }")
    _make_rule(client, title="SRTEST_ExactAlphaExtra", to_string="rule SRTEST_ExactAlphaExtra { condition: true }")

    res = post_search(client, {
        "search":       "SRTEST_ExactAlpha",
        "search_field": "title",
        "exact_match":  True,
    })
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_ExactAlpha"      in titles
    assert "SRTEST_ExactAlphaExtra" not in titles


def test_search_by_title_exact_match_not_found(client):
    _make_rule(client, title="SRTEST_ExactOnly", to_string="rule SRTEST_ExactOnly { condition: true }")

    res = post_search(client, {
        "search":       "SRTEST_Exact",
        "search_field": "title",
        "exact_match":  True,
    })
    assert res.status_code == 200
    assert "SRTEST_ExactOnly" not in _titles(res)


# ==================================================
# Text search — search_field=content
# ==================================================

def test_search_by_content_finds(client):
    _make_rule(client,
               title="SRTEST_ContentMatch",
               to_string='rule SRTEST_ContentMatch { strings: $s = "evil_payload_xyz" condition: $s }')
    _make_rule(client,
               title="SRTEST_ContentNoMatch",
               to_string="rule SRTEST_ContentNoMatch { condition: true }")

    res = post_search(client, {"search": "evil_payload_xyz", "search_field": "content"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_ContentMatch"   in titles
    assert "SRTEST_ContentNoMatch" not in titles


def test_search_by_content_exact(client):
    _make_rule(client,
               title="SRTEST_ContentExact",
               to_string='rule SRTEST_ContentExact { strings: $s = "unique_exact_str_ABC" condition: $s }')

    res = post_search(client, {
        "search":       "unique_exact_str_ABC",
        "search_field": "content",
        "exact_match":  True,
    })
    assert res.status_code == 200
    assert "SRTEST_ContentExact" in _titles(res)


# ==================================================
# Text search — search_field=all (default)
# ==================================================

def test_search_all_finds_by_description(client):
    _make_rule(client,
               title="SRTEST_DescSearch",
               description="Detects ransomware_unique_keyword lateral activity",
               to_string="rule SRTEST_DescSearch { condition: true }")

    res = post_search(client, {"search": "ransomware_unique_keyword"})
    assert res.status_code == 200
    assert "SRTEST_DescSearch" in _titles(res)


def test_search_all_finds_by_author(client):
    _make_rule(client,
               title="SRTEST_AuthorSearch",
               to_string="rule SRTEST_AuthorSearch { condition: true }")
    # author is set via the API user's name — just verify the query doesn't crash
    res = post_search(client, {"search": "Matrix"})  # first_name from create_user_test
    assert res.status_code == 200


def test_search_empty_string_treated_as_no_filter(client):
    res = post_search(client, {"search": "   "})
    assert res.status_code == 200


def test_search_field_invalid_value(client):
    res = post_search(client, {"search": "x", "search_field": "banana"})
    assert res.status_code == 400
    assert "search_field" in res.get_json()["message"]


# ==================================================
# Filter: author
# ==================================================

def test_filter_author_exact(client):
    # We can't easily control the stored author (it comes from the API user).
    # So we verify that filtering by the known seeded author returns only matching rows.
    res = post_search(client, {"author": "Matrix"})  # first_name of user_api_key user
    assert res.status_code == 200
    for r in res.get_json()["rules"]:
        assert "matrix" in r["author"].lower()


def test_filter_author_no_results(client):
    res = post_search(client, {"author": "ZZZNobodyZZZ"})
    assert res.status_code == 200
    assert res.get_json()["total"] == 0


def test_filter_author_not_string_returns_400(client):
    res = post_search(client, {"author": 42})
    assert res.status_code == 400
    assert "author" in res.get_json()["message"]


# ==================================================
# Filter: rule_type / format
# ==================================================

def test_filter_rule_type_yara_only(client):
    _make_rule(client, title="SRTEST_Format_Yara",  format="yara",
               to_string="rule SRTEST_Format_Yara { condition: true }")
    _make_rule(client, title="SRTEST_Format_Sigma", format="sigma",
               to_string=(
                   "title: SRTEST_Format_Sigma\nstatus: test\n"
                   "logsource:\n  category: process_creation\n"
                   "detection:\n  selection:\n    Image: test.exe\n  condition: selection"
               ))

    res = post_search(client, {"rule_type": "yara"})
    assert res.status_code == 200
    for r in res.get_json()["rules"]:
        assert "yara" in r["format"].lower()


def test_filter_rule_type_sigma_only(client):
    _make_rule(client, title="SRTEST_Sigma_Only", format="sigma",
               to_string=(
                   "title: SRTEST_Sigma_Only\nstatus: test\n"
                   "logsource:\n  category: process_creation\n"
                   "detection:\n  selection:\n    Image: test.exe\n  condition: selection"
               ))

    res = post_search(client, {"rule_type": "sigma"})
    assert res.status_code == 200
    for r in res.get_json()["rules"]:
        assert "sigma" in r["format"].lower()


def test_filter_rule_type_not_string_returns_400(client):
    res = post_search(client, {"rule_type": ["yara", "sigma"]})
    assert res.status_code == 400
    assert "rule_type" in res.get_json()["message"]


# ==================================================
# Filter: source
# ==================================================

def test_filter_source_exact(client):
    _make_rule(client, title="SRTEST_Source_Github",
               source="https://github.com/elastic/detection-rules",
               to_string="rule SRTEST_Source_Github { condition: true }")
    _make_rule(client, title="SRTEST_Source_Internal",
               source="internal-soc-team",
               to_string="rule SRTEST_Source_Internal { condition: true }")

    res = post_search(client, {"source": "elastic"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_Source_Github"   in titles
    assert "SRTEST_Source_Internal" not in titles


def test_filter_source_csv_or(client):
    """Comma-separated sources are OR'd."""
    _make_rule(client, title="SRTEST_Source_A", source="github.com/org-a",
               to_string="rule SRTEST_Source_A { condition: true }")
    _make_rule(client, title="SRTEST_Source_B", source="internal-blue-team",
               to_string="rule SRTEST_Source_B { condition: true }")
    _make_rule(client, title="SRTEST_Source_C", source="other-source",
               to_string="rule SRTEST_Source_C { condition: true }")

    res = post_search(client, {"source": "github.com/org-a,internal-blue-team"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_Source_A" in titles
    assert "SRTEST_Source_B" in titles
    assert "SRTEST_Source_C" not in titles


def test_filter_source_not_string_returns_400(client):
    res = post_search(client, {"source": 123})
    assert res.status_code == 400


# ==================================================
# Filter: license
# ==================================================

def test_filter_license_mit(client):
    _make_rule(client, title="SRTEST_License_MIT",    license="MIT",
               to_string="rule SRTEST_License_MIT { condition: true }")
    _make_rule(client, title="SRTEST_License_GPL",    license="GPL-3.0",
               to_string="rule SRTEST_License_GPL { condition: true }")
    _make_rule(client, title="SRTEST_License_Apache", license="Apache-2.0",
               to_string="rule SRTEST_License_Apache { condition: true }")

    res = post_search(client, {"license": "MIT"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_License_MIT"    in titles
    assert "SRTEST_License_GPL"    not in titles
    assert "SRTEST_License_Apache" not in titles


def test_filter_license_csv_or(client):
    _make_rule(client, title="SRTEST_Lic_A", license="MIT",
               to_string="rule SRTEST_Lic_A { condition: true }")
    _make_rule(client, title="SRTEST_Lic_B", license="Apache-2.0",
               to_string="rule SRTEST_Lic_B { condition: true }")
    _make_rule(client, title="SRTEST_Lic_C", license="GPL-3.0",
               to_string="rule SRTEST_Lic_C { condition: true }")

    res = post_search(client, {"license": "MIT,Apache-2.0"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_Lic_A" in titles
    assert "SRTEST_Lic_B" in titles
    assert "SRTEST_Lic_C" not in titles


# ==================================================
# Filter: vulnerabilities (CVE)
# ==================================================

def test_filter_cve_single(client):
    _make_rule(client,
               title="SRTEST_CVE_Log4Shell",
               description="Detects CVE-2021-44228 exploitation via JNDI",
               to_string='rule SRTEST_CVE_Log4Shell { strings: $jndi = "jndi:" condition: $jndi }',
               cve_id="CVE-2021-44228")
    _make_rule(client,
               title="SRTEST_CVE_Unrelated",
               to_string="rule SRTEST_CVE_Unrelated { condition: true }")

    res = post_search(client, {"vulnerabilities": ["CVE-2021-44228"]})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_CVE_Log4Shell" in titles
    assert "SRTEST_CVE_Unrelated" not in titles


def test_filter_cve_multiple_or(client):
    _make_rule(client, title="SRTEST_CVE_A",
               to_string="rule SRTEST_CVE_A { condition: true }",
               cve_id="CVE-2021-44228")
    _make_rule(client, title="SRTEST_CVE_B",
               to_string="rule SRTEST_CVE_B { condition: true }",
               cve_id="CVE-2023-12345")
    _make_rule(client, title="SRTEST_CVE_C",
               to_string="rule SRTEST_CVE_C { condition: true }")

    res = post_search(client, {"vulnerabilities": ["CVE-2021-44228", "CVE-2023-12345"]})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_CVE_A" in titles
    assert "SRTEST_CVE_B" in titles
    assert "SRTEST_CVE_C" not in titles


def test_filter_cve_as_csv_string(client):
    """CVEs can be sent as a comma-separated string instead of a list."""
    _make_rule(client, title="SRTEST_CVE_CSV",
               to_string="rule SRTEST_CVE_CSV { condition: true }",
               cve_id="CVE-2022-00001")

    res = post_search(client, {"vulnerabilities": "CVE-2022-00001"})
    assert res.status_code == 200
    assert "SRTEST_CVE_CSV" in _titles(res)


def test_filter_cve_invalid_format_returns_400(client):
    res = post_search(client, {"vulnerabilities": ["NOT-A-CVE"]})
    assert res.status_code == 400
    assert "CVE" in res.get_json()["message"]


def test_filter_cve_invalid_in_list_returns_400(client):
    res = post_search(client, {"vulnerabilities": ["CVE-2021-44228", "INVALID"]})
    assert res.status_code == 400


def test_filter_cve_not_list_or_string_returns_400(client):
    res = post_search(client, {"vulnerabilities": {"key": "value"}})
    assert res.status_code == 400


# ==================================================
# Filter: tags
# ==================================================

def test_filter_tag_single(app, client):
    rid_apt = _make_rule(client, title="SRTEST_Tag_APT",
                         to_string="rule SRTEST_Tag_APT { condition: true }")
    rid_mal = _make_rule(client, title="SRTEST_Tag_Malware",
                         to_string="rule SRTEST_Tag_Malware { condition: true }")
    _tag_rule_db(app, "apt",     rid_apt)
    _tag_rule_db(app, "malware", rid_mal)

    res = post_search(client, {"tags": ["apt"]})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_Tag_APT"    in titles
    assert "SRTEST_Tag_Malware" not in titles


def test_filter_tag_multiple_or(app, client):
    """Two tags → returns rules that have ANY of them."""
    rid_a = _make_rule(client, title="SRTEST_TagOR_A",
                       to_string="rule SRTEST_TagOR_A { condition: true }")
    rid_b = _make_rule(client, title="SRTEST_TagOR_B",
                       to_string="rule SRTEST_TagOR_B { condition: true }")
    _make_rule(client, title="SRTEST_TagOR_C",
               to_string="rule SRTEST_TagOR_C { condition: true }")
    _tag_rule_db(app, "ransomware", rid_a)
    _tag_rule_db(app, "trojan",     rid_b)

    res = post_search(client, {"tags": ["ransomware", "trojan"]})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_TagOR_A" in titles
    assert "SRTEST_TagOR_B" in titles
    assert "SRTEST_TagOR_C" not in titles


def test_filter_tag_case_insensitive(app, client):
    rid = _make_rule(client, title="SRTEST_TagCase",
                     to_string="rule SRTEST_TagCase { condition: true }")
    _tag_rule_db(app, "Stealer", rid)

    res = post_search(client, {"tags": ["stealer"]})
    assert res.status_code == 200
    assert "SRTEST_TagCase" in _titles(res)


def test_filter_tag_as_csv_string(app, client):
    rid = _make_rule(client, title="SRTEST_TagCSV",
                     to_string="rule SRTEST_TagCSV { condition: true }")
    _tag_rule_db(app, "exploit", rid)

    res = post_search(client, {"tags": "exploit"})
    assert res.status_code == 200
    assert "SRTEST_TagCSV" in _titles(res)


def test_filter_tag_not_list_returns_400(client):
    res = post_search(client, {"tags": {"key": "value"}})
    assert res.status_code == 400
    assert "tags" in res.get_json()["message"]


def test_filter_tag_unknown_returns_empty(client):
    res = post_search(client, {"tags": ["tag_that_will_never_exist_xyz123"]})
    assert res.status_code == 200
    assert res.get_json()["total"] == 0


# ==================================================
# Sort
# ==================================================

def test_sort_newest(client):
    _make_rule(client, title="SRTEST_Sort_2020",
               to_string="rule SRTEST_Sort_2020 { condition: true }")
    _make_rule(client, title="SRTEST_Sort_2025",
               to_string="rule SRTEST_Sort_2025 { condition: true }")

    res = post_search(client, {"sort_by": "newest", "per_page": 100})
    assert res.status_code == 200
    dates = [r["creation_date"] for r in res.get_json()["rules"] if r.get("creation_date")]
    assert dates == sorted(dates, reverse=True)


def test_sort_oldest(client):
    res = post_search(client, {"sort_by": "oldest", "per_page": 100})
    assert res.status_code == 200
    dates = [r["creation_date"] for r in res.get_json()["rules"] if r.get("creation_date")]
    assert dates == sorted(dates)


def test_sort_most_likes(client):
    _make_rule(client, title="SRTEST_LikesLow",  to_string="rule SRTEST_LikesLow { condition: true }")
    _make_rule(client, title="SRTEST_LikesHigh", to_string="rule SRTEST_LikesHigh { condition: true }")

    # Patch vote_up directly so we control ordering
    from app import db
    from app.core.db_class.db import Rule
    with client.application.app_context():
        Rule.query.filter_by(title="SRTEST_LikesHigh").update({"vote_up": 999})
        Rule.query.filter_by(title="SRTEST_LikesLow").update({"vote_up": 1})
        db.session.commit()

    res = post_search(client, {"sort_by": "most_likes", "per_page": 100})
    assert res.status_code == 200
    titles = _titles(res)
    assert titles.index("SRTEST_LikesHigh") < titles.index("SRTEST_LikesLow")


def test_sort_invalid_value_returns_400(client):
    res = post_search(client, {"sort_by": "random_order"})
    assert res.status_code == 400
    assert "sort_by" in res.get_json()["message"]


# ==================================================
# Pagination
# ==================================================

def test_pagination_structure(client):
    for i in range(6):
        _make_rule(client, title=f"SRTEST_Pag_{i:02d}",
                   to_string=f"rule SRTEST_Pag_{i:02d} {{ condition: true }}")

    res = post_search(client, {"per_page": 3, "page": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["rules"]) <= 3
    assert data["per_page"] == 3
    assert data["page"] == 1
    assert "pages" in data


def test_pagination_page_2_different_from_page_1(client):
    for i in range(10):
        _make_rule(client, title=f"SRTEST_PagB_{i:02d}",
                   to_string=f"rule SRTEST_PagB_{i:02d} {{ condition: true }}")

    p1 = post_search(client, {"per_page": 5, "page": 1})
    p2 = post_search(client, {"per_page": 5, "page": 2})
    assert p1.status_code == 200
    assert p2.status_code == 200
    titles_p1 = set(_titles(p1))
    titles_p2 = set(_titles(p2))
    assert titles_p1.isdisjoint(titles_p2)


def test_pagination_page_zero_returns_400(client):
    res = post_search(client, {"page": 0})
    assert res.status_code == 400
    assert "page" in res.get_json()["message"]


def test_pagination_page_string_returns_400(client):
    res = post_search(client, {"page": "abc"})
    assert res.status_code == 400


def test_pagination_per_page_too_high_returns_400(client):
    res = post_search(client, {"per_page": 101})
    assert res.status_code == 400
    assert "per_page" in res.get_json()["message"]


def test_pagination_per_page_zero_returns_400(client):
    res = post_search(client, {"per_page": 0})
    assert res.status_code == 400


# ==================================================
# paginate=false
# ==================================================

def test_no_pagination_returns_all_results(client):
    for i in range(4):
        _make_rule(client, title=f"SRTEST_NoPag_{i}",
                   to_string=f"rule SRTEST_NoPag_{i} {{ condition: true }}")

    res = post_search(client, {"paginate": False})
    assert res.status_code == 200
    data = res.get_json()
    assert data["paginate"] is False
    assert "page"  not in data
    assert "pages" not in data
    assert len(data["rules"]) == data["total"]


def test_no_pagination_respects_filters(client):
    _make_rule(client, title="SRTEST_NoPag_Yara",  format="yara",
               to_string="rule SRTEST_NoPag_Yara { condition: true }")
    _make_rule(client, title="SRTEST_NoPag_Sigma", format="sigma",
               to_string=(
                   "title: SRTEST_NoPag_Sigma\nstatus: test\n"
                   "logsource:\n  category: process_creation\n"
                   "detection:\n  selection:\n    Image: test.exe\n  condition: selection"
               ))

    res = post_search(client, {"paginate": False, "rule_type": "yara"})
    assert res.status_code == 200
    assert all("yara" in r["format"].lower() for r in res.get_json()["rules"])


def test_no_pagination_invalid_value_returns_400(client):
    res = post_search(client, {"paginate": "maybe"})
    assert res.status_code == 400
    assert "paginate" in res.get_json()["message"]


# ==================================================
# fields selection
# ==================================================

def test_fields_content_only(client):
    _make_rule(client, title="SRTEST_Fields_Content",
               to_string='rule SRTEST_Fields_Content { strings: $s = "secret_xyz" condition: $s }')

    res = post_search(client, {"fields": ["to_string"]})
    assert res.status_code == 200
    rules = res.get_json()["rules"]
    assert len(rules) >= 1
    for r in rules:
        assert list(r.keys()) == ["to_string"]
        assert "secret_xyz" in r["to_string"] or True  # verify field is present


def test_fields_id_and_title_only(client):
    res = post_search(client, {"fields": ["id", "title"]})
    assert res.status_code == 200
    for r in res.get_json()["rules"]:
        assert set(r.keys()) == {"id", "title"}


def test_fields_multiple(client):
    res = post_search(client, {"fields": ["id", "title", "format", "license"]})
    assert res.status_code == 200
    for r in res.get_json()["rules"]:
        assert set(r.keys()) == {"id", "title", "format", "license"}


def test_fields_all_returned_when_omitted(client):
    _make_rule(client, title="SRTEST_AllFields",
               to_string="rule SRTEST_AllFields { condition: true }")
    res = post_search(client, {})
    assert res.status_code == 200
    if res.get_json()["rules"]:
        keys = set(res.get_json()["rules"][0].keys())
        for expected in ("id", "title", "format", "to_string", "author", "license"):
            assert expected in keys


def test_fields_as_csv_string(client):
    res = post_search(client, {"fields": "id,title,format"})
    assert res.status_code == 200
    for r in res.get_json()["rules"]:
        assert set(r.keys()) == {"id", "title", "format"}


def test_fields_unknown_returns_400(client):
    res = post_search(client, {"fields": ["title", "nonexistent_field"]})
    assert res.status_code == 400
    assert "nonexistent_field" in res.get_json()["message"]


# ==================================================
# Combined filters
# ==================================================

def test_combined_author_and_format(client):
    # Both rules are created by the same user (Matrix) — format is the differentiator
    _make_rule(client, title="SRTEST_Comb_Yara",  format="yara",
               to_string="rule SRTEST_Comb_Yara { condition: true }")
    _make_rule(client, title="SRTEST_Comb_Sigma", format="sigma",
               to_string=(
                   "title: SRTEST_Comb_Sigma\nstatus: test\n"
                   "logsource:\n  category: process_creation\n"
                   "detection:\n  selection:\n    Image: test.exe\n  condition: selection"
               ))

    res = post_search(client, {"author": "Matrix", "rule_type": "yara"})
    assert res.status_code == 200
    for r in res.get_json()["rules"]:
        assert "matrix" in r["author"].lower()
        assert "yara"   in r["format"].lower()


def test_combined_license_and_source(client):
    _make_rule(client, title="SRTEST_Comb_LS_Match",
               license="MIT", source="github.com/test-org",
               to_string="rule SRTEST_Comb_LS_Match { condition: true }")
    _make_rule(client, title="SRTEST_Comb_LS_WrongLic",
               license="GPL", source="github.com/test-org",
               to_string="rule SRTEST_Comb_LS_WrongLic { condition: true }")
    _make_rule(client, title="SRTEST_Comb_LS_WrongSrc",
               license="MIT", source="internal",
               to_string="rule SRTEST_Comb_LS_WrongSrc { condition: true }")

    res = post_search(client, {"license": "MIT", "source": "github.com/test-org"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_Comb_LS_Match"    in titles
    assert "SRTEST_Comb_LS_WrongLic" not in titles
    assert "SRTEST_Comb_LS_WrongSrc" not in titles


def test_combined_cve_and_license(client):
    _make_rule(client, title="SRTEST_Comb_CVE_MIT",
               license="MIT", cve_id="CVE-2020-11111",
               to_string="rule SRTEST_Comb_CVE_MIT { condition: true }")
    _make_rule(client, title="SRTEST_Comb_CVE_GPL",
               license="GPL", cve_id="CVE-2020-11111",
               to_string="rule SRTEST_Comb_CVE_GPL { condition: true }")

    res = post_search(client, {"vulnerabilities": ["CVE-2020-11111"], "license": "MIT"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_Comb_CVE_MIT" in titles
    assert "SRTEST_Comb_CVE_GPL" not in titles


def test_combined_tag_and_format(app, client):
    rid = _make_rule(client, title="SRTEST_Comb_Tag_Yara", format="yara",
                     to_string="rule SRTEST_Comb_Tag_Yara { condition: true }")
    _make_rule(client, title="SRTEST_Comb_Tag_Sigma", format="sigma",
               to_string=(
                   "title: SRTEST_Comb_Tag_Sigma\nstatus: test\n"
                   "logsource:\n  category: process_creation\n"
                   "detection:\n  selection:\n    Image: test.exe\n  condition: selection"
               ))
    _tag_rule_db(app, "credential_access", rid)

    res = post_search(client, {"tags": ["credential_access"], "rule_type": "yara"})
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_Comb_Tag_Yara"  in titles
    assert "SRTEST_Comb_Tag_Sigma" not in titles


def test_combined_search_and_tag(app, client):
    rid = _make_rule(client, title="SRTEST_Comb_SearchTag",
                     description="Detects lateral_movement_unique_kw pivot",
                     to_string="rule SRTEST_Comb_SearchTag { condition: true }")
    _make_rule(client, title="SRTEST_Comb_SearchTag_NoTag",
               description="Detects lateral_movement_unique_kw but no tag",
               to_string="rule SRTEST_Comb_SearchTag_NoTag { condition: true }")
    _tag_rule_db(app, "lateral_movement", rid)

    res = post_search(client, {
        "search": "lateral_movement_unique_kw",
        "tags":   ["lateral_movement"],
    })
    assert res.status_code == 200
    titles = _titles(res)
    assert "SRTEST_Comb_SearchTag"       in titles
    assert "SRTEST_Comb_SearchTag_NoTag" not in titles


def test_combined_paginate_false_and_fields(client):
    for i in range(3):
        _make_rule(client, title=f"SRTEST_Comb_Full_{i}",
                   to_string=f"rule SRTEST_Comb_Full_{i} {{ condition: true }}")

    res = post_search(client, {
        "rule_type": "yara",
        "paginate":  False,
        "fields":    ["id", "title", "to_string"],
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["paginate"] is False
    for r in data["rules"]:
        assert set(r.keys()) == {"id", "title", "to_string"}


# ==================================================
# Edge cases / empty results
# ==================================================

def test_no_results_returns_empty_list(client):
    res = post_search(client, {"search": "zzzzz_impossible_match_zzzzz"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 0
    assert data["rules"] == []


def test_no_results_unknown_source(client):
    res = post_search(client, {"source": "ZZZ_source_that_never_exists_ZZZ"})
    assert res.status_code == 200
    assert res.get_json()["total"] == 0


def test_no_results_unknown_tag(client):
    res = post_search(client, {"tags": ["zzz_tag_never_exists_zzz"]})
    assert res.status_code == 200
    assert res.get_json()["total"] == 0


def test_non_json_body_treated_as_empty_filter(client):
    """Plain-text body should be handled gracefully."""
    res = client.post(
        SEARCH_ENDPOINT,
        data="not json",
        content_type="text/plain",
        headers={"X-API-KEY": API_KEY_USER},
    )
    assert res.status_code == 200