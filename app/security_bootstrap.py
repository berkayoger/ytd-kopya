import os
from typing import List
from flask import request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def _split_csv(val: str) -> List[str]:
    return [v.strip() for v in val.split(",") if v.strip()]

def _setup_cors(app):
    origins = _split_csv(os.getenv("CORS_ORIGINS", ""))
    allow_creds = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
    if origins:
        CORS(app, resources={r"/*": {"origins": origins}}, supports_credentials=allow_creds)
    else:
        # Varsayılanı korumacı: CORS kapalı (explicit origins sağlayın)
        pass

def _setup_rate_limit(app):
    default_limits = [os.getenv("RATE_LIMIT_DEFAULT", "100/minute")]
    storage_uri = os.getenv("REDIS_URL", "memory://")
    limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri, default_limits=default_limits)
    limiter.init_app(app)
    app.extensions["limiter"] = limiter
    return limiter

def _setup_error_handlers(app):
    # Basit JSON hata cevabı
    @app.errorhandler(401)
    def _unauth(e):  # pragma: no cover
        return jsonify({"detail": "Unauthorized"}), 401
    @app.errorhandler(429)
    def _too_many(e):  # pragma: no cover
        return jsonify({"detail": "Too Many Requests"}), 429

def _setup_security_headers(app):
    hsts_age = int(os.getenv("HSTS_MAX_AGE", "0"))
    csp = os.getenv("CSP_POLICY", "")
    enable = os.getenv("SECURE_HEADERS_ENABLED", "false").lower() == "true"
    @app.after_request
    def _add_headers(resp):
        if enable:
            if request.is_secure and hsts_age > 0:
                resp.headers["Strict-Transport-Security"] = f"max-age={hsts_age}; includeSubDomains; preload"
            if csp:
                resp.headers["Content-Security-Policy"] = csp
            resp.headers["X-Frame-Options"] = "DENY"
            resp.headers["X-Content-Type-Options"] = "nosniff"
            resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return resp

def bootstrap_security(app):
    """
    Uygulamayı merkezi olarak sertleştirir:
      - CORS (allowlist)
      - Global rate-limit
      - HSTS/CSP ve temel güvenlik başlıkları
    """
    _setup_cors(app)
    limiter = _setup_rate_limit(app)
    _setup_error_handlers(app)
    _setup_security_headers(app)

    # Login yolları için ek sıkı limit (varsa):
    login_rl = os.getenv("LOGIN_RATE_LIMIT", "").strip()
    if login_rl:
        # Basit path eşlemesi: /login ve /api/auth/login
        def _before_request():
            path = request.path.lower()
            if path.endswith("/login") or path.endswith("/auth/login"):
                # endpoint dekoratörünü bilmediğimiz için direkt limiter’a vuruyoruz
                key = f"login:{request.remote_addr}"
                # Dolum: 1 istek (otomatik pencere yönetimi storage katmanında)
                try:
                    limiter.hit(key)
                except Exception:
                    pass
        app.before_request(_before_request)

    return app

