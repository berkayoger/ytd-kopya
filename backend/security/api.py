"""API endpoints for mobile/SDK clients (token-based auth)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from flask import Blueprint, request
from flask_jwt_extended import create_access_token

from backend.extensions import csrf, limiter
from backend.settings import get_settings

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

if csrf:
    csrf.exempt(api_bp)


@api_bp.route("/ping", methods=["GET"])
def api_ping():
    """Health check for API endpoints."""
    return {
        "ok": True,
        "service": "ytd-kopya-api",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    """Mobile/SDK login endpoint returning JWT tokens."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not email or not password:
        return {"error": "email_and_password_required"}, 400
    if email == "demo@example.com" and password == "demo123":
        s = get_settings()
        access_token = create_access_token(
            identity={"user_id": 1, "email": email},
            expires_delta=timedelta(hours=s.jwt_access_token_expires_hours),
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": s.jwt_access_token_expires_hours * 3600,
            "user": {"id": 1, "email": email},
        }
    logger.warning("Failed API login attempt for email: %s", email)
    return {"error": "invalid_credentials"}, 401


if limiter:
    limiter.limit("10/minute")(api_login)
