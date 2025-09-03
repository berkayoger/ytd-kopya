from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import List, Optional

from pydantic import AnyUrl, Field, SecretStr
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
    secret_key: SecretStr
    jwt_secret: SecretStr
    jwt_key_version: int = 1

    # Service connections
    database_url: AnyUrl
    redis_url: AnyUrl

    # CORS & rate limit
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    rate_limit_default: str = "200/minute"
    rate_limit_login: str = "10/minute"
    rate_limit_headers_enabled: bool = True
    rate_limit_strategy: str = "fixed-window-elastic-expiry"
    rate_limit_whitelist: List[str] = Field(default_factory=list)

    # Misuse / ban
    auto_ban_threshold: int = 200
    auto_ban_duration_seconds: int = 86400

    # Model configuration
    model_config = SettingsConfigDict(
        env_prefix="YTD_",
        secrets_dir="/run/secrets",
        extra="ignore",
        validate_default=True,
    )

    @classmethod
    @lru_cache
    def load(cls, env: Optional[str] = None) -> "Settings":
        env = env or os.getenv("YTD_ENV", "development")
        s = cls(_env_file=f"backend/config/.env.{env}", _env_file_encoding="utf-8")
        s.env = env
        payload = (
            f"{s.env}|{s.rate_limit_default}|{s.rate_limit_login}|v{s.config_version}"
        )
        s.config_hash = hashlib.sha256(payload.encode()).hexdigest()[:12]
        return s


def get_settings() -> Settings:
    """Cached accessor for application settings."""
    return Settings.load()
