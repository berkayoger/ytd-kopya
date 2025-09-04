"""Flask application factory with security enhancements."""

from __future__ import annotations

import logging
import os
from typing import Type

from dotenv import load_dotenv
from .extensions import init_extensions, limiter

try:
    from celery import Celery
except Exception:
    Celery = None

def create_app(config_object: str | None = None):
    """Create Flask app ensuring .env is loaded when not in production."""
    if os.getenv("FLASK_ENV", "development") != "production":
        load_dotenv()
    from .app import create_app as _create_app

    app = _create_app(config_object)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY') or 'dev-secret-key'
    try:
        init_extensions(app)
        from .security import api_bp, auth_bp, csrf_bp
        app.register_blueprint(csrf_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(api_bp)
    except Exception as exc:
        logger.error("Extension initialization failed: %s", exc)
    return app

from .db import db as db

if Celery is not None:
    celery_app = Celery(
        "ytdcrypto",
        broker=os.getenv("CELERY_BROKER_URL", "memory://"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "cache+memory://"),
    )
else:
    celery_app = None

try:
    from flask_socketio import SocketIO
    socketio = None
except Exception:
    socketio = None

if os.getenv("FLASK_ENV", "development") != "production":
    load_dotenv()

logger = logging.getLogger("backend")

from .config import BaseConfig, DevelopmentConfig, ProductionConfig, TestingConfig

def _select_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "testing":
        return TestingConfig
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig

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