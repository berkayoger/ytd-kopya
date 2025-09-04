"""CSRF token management for web applications."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, make_response
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import generate_csrf

from backend.extensions import limiter, redis_client
from backend.settings import get_settings

logger = logging.getLogger(__name__)

csrf_bp = Blueprint("csrf", __name__, url_prefix="/auth")


@csrf_bp.route("/csrf-token", methods=["GET"])
def get_csrf_token():
    """Issue CSRF token for SPA/AJAX applications."""
    s = get_settings()
    try:
        token = generate_csrf()
        expires_at = datetime.utcnow() + timedelta(seconds=s.csrf_time_limit_seconds)
        resp = make_response(
            jsonify(
                {
                    "csrfToken": token,
                    "expiresAt": expires_at.isoformat() + "Z",
                    "headerName": s.csrf_header_name,
                }
            )
        )
        resp.set_cookie(
            key=s.csrf_cookie_name,
            value=token,
            max_age=s.csrf_time_limit_seconds,
            secure=s.session_cookie_secure,
            httponly=False,
            samesite=s.session_cookie_samesite,
            path="/",
        )
        if redis_client:
            client_ip = get_remote_address()
            redis_client.incr(f"csrf_tokens_issued:{client_ip}")
            redis_client.expire(f"csrf_tokens_issued:{client_ip}", 3600)
        logger.info("CSRF token issued for client %s", get_remote_address())
        return resp
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to generate CSRF token: %s", exc)
        return {"error": "csrf_generation_failed"}, 500


@csrf_bp.route("/csrf-validate", methods=["POST"])
def validate_csrf_token():
    """Validate CSRF token (for testing purposes)."""
    return {
        "valid": True,
        "message": "CSRF token is valid",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


if limiter:
    limiter.limit("100/minute")(get_csrf_token)
