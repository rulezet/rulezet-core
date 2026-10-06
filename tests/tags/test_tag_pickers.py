"""Lazy tag pickers & filters — TagInput (/tags/picker/*, /tags/get_all_tags)
and MultiTagFilter (/rule|/bundle/get_all_tags_usage?view=…): folders first,
one folder page at a time, server-side search — never the whole catalog.
Visibility must be exactly the one of the full endpoints."""

import datetime
import uuid

import pytest

from app import db
from app.core.db_class.db import (Bundle, BundleTagAssociation, Rule, RuleTagAssociation, Tag, User,
                                  tag_namespace)


def _user(email):
    return User.query.filter_by(email=email).first()


def _tag(name, visibility="public", owner=None, source="Manual", active=True):
    t = Tag(uuid=str(uuid.uuid4()), name=name, visibility=visibility, source=source, is_active=active,
            created_by=(owner or _user("admin@admin.admin")).id)
    db.session.add(t)
    db.session.commit()
    return t


def _rule(fmt="yara"):
    r = Rule(format=fmt, title=f"R {uuid.uuid4().hex[:6]}", license="MIT", description="d",
             uuid=str(uuid.uuid4()), source="test", author="a", version=1, user_id=_user("t@t.t").id,
             to_string="rule a { condition: true }", vote_up=0, vote_down=0,
             creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
             last_modif=datetime.datetime.now(tz=datetime.timezone.utc))
    db.session.add(r)
    db.session.commit()
    return r


def _link(rule, *tags):
    for t in tags:
        db.session.add(RuleTagAssociation(uuid=str(uuid.uuid4()), rule_id=rule.id, tag_id=t.id,
                                          user_id=rule.user_id))
    db.session.commit()


def _login(client, user):
    from flask import g
    with client.session_transaction() as s:
        if user is None:
            s.pop("_user_id", None)
        else:
            s["_user_id"] = str(user.id)
            s["_fresh"] = True
    g.pop("_login_user", None)


# ── namespace column ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,expected", [
    ("tlp:clear", "tlp"), ('misp-galaxy:tool="Cobalt Strike"', "tool"), ("malware", ""),
    ("misp-galaxy:tool", "misp-galaxy"), ('kunai:"<=0.6"', "kunai"),
])
def test_tag_namespace_rule(name, expected):
    assert tag_namespace(name) == expected


def test_namespace_is_kept_in_sync(app):
    with app.app_context():
        t = _tag("alpha:one")
        assert t.namespace == "alpha"
        t.name = "beta:one"
        db.session.commit()
        assert db.session.get(Tag, t.id).namespace == "beta"


# ── TagInput: folders, folder pages, search ─────────────────────────────────

def test_picker_folders_respect_visibility(client, app):
    with app.app_context():
        me, other = _user("t@t.t"), _user("neo@admin.admin")
        _tag("zz:public1"); _tag("zz:public2")
        _tag("zz:mine", "private", me)
        _tag("zz:theirs", "private", other)
        _tag("zz:off", active=False)

        _login(client, me)
        groups = client.get(f"/tags/picker/namespaces?user_id={me.id}").get_json()["groups"]
        assert {"namespace": "zz", "count": 2} in groups["Public"]
        assert {"namespace": "zz", "count": 1} in groups["Private"]           # only mine

        # without their own user_id: public only (same rule as get_all_tags)
        _login(client, me)
        assert "Private" not in client.get("/tags/picker/namespaces").get_json()["groups"]

        _login(client, me)
        names = [t["name"] for t in client.get(
            f"/tags/picker/tags?user_id={me.id}&type=Private&namespace=zz").get_json()["tags"]]
        assert names == ["zz:mine"]

        _login(client, _user("admin@admin.admin"))
        groups = client.get("/tags/picker/namespaces").get_json()["groups"]
        assert {"namespace": "zz", "count": 2} in groups["Private"]           # admin: every active tag

        _login(client, None)
        assert client.get("/tags/picker/namespaces").status_code in (302, 401)


def test_picker_folder_pagination_and_lean_json(client, app):
    with app.app_context():
        for i in range(7):
            _tag(f"pg:t{i}")
        _tag("plain-name")
        _login(client, _user("t@t.t"))
        data = client.get("/tags/picker/tags?type=Public&namespace=pg&per_page=3&page=3").get_json()
        assert [t["name"] for t in data["tags"]] == ["pg:t6"]
        assert data["total"] == 7 and data["has_more"] is False
        assert set(data["tags"][0]) == {"id", "uuid", "name", "color", "icon", "source", "visibility", "namespace"}
        _login(client, _user("t@t.t"))
        other = client.get("/tags/picker/tags?type=Public&namespace=").get_json()
        assert "plain-name" in [t["name"] for t in other["tags"]]
        _login(client, _user("t@t.t"))
        assert client.get("/tags/picker/tags?page=x").status_code == 400


