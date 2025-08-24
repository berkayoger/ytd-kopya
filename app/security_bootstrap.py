import os
from typing import List, Optional
from flask import request, jsonify, make_response, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from limits import parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter
from uuid import uuid4


def _split_csv(val: str) -> List[str]:
    return [v.strip() for v in val.split(",") if v.strip()]


def _apply_secure_defaults(app):
    """Uygulama konfigine sert varsayılanları uygula (env ile override edilebilir)."""
    def _bool(env_key: str, default: bool) -> bool:
        return (os.getenv(env_key, str(default)).lower() == "true")
    app.config.setdefault("SESSION_COOKIE_SECURE", _bool("SESSION_COOKIE_SECURE", True))
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", _bool("SESSION_COOKIE_HTTPONLY", True))
    app.config.setdefault("SESSION_COOKIE_SAMESITE", os.getenv("SESSION_COOKIE_SAMESITE", "Lax"))
    # Büyük payload DOS'una karşı üst limit (örn. 2 MiB)
    try:
        app.config.setdefault("MAX_CONTENT_LENGTH", int(os.getenv("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024))))
    except Exception:
        app.config.setdefault("MAX_CONTENT_LENGTH", 2 * 1024 * 1024)


def _origin_allowed(origin: Optional[str], allowlist: List[str]) -> bool:
    return bool(origin and origin in allowlist)


def _setup_rate_limit(app):
    default_limits = [os.getenv("RATE_LIMIT_DEFAULT", "100/minute")]
    storage_uri = os.getenv("REDIS_URL", "memory://")
    limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri, default_limits=default_limits)
    limiter.init_app(app)
    app.extensions["limiter"] = limiter
    return limiter


def _setup_request_id(app):
    @app.before_request
    def _rid_assign():
        rid = request.headers.get("X-Request-ID") or uuid4().hex
        g.request_id = rid
    @app.after_request
    def _rid_header(resp):
        rid = getattr(g, "request_id", None)
        if rid:
            resp.headers["X-Request-ID"] = rid
        return resp


def _setup_cors(app):
    """
    3. partiye gerek kalmadan CORS allowlist ve preflight yönetimi.
    """
    # Ortam değişkeni ile whitelist edilen origin'ler
    origins = _split_csv(os.getenv("SECURITY_CORS_ALLOWED_ORIGINS", ""))
    # Varsayılan olarak credential paylaşımı kapalı
    allow_creds = os.getenv("SECURITY_CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
    # Sadece gerekli metod ve header'lara izin veriyoruz
    allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    allow_headers = ["Authorization", "Content-Type"]
    expose_headers: List[str] = []

    @app.before_request
    def _cors_preflight():
        # Preflight kısa devre
        if request.method == "OPTIONS":
            origin = request.headers.get("Origin")
            if not _origin_allowed(origin, origins):
                # Origin verilmemişse veya allowlist dışındaysa cevapsız bırakıyoruz
                return ("", 204)
            resp = make_response("", 204)
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Methods"] = ", ".join(allow_methods)
            if allow_headers:
                resp.headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)
            if allow_creds:
                resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Max-Age"] = "600"
            return resp

    @app.after_request
    def _cors_headers(resp):
        origin = request.headers.get("Origin")
        if _origin_allowed(origin, origins):
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            if expose_headers:
                resp.headers["Access-Control-Expose-Headers"] = ", ".join(expose_headers)
            if allow_creds:
                resp.headers["Access-Control-Allow-Credentials"] = "true"
        return resp


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
                # CSP'yi gerektiğinde frame-ancestors ile genişlet
                final_csp = csp
                if "frame-ancestors" not in csp.replace(" ", ""):
                    final_csp = f"{csp}; frame-ancestors 'none'"
                resp.headers["Content-Security-Policy"] = final_csp
            resp.headers["X-Frame-Options"] = "DENY"
            resp.headers["X-Content-Type-Options"] = "nosniff"
            resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            # Site izolasyonu (Paylaşımlı worker/POP saldırılarını azaltır)
            resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            resp.headers["Cross-Origin-Resource-Policy"] = "same-site"
        return resp


def bootstrap_security(app):
    """
    Uygulamayı merkezi olarak sertleştirir:
      - CORS (allowlist)
      - Global rate-limit
      - HSTS/CSP ve temel güvenlik başlıkları
    """
    _apply_secure_defaults(app)
    _setup_cors(app)
    limiter = _setup_rate_limit(app)
    _setup_error_handlers(app)
    _setup_security_headers(app)
    _setup_request_id(app)

    # Login yolları için ek sıkı limit (varsa):
    login_rl = os.getenv("LOGIN_RATE_LIMIT", "").strip()
    if login_rl:
        # Basit path eşlemesi: /login ve /api/auth/login
        storage = storage_from_string(os.getenv("REDIS_URL", "memory://"))
        strategy = MovingWindowRateLimiter(storage)
        limit = parse(login_rl)

        def _before_request():
            path = request.path.lower()
            if path.endswith("/login") or path.endswith("/auth/login"):

                addr = get_remote_address()
                key = f"login:{addr}"
                allowed = strategy.hit(limit, key)
                if not allowed:
                    # Limit aşıldığında uyarı logu yaz ve isteği engelle
                    app.logger.warning("Giriş rate limit aşıldı ip=%s", addr)

                    return jsonify({"detail": "Too Many Requests"}), 429

        app.before_request(_before_request)

    return app
