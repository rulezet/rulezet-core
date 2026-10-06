"""Unexpected errors: the client gets a neutral message, the exception text
(SQL, paths, internals) only goes to the server log."""

from app.features.rule import rule_core as RuleModel
from app.features.bundle import bundle_core as BundleModel


def _boom(*_a, **_k):
    raise RuntimeError("SELECT secret FROM /srv/rulezet/internal.db")


def test_raw_exception_never_reaches_the_client(client, app, monkeypatch, caplog):
    monkeypatch.setattr(RuleModel, "get_tags_for_rule", _boom)
    monkeypatch.setattr(BundleModel, "get_all_used_tags_with_counts", _boom)
    with app.app_context():
        for url in ("/rule/get_tags/1", "/bundle/get_all_tags_usage"):
            resp = client.get(url)
            assert resp.status_code == 500
            assert "secret" not in resp.get_data(as_text=True)
            assert "/srv/rulezet" not in resp.get_data(as_text=True)
    assert any("secret" in str(r.exc_info[1]) for r in caplog.records if r.exc_info)
