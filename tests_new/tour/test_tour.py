"""Tutorial (app/features/tour): the tour data embedded in every page is filtered by role on the
server, the full tour adapts to who is browsing, and an empty instance gets the demo pages."""
import json
import re

from app.core.db_class.bundle import Bundle
from app.core.db_class.rule import Rule


def tour_data(client, url):
    page = client.get(url).get_data(as_text=True)
    m = re.search(r'id="rz-tour-data">(.*?)</script>', page, re.S)
    return json.loads(m.group(1)) if m else None


def test_every_page_has_the_tutorial_icon_but_the_login_flow(clients):
    assert tour_data(clients["anonymous"], "/rule/rules_list")["page"] == "rule.rules_list"
    assert 'id="rz-tour-launch"' in clients["anonymous"].get("/").get_data(as_text=True)
    assert tour_data(clients["anonymous"], "/account/login") is None


def test_steps_are_filtered_by_role(clients):
    anon = tour_data(clients["anonymous"], "/")
    user = tour_data(clients["user"], "/")
    assert anon["intro"]["role_badge"] == "Visitor" and user["intro"]["role_badge"] == "Member"
    titles = lambda d: [s["title"] for s in d["tour"]["steps"]]   # noqa: E731
    assert "Join to contribute" in titles(anon) and "Add a rule or build a bundle" not in titles(anon)
    assert "Add a rule or build a bundle" in titles(user) and "Join to contribute" not in titles(user)
    assert tour_data(clients["admin"], "/")["intro"]["role_badge"] == "Administrator"


def test_a_page_without_its_own_tour_gets_the_generic_one(clients):
    data = tour_data(clients["user"], "/community/comments")
    assert data and data["tour"] is None                     # built in the browser from the page


def test_full_tour_adapts_to_the_visitor(clients):
    pages = lambda who: [p["title"] for p in clients[who].get("/tour/full").json["pages"]]   # noqa: E731
    assert "Administration" in pages("admin")
    assert "Administration" not in pages("user") and "Add rules" in pages("user")
    assert "Add rules" not in pages("anonymous") and "Your account" not in pages("anonymous")


def test_empty_instance_tours_the_demo_pages(app, clients):
    Rule.query.update({Rule.is_deleted: True})
    Bundle.query.delete()
    from app import db
    db.session.commit()
    urls = {p["title"]: p["url"] for p in clients["anonymous"].get("/tour/full").json["pages"]}
    assert urls["A rule"] == "/tour/demo/rule" and urls["A bundle"] == "/tour/demo/bundle"
    for kind in ("rule", "bundle"):
        page = clients["anonymous"].get(f"/tour/demo/{kind}")
        assert page.status_code == 200 and "Example for the tutorial" in page.get_data(as_text=True)
    assert Rule.query.filter_by(is_deleted=False).count() == 0 and Bundle.query.count() == 0   # nothing saved
    assert clients["anonymous"].get("/tour/demo/other").status_code == 404


def test_the_icon_can_be_switched_off(clients, monkeypatch):
    from app.features.tour import tour_core
    real = tour_core._setting
    monkeypatch.setattr(tour_core, "_setting", lambda k, d=None: False if k == "tour.enabled" else real(k, d))
    assert tour_data(clients["user"], "/") is None


def test_an_empty_rulezet_starts_on_the_welcome_page(clients):
    from app import db
    Rule.query.update({Rule.is_deleted: True})
    db.session.commit()
    assert tour_data(clients["anonymous"], "/")["autostart"] is True
    pages = lambda who: [p["title"] for p in clients[who].get("/tour/full").json["pages"]]   # noqa: E731
    assert pages("anonymous")[0] == "Welcome" and "Connectors" not in pages("anonymous")
    assert pages("admin")[:2] == ["Welcome", "Connectors"]
    page = clients["admin"].get("/tour/welcome").get_data(as_text=True)
    assert "Welcome to Rulezet" in page and "Set up a connector" in page
    assert "Set up a connector" not in clients["user"].get("/tour/welcome").get_data(as_text=True)


