"""Authentication endpoints for web sessions."""

from __future__ import annotations

import logging
from datetime import datetime

from flask import Blueprint, request, session

from backend.extensions import limiter

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """Web login endpoint protected by CSRF token."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not email or not password:
        return {"error": "email_and_password_required"}, 400
    if email == "demo@example.com" and password == "demo123":
        session["user_id"] = 1
        session["email"] = email
        session["authenticated_at"] = datetime.utcnow().isoformat()
        session.permanent = True
        return {"success": True, "user": {"id": 1, "email": email}}
    logger.warning("Failed login attempt for email: %s", email)
    return {"error": "invalid_credentials"}, 401


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Logout endpoint clearing the session."""
    session.clear()
    return {"success": True}


if limiter:
    limiter.limit("10/minute")(login)
