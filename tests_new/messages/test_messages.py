"""Messages (features/messages/): channels and direct conversations — who sees, writes and manages what,
references, reactions, unread counts, notifications."""
from app import db
from app.core.db_class.message import Channel, ChannelMessage
from app.core.db_class.notification import Notification
from tests_new.helpers.bundles import make_bundle
from tests_new.helpers.rules import make_rule
from tests_new.helpers.users import make_user

API = "/messages/api"


def _channel(client, **data):
    r = client.post(f"{API}/channels", json={"name": "yara-review", **data})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["channel"]


def _post(client, uuid, content, **extra):
    return client.post(f"{API}/channels/{uuid}/messages", json={"content": content, **extra})


def test_pages_need_login(clients):
    assert clients["anonymous"].get("/messages/").status_code in (302, 401)
    assert clients["anonymous"].get(f"{API}/conversations").status_code in (302, 401)
    html = clients["user"].get("/messages/").get_data(as_text=True)
    assert 'id="messages-app"' in html and "/notifications/" in html          # shared menu


def test_public_channel_read_join_write(clients, users):
    c = _channel(clients["owner"], topic="Reviews")
    cl = clients["user"]
    assert cl.get(f"{API}/channels/{c['uuid']}").status_code == 200          # anyone signed in reads it
    assert any(x["uuid"] == c["uuid"] for x in cl.get(f"{API}/browse").get_json()["channels"])
    assert _post(cl, c["uuid"], "hello").status_code == 201                   # writing joins it
    me = cl.get(f"{API}/channels/{c['uuid']}").get_json()["channel"]
    assert me["is_member"] and me["my_role"] == "member" and not me["can_manage"]
    assert cl.post(f"{API}/channels/{c['uuid']}", json={"name": "mine"}).status_code == 403


def test_private_channel_only_members(clients, users):
    c = _channel(clients["owner"], is_private=True, member_ids=[users.admin.id])
    assert clients["user"].get(f"{API}/channels/{c['uuid']}").status_code == 404
    assert _post(clients["user"], c["uuid"], "x").status_code == 404
    assert clients["user"].post(f"{API}/channels/{c['uuid']}/join").status_code == 404
    assert not any(x["uuid"] == c["uuid"] for x in clients["user"].get(f"{API}/browse").get_json()["channels"])
    assert clients["owner"].post(f"{API}/channels/{c['uuid']}/members", json={"user_ids": [users.user.id]}).status_code == 200
    assert clients["user"].get(f"{API}/channels/{c['uuid']}").status_code == 200
    assert Notification.query.filter_by(user_id=users.user.id, notif_type="message_invite").count() == 1


def test_roles_and_admin(clients, users):
    c = _channel(clients["owner"], member_ids=[users.user.id])
    u = c["uuid"]
    # a member can't change roles; the owner can; a moderator manages but doesn't delete the channel
    assert clients["user"].post(f"{API}/channels/{u}/members/{users.user.id}/role", json={"role": "moderator"}).status_code == 403
    assert clients["owner"].post(f"{API}/channels/{u}/members/{users.user.id}/role", json={"role": "moderator"}).status_code == 200
    assert clients["user"].post(f"{API}/channels/{u}", json={"topic": "New topic"}).status_code == 200
    assert clients["user"].delete(f"{API}/channels/{u}").status_code == 403
    assert clients["user"].delete(f"{API}/channels/{u}/members/{users.owner.id}").status_code == 400   # never the owner
    # admins manage any channel
    assert clients["admin"].post(f"{API}/channels/{u}", json={"name": "renamed"}).status_code == 200
    assert clients["admin"].delete(f"{API}/channels/{u}").status_code == 200
    assert Channel.query.filter_by(uuid=u).first() is None


def test_owner_leaving_hands_over(clients, users):
    c = _channel(clients["owner"], member_ids=[users.user.id])
    assert clients["owner"].post(f"{API}/channels/{c['uuid']}/leave").status_code == 200
    ch = clients["user"].get(f"{API}/channels/{c['uuid']}").get_json()["channel"]
    assert ch["my_role"] == "owner"


def test_direct_conversation_is_private_even_for_admins(clients, users):
    r = clients["user"].post(f"{API}/direct/{users.owner.id}")
    d = r.get_json()["channel"]
    assert clients["owner"].post(f"{API}/direct/{users.user.id}").get_json()["channel"]["uuid"] == d["uuid"]   # one per pair
    assert _post(clients["user"], d["uuid"], "psst").status_code == 201
    assert clients["admin"].get(f"{API}/channels/{d['uuid']}").status_code == 404
    assert clients["admin"].get(f"{API}/channels/{d['uuid']}/messages").status_code == 404
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="message_direct").count() == 1
    _post(clients["user"], d["uuid"], "again")                                 # still one unread notification
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="message_direct").count() == 1
    assert clients["user"].post(f"{API}/direct/{users.user.id}").status_code == 404   # not with yourself


