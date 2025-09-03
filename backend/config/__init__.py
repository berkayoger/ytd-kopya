"""Configuration management module."""

from .factory import get_settings
from .legacy import (BaseConfig, DevelopmentConfig, ProductionConfig,
                     TestingConfig)

__all__ = [
    "get_settings",
    "BaseConfig",
    "DevelopmentConfig",
    "ProductionConfig",
    "TestingConfig",
]
