"""Configuration factory for environment-specific settings."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict

from .settings import Environment, Settings


class ConfigurationError(Exception):
    """Configuration-related errors."""


class EnvironmentSettingsFactory:
    """Factory for creating environment-specific configuration."""

    @staticmethod
    def create_development_overrides() -> Dict[str, Any]:
        """Development environment specific overrides."""
        return {
            "debug": True,
            "database": {"echo": True, "pool_size": 2},
            "security": {
                "cors_origins": ["http://localhost:3000", "http://localhost:8000"],
                "rate_limit_default": "1000 per hour",
            },
            "monitoring": {"log_level": "DEBUG", "enable_tracing": True},
            "features": {
                "enable_advanced_analytics": True,
                "enable_portfolio_tracking": True,
            },
        }

    @staticmethod
    def create_testing_overrides() -> Dict[str, Any]:
        """Testing environment specific overrides."""
        return {
            "testing": True,
            "database": {
                "url": "postgresql://test:test@localhost:5432/ytd_test",
                "echo": False,
                "pool_size": 1,
            },
            "redis": {"url": "redis://localhost:6379/15"},
            "security": {
                "jwt_access_token_expires": 300,
                "rate_limit_default": "10000 per hour",
            },
            "monitoring": {"log_level": "WARNING", "enable_metrics": False},
            "features": {"enable_background_tasks": False},
        }

    @staticmethod
    def create_production_overrides() -> Dict[str, Any]:
        """Production environment specific overrides."""
        return {
            "debug": False,
            "database": {"pool_size": 20, "echo": False},
            "security": {"cors_origins": []},
            "monitoring": {
                "log_level": "INFO",
                "enable_metrics": True,
                "enable_alerts": True,
            },
        }

    @classmethod
    def get_environment_overrides(cls, env: Environment) -> Dict[str, Any]:
        """Get environment-specific configuration overrides."""
        mapping = {
            Environment.DEVELOPMENT: cls.create_development_overrides(),
            Environment.TESTING: cls.create_testing_overrides(),
            Environment.PRODUCTION: cls.create_production_overrides(),
            Environment.STAGING: cls.create_production_overrides(),
        }
        return mapping.get(env, {})


@lru_cache()
def get_settings() -> Settings:
    """Create and cache application settings."""
    try:
        settings = Settings()
        return settings
    except Exception as exc:  # pragma: no cover - defensive programming
        raise ConfigurationError(f"Failed to load configuration: {exc}") from exc


def get_test_settings(**overrides: Any) -> Settings:
    """Create test settings with optional overrides."""
    test_overrides = {"environment": Environment.TESTING, **overrides}

    original_env = os.environ.copy()
    try:
        for key, value in test_overrides.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    env_key = f"{key.upper()}_{nested_key.upper()}"
                    os.environ[env_key] = str(nested_value)
            else:
                os.environ[key.upper()] = str(value)

        return Settings()
    finally:
        os.environ.clear()
        os.environ.update(original_env)
