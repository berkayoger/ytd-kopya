"""Centralized initialization for Flask extensions."""

from __future__ import annotations

import ipaddress

import redis
from flask import g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .settings import get_settings

redis_client: redis.Redis | None = None
limiter: Limiter | None = None


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
            continue
    return False


def _is_banned(ip: str) -> bool:
    """Return True if IP address is currently banned."""
    global redis_client
    if not redis_client:
        return False
    return bool(redis_client.get(f"banned_ip:{ip}"))


def client_identity() -> str:
    """Determine client identity for rate limiting."""
    ip = get_remote_address()
    if ip and (_is_whitelisted(ip) or _is_banned(ip)):
        pass
    if hasattr(g, "api_key") and getattr(g.api_key, "id", None):
        return f"api:{g.api_key.id}"
    if hasattr(g, "user_id") and g.user_id:
        return f"user:{g.user_id}"
    return ip or "anonymous"


def init_extensions(app) -> None:
    """Initialize Redis and Limiter within application context."""
    global redis_client, limiter
    s = get_settings()
    redis_client = redis.from_url(
        str(s.redis_url), socket_timeout=5, retry_on_timeout=True
    )
    limiter = Limiter(
        key_func=client_identity,
        storage_uri=str(s.redis_url),
        strategy=s.rate_limit_strategy,
        default_limits=[s.rate_limit_default],
        headers_enabled=s.rate_limit_headers_enabled,
        swallow_errors=True,
    )
    limiter.init_app(app)

    @limiter.request_filter
    def _whitelist_filter() -> bool:  # noqa: WPS430
        ip = get_remote_address()
        return bool(ip and _is_whitelisted(ip))

    @limiter.request_filter
    def _health_and_docs() -> bool:  # noqa: WPS430
        p = request.path or ""
        return (
            p in ("/healthz", "/readyz")
            or p.startswith("/static/")
            or p.startswith("/docs")
        )
