"""Kullanıcı limit servisleri."""

from datetime import datetime

from sqlalchemy import func

from backend import db
from backend.db.models import UsageLog, User


def get_user_limits(user_id: int) -> dict:
    """Belirli bir kullanıcının plan ve limit bilgilerini döndür."""

    user: User | None = User.query.get(user_id)
    if not user or not user.plan:
        return {"plan": None, "limits": {}}

    plan_name = user.plan.name
    features = user.plan.features_dict()

    daily_max = features.get("api_request_daily", 0)
    monthly_max = features.get("api_request_monthly", 0)

    now = datetime.utcnow()
    start_of_day = datetime(now.year, now.month, now.day)
    start_of_month = datetime(now.year, now.month, 1)

    daily_used = (
        db.session.query(func.count(UsageLog.id))
        .filter(
            UsageLog.user_id == user_id,
            UsageLog.action == "api_request",
            UsageLog.timestamp >= start_of_day,
        )
        .scalar()
    )

    monthly_used = (
        db.session.query(func.count(UsageLog.id))
        .filter(
            UsageLog.user_id == user_id,
            UsageLog.action == "api_request",
            UsageLog.timestamp >= start_of_month,
        )
        .scalar()
    )

    return {
        "plan": plan_name,
        "limits": {
            "daily_requests": {"used": daily_used, "max": daily_max},
            "monthly_requests": {"used": monthly_used, "max": monthly_max},
        },
    }
