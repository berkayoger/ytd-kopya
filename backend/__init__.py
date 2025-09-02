"""
backend paket giriş noktası:
- create_app fonksiyonunu, limiter'ı ve testlerin beklediği bazı objeleri dışa aktarır.

Amaç: Test ortamında import hatalarını önlemek için Celery ve Socket.IO gibi
bağımlılıklar için güvenli placeholder'lar sağlar.
"""

from __future__ import annotations

import logging
import os
from typing import Type

from dotenv import load_dotenv  # re-export for tests to patch

try:
    from celery import Celery
except Exception:  # pragma: no cover
    Celery = None  # type: ignore


class _NoOpLimiter:
    """Fallback limiter to satisfy imports when real limiter is unavailable."""

    def limit(self, *args, **kwargs):  # noqa: D401
        def decorator(func):
            return func

        return decorator


limiter = _NoOpLimiter()


# Flask app factory wrapper
def create_app(config_object: str | None = None):
    """Create Flask app ensuring .env is loaded when not in production."""
    # Load environment variables from .env for non-production envs
    if os.getenv("FLASK_ENV", "development") != "production":
        load_dotenv()
    # Import here to avoid circular import issues during module init
    from .app import create_app as _create_app

    return _create_app(config_object)


# SQLAlchemy db nesnesini üst seviyeden de sun
from .db import db as db  # type: ignore

# Celery uygulamasını üst seviyeden de sun (bazı modüller backend.celery_app bekliyor)
if Celery is not None:
    # Hafif, bellek içi varsayılanlar ile test dostu bir Celery örneği
    celery_app = Celery(
        "ytdcrypto",
        broker=os.getenv("CELERY_BROKER_URL", "memory://"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "cache+memory://"),
    )
else:  # pragma: no cover
    celery_app = None  # type: ignore

# Socket.IO referansı (uygulama init aşamasında extension olarak set edilebilir)
try:
    from flask_socketio import SocketIO  # lazy import

    socketio: SocketIO | None = None
except Exception:  # pragma: no cover
    socketio = None

# Ortam değişkenlerini .env'den yükle (production hariç)
if os.getenv("FLASK_ENV", "development") != "production":
    load_dotenv()

# Basit logger
logger = logging.getLogger("backend")

# Config seçim ve re-export
from .config import (BaseConfig, DevelopmentConfig, ProductionConfig,
                     TestingConfig)


def _select_config() -> Type[BaseConfig]:  # type: ignore[misc]
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "testing":
        return TestingConfig  # type: ignore[return-value]
    if env == "production":
        return ProductionConfig  # type: ignore[return-value]
    return DevelopmentConfig  # type: ignore[return-value]


# Tests patch this: monkeypatch.setattr("backend.Config....")
Config = _select_config()

__all__ = [
    "create_app",
    "limiter",
    "db",
    "celery_app",
    "socketio",
    "logger",
    "Config",
    "load_dotenv",
]
