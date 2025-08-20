from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from backend.utils.logger import create_log


def create_app() -> Flask:
    """Uygulama fabrikası: rate limit ve login koruması."""
    app = Flask(__name__)

    # Genel rate limit ayarları
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per day", "100 per hour"],
    )

    @limiter.limit("5 per minute")
    @app.route("/api/auth/login", methods=["POST"])
    def rate_limited_login():
        """Login denemeleri için özel limit; gerçek iş mantığı ayrı blueprint'te."""
        create_log(action="login_rate_limit", endpoint="/api/auth/login")
        return "", 204

    return app

