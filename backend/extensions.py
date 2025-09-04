"""Centralized initialization for Flask extensions."""

from __future__ import annotations

import ipaddress
import logging
from datetime import timedelta

import redis
from flask import Flask, g, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import TooManyRequests

from .settings import get_settings

logger = logging.getLogger(__name__)


class _NoOpLimiter:
    """Fallback limiter used before real limiter is initialized."""

    def limit(self, *args, **kwargs):  # noqa: D401
        def decorator(func):
            return func

        return decorator


redis_client: redis.Redis | None = None
limiter: Limiter | _NoOpLimiter | None = _NoOpLimiter()
csrf: CSRFProtect | None = None
talisman: Talisman | None = None


def _is_whitelisted(ip: str) -> bool:
    """Return True if IP address is in whitelist."""
    s = get_settings()
    for item in s.rate_limit_whitelist:
        item = item.strip()
        if not item:
            continue
        try:
            if "/" in item:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(item, strict=False):
                    return True
            elif ip == item:
                return True
        except ValueError:
            logger.warning("Invalid IP/network in whitelist: %s", item)
            continue
    return False


def _is_banned(ip: str) -> bool:
    """Return True if IP address is currently banned."""
    global redis_client
    if not redis_client:
        return False
    return bool(redis_client.get(f"banned_ip:{ip}"))


def _log_suspicious_activity(ip: str, reason: str) -> None:
    """Log suspicious activity for monitoring."""
    global redis_client
    if not redis_client:
        return
    key = f"suspicious:{ip}"
    count = redis_client.incr(key)
    redis_client.expire(key, 3600)
    logger.warning("Suspicious activity from %s: %s (count: %s)", ip, reason, count)
    s = get_settings()
    if count >= s.suspicious_activity_threshold:
        ban_key = f"banned_ip:{ip}"
        redis_client.setex(ban_key, s.auto_ban_duration_seconds, reason)
        logger.error("Auto-banned IP %s for %s", ip, reason)


def client_identity() -> str:
    """Determine client identity for rate limiting."""
    ip = get_remote_address()
    if ip and _is_banned(ip):
        _log_suspicious_activity(ip, "accessing while banned")
    if hasattr(g, "api_key") and getattr(g.api_key, "id", None):
        return f"api:{g.api_key.id}"
    if hasattr(g, "user_id") and g.user_id:
        return f"user:{g.user_id}"
    return ip or "anonymous"


def _setup_limiter_callbacks(app: Flask) -> None:
    global limiter
    if not isinstance(limiter, Limiter):
        return

    @limiter.request_filter
    def _whitelist_filter() -> bool:  # noqa: WPS430
        ip = get_remote_address()
        return bool(ip and _is_whitelisted(ip))

    @limiter.request_filter
    def _health_and_static_filter() -> bool:  # noqa: WPS430
        p = request.path or ""
        return (
            p in ("/healthz", "/readyz", "/metrics")
            or p.startswith("/static/")
            or p.startswith("/docs")
            or p.startswith("/swagger")
        )

    @app.errorhandler(429)
    def handle_rate_limit_exceeded(e: TooManyRequests):  # noqa: WPS430
        ip = get_remote_address()
        _log_suspicious_activity(
            ip or "unknown", f"rate limit exceeded: {e.description}"
        )
        return {"error": "rate_limit_exceeded", "message": "Too many requests"}, 429


def _setup_csrf_protection(app: Flask) -> None:
    global csrf
    s = get_settings()
    if not s.csrf_enabled:
        logger.warning("CSRF protection is disabled!")
        return
    csrf = CSRFProtect()
    app.config.update(
        {
            "WTF_CSRF_TIME_LIMIT": s.csrf_time_limit_seconds,
            "WTF_CSRF_METHODS": list(s.csrf_protect_methods),
            "WTF_CSRF_CHECK_DEFAULT": True,
            "WTF_CSRF_HEADERS": [s.csrf_header_name, "X-CSRFToken", "X-CSRF-Token"],
            "WTF_CSRF_SSL_STRICT": s.env == "production",
        }
    )
    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e: CSRFError):
        ip = get_remote_address()
        _log_suspicious_activity(
            ip or "unknown", f"CSRF validation failed: {e.description}"
        )
        return {"error": "csrf_failed", "message": e.description}, 400


def _setup_security_headers(app: Flask) -> None:
    global talisman
    s = get_settings()
    talisman = Talisman(
        app,
        force_https=s.force_https,
        strict_transport_security=s.strict_transport_security,
        strict_transport_security_max_age=s.strict_transport_security_max_age,
        content_security_policy=s.content_security_policy,
        feature_policy={
            "geolocation": "'none'",
            "microphone": "'none'",
            "camera": "'none'",
        },
    )


def init_extensions(app: Flask) -> None:
    """Initialize Redis, rate limiter, CSRF, and security headers."""
    global redis_client, limiter
    s = get_settings()

    CORS(
        app,
        origins=s.cors_allow_origins,
        methods=s.cors_allow_methods,
        allow_headers=s.cors_allow_headers,
        expose_headers=s.cors_expose_headers,
        supports_credentials=s.cors_supports_credentials,
        max_age=s.cors_max_age,
    )
    JWTManager(app)

    redis_client = redis.from_url(
        str(s.redis_url), socket_timeout=5, retry_on_timeout=True
    )
    try:
        redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as exc:  # pragma: no cover
        logger.error("Redis connection failed: %s", exc)
        raise

    limiter = Limiter(
        key_func=client_identity,
        storage_uri=str(s.redis_url),
        strategy=s.rate_limit_strategy,
        default_limits=[s.rate_limit_default],
        headers_enabled=s.rate_limit_headers_enabled,
        swallow_errors=True,
    )
    limiter.init_app(app)
    _setup_limiter_callbacks(app)
    _setup_csrf_protection(app)
    if s.env != "development":
        _setup_security_headers(app)
    app.config.update(
        {
            "SESSION_COOKIE_NAME": s.session_cookie_name,
            "SESSION_COOKIE_SAMESITE": s.session_cookie_samesite,
            "SESSION_COOKIE_SECURE": s.session_cookie_secure,
            "SESSION_COOKIE_HTTPONLY": s.session_cookie_httponly,
            "PERMANENT_SESSION_LIFETIME": timedelta(hours=s.session_lifetime_hours),
            "MAX_CONTENT_LENGTH": s.max_content_length_mb * 1024 * 1024,
        }
    )
    logger.info("Extensions initialized for environment: %s", s.env)