def test_messages_edit_delete_react_pin_unread(clients, users):
    c = _channel(clients["owner"], member_ids=[users.user.id])
    u = c["uuid"]
    m = _post(clients["user"], u, f"see @[Owner]({users.owner.id})").get_json()["message"]
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="message_mention").count() == 1
    convs = clients["owner"].get(f"{API}/conversations").get_json()
    assert convs["unread"] == 1
    clients["owner"].post(f"{API}/channels/{u}/read", json={})
    assert clients["owner"].get(f"{API}/conversations").get_json()["unread"] == 0
    # only the author edits; author or moderator deletes
    assert clients["owner"].post(f"{API}/channels/{u}/messages/{m['id']}", json={"content": "hacked"}).status_code == 403
    assert clients["user"].post(f"{API}/channels/{u}/messages/{m['id']}", json={"content": "edited"}).get_json()["message"]["edited_at"]
    r = clients["owner"].post(f"{API}/channels/{u}/messages/{m['id']}/react", json={"emoji": "👍"}).get_json()["message"]
    assert r["reactions"][0]["count"] == 1 and r["reactions"][0]["mine"]
    assert clients["owner"].post(f"{API}/channels/{u}/messages/{m['id']}/react", json={"emoji": "<script>"}).status_code == 400
    assert clients["user"].post(f"{API}/channels/{u}/messages/{m['id']}/pin").status_code == 403
    assert clients["owner"].post(f"{API}/channels/{u}/messages/{m['id']}/pin").get_json()["message"]["is_pinned"]
    reply = _post(clients["owner"], u, "answer", reply_to_id=m["id"]).get_json()["message"]
    assert reply["reply_to"]["id"] == m["id"]
    assert clients["owner"].delete(f"{API}/channels/{u}/messages/{m['id']}").get_json()["message"]["is_deleted"]
    older = clients["owner"].get(f"{API}/channels/{u}/messages?before={reply['id']}").get_json()["messages"]
    assert all(x["id"] < reply["id"] for x in older)
    assert clients["owner"].get(f"{API}/search?q=answer").get_json()["results"][0]["id"] == reply["id"]
    assert _post(clients["owner"], u, "   ").status_code == 400


def test_references_and_channel_about(clients, users):
    rule = make_rule(users.owner)
    private = make_bundle(users.owner, public=False)
    items = clients["user"].get(f"/messages/api/refs?q={rule.title[:6]}&kinds=rule").get_json()["items"]
    assert any(i["key"] == str(rule.id) for i in items)
    assert not any(i["key"] == str(private.id) for i in
                   clients["user"].get(f"/messages/api/refs?q={private.name[:5]}&kinds=bundle").get_json()["items"])
    assert clients["user"].get(f"/messages/ref/bundle/{private.id}").status_code == 404   # a chip never leads to what you can't see
    assert clients["user"].get(f"/messages/ref/rule/{rule.id}").status_code == 302
    assert clients["user"].get("/messages/ref/cve/cve-2021-44228").headers["Location"].endswith("/vulnerability/CVE-2021-44228")
    c = _channel(clients["user"], ref_type="rule", ref_key=str(rule.id))
    assert c["ref"]["label"] == rule.title
    about = clients["owner"].get(f"/messages/api/about/rule/{rule.id}").get_json()["channels"]
    assert [x["uuid"] for x in about] == [c["uuid"]]
    assert clients["user"].post(f"{API}/channels", json={"name": "x", "ref_type": "bundle", "ref_key": str(private.id)}).status_code == 400
    assert "New channel about it" in clients["user"].get(f"/rule/detail_rule/{rule.id}").get_data(as_text=True)
    assert clients["user"].get(f"/messages/new?ref=rule:{rule.id}").status_code == 200


def test_cascade_on_delete(app, users):
    from app.features.messages import messages_core as M
    c, _ = M.create_channel(users.owner, "tmp")
    M.post_message(c, users.owner, "a")
    cid = c.id
    M.delete_channel(c)
    assert ChannelMessage.query.filter_by(channel_id=cid).count() == 0


def _png(size=(40, 30)):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, (13, 110, 253)).save(buf, "PNG")
    buf.seek(0)
    return buf


