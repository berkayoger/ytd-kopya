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
    include_inactive_param = request.args.get("include_inactive", "true").lower()
    include_inactive = include_inactive_param != "false"
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        if page < 1 or per_page < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "page and per_page must be positive integers"}), 400
    try:
        start_date = datetime.fromisoformat(start) if start else None
        end_date = datetime.fromisoformat(end) if end else None
    except Exception:
        return jsonify({"error": "Tarih formatı geçersiz (YYYY-MM-DD)"}), 400

    q = PromoCodeUsage.query.join(PromoCode, PromoCode.id == PromoCodeUsage.promo_code_id)
    if start_date:
        q = q.filter(PromoCodeUsage.used_at >= start_date)
    if end_date:
        q = q.filter(PromoCodeUsage.used_at <= end_date)
    if not include_inactive:
        q = q.filter(PromoCode.is_active.is_(True))

    stats_query = (
        q.with_entities(PromoCode.code, func.count(PromoCodeUsage.id).label("count"))
        .group_by(PromoCode.code)
        .order_by(func.count(PromoCodeUsage.id).desc())
    )

    total = stats_query.count()
    stats = stats_query.offset((page - 1) * per_page).limit(per_page).all()

    result = [
        {"code": code, "count": count}
        for code, count in stats
    ]
    return jsonify({"total": total, "page": page, "per_page": per_page, "items": result})
