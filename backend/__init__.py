"""Flask application factory with security enhancements."""

from __future__ import annotations

import logging
import os
from typing import Type

from dotenv import load_dotenv  # re-export for tests to patch

from .extensions import init_extensions, limiter

try:
    from celery import Celery
except Exception:  # pragma: no cover
    Celery = None  # type: ignore


# Flask app factory wrapper
def create_app(config_object: str | None = None):
    """Create Flask app ensuring .env is loaded when not in production."""
    if os.getenv("FLASK_ENV", "development") != "production":
        load_dotenv()
    from .app import create_app as _create_app

    app = _create_app(config_object)
    try:
        init_extensions(app)
        from .security import api_bp, auth_bp, csrf_bp

        app.register_blueprint(csrf_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(api_bp)
    except Exception as exc:  # pragma: no cover
        logger.error("Extension initialization failed: %s", exc)
    return app


# SQLAlchemy db nesnesini üst seviyeden de sun
from .db import db as db  # type: ignore  # noqa: E402

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
from .config import (  # noqa: E402  # isort: skip
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
)


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