def test_channel_picture(clients, users):
    import os
    from app.features.messages.messages_core import AVATAR_DIR
    c = _channel(clients["owner"], member_ids=[users.user.id])
    url = f"{API}/channels/{c['uuid']}/avatar"
    assert clients["user"].post(url, data={"avatar": (_png(), "a.png")}, content_type="multipart/form-data").status_code == 403
    bad = clients["owner"].post(url, data={"avatar": (__import__("io").BytesIO(b"<svg onload=x>"), "a.png")},
                                content_type="multipart/form-data")
    assert bad.status_code == 400
    r = clients["owner"].post(url, data={"avatar": (_png(), "a.png")}, content_type="multipart/form-data").get_json()
    avatar = r["channel"]["avatar"]
    path = os.path.join(AVATAR_DIR, avatar.rsplit("/", 1)[1])
    from PIL import Image
    assert Image.open(path).size == (256, 256)                               # re-encoded square PNG
    assert clients["user"].get(f"{API}/conversations").get_json()["conversations"][0]["avatar"] == avatar
    assert clients["owner"].delete(url).get_json()["channel"]["avatar"] is None
    assert not os.path.exists(path)


def test_notifications_mute_and_readers_only(clients, users):
    outsider = make_user("outsider")
    c = _channel(clients["owner"], is_private=True, member_ids=[users.user.id])
    u = c["uuid"]
    # mentioning someone who can't read the private channel tells them nothing
    _post(clients["owner"], u, f"@[Out]({outsider.id}) @[User]({users.user.id})")
    assert Notification.query.filter_by(user_id=outsider.id).count() == 0
    assert Notification.query.filter_by(user_id=users.user.id, notif_type="message_mention").count() == 1
    # a muted direct conversation sends no notification and no unread count in the nav
    d = clients["user"].post(f"{API}/direct/{users.owner.id}").get_json()["channel"]
    clients["owner"].post(f"{API}/channels/{d['uuid']}/me", json={"muted": True})
    _post(clients["user"], d["uuid"], "hi")
    assert Notification.query.filter_by(user_id=users.owner.id, notif_type="message_direct").count() == 0
    from app.features.messages.messages_core import unread_total
    assert unread_total(users.owner) == 0
    # the notification preference "Messages" off (muted kinds) — nothing is created
    from app.features.notification.notification_core import update_preference
    update_preference(users.user.id, {"muted_types": ["message_mention"]})
    _post(clients["owner"], u, f"again @[User]({users.user.id})")
    assert Notification.query.filter_by(user_id=users.user.id, notif_type="message_mention").count() == 1
    # the links in notifications open the conversation
    n = Notification.query.filter_by(user_id=users.user.id, notif_type="message_mention").first()
    assert n.link.startswith(f"/messages/c/{u}") and clients["user"].get(n.link).status_code == 200


def test_attach_menu_lists_latest_of_one_kind(clients, users):
    rule = make_rule(users.owner)
    items = clients["user"].get("/messages/api/refs?q=&kinds=rule").get_json()["items"]
    assert items and items[0]["key"] == str(rule.id)
    assert clients["user"].get("/messages/api/refs?q=").get_json()["items"] == []     # no kind: nothing without a search


def test_reference_search_words_id_uuid(clients, users):
    rule = make_rule(users.owner, title="my_detection-rule")
    find = lambda q: [i["key"] for i in clients["user"].get(f"/messages/api/refs?kinds=rule&q={q}").get_json()["items"]]
    for q in ("my detection rule", "rule my", "mydetectionrule", "MY DETECTION", str(rule.id), rule.uuid[:8], rule.uuid):
        assert str(rule.id) in find(q), q
    assert str(rule.id) not in find("my other")
    bundle = make_bundle(users.owner, name="Ransomware pack")
    b = [i["key"] for i in clients["user"].get(f"/messages/api/refs?kinds=bundle&q=ransomwarepack").get_json()["items"]]
    assert str(bundle.id) in b


def test_delete_conversation_for_me(clients, users):
    d = clients["user"].post(f"{API}/direct/{users.owner.id}").get_json()["channel"]
    _post(clients["user"], d["uuid"], "old secret")
    assert clients["owner"].post(f"{API}/channels/{d['uuid']}/clear").status_code == 200
    assert not clients["owner"].get(f"{API}/conversations").get_json()["conversations"]          # gone from my list
    assert clients["owner"].get(f"{API}/channels/{d['uuid']}/messages").get_json()["messages"] == []
    assert clients["owner"].get(f"{API}/search?q=secret").get_json()["results"] == []
    assert len(clients["user"].get(f"{API}/channels/{d['uuid']}/messages").get_json()["messages"]) == 1   # the other keeps it
    _post(clients["user"], d["uuid"], "new one")                                                   # comes back on a new message
    convs = clients["owner"].get(f"{API}/conversations").get_json()
    assert [c["uuid"] for c in convs["conversations"]] == [d["uuid"]] and convs["unread"] == 1
    assert [m["content"] for m in clients["owner"].get(f"{API}/channels/{d['uuid']}/messages").get_json()["messages"]] == ["new one"]


