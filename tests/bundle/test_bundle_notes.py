"""Community notes / known issues on bundles and their access rules:
write while public, lose access (even to your own note) when the bundle
goes private — except through the share link."""

from app import db
from app.core.db_class.db import Bundle

from bundle_helpers import admin, as_anonymous, login, make_bundle, other, owner


NOTE = {"title": "Needs HTTP app-layer", "content": "**Warning**: enable `app-layer.protocols.http` first.", "severity": "warning"}


def _note(client, bundle_id, payload=NOTE):
    return client.post(f"/bundle/{bundle_id}/notes", json=payload)


def test_anyone_logged_in_can_add_a_note_on_a_public_bundle(client, app):
    with app.app_context():
        b = make_bundle()
        login(client, other())
        r = _note(client, b.id)
        assert r.status_code == 201
        d = client.get(f"/bundle/{b.id}/notes").get_json()
        assert d["open"] == 1 and d["notes"][0]["can_edit"] and not d["notes"][0]["can_resolve"]

        as_anonymous()
        anon = app.test_client()
        assert anon.get(f"/bundle/{b.id}/notes").status_code == 200          # public: readable
        assert anon.post(f"/bundle/{b.id}/notes", json=NOTE).status_code in (302, 401)


def test_note_validation(client, app):
    with app.app_context():
        b = make_bundle()
        login(client, other())
        assert _note(client, b.id, {**NOTE, "title": "x"}).status_code == 400
        assert _note(client, b.id, {**NOTE, "content": ""}).status_code == 400
        assert _note(client, b.id, {**NOTE, "severity": "apocalypse"}).status_code == 400
        assert _note(client, b.id, {**NOTE, "content": "x" * 20001}).status_code == 400


def test_private_bundle_hides_notes_from_their_author_except_via_share_link(client, app):
    with app.app_context():
        b = make_bundle()
        login(client, other())
        note_id = _note(client, b.id).get_json()["note"]["id"]

        # the owner makes the bundle private
        db.session.get(Bundle, b.id).access = False
        db.session.commit()
        login(client, other())
        assert client.get(f"/bundle/{b.id}/notes").status_code == 403
        assert client.put(f"/bundle/{b.id}/notes/{note_id}", json=NOTE).status_code == 403
        assert client.delete(f"/bundle/{b.id}/notes/{note_id}").status_code == 403
        assert _note(client, b.id).status_code == 403

        # …until they open the share link
        login(client, owner())
        token = client.post(f"/bundle/{b.id}/share").get_json()["url"].split("share=")[1]
        login(client, other())
        assert client.get(f"/bundle/detail/{b.id}?share={token}").status_code == 200
        d = client.get(f"/bundle/{b.id}/notes").get_json()
        assert d["notes"][0]["id"] == note_id and d["notes"][0]["can_edit"]
        assert d["can_create"] is False                                     # still: no new notes while private
        assert client.put(f"/bundle/{b.id}/notes/{note_id}", json={**NOTE, "title": "Updated title"}).status_code == 200
        assert _note(client, b.id).status_code == 403


def test_only_author_edits_only_managers_resolve(client, app):
    with app.app_context():
        b = make_bundle()
        login(client, other())
        note_id = _note(client, b.id).get_json()["note"]["id"]

        login(client, admin())     # admin: can resolve and edit anything
        assert client.post(f"/bundle/{b.id}/notes/{note_id}/status", json={"status": "resolved"}).get_json()["note"]["status"] == "resolved"

        login(client, other())     # author: edit yes, resolve no
        assert client.post(f"/bundle/{b.id}/notes/{note_id}/status", json={"status": "open"}).status_code == 403
        assert client.put(f"/bundle/{b.id}/notes/{note_id}", json=NOTE).status_code == 200

        login(client, owner())     # bundle owner: moderates
        assert client.post(f"/bundle/{b.id}/notes/{note_id}/status", json={"status": "open"}).status_code == 200
        assert client.delete(f"/bundle/{b.id}/notes/{note_id}").status_code == 200
        assert client.get(f"/bundle/{b.id}/notes").get_json()["notes"] == []


def test_notes_cannot_be_touched_through_another_bundle(client, app):
    with app.app_context():
        b1, b2 = make_bundle("one"), make_bundle("two")
        login(client, other())
        note_id = _note(client, b1.id).get_json()["note"]["id"]
        login(client, owner())                          # owner of b2 (and b1) — but wrong bundle id
        assert client.delete(f"/bundle/{b2.id}/notes/{note_id}").status_code == 404
        client.post(f"/bundle/delete?id={b1.id}")
        from app.core.db_class.db import BundleNote
        db.session.expire_all()
        assert BundleNote.query.filter_by(bundle_id=b1.id).count() == 0     # deleted with the bundle
