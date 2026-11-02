"""Profile picture builder (/account/edit): the icons come from the bundled Font Awesome (it moved to 7.3.1 and
the list was empty — no icon to search, no preview)."""


def test_icons_offered_and_rendered(clients):
    from app.features.account import account_core as A
    icons = A.get_avatar_icons()
    assert len(icons) > 20 and "user-secret" in icons
    bg = A.AVATAR_BACKGROUNDS[0] if isinstance(A.AVATAR_BACKGROUNDS, (list, tuple)) else list(A.AVATAR_BACKGROUNDS)[0]
    r = clients["user"].get("/account/avatar_preview.png", query_string={"kind": "icon", "choice": "user-secret", "bg": bg})
    assert r.status_code == 200 and r.data[:4] == b"\x89PNG"
    page = clients["user"].get("/account/edit").get_data(as_text=True)
    assert 'data-icon-name="user-secret"' in page