def test_people_directory_with_organisations(clients, users):
    from app.core.db_class.user import Organisation
    org = Organisation(name="CIRCL")
    db.session.add(org)
    users.user.organisations.append(org)
    users.admin.organisations.append(org)
    db.session.commit()
    data = clients["user"].get(f"{API}/people").get_json()
    names = {u["id"]: u for u in data["users"]}
    assert users.user.id not in names and users.owner.id in names                 # not yourself
    assert data["my_orgs"] == [org.id] and data["orgs"][0]["mine"]
    mine = clients["user"].get(f"{API}/people?org=mine").get_json()["users"]
    assert [u["id"] for u in mine] == [users.admin.id] and mine[0]["orgs"][0]["name"] == "CIRCL"
    assert clients["user"].get(f"{API}/people?org=mine&ids_only=1").get_json()["ids"] == [users.admin.id]
    c = _channel(clients["owner"], member_ids=[users.admin.id])
    flagged = {u["id"]: u["in_channel"] for u in clients["owner"].get(f"{API}/people?channel={c['uuid']}").get_json()["users"]}
    assert flagged[users.admin.id] is True and flagged[users.user.id] is False


def test_invite_link_and_who_adds_people(clients, users):
    c = _channel(clients["owner"], is_private=True, member_ids=[users.admin.id])
    u = c["uuid"]
    assert clients["user"].post(f"{API}/channels/{u}/invite").status_code == 404     # not even visible
    code = clients["owner"].post(f"{API}/channels/{u}/invite").get_json()["channel"]["invite_code"]
    assert code
    r = clients["user"].get(f"/messages/join/{code}")
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/messages/c/{u}")
    me = clients["user"].get(f"{API}/channels/{u}").get_json()["channel"]
    assert me["is_member"] and me["invite_code"] is None                        # members don't see the code
    # a member adds people only when the channel allows it
    outsider = make_user("outsider2")
    assert clients["user"].post(f"{API}/channels/{u}/members", json={"user_ids": [outsider.id]}).status_code == 403
    clients["owner"].post(f"{API}/channels/{u}", json={"members_can_invite": True})
    assert clients["user"].post(f"{API}/channels/{u}/members", json={"user_ids": [outsider.id]}).get_json()["added"] == 1
    # renewing / turning off the link stops the old one
    clients["owner"].delete(f"{API}/channels/{u}/invite")
    late = make_user("late")
    from tests_new.conftest import _logged_in_client
    from flask import current_app
    assert _logged_in_client(current_app, late).get(f"/messages/join/{code}").status_code == 404


def test_going_private_keeps_members(clients, users):
    c = _channel(clients["owner"])
    _post(clients["user"], c["uuid"], "hi")                                       # joined while public
    clients["owner"].post(f"{API}/channels/{c['uuid']}", json={"is_private": True})
    assert clients["user"].get(f"{API}/channels/{c['uuid']}").status_code == 200   # still in
    assert clients["admin"].get(f"{API}/channels/{c['uuid']}").status_code == 200  # admins moderate
    newcomer = make_user("newcomer")
    from tests_new.conftest import _logged_in_client
    from flask import current_app
    assert _logged_in_client(current_app, newcomer).get(f"{API}/channels/{c['uuid']}").status_code == 404


def test_write_to_the_author_from_a_rule(clients, users):
    rule = make_rule(users.owner)
    html = clients["user"].get(f"/rule/detail_rule/{rule.id}").get_data(as_text=True)
    assert "Write to the author" in html
    assert "Write to the author" not in clients["owner"].get(f"/rule/detail_rule/{rule.id}").get_data(as_text=True)
    page = clients["user"].get(f"/messages/new?to={users.owner.id}&ref=rule:{rule.id}").get_data(as_text=True)
    assert '"prefill"' in page and f'"key": "{rule.id}"' in page.replace("'", '"')
    about = clients["user"].get(f"/messages/api/about/rule/{rule.id}").get_json()["channels"]
    assert about == []
    c = _channel(clients["owner"], ref_type="rule", ref_key=str(rule.id))
    listed = clients["user"].get(f"/messages/api/about/rule/{rule.id}").get_json()["channels"]
    assert listed[0]["uuid"] == c["uuid"] and listed[0]["is_member"] is False           # "Join" offered
    assert clients["user"].post(f"{API}/channels/{c['uuid']}/join").status_code == 200


