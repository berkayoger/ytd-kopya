from __future__ import annotations

from flask import Flask
import os
from backend.api.admin.logs import admin_logs_bp
import logging

from .logging_config import configure_json_logging
from .middleware.request_id import request_id_middleware
from .health import bp as health_bp
from .security import security_headers
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(config_object: str | None = None) -> Flask:
    """Basit Flask uygulaması oluştur."""
    app = Flask(__name__)
    if config_object:
        app.config.from_object(config_object)

    # --- Logging (JSON) ---
    log_level = os.getenv("LOG_LEVEL", "INFO")
    configure_json_logging(log_level)
    logging.getLogger(__name__).info("app_boot", extra={"stage": "init"})

    # --- Request-ID middleware ---
    request_id_middleware(app)

    # --- Güvenlik başlıkları ---
    security_headers(app)

    # --- ProxyFix ---
    if os.getenv("ENABLE_PROXY_FIX", "false").lower() == "true":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    # --- Blueprints ---
    app.register_blueprint(admin_logs_bp)

    return app
