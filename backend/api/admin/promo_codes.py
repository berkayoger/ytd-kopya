from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.auth.middlewares import admin_required
from backend.db.models import db, PromoCode
from datetime import datetime, timedelta

admin_promo_bp = Blueprint("admin_promo", __name__, url_prefix="/api/admin/promo-codes")


@admin_promo_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required()
def list_promo_codes():
    codes = PromoCode.query.order_by(PromoCode.created_at.desc()).all()
    return jsonify([c.to_dict() for c in codes]), 200


@admin_promo_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required()
def create_promo_code():
    data = request.get_json() or {}
    try:
        code = PromoCode(
            code=data["code"].upper(),
            plan=data["plan"].upper(),
            duration_days=int(data["duration_days"]),
            max_uses=int(data["max_uses"]),
            expires_at=datetime.utcnow() + timedelta(days=int(data.get("expires_in_days", 30))),
            created_by="admin"
        )
        db.session.add(code)
        db.session.commit()
        return jsonify(code.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@admin_promo_bp.route("/<int:promo_id>", methods=["DELETE"])
@jwt_required()
@admin_required()
def delete_promo_code(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    db.session.delete(promo)
    db.session.commit()
    return jsonify({"message": "Silindi"}), 200


@admin_promo_bp.route("/<int:promo_id>", methods=["PATCH"])
@jwt_required()
@admin_required()
def update_promo_code(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    data = request.get_json() or {}
    try:
        if "max_uses" in data:
            promo.max_uses = int(data["max_uses"])
        if "duration_days" in data:
            promo.duration_days = int(data["duration_days"])
        if "is_active" in data:
            promo.is_active = bool(data["is_active"])
        db.session.commit()
        return jsonify(promo.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@admin_promo_bp.route("/<int:promo_id>/expiration", methods=["PATCH"])
@jwt_required()
@admin_required()
def update_promo_expiration(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    data = request.get_json() or {}
    expires_at_str = data.get("expires_at")
    if not expires_at_str:
        return jsonify({"error": "expires_at field is required"}), 400
    try:
        new_date = datetime.fromisoformat(expires_at_str)
    except ValueError:
        return jsonify({"error": "Invalid ISO date"}), 400
    if new_date <= datetime.utcnow():
        return jsonify({"error": "Expiration must be in the future"}), 400
    try:
        promo.expires_at = new_date
        db.session.commit()
        return jsonify(promo.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

