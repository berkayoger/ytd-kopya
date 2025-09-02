import os
import re
from typing import List

from flask import Blueprint, current_app, jsonify, request

from ..core.security import (PasswordPolicy, create_access_token,
                             create_email_token, create_refresh_token,
                             decode_token, generate_totp_secret,
                             get_password_hash, get_totp_uri, is_locked,
                             record_failed_login, reset_login_failures,
                             rotate_refresh_token,
                             validate_and_normalize_email, verify_password,
                             verify_totp)
from ..models.db import User, db

bp = Blueprint("authx", __name__)


def _json():
    try:
        return request.get_json(force=True) or {}
    except Exception:
        return {}


def _need(fields, data):
    missing = [f for f in fields if f not in data]
    return ", ".join(missing) if missing else None


def _send_email(to, subject, body):
    current_app.logger.info("[EMAIL] to=%s subject=%s body=%s", to, subject, body)


def validate_password(password: str) -> List[str]:
    """Şifre için temel güvenlik kontrolleri"""
    errors: List[str] = []
    if len(password) < 12:
        errors.append("Password must be at least 12 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain lowercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("Password must contain number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain special character")
    common = ["password", "123456", "qwerty", "admin"]
    if any(c in password.lower() for c in common):
        errors.append("Password is too common")
    return errors


@bp.post("/register")
def register():
    data = _json()
    miss = _need(["email", "password", "accept_tos"], data)
    if miss:
        return jsonify({"detail": f"Missing: {miss}"}), 422
    email = validate_and_normalize_email(data["email"])
    password_errors = validate_password(data.get("password", ""))
    ok, msg = PasswordPolicy.validate(data["password"])
    if not ok:
        password_errors.append(msg)
    if password_errors:
        return jsonify({"errors": password_errors}), 422
    if not data.get("accept_tos"):
        return jsonify({"detail": "Terms must be accepted"}), 422
    if User.query.filter_by(email=email).first():
        return jsonify({"detail": "Email already registered"}), 409
    user = User(
        email=email,
        password_hash=get_password_hash(data["password"]),
        email_verified=False,
    )
    db.session.add(user)
    db.session.commit()
    token = create_email_token(subject=user.id, expires_minutes=60 * 24)
    verify_url = f"{os.getenv('SITE_URL','').rstrip('/')}/api/auth/verify?token={token}"
    _send_email(email, "Verify your email", f"Click to verify: {verify_url}")
    return jsonify({"status": "ok"}), 201


@bp.get("/verify")
def verify():
    token = request.args.get("token")
    if not token:
        return jsonify({"detail": "missing token"}), 422
    try:
        # Token mutlaka e-posta doğrulama niyetinde olmalı
        p = decode_token(token)
        token_type = (p.get("type") or "").lower()
        token_hint = (p.get("t") or "").lower()
        if token_type != "email" and token_hint != "email":
            return jsonify({"detail": "invalid token"}), 401
        uid = p["sub"]
    except Exception:
        return jsonify({"detail": "invalid token"}), 401
    user = User.query.get(uid)
    if not user:
        return jsonify({"detail": "user not found"}), 404
    if not user.email_verified:
        user.email_verified = True
        db.session.commit()
    return (
        jsonify(
            {
                "access": create_access_token(subject=user.id),
                "refresh": create_refresh_token(subject=user.id),
            }
        ),
        200,
    )


@bp.post("/login")
def login():
    data = _json()
    miss = _need(["email", "password"], data)
    if miss:
        return jsonify({"detail": f"Missing: {miss}"}), 422
    email = validate_and_normalize_email(data["email"])
    ident = email
    if is_locked(ident):
        return jsonify({"detail": "Account temporarily locked"}), 429
    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(data["password"], user.password_hash):
        cnt = record_failed_login(ident)
        return jsonify({"detail": "Invalid credentials", "attempts": cnt}), 401
    if user.totp_secret:
        if not data.get("totp_code") or not verify_totp(
            data["totp_code"], user.totp_secret
        ):
            return jsonify({"detail": "TOTP required/invalid"}), 401
    reset_login_failures(ident)
    return (
        jsonify(
            {
                "access": create_access_token(subject=user.id),
                "refresh": create_refresh_token(subject=user.id),
            }
        ),
        200,
    )


@bp.post("/refresh")
def refresh():
    data = _json()
    if "refresh" not in data:
        return jsonify({"detail": "Missing: refresh"}), 422
    try:
        new_r = rotate_refresh_token(data["refresh"])
        p = decode_token(new_r, require_type="refresh")
        return (
            jsonify(
                {"access": create_access_token(subject=p["sub"]), "refresh": new_r}
            ),
            200,
        )
    except Exception:
        return jsonify({"detail": "invalid refresh"}), 401


@bp.post("/logout")
def logout():
    from ..core.security import revoke_token

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            p = decode_token(auth.split(" ", 1)[1])
            revoke_token(p["jti"], p["exp"])
        except Exception:
            pass
    data = _json()
    if data.get("refresh"):
        try:
            p = decode_token(data["refresh"], require_type="refresh")
            revoke_token(p["jti"], p["exp"])
        except Exception:
            pass
    return jsonify({"status": "ok"}), 200


@bp.post("/totp/setup")
def totp_setup():
    data = _json()
    if "access" not in data:
        return jsonify({"detail": "Missing: access"}), 422
    try:
        p = decode_token(data["access"], require_type="access")
    except Exception:
        return jsonify({"detail": "invalid token"}), 401
    user = User.query.get(p["sub"])
    if not user:
        return jsonify({"detail": "user not found"}), 404
    if user.totp_secret:
        return jsonify({"detail": "already enabled"}), 409
    secret = generate_totp_secret()
    user.totp_secret = secret
    db.session.commit()
    uri = get_totp_uri(user.email, secret)
    return jsonify({"otpauth_uri": uri}), 200
