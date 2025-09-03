"""
Pydantic-based configuration management for YTD-Kopya.

This module provides type-safe, validated configuration management
with support for multiple environments and secret management.
"""

from __future__ import annotations

import secrets
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic.v1 import (BaseModel, BaseSettings, Field, HttpUrl, PostgresDsn,
                         RedisDsn, SecretStr, validator)


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseModel):
    """Database configuration with validation."""

    url: PostgresDsn
    pool_size: int = Field(default=5, ge=1, le=50)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    pool_recycle: int = Field(default=3600, ge=300, le=86400)
    echo: bool = Field(default=False)

    @validator("url")
    def validate_database_url(cls, v: PostgresDsn) -> PostgresDsn:  # type: ignore[override]
        """Validate database URL format and requirements."""
        parsed = urlparse(str(v))
        if not parsed.hostname:
            raise ValueError("Database URL must include hostname")
        if not parsed.port:
            raise ValueError("Database URL must include port")
        if not parsed.path or parsed.path == "/":
            raise ValueError("Database URL must include database name")
        return v


class RedisConfig(BaseModel):
    """Redis configuration with validation."""

    url: RedisDsn
    max_connections: int = Field(default=20, ge=1, le=100)
    socket_timeout: int = Field(default=5, ge=1, le=30)
    socket_connect_timeout: int = Field(default=5, ge=1, le=30)
    health_check_interval: int = Field(default=30, ge=10, le=300)

    @validator("url")
    def validate_redis_url(cls, v: RedisDsn) -> RedisDsn:  # type: ignore[override]
        """Validate Redis URL format."""
        parsed = urlparse(str(v))
        if not parsed.hostname:
            raise ValueError("Redis URL must include hostname")
        return v


class CeleryConfig(BaseModel):
    """Celery configuration settings."""

    broker_url: RedisDsn
    result_backend: RedisDsn
    task_serializer: str = Field(default="json")
    accept_content: List[str] = Field(default_factory=lambda: ["json"])
    result_serializer: str = Field(default="json")
    timezone: str = Field(default="UTC")
    enable_utc: bool = Field(default=True)
    worker_prefetch_multiplier: int = Field(default=1, ge=1, le=10)
    task_acks_late: bool = Field(default=True)
    worker_disable_rate_limits: bool = Field(default=False)

    # Task routing
    task_routes: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "backend.tasks.crypto_analysis.*": {"queue": "crypto_analysis"},
            "backend.tasks.price_fetching.*": {"queue": "price_fetching"},
            "backend.tasks.notifications.*": {"queue": "notifications"},
        }
    )

    # Retry configuration
    task_default_retry_delay: int = Field(default=60, ge=1, le=3600)
    task_max_retries: int = Field(default=3, ge=0, le=10)


class SecurityConfig(BaseModel):
    """Security-related configuration."""

    secret_key: SecretStr = Field(..., min_length=32)
    jwt_secret_key: SecretStr = Field(..., min_length=32)
    jwt_access_token_expires: int = Field(default=3600, ge=300, le=86400)
    jwt_refresh_token_expires: int = Field(default=2592000, ge=86400)
    password_hash_rounds: int = Field(default=12, ge=10, le=16)

    # CORS settings
    cors_origins: List[str] = Field(default_factory=list)
    cors_allow_credentials: bool = Field(default=True)

    # Rate limiting
    rate_limit_storage_url: RedisDsn
    rate_limit_default: str = Field(default="100 per hour")
    rate_limit_login: str = Field(default="5 per minute")

    @validator("secret_key", "jwt_secret_key", pre=True)
    def validate_secrets(
        cls, v: Union[str, SecretStr]
    ) -> SecretStr:  # type: ignore[override]
        """Validate and generate secrets if needed."""
        if isinstance(v, SecretStr):
            secret_value = v.get_secret_value()
        else:
            secret_value = v

        if not secret_value or secret_value in ["change-me", "dev-key"]:
            secret_value = secrets.token_urlsafe(32)

        if len(secret_value) < 32:
            raise ValueError("Secret keys must be at least 32 characters long")

        return SecretStr(secret_value)


class APIConfig(BaseModel):
    """External API configuration."""

    coingecko_api_key: Optional[SecretStr] = Field(default=None)
    coingecko_base_url: HttpUrl = Field(default="https://api.coingecko.com/api/v3")
    coingecko_timeout: int = Field(default=30, ge=5, le=120)
    coingecko_retries: int = Field(default=3, ge=0, le=5)

    # Rate limiting for external APIs
    coingecko_rate_limit: int = Field(default=50, ge=1, le=1000)

    @validator("coingecko_api_key")
    def validate_api_key(
        cls, v: Optional[SecretStr]
    ) -> Optional[SecretStr]:  # type: ignore[override]
        """Validate API key format."""
        if v is None:
            return v

        key_value = v.get_secret_value()
        if len(key_value) < 10:
            raise ValueError("CoinGecko API key appears to be invalid")

        return v


class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""

    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_format: str = Field(default="json")
    enable_metrics: bool = Field(default=True)
    enable_tracing: bool = Field(default=False)

    # Health check settings
    health_check_interval: int = Field(default=30, ge=5, le=300)
    health_check_timeout: int = Field(default=10, ge=1, le=60)

    # Alerting
    enable_alerts: bool = Field(default=False)
    alert_webhook_url: Optional[HttpUrl] = Field(default=None)
    slack_webhook_url: Optional[HttpUrl] = Field(default=None)


class FeatureFlags(BaseModel):
    """Feature flags for runtime behavior control."""

    enable_registration: bool = Field(default=True)
    enable_password_reset: bool = Field(default=True)
    enable_email_notifications: bool = Field(default=False)
    enable_advanced_analytics: bool = Field(default=False)
    enable_rate_limiting: bool = Field(default=True)
    enable_caching: bool = Field(default=True)
    enable_background_tasks: bool = Field(default=True)

    # Beta features
    enable_portfolio_tracking: bool = Field(default=False)
    enable_automated_trading: bool = Field(default=False)
    enable_social_features: bool = Field(default=False)


class Settings(BaseSettings):
    """Main application settings with environment-based configuration."""

    # Environment settings
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    testing: bool = Field(default=False)

    # Application metadata
    app_name: str = Field(default="YTD-Kopya")
    app_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")

    # Configuration sections
    database: DatabaseConfig
    redis: RedisConfig
    celery: CeleryConfig
    security: SecurityConfig
    apis: APIConfig
    monitoring: MonitoringConfig
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False

        fields = {
            "database": {"env_prefix": "DATABASE_"},
            "redis": {"env_prefix": "REDIS_"},
            "celery": {"env_prefix": "CELERY_"},
            "security": {"env_prefix": "SECURITY_"},
            "apis": {"env_prefix": "API_"},
            "monitoring": {"env_prefix": "MONITORING_"},
            "features": {"env_prefix": "FEATURE_"},
        }

    @validator("environment", pre=True)
    def validate_environment(
        cls, v: Union[str, Environment]
    ) -> Environment:  # type: ignore[override]
        """Validate and convert environment string."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @validator("debug")
    def set_debug_based_on_environment(
        cls, v: bool, values: Dict[str, Any]
    ) -> bool:  # type: ignore[override]
        """Set debug mode based on environment if not explicitly set."""
        if "environment" in values:
            env = values["environment"]
            if env in (Environment.DEVELOPMENT, Environment.TESTING):
                return True
            if env == Environment.PRODUCTION:
                return False
        return v

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING
