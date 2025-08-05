"""Geçici Feature Flag kontrol sistemi.

İleride Redis veya DB destekli yapıya taşınabilir.
"""

from typing import Dict
import os
import redis

USE_REDIS = os.getenv("USE_REDIS_FEATURE_FLAGS", "1") == "1"

try:
    redis_client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )
    redis_client.ping()
except Exception:
    redis_client = None
    USE_REDIS = False

# Fallback in-memory store
_flags: Dict[str, bool] = {
    "recommendation_enabled": True,
    "next_generation_model": False,
    "advanced_forecast": False,
}


def feature_flag_enabled(flag_name: str) -> bool:
    """Return ``True`` if the feature flag is enabled."""
    if USE_REDIS and redis_client:
        value = redis_client.get(f"feature_flag:{flag_name}")
        if value is None:
            return False
        return value == "true"
    return _flags.get(flag_name, False)


def set_feature_flag(flag_name: str, value: bool) -> None:
    """Update a specific feature flag."""
    if USE_REDIS and redis_client:
        redis_client.set(f"feature_flag:{flag_name}", str(value).lower())
    else:
        if flag_name in _flags:
            _flags[flag_name] = value


def all_feature_flags() -> dict:
    """Return a mapping of all feature flags and their states."""
    if USE_REDIS and redis_client:
        result: Dict[str, bool] = {}
        for flag in _flags:
            result[flag] = feature_flag_enabled(flag)
        return result
    return {flag: _flags[flag] for flag in _flags}
