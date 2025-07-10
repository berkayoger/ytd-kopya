from flask import Blueprint, request, jsonify
from backend.models.plan import Plan
from backend.db import db

plan_bp = Blueprint("plan_bp", __name__)

@plan_bp.route("/plans", methods=["GET"])
def get_plans():
    plans = Plan.query.all()
    return jsonify([p.to_dict() for p in plans])

@plan_bp.route("/plans", methods=["POST"])
def create_plan():
    data = request.get_json()
    new_plan = Plan(
        name=data["name"],
        price=data["price"],
        features=data.get("features", ""),
    )
    db.session.add(new_plan)
    db.session.commit()
    return jsonify(new_plan.to_dict()), 201

@plan_bp.route("/plans/<int:plan_id>", methods=["PUT"])
def update_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    data = request.get_json()
    plan.name = data.get("name", plan.name)
    plan.price = data.get("price", plan.price)
    plan.features = data.get("features", plan.features)
    plan.is_active = data.get("is_active", plan.is_active)
    db.session.commit()
    return jsonify(plan.to_dict())

@plan_bp.route("/plans/<int:plan_id>", methods=["DELETE"])
def delete_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"message": "Plan silindi"})
