"""Geçici Feature Flag kontrol sistemi.

İleride Redis veya DB destekli yapıya taşınabilir.
"""

from typing import Dict, Optional
import os
import json
import redis

USE_REDIS = os.getenv("USE_REDIS_FEATURE_FLAGS", "1") == "1"

redis_client: Optional[redis.Redis]
try:
    redis_client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )
    redis_client.ping()
    redis_client.json = redis_client  # mock json client if redis-py json is not enabled
    if hasattr(redis_client, "json"):
        redis_client.json.get = (
            lambda key, path=None: json.loads(redis_client.get(key) or "null")
        )
except Exception:
    redis_client = None
    USE_REDIS = False

# Fallback in-memory store
_default_flags: Dict[str, bool] = {
    "recommendation_enabled": True,
    "next_generation_model": False,
    "advanced_forecast": False,
    "health_check": True,
    "draks": False,
}

# In-memory metadata store for feature flags
_default_flag_meta: Dict[str, Dict[str, str]] = {
    flag: {"description": "", "category": "general"} for flag in _default_flags
}

_flag_groups: Dict[str, list] = {}


def feature_flag_enabled(flag_name: str) -> bool:
    """Return ``True`` if the feature flag is enabled."""
    if USE_REDIS and redis_client:
        value = redis_client.get(f"feature_flag:{flag_name}")
        if value is None:
            return False
        return value == "true"
    return _default_flags.get(flag_name, False)


def set_feature_flag(flag_name: str, value: bool) -> None:
    """Update a specific feature flag."""
    if USE_REDIS and redis_client:
        redis_client.set(f"feature_flag:{flag_name}", str(value).lower())
    else:
        if flag_name in _default_flags:
            _default_flags[flag_name] = value


def all_feature_flags() -> Dict[str, bool]:
    """Return a mapping of all feature flags and their states."""
    if USE_REDIS and redis_client:
        return {flag: feature_flag_enabled(flag) for flag in _default_flags}
    return {flag: _default_flags[flag] for flag in _default_flags}


def create_feature_flag(
    flag_name: str,
    enabled: bool,
    description: str = "",
    category: str = "general",
):
    """Create a new feature flag and optionally store metadata"""
    if USE_REDIS and redis_client:
        redis_client.set(f"feature_flag:{flag_name}", str(enabled).lower())
        redis_client.hset(
            f"feature_flag_meta:{flag_name}",
            mapping={"description": description, "category": category},
        )
        redis_client.sadd(f"feature_flags:category:{category}", flag_name)
    _default_flags[flag_name] = enabled
    _default_flag_meta[flag_name] = {
        "description": description,
        "category": category,
    }


def get_feature_flag_metadata(flag_name: str) -> Dict[str, str]:
    """Get metadata for a feature flag (description, category)"""
    if USE_REDIS and redis_client:
        return redis_client.hgetall(f"feature_flag_meta:{flag_name}")
    return _default_flag_meta.get(
        flag_name, {"description": "", "category": "general"}
    )


def get_flags_by_category(category: str) -> Dict[str, bool]:
    """Get all flags in a specific category."""
    if USE_REDIS and redis_client:
        keys = redis_client.smembers(f"feature_flags:category:{category}")
        return {k: feature_flag_enabled(k) for k in keys}
    return {
        k: v
        for k, v in _default_flags.items()
        if _default_flag_meta.get(k, {}).get("category") == category
    }


def export_all_flags() -> str:
    return json.dumps({
        "flags": _default_flags,
        "meta": _default_flag_meta,
    })


def import_flags_from_json(data: str) -> None:
    parsed = json.loads(data)
    for k, v in parsed.get("flags", {}).items():
        desc = parsed.get("meta", {}).get(k, {}).get("description", "")
        cat = parsed.get("meta", {}).get(k, {}).get("category", "general")
        create_feature_flag(k, v, desc, cat)
