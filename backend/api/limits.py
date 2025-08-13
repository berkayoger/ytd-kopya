from flask import Blueprint, jsonify, g, request
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
import os
import json

from backend.middleware.plan_limits import enforce_plan_limit
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log
from backend.services.limit_service import get_user_limits
from backend.db.models import User  # custom_features alanı için

# Limit sorgu uç noktası için blueprint
bp = Blueprint("limits", __name__, url_prefix="/api/limits")


@bp.route("/status", methods=["GET"])
@jwt_required()
@enforce_plan_limit("api_request_daily")
def get_limits_status():
    """Kullanıcının planı ve limit durumunu döndürür."""

    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 401

    if not feature_flag_enabled("limits_status"):
        # Özellik kapalıysa logla ve erişimi engelle
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="limit_status_denied",
            target="/api/limits/status",
            description="limits_status özelliği kapalı.",
            status="forbidden",
            user_agent=request.headers.get("User-Agent", ""),
        )
        return jsonify({"error": "Özellik kapalı."}), 403

    try:
        limits_data = get_user_limits(user.id)
        # Kullanıcıya tanımlı özel özellikleri ekle
        user_obj = User.query.get(user.id)
        if user_obj and getattr(user_obj, "custom_features", None):
            try:
                features = (
                    json.loads(user_obj.custom_features)
                    if isinstance(user_obj.custom_features, str)
                    else user_obj.custom_features
                )
            except json.JSONDecodeError:
                features = {}
            limits_data["custom_features"] = features or {}
        else:
            limits_data["custom_features"] = {}
    except Exception as exc:  # pragma: no cover
        # Hata durumunu logla
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="limit_status_error",
            target="/api/limits/status",
            description=str(exc),
            status="error",
            user_agent=request.headers.get("User-Agent", ""),
        )
        return jsonify({"error": "Limitler alınamadı."}), 500

    # Limitlerin resetleneceği zamanı hesapla (yapılandırılabilir)
    def _next_monthly_reset(now_utc: datetime, day: int) -> datetime:
        """Ayın verilen günündeki (1-28) bir sonraki reset tarihini döndürür."""
        day = max(1, min(28, int(day)))
        try:
            candidate = datetime(now_utc.year, now_utc.month, day)
        except ValueError:
            candidate = datetime(now_utc.year, now_utc.month, 1)
        if candidate <= now_utc:
            if now_utc.month == 12:
                return datetime(now_utc.year + 1, 1, day)
            return datetime(now_utc.year, now_utc.month + 1, day)
        return candidate

    now = datetime.utcnow()
    reset_day_env = os.getenv("LIMITS_RESET_DAY", "1").strip()
    try:
        reset_day = int(reset_day_env)
    except ValueError:
        reset_day = 1
    reset_at = _next_monthly_reset(now, reset_day)
    limits_data["reset_at"] = reset_at.isoformat()

    # Kullanım yüzdelerini hesapla
    for key, val in limits_data.get("limits", {}).items():
        max_val = val.get("max", 0)
        used_val = val.get("used", 0)
        val["percent"] = round((used_val / max_val) * 100, 2) if max_val > 0 else 0

    create_log(
        user_id=str(user.id),
        username=user.username,
        ip_address=request.remote_addr or "unknown",
        action="limit_status",
        target="/api/limits/status",
        description="Kullanıcı limit durumu sorgulandı.",
        status="success",
        user_agent=request.headers.get("User-Agent", ""),
    )

    return jsonify(limits_data), 200
