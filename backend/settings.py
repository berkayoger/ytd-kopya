from __future__ import annotations

import hashlib
import os
import secrets
from functools import lru_cache
from typing import List, Optional, Set

from pydantic import AnyUrl, Field, SecretStr, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration using Pydantic Settings."""

    # General
    env: str = Field(
        default="development", description="development|staging|production"
    )
    debug: bool = False
    config_version: int = 2
    config_hash: str = ""

    # Security / JWT
    secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_hex(32))
    )
    jwt_secret: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_hex(32))
    )
    jwt_key_version: int = 1
    jwt_access_token_expires_hours: int = 1
    jwt_refresh_token_expires_days: int = 30

    # Service connections
    database_url: AnyUrl
    redis_url: AnyUrl

    # CORS & rate limit
    cors_allow_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    cors_allow_methods: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    cors_allow_headers: List[str] = Field(
        default_factory=lambda: [
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",
            "X-Request-Id",
        ]
    )
    cors_expose_headers: List[str] = Field(
        default_factory=lambda: [
            "X-RateLimit-Remaining",
            "X-Request-Id",
            "X-Total-Count",
        ]
    )
    cors_supports_credentials: bool = True
    cors_max_age: int = 3600
    rate_limit_default: str = "200/minute"
    rate_limit_login: str = "10/minute"
    rate_limit_csrf_token: str = "100/minute"
    rate_limit_headers_enabled: bool = True
    rate_limit_strategy: str = "fixed-window-elastic-expiry"
    rate_limit_whitelist: List[str] = Field(default_factory=list)

    # Misuse / ban
    auto_ban_threshold: int = 200
    auto_ban_duration_seconds: int = 86400
    suspicious_activity_threshold: int = 50

    # CSRF Protection
    csrf_enabled: bool = True
    csrf_cookie_name: str = "XSRF-TOKEN"
    csrf_header_name: str = "X-CSRF-Token"
    csrf_time_limit_seconds: int = 3600
    csrf_protect_methods: Set[str] = Field(
        default_factory=lambda: {"POST", "PUT", "PATCH", "DELETE"}
    )
    csrf_exempt_endpoints: List[str] = Field(
        default_factory=lambda: ["/api/v1/auth/login", "/api/v1/auth/register"]
    )

    # Session & Cookies
    session_cookie_name: str = "ytd_session"
    session_cookie_samesite: str = "Lax"  # Lax|Strict|None
    session_cookie_secure: bool = False  # Auto-enabled in production
    session_cookie_httponly: bool = True
    session_lifetime_hours: int = 24
    remember_cookie_duration_days: int = 30

    # Security Headers (Talisman)
    content_security_policy: dict = Field(
        default_factory=lambda: {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline'",
            "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data: https:",
            "font-src": "'self'",
            "connect-src": "'self'",
            "frame-ancestors": "'none'",
        }
    )
    force_https: bool = False  # Auto-enabled in production
    strict_transport_security: bool = True
    strict_transport_security_max_age: int = 31536000  # 1 year

    # API Security
    api_require_auth: bool = True
    api_key_header: str = "X-API-Key"
    max_content_length_mb: int = 16
    trusted_proxies: List[str] = Field(default_factory=list)

    # Model configuration
    model_config = SettingsConfigDict(
        env_prefix="YTD_",
        secrets_dir="/run/secrets",
        extra="ignore",
        validate_default=True,
    )

    @validator("cors_allow_origins")
    def validate_cors_origins(cls, v, values):
        """Validate CORS origins - no wildcards in production with credentials."""
        env = values.get("env", "development")
        supports_credentials = values.get("cors_supports_credentials", True)
        if env == "production" and supports_credentials and "*" in v:
            raise ValueError(
                "Cannot use wildcard '*' in CORS origins with credentials enabled in production"
            )
        return v

    @validator("csrf_protect_methods", pre=True)
    def validate_csrf_methods(cls, v):
        """Convert list to set for csrf_protect_methods."""
        if isinstance(v, list):
            return set(v)
        return v

    @classmethod
    @lru_cache
    def load(cls, env: Optional[str] = None) -> "Settings":
        env = env or os.getenv("YTD_ENV", "development")
        s = cls(_env_file=f"backend/config/.env.{env}", _env_file_encoding="utf-8")
        s.env = env

        if s.env == "production":
            s.session_cookie_secure = True
            s.force_https = True
            s.debug = False
            if s.cors_supports_credentials and "*" in s.cors_allow_origins:
                s.cors_allow_origins = ["https://yourdomain.com"]

        payload = f"{s.env}|{s.csrf_enabled}|{s.rate_limit_default}|v{s.config_version}"
        s.config_hash = hashlib.sha256(payload.encode()).hexdigest()[:12]
        return s


def get_settings() -> Settings:
    """Cached accessor for application settings."""
    return Settings.load()
