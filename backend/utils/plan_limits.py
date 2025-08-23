# backend/utils/plan_limits.py
from __future__ import annotations

from typing import Dict, Optional
from flask import g, request
from datetime import datetime, timedelta

# Mevcut modellerle uyumlu kalmak adına yalnızca User'ı zorunlu alıyoruz.
from backend.db.models import User

try:
    # Ek modeller isteğe bağlı, test ortamında yoksa hata vermesin
    from backend.db.models import db, SubscriptionPlan, UsageLimitLog
except Exception:  # pragma: no cover
    db = None  # type: ignore
    SubscriptionPlan = UsageLimitLog = None  # type: ignore


# DB tanımı yoksa çalışacak güvenli defaultlar (plan -> feature -> (daily, burst))
PLAN_DEFAULTS: Dict[str, Dict[str, tuple[int, int]]] = {
    "BASIC": {
        "global_api": (60, 60),
        "coin_analysis": (50, 10),
        "prediction": (20, 5),
        "market_data": (100, 30),
    },
    "ADVANCED": {
        "global_api": (500, 120),
        "coin_analysis": (200, 30),
        "prediction": (100, 20),
        "market_data": (1000, 60),
    },
    "PREMIUM": {
        "global_api": (2000, 300),
        "coin_analysis": (1000, 100),
        "prediction": (500, 50),
        "market_data": (5000, 150),
    },
}

# Plan bazlı rate limitleri (Flask-Limiter formatında)
PLAN_RATE_MAP = {
    "free": "60 per hour",
    "basic": "1000 per hour",
    "premium": "5000 per hour",
    "enterprise": "20000 per hour",
}


def _user_for(user_id: Optional[str]) -> Optional[User]:
    if user_id:
        try:
            return User.query.get(user_id)
        except Exception:
            return None
    if hasattr(g, "user") and isinstance(getattr(g, "user", None), User):
        return g.user  # type: ignore[return-value]
    return None


def get_user_effective_limits(user_id: Optional[str], feature_key: str) -> Dict[str, int]:
    """Kullanıcının efektif limitleri.

    Öncelik: (1) PlanLimit (varsa) → (2) UserLimitOverride (varsa && süresi geçmemişse)
             → (3) PLAN_DEFAULTS.
    Model tabloları projede yoksa sessizce defaultlara düşer.
    """
    user = _user_for(user_id)
    plan_name = (getattr(user, "subscription_level", None) or "BASIC").upper()

    # Başlangıç değerleri: defaultlar
    default_daily, default_burst = PLAN_DEFAULTS.get(plan_name, {}).get(feature_key, (0, 0))
    daily_quota, burst_per_minute = default_daily, default_burst

    # Opsiyonel: PlanLimit
    try:
        from backend.db.models import PlanLimit  # type: ignore
        row = (
            PlanLimit.query.filter_by(plan_name=plan_name, feature_key=feature_key)
            .first()
        )
        if row:
            daily_quota = int(row.daily_quota or daily_quota)
            burst_per_minute = int(row.burst_per_minute or burst_per_minute)
    except Exception:
        pass

    # Opsiyonel: UserLimitOverride
    try:
        from backend.db.models import UserLimitOverride  # type: ignore
        if user is not None:
            ov = (
                UserLimitOverride.query.filter_by(
                    user_id=str(user.id), feature_key=feature_key
                ).first()
            )
            if ov and (ov.expires_at is None or ov.expires_at > datetime.utcnow()):
                if ov.daily_quota_override is not None:
                    daily_quota = int(ov.daily_quota_override)
                if ov.burst_per_minute_override is not None:
                    burst_per_minute = int(ov.burst_per_minute_override)
    except Exception:
        pass

    return {
        "plan_name": plan_name,
        "feature_key": feature_key,
        "daily_quota": max(0, int(daily_quota)),
        "burst_per_minute": max(0, int(burst_per_minute)),
    }


def get_all_feature_keys() -> list[str]:
    """UI için bilinen feature anahtarları."""
    keys = set()
    for d in PLAN_DEFAULTS.values():
        keys.update(d.keys())
    # PlanLimit varsa DB'den de toplayalım (mevcutsa)
    try:
        from backend.db.models import PlanLimit  # type: ignore
        for (fk,) in PlanLimit.query.with_entities(PlanLimit.feature_key).distinct().all():
            keys.add(fk)
    except Exception:
        pass
    return sorted(keys)


