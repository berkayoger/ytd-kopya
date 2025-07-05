from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.auth.middlewares import admin_required
from backend.db import db
from backend.db.models import PredictionOpportunity
from datetime import datetime

predictions_bp = Blueprint("predictions", __name__, url_prefix="/api/admin/predictions")


@predictions_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required()
def list_predictions():
    predictions = PredictionOpportunity.query.order_by(PredictionOpportunity.created_at.desc()).all()
    return jsonify([p.to_dict() for p in predictions])


@predictions_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required()
def create_prediction():
    data = request.get_json() or {}
    try:
        pred = PredictionOpportunity(
            symbol=data["symbol"].upper(),
            current_price=float(data["current_price"]),
            target_price=float(data["target_price"]),
            forecast_horizon=data.get("forecast_horizon"),
            expected_gain_pct=float(data["expected_gain_pct"]),
            confidence_score=float(data.get("confidence_score", 0.0)),
            trend_type=data.get("trend_type", "short_term"),
            source_model=data.get("source_model", "AIModel"),
            is_active=bool(data.get("is_active", True)),
            created_at=datetime.utcnow()
        )
        db.session.add(pred)
        db.session.commit()
        return jsonify(pred.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@predictions_bp.route("/<int:prediction_id>", methods=["PATCH"])
@jwt_required()
@admin_required()
def update_prediction(prediction_id):
    data = request.get_json() or {}
    pred = PredictionOpportunity.query.get_or_404(prediction_id)
    try:
        for field in ["symbol", "current_price", "target_price", "forecast_horizon",
                      "expected_gain_pct", "confidence_score", "trend_type", "source_model", "is_active"]:
            if field in data:
                if field in ["current_price", "target_price", "expected_gain_pct", "confidence_score"]:
                    setattr(pred, field, float(data[field]))
                else:
                    setattr(pred, field, data[field])
        db.session.commit()
        return jsonify(pred.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@predictions_bp.route("/<int:prediction_id>", methods=["DELETE"])
@jwt_required()
@admin_required()
def delete_prediction(prediction_id):
    pred = PredictionOpportunity.query.get_or_404(prediction_id)
    db.session.delete(pred)
    db.session.commit()
    return jsonify({"message": "Silindi"}), 200
