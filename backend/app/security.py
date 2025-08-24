import os


def security_headers(app):
    """Temel güvenlik başlıklarını ekle."""
    csp = os.getenv("SECURITY_CSP", "default-src 'self';")

    @app.after_request
    def _add_headers(resp):
        # HSTS
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        # Clickjacking ve MIME sniffing korumaları
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        # Referrer gizliliği
        resp.headers["Referrer-Policy"] = "no-referrer"
        # İçerik güvenlik politikası (override edilebilir)
        resp.headers["Content-Security-Policy"] = csp
        return resp
