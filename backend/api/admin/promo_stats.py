from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.auth.middlewares import admin_required
from backend.db.models import PromoCodeUsage, PromoCode
from sqlalchemy import func
from datetime import datetime

stats_bp = Blueprint("promo_stats", __name__)

@stats_bp.route("/api/admin/promo-codes/stats", methods=["GET"])
@jwt_required()
@admin_required()
def promo_usage_stats():
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    try:
        start_date = datetime.fromisoformat(start) if start else None
        end_date = datetime.fromisoformat(end) if end else None
    except Exception:
        return jsonify({"error": "Tarih formatı geçersiz (YYYY-MM-DD)"}), 400

    q = PromoCodeUsage.query
    if start_date:
        q = q.filter(PromoCodeUsage.used_at >= start_date)
    if end_date:
        q = q.filter(PromoCodeUsage.used_at <= end_date)

    stats = (
        q.join(PromoCode, PromoCode.id == PromoCodeUsage.promo_code_id)
        .with_entities(PromoCode.code, func.count(PromoCodeUsage.id))
        .group_by(PromoCode.code)
        .order_by(func.count(PromoCodeUsage.id).desc())
        .all()
    )

    result = [
        {"code": code, "count": count}
        for code, count in stats
    ]
    return jsonify(result)
