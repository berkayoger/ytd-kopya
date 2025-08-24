"""Geçici Feature Flag kontrol sistemi.

İleride Redis veya DB destekli yapıya taşınabilir.
"""

from typing import Dict, Optional
import os
import json
from contextlib import suppress
try:
    import redis  # type: ignore
except Exception:
    redis = None

USE_REDIS = os.getenv("USE_REDIS_FEATURE_FLAGS", "1") == "1" and redis is not None

redis_client: Optional["redis.Redis"]  # type: ignore[name-defined]
try:
    redis_client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )
    redis_client.ping()
    # yumuşak JSON desteği: yoksa .get/.set ile çalışacağız
except Exception:
    redis_client = None
    USE_REDIS = False

# Fallback in-memory store
_default_flags: Dict[str, bool] = {
    "recommendation_enabled": True,
    "next_generation_model": False,
    "advanced_forecast": False,
    "health_check": True,
    # DRAKS için hem kısa hem _enabled alias'ı destekleyelim
    "draks": False,
    "draks_enabled": False,
    "decision_consensus": True,

}

# In-memory metadata store for feature flags
_default_flag_meta: Dict[str, Dict[str, str]] = {
    flag: {"description": "", "category": "general"} for flag in _default_flags
}

_flag_groups: Dict[str, list] = {}


def _aliases(name: str) -> list[str]:
    """İstenen flag adı için muhtemel alias'ları döndür."""
    if name.endswith("_enabled"):
        base = name[: -len("_enabled")]
        return [name, base]
    else:
        return [name, f"{name}_enabled"]

def _redis_get_bool(n: str) -> Optional[bool]:
    if not (USE_REDIS and redis_client):
        return None
    with suppress(Exception):
        raw = redis_client.get(f"feature_flag:{n}")
        if raw is not None:
            try:
                val = json.loads(raw)
            except Exception:
                val = raw
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                if val.lower() in ("true", "1"):
                    return True
                if val.lower() in ("false", "0"):
                    return False
            if isinstance(val, (int, float)):
                return bool(val)
    return None


def feature_flag_enabled(flag_name: str) -> bool:
    """Flag açık mı? (alias'lar: name ve name_enabled). Redis yoksa in-memory fallback."""
    candidates = _aliases(flag_name)
    for n in candidates:
        v = _redis_get_bool(n)
        if v is not None:
            return bool(v)
    for n in candidates:
        if n in _default_flags:
            return bool(_default_flags[n])
    return False


def set_feature_flag(flag_name: str, value: bool) -> None:
    """Update a specific feature flag."""
    if USE_REDIS and redis_client:
        # alias olanları da birlikte yaz
        for n in _aliases(flag_name):
            redis_client.set(f"feature_flag:{n}", str(value).lower())
    for n in _aliases(flag_name):
        _default_flags[n] = bool(value)


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
    meta: Optional[Dict[str, str]] = None,
) -> bool:
    """Create a new feature flag and optionally store metadata"""
    meta_data = meta or {"description": description, "category": category}
    if USE_REDIS and redis_client:
        with suppress(Exception):
            redis_client.hset(
                f"feature_flag_meta:{flag_name}",
                mapping=meta_data,
            )
            redis_client.sadd(
                f"feature_flags:category:{meta_data.get('category', 'general')}",
                flag_name,
            )
    _default_flag_meta[flag_name] = {
        **_default_flag_meta.get(flag_name, {}),
        **meta_data,
    }
    # flag değeri ve alias'ları güncelle
    set_feature_flag(flag_name, enabled)
    return True


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
