import os
import secrets


class Config:
    """Temel yapılandırma; SECRET_KEY üretimi güvenli."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV") == "production":
            raise ValueError("SECRET_KEY must be set in production")
        SECRET_KEY = secrets.token_urlsafe(32)

