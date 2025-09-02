from backend.app import create_app


def test_security_headers_present():
    app = create_app()
    client = app.test_client()
    resp = client.get("/health")
    assert (
        resp.headers["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains; preload"
    )
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert resp.headers["Content-Security-Policy"] == "default-src 'self';"
