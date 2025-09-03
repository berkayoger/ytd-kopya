from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import g, jsonify, request

from backend.extensions import limiter
from backend.models import db
from backend.models.api_key import APIKey


class APIKeyManager:
    """Utility for managing API keys."""

    @staticmethod
    def generate_api_key() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_api_key(api_key: str) -> bytes:
        salt = os.getenv("API_KEY_SALT", "change-me").encode()
        return hashlib.pbkdf2_hmac("sha256", api_key.encode(), salt, 200_000)

    @staticmethod
    def verify_api_key(api_key: str, hashed: bytes) -> bool:
        return hmac.compare_digest(APIKeyManager.hash_api_key(api_key), hashed)

    @staticmethod
    def create_api_key(
        user_id: int,
        name: str,
        rate_limit_override: str | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[str, int]:
        api_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(api_key)
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=365)
        rec = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            rate_limit_override=rate_limit_override,
            expires_at=expires_at,
            is_active=True,
        )
        db.session.add(rec)
        db.session.commit()
        return api_key, rec.id

    @staticmethod
    def validate_api_key(api_key: str | None) -> APIKey | None:
        if not api_key:
            return None
        for rec in APIKey.query.filter_by(is_active=True).all():
            if APIKeyManager.verify_api_key(api_key, rec.key_hash):
                if rec.expires_at and rec.expires_at < datetime.utcnow():
                    return None
                rec.last_used_at = datetime.utcnow()
                rec.usage_count = (rec.usage_count or 0) + 1
                db.session.commit()
                return rec
        return None


def require_api_key(fn):
    """Decorator to require a valid API key."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.headers.get(
            "Authorization"
        )
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]
        rec = APIKeyManager.validate_api_key(api_key)
        if not rec:
            return jsonify({"error": "API key required"}), 401
        g.api_key = rec
        g.user_id = rec.user_id
        return fn(*args, **kwargs)

    return wrapper


def limit_by_api_key(default_limit: str):
    """Apply dynamic rate limit based on API key configuration."""

    def dynamic_limit() -> str:
        if hasattr(g, "api_key") and g.api_key and g.api_key.rate_limit_override:
            return g.api_key.rate_limit_override
        return default_limit

    def decorator(fn):
        return limiter.limit(dynamic_limit)(fn)

    return decorator