def test_message_images_private_and_in_admin_media(clients, users):
    c = _channel(clients["owner"], is_private=True, member_ids=[users.user.id])
    up = clients["user"].post(f"{API}/channels/{c['uuid']}/images", data={"image": (_png((3000, 1000)), "shot.png")},
                              content_type="multipart/form-data")
    assert up.status_code == 201
    url = up.get_json()["url"]
    assert url.startswith(f"/messages/files/{c['uuid']}/")
    bad = clients["user"].post(f"{API}/channels/{c['uuid']}/images", data={"image": (__import__("io").BytesIO(b"GIF89a<script>"), "x.gif")},
                               content_type="multipart/form-data")
    assert bad.status_code == 400
    _post(clients["user"], c["uuid"], f"look ![shot]({url})")
    r = clients["owner"].get(url)
    assert r.status_code == 200 and r.mimetype == "image/png"
    from PIL import Image
    import io
    assert max(Image.open(io.BytesIO(r.data)).size) == 2400                       # resized
    outsider = make_user("peek")
    from tests_new.conftest import _logged_in_client
    from flask import current_app
    assert _logged_in_client(current_app, outsider).get(url).status_code == 404     # not for who can't read it
    assert clients["owner"].get(f"/messages/files/{c['uuid']}/../../config.py").status_code == 404
    # Admin → Media → Uploads
    from app.features.admin.media import media_core
    cats = {x["key"]: x for x in media_core.list_uploads()}
    rel = url.split("/messages/files/")[1]
    f = next(f for f in cats["messages"]["files"] if f["rel"] == rel)
    assert "Image by" in f["owner"]["label"]
    media_core.delete_upload("messages", rel)
    msg = ChannelMessage.query.filter(ChannelMessage.content.like("look%")).first()
    assert "image removed" in msg.content and clients["owner"].get(url).status_code == 404


def test_messages_by_email(clients, users, monkeypatch):
    import datetime
    from tests_new.helpers.account import captured_mails
    from app.features.messages import messages_core as M
    monkeypatch.setattr("app.core.utils.mail_status.is_email_available", lambda *a, **k: True)
    later = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    d = clients["user"].post(f"{API}/direct/{users.owner.id}").get_json()["channel"]
    _post(clients["user"], d["uuid"], "Can you check my YARA rule?")
    with captured_mails() as sent:                                   # off by default: nothing
        assert M.send_due_emails(later) == 0
    clients["owner"].post("/notifications/preferences", json={"email_messages": "direct"})
    with captured_mails() as sent:
        assert M.send_due_emails(datetime.datetime.utcnow()) == 0     # too early: may still read it in the app
        assert M.send_due_emails(later) == 1
        assert M.send_due_emails(later) == 0                          # never twice for the same message
    mail = sent[0]
    assert mail.recipients == [users.owner.email] and "wrote to you" in mail.subject
    assert "Can you check my YARA rule?" in mail.body and f"/messages/c/{d['uuid']}" in mail.body
    # read in time → no email; channel messages only in "all" mode, or when mentioned
    _post(clients["user"], d["uuid"], "second")
    clients["owner"].post(f"{API}/channels/{d['uuid']}/read", json={})
    c = _channel(clients["user"], member_ids=[users.owner.id])
    _post(clients["user"], c["uuid"], "general chatter")
    with captured_mails() as sent:
        assert M.send_due_emails(later) == 0
    _post(clients["user"], c["uuid"], f"@[Owner]({users.owner.id}) look")
    with captured_mails() as sent:
        assert M.send_due_emails(later) == 1 and "look" in sent[0].body and "general chatter" not in sent[0].body
    clients["owner"].post("/notifications/preferences", json={"email_messages": "all"})
    _post(clients["user"], c["uuid"], "news for all")
    clients["owner"].post(f"{API}/channels/{c['uuid']}/me", json={"muted": True})     # muted: never
    with captured_mails() as sent:
        assert M.send_due_emails(later) == 0
    clients["owner"].post(f"{API}/channels/{c['uuid']}/me", json={"muted": False})
    with captured_mails() as sent:
        assert M.send_due_emails(later) == 1 and "news for all" in sent[0].body
    assert clients["owner"].get("/notifications/preferences").get_json()["email_messages"] == "all"
