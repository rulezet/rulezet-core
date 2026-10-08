"""A comment thread is exactly as visible as the object it hangs on: nobody
reads, writes or reacts to comments on a private bundle, a draft blog post
or a trashed rule they couldn't open themselves."""

import datetime
import uuid

from flask import g

from app import db
from app.core.db_class.db import BlogPost, Rule, UnifiedComment, User
from app.features.bundle import bundle_core as BM


def _user(email):
    return User.query.filter_by(email=email).first()


def _login(client, user):
    with client.session_transaction() as s:
        if user is None:
            s.pop("_user_id", None)
        else:
            s["_user_id"] = str(user.id)
            s["_fresh"] = True
    g.pop("_login_user", None)


def _comment(client, user, object_type, object_id, content="hello"):
    _login(client, user)
    return client.post("/api/comments/", json={"object_type": object_type, "object_id": object_id,
                                               "content": content})


def _list(client, user, object_type, object_id):
    _login(client, user)
    return client.get(f"/api/comments/?object_type={object_type}&object_id={object_id}")


def test_private_bundle_thread(client, app):
    with app.app_context():
        owner, other, admin = _user("t@t.t"), _user("neo@admin.admin"), _user("admin@admin.admin")
        b = BM.create_bundle({"name": "Secret", "description": "x", "public": False}, owner)
        assert _comment(client, owner, "bundle", b.id, "owner-only note").status_code == 201
        c = UnifiedComment.query.filter_by(object_type="bundle", object_id=b.id).first()

        # nobody else reads, writes, reacts or resolves
        assert _list(client, None, "bundle", b.id).status_code == 404
        assert _list(client, other, "bundle", b.id).status_code == 404
        assert _comment(client, other, "bundle", b.id, "intruder").status_code == 404
        _login(client, other)
        assert client.post(f"/api/comments/{c.uuid}/react", json={"reaction": "like"}).status_code == 404
        _login(client, owner)
        assert client.post(f"/api/comments/{c.uuid}/react", json={"reaction": "like"}).status_code == 200
        _login(client, other)
        assert client.get(f"/api/comments/{c.uuid}/reactors").status_code == 404
        _login(client, None)
        assert client.get(f"/api/comments/resolve/{c.id}").status_code == 404
        _login(client, other)
        assert client.post(f"/bundle/add_comment?bundle_id={b.id}&content=intruder2").status_code == 404
        assert UnifiedComment.query.filter_by(object_type="bundle", object_id=b.id).count() == 1

        # owner and admin do
        items = _list(client, owner, "bundle", b.id).get_json()["items"]
        assert [i["content"] for i in items] == ["owner-only note"]
        assert _list(client, admin, "bundle", b.id).status_code == 200

        # made public: open to everyone again
        b.access = True
        db.session.commit()
        assert _list(client, None, "bundle", b.id).status_code == 200
        assert _comment(client, other, "bundle", b.id, "now welcome").status_code == 201


def test_draft_blog_post_and_trashed_rule_threads(client, app):
    with app.app_context():
        author, other = _user("t@t.t"), _user("neo@admin.admin")
        now = datetime.datetime.utcnow()
        post = BlogPost(uuid=str(uuid.uuid4()), slug=f"draft-{uuid.uuid4().hex[:6]}", title="Draft", content="x",
                        is_public=False, is_draft=True, user_id=author.id, created_at=now, updated_at=now)
        db.session.add(post)
        db.session.commit()
        assert _comment(client, author, "blog_post", post.id).status_code == 201
        assert _list(client, None, "blog_post", post.id).status_code == 404
        assert _comment(client, other, "blog_post", post.id).status_code == 404

        rule = Rule.query.filter(Rule.is_deleted == False).first()
        assert _comment(client, other, "rule", rule.id).status_code == 201
        assert _list(client, None, "rule", rule.id).status_code == 200
        rule.is_deleted = True
        db.session.commit()
        assert _list(client, None, "rule", rule.id).status_code == 404
        assert _comment(client, other, "rule", rule.id).status_code == 404


def test_hub_hides_unpublished_blog_post_threads(client, app):
    with app.app_context():
        author, other = _user("t@t.t"), _user("neo@admin.admin")
        now = datetime.datetime.utcnow()
        post = BlogPost(uuid=str(uuid.uuid4()), slug=f"draft-{uuid.uuid4().hex[:6]}", title="Unreleased research",
                        content="x", is_public=False, is_draft=True, user_id=author.id, created_at=now, updated_at=now)
        db.session.add(post)
        db.session.commit()
        assert _comment(client, author, "blog_post", post.id, "draft discussion").status_code == 201

        def hub_types(user):
            _login(client, user)
            items = client.get("/api/comments/hub?scope=all").get_json()["items"]
            return [(i["object_type"], i.get("object_id")) for i in items]

        assert ("blog_post", post.id) not in hub_types(other)
        assert any(t == "blog_post" for t, _ in hub_types(author))
