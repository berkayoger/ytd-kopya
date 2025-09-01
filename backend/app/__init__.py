from __future__ import annotations

import logging
import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from backend.api.admin.logs import admin_logs_bp
from backend.app_rate_limit import setup_rate_limit
from backend.app_security import harden_app

from .logging_config import configure_json_logging
from .middleware.request_id import request_id_middleware
from .security import security_headers

try:  # pragma: no cover
    from backend.utils.logging import before_request_hook
except Exception:  # pragma: no cover
    before_request_hook = None


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


app = create_app()

if before_request_hook:
    app.before_request(before_request_hook)
harden_app(app)
limiter = setup_rate_limit(app)
