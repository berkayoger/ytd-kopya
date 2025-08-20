import os
import secrets
from datetime import timedelta


class Config:
    """Temel yapılandırma; SECRET_KEY üretimi güvenli."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV") == "production":
            raise ValueError("SECRET_KEY must be set in production")
        SECRET_KEY = secrets.token_urlsafe(32)

    # Oturum güvenliği
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)

