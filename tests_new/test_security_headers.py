"""Every page: no framing by another site (clickjacking), no full address sent to other sites, no sniffing."""


def test_security_headers(clients):
    for path in ("/", "/rule/rules_list", "/account/login"):
        r = clients["anonymous"].get(path)
        assert r.headers["X-Frame-Options"] == "SAMEORIGIN"
        assert "frame-ancestors 'self'" in r.headers["Content-Security-Policy"]
        assert r.headers["Referrer-Policy"] in ("strict-origin-when-cross-origin", "no-referrer")
        assert r.headers["X-Content-Type-Options"] == "nosniff"
