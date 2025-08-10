from __future__ import annotations

from flask import Flask
import os
import logging

from .logging_config import configure_json_logging
from .middleware.request_id import request_id_middleware
from .health import bp as health_bp


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

    # --- Blueprints ---
    app.register_blueprint(health_bp)

    return app
