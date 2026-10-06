"""Every bundle route, called on someone else's PRIVATE bundle, as an
anonymous visitor and as a regular user: nothing may be readable or
writable. Guards against a new route forgetting its access check."""

import re

from bundle_helpers import D, F, R, login, logout, make_bundle, make_rule, other, owner, save_structure

# Routes that are not scoped to one bundle (lists, search, create…)
NOT_BUNDLE_SCOPED = {
    "/bundle/list", "/bundle/create", "/bundle/data_table", "/bundle/get_all_bundles", "/bundle/note_tags",
    "/bundle/get_bundle_page", "/bundle/get_all_rule", "/bundle/get_bundles_page_filter_with_id",
    "/bundle/get_bundle_list_rule_part_of", "/bundle/get_all_tags_usage", "/bundle/get_all_vulnerabilities_usage",
    "/bundle/get_bundle_creators_usage", "/bundle/my-bundles", "/bundle/create_from_rule",
    "/bundle/attacks_usage",          # global technique counts for the list filter — no per-bundle data
}
OK_CODES = {302, 400, 401, 403, 404, 405}


def _bundle_routes(app):
    for r in app.url_map.iter_rules():
        if r.rule.startswith("/bundle/") and r.rule not in NOT_BUNDLE_SCOPED:
            yield r


def _fill(rule, b, rule_id, node_id):
    url = rule.rule
    for arg in rule.arguments:
        val = {"bundle_id": b.id, "bundle_uuid": b.uuid, "rule_id": rule_id, "release_id": 1, "entry_id": 1,
               "note_id": 1, "ref": "v1.0.0", "token": "not-a-real-token", "filename": "x"}.get(arg, 1)
        url = re.sub(r"<(?:[^:>]+:)?%s>" % arg, str(val), url)
    sep = "&" if "?" in url else "?"
    return url + f"{sep}bundle_id={b.id}&id={b.id}&bundleId={b.id}&rule_id={rule_id}"


def _check_all(client, app, b, rule_id, node_id, who):
    failures = []
    for r in _bundle_routes(app):
        url = _fill(r, b, rule_id, node_id)
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            if who == "anon":
                logout(client)
            else:
                login(client, other())
            resp = client.open(url, method=m, json={"structure": [], "fix": {"action": "remove_rule", "rule_id": rule_id},
                                                    "version": "v9.9.9", "title": "hack note", "content": "x",
                                                    "status": "resolved"})
            if resp.status_code not in OK_CODES:
                failures.append(f"{who} {m} {url} → {resp.status_code}")
    return failures


def test_private_bundle_routes_refuse_outsiders(client, app):
    with app.app_context():
        rule = make_rule("secret rule", "yara", "rule secret { condition: true }")
        b = make_bundle(public=False)
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(rule.id), F("README.md", "secret readme")])])
        client.post(f"/bundle/{b.id}/releases", json={"version": "v1.0.0"})
        client.post(f"/bundle/{b.id}/notes", json={"title": "owner note", "content": "x", "severity": "info"})
        failures = _check_all(client, app, b, rule.id, None, "anon") + _check_all(client, app, b, rule.id, None, "user")
        assert not failures, "\n".join(failures)

        # and the bundle is intact
        from app import db
        from app.core.db_class.db import Bundle, BundleNode, BundleRelease
        db.session.expire_all()
        assert db.session.get(Bundle, b.id) is not None
        assert BundleNode.query.filter_by(bundle_id=b.id, rule_id=rule.id).count() == 1
        assert BundleRelease.query.filter_by(bundle_id=b.id).count() == 1


# Writes a regular user may legitimately do on someone else's PUBLIC bundle
ALLOWED_WRITES_ON_PUBLIC = {
    ("POST", "/bundle/evaluate"),                       # vote
    ("POST", "/bundle/<int:bundle_id>/notes"),          # add a note
    ("POST", "/bundle/add_comment"),                    # legacy comments
    ("POST", "/bundle/add_reaction"),
    ("POST", "/bundle/favorite/<int:bundle_id>"),       # star it (the user's own favorites list)
}


def test_public_bundle_writes_refused_for_non_owner(client, app):
    from app import db
    from app.core.db_class.db import Bundle, BundleNode
    with app.app_context():
        rule = make_rule("public rule", "yara", "rule pub { condition: true }")
        b = make_bundle(public=True)
        login(client, owner())
        save_structure(client, b.id, [D("Main", [R(rule.id), F("README.md", "x")])])
        failures = []
        for r in _bundle_routes(app):
            url = _fill(r, b, rule.id, None)
            for m in sorted(r.methods - {"HEAD", "OPTIONS", "GET"}):
                if (m, r.rule) in ALLOWED_WRITES_ON_PUBLIC:
                    continue
                login(client, other())
                resp = client.open(url, method=m, json={"structure": [], "fix": {"action": "remove_rule", "rule_id": rule.id},
                                                        "version": "v9.9.9", "title": "x", "content": "x", "status": "resolved"})
                if resp.status_code not in OK_CODES:
                    failures.append(f"{m} {url} → {resp.status_code}")
        assert not failures, "\n".join(failures)
        db.session.expire_all()
        b2 = db.session.get(Bundle, b.id)
        assert b2 is not None and b2.access is True
        assert BundleNode.query.filter_by(bundle_id=b.id, rule_id=rule.id).count() == 1
