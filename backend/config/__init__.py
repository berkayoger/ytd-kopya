"""Configuration management module."""

from .factory import get_settings
from .legacy import (
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
)


def get_config(name: str):
    """Return a legacy-style config class by environment name."""
    env = (name or "development").lower()
    if env == "production":
        return ProductionConfig
    if env == "testing":
        return TestingConfig
    if env == "development":
        return DevelopmentConfig
    return BaseConfig


__all__ = [
    "get_settings",
    "BaseConfig",
    "DevelopmentConfig",
    "ProductionConfig",
    "TestingConfig",
    "get_config",
]
