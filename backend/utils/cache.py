from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
from typing import Any, Callable

from cachetools import TTLCache
from flask import current_app

# Try to import Flask-Caching for better integration
try:
    from flask_caching import Cache
    HAS_FLASK_CACHING = True
except ImportError:
    HAS_FLASK_CACHING = False

logger = logging.getLogger(__name__)

# L1 in-memory cache with default TTL
_DEFAULT_L1_TTL = int(os.getenv("L1_CACHE_TTL", "60"))
_l1_cache: TTLCache[str, Any] = TTLCache(maxsize=1024, ttl=_DEFAULT_L1_TTL)


def init_l1_cache_from_config() -> None:
    """Initialize L1 cache TTL from Flask config if available."""
    global _l1_cache
    try:
        ttl = int(current_app.config.get("L1_CACHE_TTL", _DEFAULT_L1_TTL))
    except Exception:
        ttl = _DEFAULT_L1_TTL
    _l1_cache = TTLCache(maxsize=1024, ttl=ttl)


def _hash_key(prefix: str, *args, **kwargs) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    hexdigest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    key_prefix = os.getenv("CACHE_KEY_PREFIX", current_app.config.get("CACHE_KEY_PREFIX", "ytd:"))
    return f"{key_prefix}{prefix}:{hexdigest}"


def _get_redis_client():
    """Get Redis client with Flask-Caching integration support"""
    # First try Flask-Caching if available
    if HAS_FLASK_CACHING:
        cache: Cache = current_app.extensions.get("cache")
        if cache and hasattr(cache.cache, "_write_client"):
            return cache.cache._write_client
    
    # Prefer initialized Redis client from extensions
    ext = getattr(current_app, "extensions", {}) or {}
    client = ext.get("redis_client")
    if client:
        return client
    
    # Fallback: construct from REDIS_URL if available (avoid in tests if possible)
    try:
        import redis  # local import to avoid hard dependency at import time

        url = os.getenv("CACHE_REDIS_URL") or os.getenv("REDIS_URL")
        if url:
            return redis.from_url(url, decode_responses=True)
    except Exception:  # pragma: no cover - defensive
        return None
    return None


def _get_flask_cache():
    """Get Flask-Caching instance if available"""
    if not HAS_FLASK_CACHING:
        return None
    return current_app.extensions.get("cache")


def cache_l1_l2(prefix: str, timeout: int | None = None):
    """Two-level cache decorator: L1 in-memory, L2 Redis if configured."""

    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _hash_key(prefix, *args, **kwargs)

            # L1 check
            if key in _l1_cache:
                logger.debug("L1 cache hit: %s", key)
                return _l1_cache[key]

            # L2 cache check - try Flask-Caching first, then Redis
            flask_cache = _get_flask_cache()
            if flask_cache:
                try:
                    val = flask_cache.get(key)
                    if val is not None:
                        logger.debug("Flask-Caching L2 hit: %s", key)
                        _l1_cache[key] = val
                        return val
                except Exception as exc:
                    logger.warning("Flask-Caching get failed: %s", exc)
            
            # Fallback to direct Redis
            client = _get_redis_client()
            if client is not None:
                try:
                    raw = client.get(key)
                    if raw is not None:
                        logger.debug("Redis L2 hit: %s", key)
                        val = json.loads(raw)
                        _l1_cache[key] = val
                        return val
                except Exception as exc:
                    logger.warning("Redis L2 get failed: %s", exc)

            # Compute
            val = func(*args, **kwargs)

            # Store in L1
            _l1_cache[key] = val
            
            # Store in L2 - try Flask-Caching first, then Redis
            if flask_cache:
                try:
                    flask_cache.set(key, val, timeout=timeout)
                    logger.debug("Flask-Caching L2 stored: %s", key)
                except Exception as exc:
                    logger.warning("Flask-Caching set failed: %s", exc)
            elif client is not None:
                try:
                    payload = json.dumps(val, default=str)
                    if timeout is not None:
                        client.setex(key, timeout, payload)
                    else:
                        client.set(key, payload)
                    logger.debug("Redis L2 stored: %s", key)
                except Exception as exc:
                    logger.warning("Redis L2 set failed: %s", exc)
            
            return val

        return wrapper

    return decorator


def cache_invalidate(prefix: str) -> None:
    """Invalidate entries with a prefix in both L1 and L2."""
    # L2
    client = _get_redis_client()
    if client is not None:
        try:
            key_prefix = os.getenv("CACHE_KEY_PREFIX", current_app.config.get("CACHE_KEY_PREFIX", "ytd:"))
            pattern = f"{key_prefix}{prefix}:*"
            # Using scan_iter to avoid blocking Redis
            keys = list(client.scan_iter(match=pattern))
            if keys:
                client.delete(*keys)
                logger.info("Invalidated %d L2 cache entries for %s", len(keys), prefix)
        except Exception as exc:
            logger.error("L2 cache invalidation failed: %s", exc)

    # L1
    try:
        to_remove = [k for k in _l1_cache.keys() if f":{prefix}:" in k or k.endswith(f"{prefix}") or k.startswith(prefix)]
        for k in to_remove:
            _l1_cache.pop(k, None)
        if to_remove:
            logger.info("Invalidated %d L1 cache entries for %s", len(to_remove), prefix)
    except Exception:  # pragma: no cover
        pass

