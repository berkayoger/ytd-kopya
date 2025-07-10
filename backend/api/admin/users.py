from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from backend.auth.middlewares import admin_required
from backend.db import db
from backend.db.models import User, SubscriptionPlan, UserRole


user_admin_bp = Blueprint("user_admin", __name__, url_prefix="/api/admin/users")


@user_admin_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required()
def list_users():
    email = request.args.get("email")
    role = request.args.get("role")
    plan = request.args.get("subscription_level")

    query = User.query

    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if role:
        query = query.filter(User.role == role)
    if plan:
        query = query.filter(User.subscription_level == plan)

    users = query.all()
    return jsonify([u.to_dict() for u in users])


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
