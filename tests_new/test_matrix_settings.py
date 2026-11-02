"""Matrix room of the update messages (Admin → Settings → Configuration, core/utils/matrix.py)."""


def test_matrix_settings_admin_only_and_test(clients, monkeypatch):
    from app.core.utils import matrix
    sent = []
    monkeypatch.setattr(matrix, "settings", lambda: {"MATRIX_HOMESERVER": "https://matrix.example", "MATRIX_ACCESS_TOKEN": "t",
                                                     "MATRIX_ROOM_ID": "!r:matrix.example"})
    monkeypatch.setattr(matrix.urllib.request, "urlopen", lambda req, timeout=10: sent.append(req) or type("R", (), {"read": lambda self: b"{}"})())
    assert clients["user"].post("/admin/settings/test_matrix", json={}).status_code == 403
    r = clients["admin"].post("/admin/settings/test_matrix", json={}).get_json()
    assert r["success"] and sent[0].get_method() == "PUT" and "%21r%3Amatrix.example" in sent[0].full_url
    assert sent[0].headers["Authorization"] == "Bearer t"


def test_not_configured_says_so(monkeypatch):
    from app.core.utils import matrix
    monkeypatch.setattr(matrix, "settings", lambda: {"MATRIX_HOMESERVER": "", "MATRIX_ACCESS_TOKEN": "", "MATRIX_ROOM_ID": ""})
    ok, err = matrix.send("x")
    assert not ok and "homeserver" in err


def test_config_never_returns_the_token(clients, monkeypatch):
    from app.features.admin import admin_core
    monkeypatch.setattr(admin_core, "read_env_file", lambda: {"MATRIX_HOMESERVER": "https://m.example",
                                                              "MATRIX_ACCESS_TOKEN": "syt_secret", "MATRIX_ROOM_ID": "!r:m.example"})
    cfg = clients["admin"].get("/admin/settings/config").get_json()
    assert cfg["matrix"] == {"homeserver": "https://m.example", "room_id": "!r:m.example", "token_set": True}
    assert "syt_secret" not in str(cfg)
