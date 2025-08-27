"""Utility functions and classes for JWT management."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, request

from ..db.models import TokenBlacklist, User


class TokenManager:
    """Secure JWT token management class"""

    @staticmethod
    def _generate_jti() -> str:
        """Generate a unique JWT ID"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def generate_tokens(
        user_id: int, additional_claims: dict | None = None
    ) -> dict:
        """Generate both access and refresh tokens with enhanced security"""
        now = datetime.now(timezone.utc)

        access_jti = TokenManager._generate_jti()
        refresh_jti = TokenManager._generate_jti()

        base_payload = {
            "user_id": user_id,
            "iat": now,
            "iss": "ytd-crypto-app",
            "aud": "ytd-crypto-users",
        }

        if additional_claims:
            base_payload.update(additional_claims)

        access_payload = base_payload.copy()
        access_payload.update(
            {
                "exp": now + timedelta(minutes=15),
                "jti": access_jti,
                "type": "access",
                "fresh": True,
            }
        )

        refresh_payload = base_payload.copy()
        refresh_payload.update(
            {
                "exp": now + timedelta(days=7),
                "jti": refresh_jti,
                "type": "refresh",
            }
        )

        secret = current_app.config.get(
            "JWT_SECRET_KEY", current_app.config.get("SECRET_KEY")
        )

        access_token = jwt.encode(access_payload, secret, algorithm="HS256")
        refresh_token = jwt.encode(refresh_payload, secret, algorithm="HS256")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_expires": access_payload["exp"],
            "refresh_expires": refresh_payload["exp"],
        }

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> dict:
        """Verify JWT token with enhanced security checks"""
        try:
            payload = jwt.decode(
                token,
                current_app.config.get(
                    "JWT_SECRET_KEY", current_app.config.get("SECRET_KEY")
                ),
                algorithms=["HS256"],
                audience="ytd-crypto-users",
                issuer="ytd-crypto-app",
            )

            if payload.get("type") != token_type:
                raise jwt.InvalidTokenError(
                    f"Invalid token type. Expected {token_type}"
                )

            jti = payload.get("jti")
            if TokenManager._is_token_blacklisted(jti):
                raise jwt.InvalidTokenError("Token has been revoked")

            user = User.query.get(payload["user_id"])
            if not user or not getattr(user, "is_active", True):
                raise jwt.InvalidTokenError("User not found or inactive")

            return payload

        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as exc:  # pragma: no cover - re-raise for clarity
            raise exc
        except Exception as exc:  # pragma: no cover - unexpected errors
            raise jwt.InvalidTokenError(f"Token verification failed: {exc}")

    @staticmethod
    def _is_token_blacklisted(jti: str | None) -> bool:
        """Check if token is blacklisted"""
        if not jti:
            return True
        return TokenBlacklist.query.filter_by(jti=jti).first() is not None


# Legacy compatibility
def generate_tokens(user_id: int, username: str, role: str | None = None):
    """Legacy function for backward compatibility"""
    tokens = TokenManager.generate_tokens(
        user_id, {"username": username, "role": role}
    )
    return tokens["access_token"], tokens["refresh_token"], secrets.token_hex(32)


def verify_access_token(token: str):
    """Legacy function for backward compatibility"""
    try:
        return TokenManager.verify_token(token, "access")
    except jwt.InvalidTokenError:
        return None


def verify_jwt(token: str):
    """Wrapper around :meth:`TokenManager.verify_token` returning payload or None"""
    try:
        return TokenManager.verify_token(token, "access")
    except jwt.InvalidTokenError:
        return None


def verify_csrf() -> bool:
    """Validate CSRF token sent via header against cookie"""
    sent = request.headers.get("X-CSRF-Token")
    stored = request.cookies.get("csrf-token")
    return bool(sent and stored and sent == stored)


def csrf_required(func):
    """Decorator enforcing CSRF validation"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_app.config.get("TESTING"):
            return func(*args, **kwargs)
        if not verify_csrf():
            return ({"error": "CSRF token is missing or invalid", "code": "INVALID_CSRF"}, 403)
        return func(*args, **kwargs)

    return wrapper


# Backwards compatibility aliases
require_csrf = csrf_required


def require_admin(func):
    """Delegate to admin_required decorator to maintain legacy API"""
    from .middlewares import admin_required

    return admin_required()(func)


def jwt_required_if_not_testing(*dargs, **dkwargs):
    """Skip JWT verification in tests or when X-API-KEY is provided"""
    from flask_jwt_extended import verify_jwt_in_request

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_app.config.get("TESTING"):
                return fn(*args, **kwargs)
            if request.headers.get("X-API-KEY"):
                return fn(*args, **kwargs)
            verify_jwt_in_request(*dargs, **dkwargs)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


