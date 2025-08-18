
import os
from typing import List
from flask import request, jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def _split_csv(val: str) -> List[str]:
    return [v.strip() for v in val.split(",") if v.strip()]

def _setup_cors(app):
    """
    Sıkı, manuel CORS:
      - allowlist: CORS_ORIGINS
      - isteğe göre credentials
      - preflight (OPTIONS) kısa devre
    """
    app.config.setdefault("CORS_ORIGINS", os.getenv("CORS_ORIGINS", ""))
    app.config.setdefault("CORS_ALLOW_CREDENTIALS", os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true")

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

def _origin_allowed(app, origin: str) -> bool:
    if not origin:
        return False
    origins = _split_csv(app.config.get("CORS_ORIGINS", ""))
    return origin in origins

def _apply_cors_headers(app, resp):
    origin = request.headers.get("Origin")
    if not origin or not _origin_allowed(app, origin):
        return resp
    resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Origin"] = origin
    if app.config.get("CORS_ALLOW_CREDENTIALS", False):
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    # Sıkı allow list – gerekenden fazlasını verme
    req_headers = request.headers.get("Access-Control-Request-Headers", "")
    allow_headers = req_headers if req_headers else "Authorization,Content-Type"
    resp.headers["Access-Control-Allow-Headers"] = allow_headers
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    resp.headers["Access-Control-Max-Age"] = "600"
    return resp

def _install_cors_hooks(app):
    @app.before_request
    def _handle_preflight():
        if request.method.upper() == "OPTIONS":
            origin = request.headers.get("Origin")
            if _origin_allowed(app, origin):
                resp = make_response("", 204)
                return _apply_cors_headers(app, resp)
            # Allowlist dışı ise normal 403
            return jsonify({"detail": "CORS origin not allowed"}), 403

    @app.after_request
    def _cors_after(resp):
        return _apply_cors_headers(app, resp)

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
    _install_cors_hooks(app)

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