def test_a_rulezet_with_rules_skips_the_welcome_pages(clients, users):
    from tests_new.helpers.rules import make_rule
    make_rule(users.owner)
    assert tour_data(clients["anonymous"], "/")["autostart"] is False
    assert "Welcome" not in [p["title"] for p in clients["admin"].get("/tour/full").json["pages"]]


def test_first_logged_in_visit_creates_a_real_first_rule_and_bundle(clients, users):
    from app import db
    Rule.query.update({Rule.is_deleted: True})
    db.session.commit()
    res = clients["user"].post("/tour/starter").json
    assert res["created"] is True
    rule = Rule.query.filter_by(is_deleted=False, source="Rulezet tutorial").one()
    assert rule.user_id == users.user.id
    bundle = Bundle.query.filter_by(user_id=users.user.id).one()
    assert res["rule"].endswith(f"/{rule.id}") and res["bundle"].endswith(f"/{bundle.id}")
    assert clients["user"].post("/tour/starter").json["created"] is False         # once only
    full = clients["user"].get("/tour/full?onboarding=1").json["pages"]
    assert full[0]["title"] == "Welcome" and full[[p["title"] for p in full].index("A rule")]["url"] == res["rule"]
    assert "open the rule" in clients["user"].get("/tour/welcome").get_data(as_text=True)
    assert clients["anonymous"].post("/tour/starter").status_code in (302, 401)


def test_the_first_admin_must_change_the_generated_password(app, clients, users):
    from app import db
    users.admin.must_change_password = True
    db.session.commit()
    res = clients["admin"].get("/rule/rules_list", headers={"Accept": "text/html"})
    assert res.status_code == 302 and "/account/edit" in res.headers["Location"]
    assert clients["admin"].get("/account/edit").status_code == 200
    assert clients["admin"].post("/tour/starter").status_code == 403
    from app.features.account import account_core as AccountModel
    AccountModel.edit_user_core({"first_name": "admin", "last_name": "admin", "email": users.admin.email,
                                 "password": "a-new-Passw0rd!"}, users.admin.id)
    db.session.refresh(users.admin)
    assert users.admin.must_change_password is False
    assert clients["admin"].get("/rule/rules_list").status_code == 200


def test_first_setup_needs_a_real_email_and_lets_assets_through(clients, users):
    from app import db
    users.admin.must_change_password = True
    users.admin.email = "admin@admin.admin"
    db.session.commit()
    c = clients["admin"]
    assert c.get("/static/image/logo.png").status_code in (200, 304)            # the logo still loads
    assert c.get("/account/avatar_preview.png?kind=rulezy&choice=chatbot&bg=white&size=small").status_code == 200
    assert c.get("/notifications/bell").status_code == 403                     # background data refused
    page = c.get("/account/edit").get_data(as_text=True)
    assert "Set up your account" in page and 'class="rz-first-setup"' in page
    form = {"first_name": "admin", "last_name": "admin", "email": "admin@admin.admin",
            "change_password": "y", "password": "N3w-passw0rd!", "password2": "N3w-passw0rd!"}
    c.post("/account/edit", data=form)
    db.session.refresh(users.admin)
    assert users.admin.must_change_password is True                             # placeholder email refused
    res = c.post("/account/edit", data={**form, "email": "me@example.org"})
    assert res.status_code == 302 and res.headers["Location"].endswith("/")
    db.session.refresh(users.admin)
    assert users.admin.must_change_password is False and users.admin.email == "me@example.org"


def test_first_start_thanks_then_celebrates_after_the_setup(clients, users):
    from app import db
    Rule.query.update({Rule.is_deleted: True})
    users.admin.must_change_password = True
    users.admin.email = "admin@admin.admin"
    db.session.commit()
    assert tour_data(clients["anonymous"], "/")["setup_pending"] is True          # thank-you card → login
    form = {"first_name": "admin", "last_name": "admin", "email": "me@example.org",
            "change_password": "y", "password": "N3w-passw0rd!", "password2": "N3w-passw0rd!"}
    clients["admin"].post("/account/edit", data=form)
    first = tour_data(clients["admin"], "/")
    assert first["just_setup"] is True and first["setup_pending"] is False         # confetti + tour
    assert tour_data(clients["admin"], "/")["just_setup"] is False                  # only once
    assert tour_data(clients["anonymous"], "/")["setup_pending"] is False
