from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# Redis yoksa in-memory'e düşer (tek instance için)
def setup_rate_limit(app: Flask) -> Limiter:
    storage_uri = app.config.get("RATELIMIT_STORAGE_URI", "memory://")
    try:
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            storage_uri=storage_uri,
        )
    except Exception:  # pragma: no cover
        limiter = Limiter(key_func=get_remote_address, app=app)
    return limiter
