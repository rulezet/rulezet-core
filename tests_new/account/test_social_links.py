"""Profile links (setting user.social_links, social_links_core.py): edit form, API, profile pages,
user list and UserChip card."""
import json

from app import db
from app.core.db_class.user import User
from tests_new.helpers.account import profile_form
from tests_new.helpers.users import api_headers

EDIT = "/account/edit"


def _edit(client, user, **social):
    form = profile_form(user)
    form.update({f"social_{k}": v for k, v in social.items()})
    return client.post(EDIT, data=form, follow_redirects=False)


def test_new_networks_saved_cleared_and_shown_everywhere(clients, users):
    r = _edit(clients["user"], users.user, linkedin="https://www.linkedin.com/in/tester", bluesky="https://bsky.app/profile/t.bsky.social")
    assert r.status_code == 302
    db.session.expire_all()
    user = db.session.get(User, users.user.id)
    assert json.loads(user.social_links) == {"linkedin": "https://www.linkedin.com/in/tester",
                                             "bluesky": "https://bsky.app/profile/t.bsky.social"}
    keys = [l["key"] for l in user.profile_links()]
    assert keys == ["linkedin", "bluesky"]                                  # the setting's order
    mini = clients["anonymous"].get(f"/account/user_mini/{user.id}").get_json()
    assert [l["key"] for l in mini["links"]] == keys and mini["links"][0]["icon"] == "fa-brands fa-linkedin"
    page = clients["owner"].get(f"/account/detail_user/{user.id}").get_data(as_text=True)
    assert "linkedin.com/in/tester" in page and 'rel="me noopener noreferrer"' in page
    _edit(clients["user"], user, linkedin="")                                # an empty field clears it
    db.session.expire_all()
    assert json.loads(db.session.get(User, user.id).social_links) == {"bluesky": "https://bsky.app/profile/t.bsky.social"}


def test_wrong_host_or_scheme_refused_and_nothing_saved(clients, users):
    for bad in ("https://evil.example/in/x", "javascript:alert(1)", "ftp://linkedin.com/in/x"):
        r = _edit(clients["user"], users.user, linkedin=bad, location="changed?")
        assert r.status_code == 200                                         # form shown again with the error
        db.session.expire_all()
        user = db.session.get(User, users.user.id)
        assert user.social_links is None and user.location != "changed?"


def test_a_field_not_sent_keeps_its_value(clients, users):
    users.user.website_url = "https://keep.example"
    db.session.commit()
    form = profile_form(users.user)
    form.pop("website_url")                                                 # e.g. network taken out of the setting
    clients["user"].post(EDIT, data=form)
    db.session.expire_all()
    assert db.session.get(User, users.user.id).website_url == "https://keep.example"


def test_a_url_never_runs_as_a_vue_template(clients, users):
    users.user.social_links = json.dumps({"medium": "https://blog.example/[[constructor.constructor('alert(1)')()]]"})
    db.session.commit()
    page = clients["owner"].get(f"/account/detail_user/{users.user.id}").get_data(as_text=True)
    i = page.index("blog.example")
    assert 'v-pre' in page[page.rindex('<div', 0, i):i]                    # the links block is not compiled by Vue


def test_api_edit(clients, users):
    h = api_headers(users.user)
    base = {"email": users.user.email, "first_name": "A", "last_name": "B"}
    r = clients["anonymous"].post("/api/account/private/edit", headers=h,
                                  json={**base, "social_links": {"youtube": "https://www.youtube.com/@t"}})
    assert r.status_code == 200, r.get_json()
    db.session.expire_all()
    assert json.loads(db.session.get(User, users.user.id).social_links) == {"youtube": "https://www.youtube.com/@t"}
    bad = clients["anonymous"].post("/api/account/private/edit", headers=h,
                                    json={**base, "social_links": {"youtube": "https://evil.example/x"}})
    assert bad.status_code == 400