def _get_current_user() -> Optional[User]:
    """Request bağlamından kullanıcıyı döndürür."""
    user = getattr(g, "current_user", None)
    if user is not None:
        return user
    return getattr(g, "user", None)


def get_plan_rate_limit(user: Optional[User] = None) -> str:
    """Kullanıcının planına göre rate limit string'i."""
    if user is None:
        user = _get_current_user()
    if not user:
        return "30 per hour"

    plan_name = None
    try:
        if getattr(user, "plan", None) and getattr(user.plan, "name", None):
            plan_name = user.plan.name
        else:
            role = getattr(user, "role", "") or ""
            if "premium" in role:
                plan_name = "premium"
            elif "basic" in role:
                plan_name = "basic"
            elif "enterprise" in role or "admin" in role:
                plan_name = "enterprise"
            else:
                plan_name = "free"
    except Exception:
        plan_name = "free"

    return PLAN_RATE_MAP.get(plan_name, PLAN_RATE_MAP["free"])


def rate_limit_key_func() -> str:
    """Flask-Limiter için rate limit anahtarı."""
    user = _get_current_user()
    if user and getattr(user, "id", None):
        return f"user:{user.id}"
    return request.headers.get("X-Real-IP") or request.remote_addr or "anon"


def check_and_increment_usage(user: User, limit_type: str, amount: int = 1) -> bool:
    """Plan limitini kontrol eder ve kullanım sayacını artırır."""
    if not user or not getattr(user, "check_plan_limit", None):
        return True

    allowed = user.check_plan_limit(limit_type)
    if not allowed:
        try:
            if UsageLimitLog and db:
                current, limit = _get_current_and_limit(user, limit_type)
                log = UsageLimitLog(
                    user_id=user.id,
                    limit_type=limit_type,
                    attempted_amount=amount,
                    current_usage=current,
                    plan_limit=limit,
                    blocked=True,
                    ip_address=(request.remote_addr if request else None),
                    user_agent=(request.headers.get("User-Agent") if request else None),
                )
                db.session.add(log)
                db.session.commit()
        finally:
            return False

    if getattr(user, "increment_usage", None):
        user.increment_usage(limit_type, amount)
    return True


def check_custom_feature(user: User, feature_name: str) -> bool:
    """Plan özellikleri içinde verilen anahtar var mı kontrol et."""
    if not user or not getattr(user, "plan", None):
        return False
    features = getattr(user.plan, "features", None)
    try:
        if isinstance(features, dict):
            return bool(features.get(feature_name))
        if isinstance(features, list):
            return feature_name in features
    except Exception:
        pass
    return False


def _get_current_and_limit(user: User, limit_type: str) -> tuple[int, int]:
    current = 0
    limit = 0
    if limit_type == "api_calls":
        current = getattr(user, "monthly_api_calls", 0) or 0
        limit = getattr(getattr(user, "plan", None), "max_api_calls_per_month", 0) or 0
    elif limit_type == "predictions":
        current = getattr(user, "monthly_predictions", 0) or 0
        limit = getattr(getattr(user, "plan", None), "max_predictions_per_month", 0) or 0
    elif limit_type == "storage":
        current = getattr(user, "storage_used", 0) or 0
        limit = getattr(getattr(user, "plan", None), "max_storage_mb", 0) or 0
    return current, limit


def give_user_boost(user_or_id, limit_type: str = "api_calls", extra: int = 100, duration_minutes: int = 60) -> bool:
    """Kullanıcıya geçici kullanım hakkı verir (testler için)."""
    if User is None or db is None:
        return False

    if isinstance(user_or_id, User):
        user = user_or_id
    else:
        user = User.query.get(int(user_or_id))
    if not user:
        return False

    extra = max(0, int(extra))
    if limit_type == "api_calls":
        user.monthly_api_calls = max(0, (user.monthly_api_calls or 0) - extra)
    elif limit_type == "predictions":
        user.monthly_predictions = max(0, (user.monthly_predictions or 0) - extra)
    elif limit_type == "storage":
        user.storage_used = max(0, (user.storage_used or 0) - extra)
    else:
        return False

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return False

    return True


__all__ = [
    "get_user_effective_limits",
    "get_all_feature_keys",
    "get_plan_rate_limit",
    "rate_limit_key_func",
    "check_and_increment_usage",
    "check_custom_feature",
    "give_user_boost",
]
