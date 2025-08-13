from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import jwt_required

from backend.auth.middlewares import admin_required
from backend.db import db
from backend.db.models import User, SubscriptionPlan, UserRole
from backend.utils.logger import create_log
from sqlalchemy.exc import SQLAlchemyError
import json
from werkzeug.security import generate_password_hash
import secrets


user_admin_bp = Blueprint("user_admin", __name__, url_prefix="/api/admin/users")


@user_admin_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required()
def list_users():
    """Tüm kullanıcıları (admin) listeler."""
    users = User.query.order_by(User.id.asc()).all()

    def _as_row(u: User) -> dict:
        # subscription_level enum veya string olabilir
        sub = None
        if getattr(u, "subscription_level", None) is not None:
            try:
                sub = (
                    u.subscription_level.name
                    if hasattr(u.subscription_level, "name")
                    else str(u.subscription_level)
                )
            except Exception:
                sub = str(u.subscription_level)
        return {
            "id": u.id,
            "username": u.username,
            "email": getattr(u, "email", None),
            "subscription_level": sub,
        }

    rows = [_as_row(u) for u in users]

    current = getattr(g, "user", None)
    create_log(
        user_id=str(current.id) if current else "unknown",
        username=current.username if current else "unknown",
        ip_address=request.remote_addr or "unknown",
        action="admin_list_users",
        target="/api/admin/users/",
        description="list users",
        status="success",
        user_agent=request.headers.get("User-Agent", ""),
    )

    return jsonify(rows), 200


@user_admin_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required()
def create_user():
    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")
    plan = data.get("subscription_level", "Free")

    if not email or not password:
        return jsonify({"error": "E-posta ve şifre zorunludur"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Bu e-posta zaten kayıtlı"}), 409

    hashed_pw = generate_password_hash(password)
    api_key = secrets.token_hex(32)

    try:
        role_enum = UserRole[role.upper()]
    except KeyError:
        role_enum = UserRole.USER

    try:
        plan_enum = SubscriptionPlan[plan.upper()]
    except KeyError:
        plan_enum = SubscriptionPlan.TRIAL

    user = User(
        username=email,
        email=email,
        password_hash=hashed_pw,
        role=role_enum,
        subscription_level=plan_enum,
        api_key=api_key,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201


@user_admin_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
@admin_required()
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    role = data.get("role")
    if role:
        try:
            user.role = UserRole[role.upper()]
        except KeyError:
            pass

    level = data.get("subscription_level")
    if level:
        try:
            user.subscription_level = SubscriptionPlan[level.upper()]
        except KeyError:
            pass

    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    db.session.commit()
    return jsonify(user.to_dict())


@user_admin_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
@admin_required()
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Kullanıcı silindi"})


@user_admin_bp.route("/<user_id>/custom_features", methods=["GET", "PUT"])
@jwt_required()
def manage_custom_features(user_id):
    """Belirli bir kullanıcının custom_features alanını getirir veya günceller."""
    current_user = getattr(g, "user", None)
    if not current_user or current_user.role != UserRole.ADMIN:
        return jsonify({"error": "Yetkisiz"}), 403

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    user = User.query.get(user_id_int)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    if request.method == "GET":
        try:
            features = (
                json.loads(user.custom_features)
                if isinstance(user.custom_features, str) and user.custom_features
                else user.custom_features or {}
            )
        except json.JSONDecodeError:
            features = {}
        return jsonify({"custom_features": features}), 200

    try:
        data = request.get_json(force=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz veri"}), 400
        user.custom_features = json.dumps(data)
        db.session.commit()
        create_log(
            user_id=str(current_user.id),
            username=current_user.username,
            ip_address=request.remote_addr or "unknown",
            action="admin_update_custom_features",
            target=f"/api/admin/users/{user_id}/custom_features",
            description=f"custom_features updated: {data}",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
        return jsonify({"success": True}), 200
    except (SQLAlchemyError, json.JSONDecodeError) as e:
        return jsonify({"error": str(e)}), 500