def test_search_for_a_user_is_limited_ranked_and_scoped(client, app):
    with app.app_context():
        me, other = _user("t@t.t"), _user("neo@admin.admin")
        _tag("xsearch-b"); _tag("a-xsearch"); _tag("xsearch-mine", "private", me)
        _tag("xsearch-theirs", "private", other)
        _login(client, me)
        tags = client.get(f"/tags/get_all_tags?user_id={me.id}&search=xsearch&limit=2&lean=1").get_json()["tags"]
        assert [t["name"] for t in tags] == ["xsearch-b", "xsearch-mine"]      # prefix first, limit 2
        _login(client, me)
        names = {t["name"] for t in client.get(
            f"/tags/get_all_tags?user_id={me.id}&search=xsearch").get_json()["tags"]}
        assert "xsearch-theirs" not in names and "a-xsearch" in names


# ── MultiTagFilter: lazy usage views ─────────────────────────────────────────

def test_rule_usage_views(client, app):
    with app.app_context():
        pub, pub2 = _tag("uf:alpha"), _tag("uf:beta")
        secret = _tag("uf:secret", "private", _user("neo@admin.admin"))
        r1, r2 = _rule(), _rule("sigma")
        _link(r1, pub, pub2, secret)
        _link(r2, pub)
        base = "/rule/get_all_tags_usage?"

        _login(client, None)
        ns = client.get(base + "view=namespaces").get_json()["namespaces"]
        uf = next(f for f in ns if f["namespace"] == "uf")
        assert uf["tag_count"] == 2 and uf["label"] == "UF"                   # private tag hidden

        page = client.get(base + "view=tags&tag_ns=uf").get_json()
        assert [(t["name"], t["usage_count"]) for t in page["tags"]] == [("uf:alpha", 2), ("uf:beta", 1)]
        assert "created_by" not in page["tags"][0]

        # the page's other filters scope the counts
        page = client.get(base + "rule_type=sigma&view=tags&tag_ns=uf").get_json()
        assert [(t["name"], t["usage_count"]) for t in page["tags"]] == [("uf:alpha", 1)]

        found = client.get(base + "view=tags&tag_q=bet").get_json()["tags"]
        assert [t["name"] for t in found] == ["uf:beta"]
        chips = client.get(base + "view=selected&names=UF:ALPHA,uf:secret").get_json()["tags"]
        assert [t["name"] for t in chips] == ["uf:alpha"]

        _login(client, _user("neo@admin.admin"))                             # the owner sees it
        page = client.get(base + "view=tags&tag_ns=uf").get_json()
        assert "uf:secret" in [t["name"] for t in page["tags"]]


def test_anonymous_never_gets_a_cached_admin_response(client, app):
    """The full endpoint used to be cached by query string for everyone."""
    with app.app_context():
        secret = _tag("leak:secret", "private", _user("admin@admin.admin"))
        _link(_rule(), secret)
        _login(client, _user("admin@admin.admin"))
        assert "leak:secret" in [t["name"] for t in client.get("/rule/get_all_tags_usage").get_json()["tags"]]
        _login(client, None)
        assert "leak:secret" not in [t["name"] for t in client.get("/rule/get_all_tags_usage").get_json()["tags"]]


def test_bundle_usage_views_count_only_visible_bundles(client, app):
    with app.app_context():
        t = _tag("bf:one")
        owner = _user("t@t.t")
        for access in (True, False):
            b = Bundle(uuid=str(uuid.uuid4()), name="b", description="", user_id=owner.id, access=access,
                       vote_up=0, vote_down=0, created_by="user")
            db.session.add(b)
            db.session.flush()
            db.session.add(BundleTagAssociation(uuid=str(uuid.uuid4()), bundle_id=b.id, tag_id=t.id,
                                                user_id=owner.id))
        db.session.commit()
        _login(client, None)
        page = client.get("/bundle/get_all_tags_usage?view=tags&tag_ns=bf").get_json()
        assert page["tags"][0]["usage_count"] == 1
        _login(client, owner)
        page = client.get("/bundle/get_all_tags_usage?view=tags&tag_ns=bf").get_json()
        assert page["tags"][0]["usage_count"] == 2
