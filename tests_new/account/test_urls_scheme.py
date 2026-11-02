"""An address typed without http(s):// gets https:// (organisations' website, profile links)."""
import pytest

from app.core.utils.urls import with_scheme


@pytest.mark.parametrize("typed, kept", [
    ("circl.lu", "https://circl.lu"), ("www.circl.lu/team?x=1", "https://www.circl.lu/team?x=1"),
    ("https://circl.lu", "https://circl.lu"), ("http://a.org", "http://a.org"),
    ("javascript:alert(1)", "javascript:alert(1)"), ("not a site", "not a site"), ("", ""),
])
def test_with_scheme(typed, kept):
    assert with_scheme(typed) == kept


def test_organisation_website_gets_https(clients, users):
    r = clients["admin"].post("/account/organisations", json={"name": "CIRCL", "website": "circl.lu"})
    assert r.status_code in (200, 201), r.get_json()
    from app.core.db_class.user import Organisation
    assert Organisation.query.filter_by(name="CIRCL").one().website == "https://circl.lu"


def test_profile_link_gets_https():
    from app.features.account.social_links_core import clean_links
    cleaned, errors = clean_links({"git": "github.com/ecrou-exact"})
    assert not errors and cleaned["git"] == "https://github.com/ecrou-exact"
