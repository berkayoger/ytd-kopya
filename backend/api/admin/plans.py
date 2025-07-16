from flask import Blueprint, request, jsonify
from backend.db import db
from backend.models.plan import Plan
from backend.db.models import User
from backend.utils.decorators import admin_required
import json
from datetime import datetime

plan_admin_bp = Blueprint("plan_admin_bp", __name__)

@plan_admin_bp.route("/admin/plans", methods=["GET"])
@admin_required
def list_plans():
    plans = Plan.query.all()
    return jsonify([p.to_dict() for p in plans])

@plan_admin_bp.route("/admin/plans", methods=["POST"])
@admin_required
def create_plan():
    data = request.get_json() or {}
    features = data.get("features", {})
    plan = Plan(
        name=data["name"],
        price=data["price"],
        features=json.dumps(features),
        is_active=data.get("is_active", True),
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify(plan.to_dict()), 201

@plan_admin_bp.route("/admin/plans/<int:plan_id>", methods=["PUT"])
@admin_required
def update_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    data = request.get_json() or {}
    plan.name = data.get("name", plan.name)
    plan.price = data.get("price", plan.price)
    plan.is_active = data.get("is_active", plan.is_active)
    if "features" in data:
        plan.features = json.dumps(data["features"])
    db.session.commit()
    return jsonify(plan.to_dict())

@plan_admin_bp.route("/admin/plans/<int:plan_id>", methods=["DELETE"])
@admin_required
def delete_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"message": "Plan silindi"})

@plan_admin_bp.route("/admin/users/<int:user_id>/plan", methods=["PUT"])
@admin_required
def change_user_plan(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    plan_id = data.get("plan_id")
    plan = Plan.query.get_or_404(plan_id)
    user.plan_id = plan.id
    if "expire_at" in data:
        user.plan_expire_at = datetime.fromisoformat(data["expire_at"])
    db.session.commit()
    return jsonify(user.to_dict())
