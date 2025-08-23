# backend/utils/plan_limits.py
from __future__ import annotations

from typing import Dict, Optional, Callable, Any
from flask import g, jsonify, request
from datetime import datetime, timedelta
import json

# Mevcut modellerle uyumlu kalmak adına yalnızca User'ı zorunlu alıyoruz.
from backend.db.models import User, UsageLog, db


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


def _user_for(user_id: Optional[str]) -> Optional[User]:
    if user_id:
        try:
            return User.query.get(user_id)
        except Exception:
            return None
    if hasattr(g, "user") and isinstance(getattr(g, "user", None), User):
        return g.user  # type: ignore[return-value]
    return None

# -----------------------------------------------------------------------------
# Back-compat: eski testler için beklenen anahtarlar
# -----------------------------------------------------------------------------
# Eski testler 'predict_daily' ve 'api_request_daily' anahtarlarını bekliyor.
PLAN_LIMITS_COMPAT: Dict[str, Dict[str, int]] = {
    "basic": {"predict_daily": 10, "api_request_daily": 100},
    "premium": {"predict_daily": 100, "api_request_daily": 1000},
    # advanced testlerde kullanılmıyorsa boş bırakılabilir; ihtiyaç olursa eklenir
}


def _get_effective_feature_limits(user_id: Optional[str], feature_key: str) -> Dict[str, int]:
    """Yeni sürüm: tek bir feature için efektif limitleri döndürür."""

    # Öncelik: (1) PlanLimit (varsa) → (2) UserLimitOverride (varsa && süresi geçmemişse)
    #          → (3) PLAN_DEFAULTS.
    # Model tabloları projede yoksa sessizce defaultlara düşer.
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


# -----------------------------------------------------------------------------
# Unified public API (back-compat friendly)
# -----------------------------------------------------------------------------
def get_user_effective_limits(arg1: Any = None, feature_key: Optional[str] = None) -> Dict:
    """
    Back-compat çok biçimli fonksiyon.
    - Eski kullanım: get_user_effective_limits(user) -> dict (predict_daily/api_request_daily)
    - Yeni kullanım: get_user_effective_limits(user_id, feature_key) -> dict (daily_quota/burst_per_minute)
    """
    # Yeni tarz: (user_id, feature_key)
    if feature_key is not None:
        user_id = str(arg1) if arg1 is not None else None
        return _get_effective_feature_limits(user_id=user_id, feature_key=feature_key)

    # Eski tarz: (user)
    user = arg1
    limits: Dict[str, int] = {}
    try:
        plan_features = json.loads(getattr(getattr(user, "plan", None), "features", "{}") or "{}")
        limits.update(plan_features)
    except Exception:
        pass

    # Geçerli boost'lar planı ezer
    try:
        if getattr(user, "boost_expire_at", None) and getattr(user, "boost_expire_at") > datetime.utcnow():
            boost = json.loads(getattr(user, "boost_features", "{}") or "{}")
            limits.update(boost)
    except Exception:
        pass

    # Custom feature'lar en yüksek öncelik
    try:
        custom = json.loads(getattr(user, "custom_features", "{}") or "{}")
        limits.update({k: v for k, v in custom.items() if isinstance(v, int)})
    except Exception:
        pass

    if limits:
        return limits

    # Hiçbiri yoksa eski sözlüğe düş
    plan = None
    try:
        plan = (
            getattr(user, "subscription_level", None)
            or getattr(getattr(user, "plan", None), "name", None)
        )
    except Exception:
        plan = None
    plan_key = str(plan or "basic").lower()
    return PLAN_LIMITS_COMPAT.get(plan_key, PLAN_LIMITS_COMPAT["basic"]).copy()


def give_user_boost(user: User, features: Dict[str, int], expires_at: datetime) -> None:
    """Kullanıcıya geçici feature boost'u ver."""
    user.boost_features = json.dumps(features)
    user.boost_expire_at = expires_at
    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()


def check_custom_feature(user: User, feature: str) -> bool:
    """Kullanıcının custom bir feature'a sahip olup olmadığını kontrol et."""
    try:
        data = json.loads(getattr(user, "custom_features", "{}") or "{}")
        return bool(data.get(feature))
    except Exception:
        return False


# -----------------------------------------------------------------------------
# Back-compat: enforce_plan_limits dekoratörü (eski testler için)
# -----------------------------------------------------------------------------
def enforce_plan_limits(limit_key: str) -> Callable:
    """Eski testler için limitleri uygular."""

    def decorator(fn: Callable) -> Callable:
        def inner(*args, **kwargs):
            # Kullanıcıyı çöz
            user = getattr(g, "user", None)
            if user is None:
                api_key = request.headers.get("X-API-KEY")
                if api_key:
                    try:
                        u = User.query.filter_by(api_key=api_key).first()
                        if u:
                            g.user = u
                            user = u
                    except Exception:
                        pass
            if user is None:
                return jsonify({"error": "Auth required"}), 401

            plan = None
            try:
                plan = (
                    getattr(user, "subscription_level", None)
                    or getattr(getattr(user, "plan", None), "name", None)
                )
            except Exception:
                plan = None
            plan_key = str(plan or "basic").lower()
            limits = PLAN_LIMITS_COMPAT.get(plan_key, PLAN_LIMITS_COMPAT["basic"])
            limit = limits.get(limit_key)
            if limit is None:
                return fn(*args, **kwargs)

            since = datetime.utcnow() - timedelta(days=1)
            usage_count = (
                UsageLog.query.filter_by(user_id=user.id, action=limit_key)
                .filter(UsageLog.timestamp > since)
                .count()
            )
            if usage_count >= int(limit):
                return jsonify({"error": "PlanLimitExceeded"}), 429

            try:
                db.session.add(
                    UsageLog(user_id=user.id, action=limit_key, timestamp=datetime.utcnow())
                )
                db.session.commit()
            except Exception:
                db.session.rollback()
            return fn(*args, **kwargs)

        return inner

    return decorator
