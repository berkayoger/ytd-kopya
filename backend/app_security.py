from flask import Flask
from flask_cors import CORS


# CORS ve güvenlik başlıkları tek noktadan yönetilir.
# Üretimde CSP'yi domainlerinize göre sıkılaştırın.
def harden_app(app: Flask) -> None:
    origins = (app.config.get("CORS_ORIGINS") or "https://app.example.com").split(",")
    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        supports_credentials=True,
    )

    @app.after_request
    def _set_security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "frame-ancestors 'none';"
        )
        return resp
