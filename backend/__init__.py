"""
backend paket giriş noktası: create_app re-export.
"""

class _NoOpLimiter:
    """Fallback limiter to satisfy imports when real limiter is unavailable."""

    def limit(self, *args, **kwargs):  # noqa: D401
        def decorator(func):
            return func
        return decorator


limiter = _NoOpLimiter()

from .app import create_app  # from backend import create_app çalışsın

__all__ = ["create_app", "limiter"]
