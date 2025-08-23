"""
Plan ve kullanıcı bazlı limit yardımcıları.
Kullanıcının planındaki özelliklerle geçici boost ve özel tanımları
birleştirerek efektif limitleri hesaplar.
"""
from __future__ import annotations

from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import json

from flask import g, jsonify, request


# ---------------------------------------------------------------------------
# DB tanımı yoksa çalışacak güvenli defaultlar (plan -> feature -> (daily, burst))
# ---------------------------------------------------------------------------
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

# ---- Back-compat alias ------------------------------------------------------
# Bazı eski testler/importlar PLAN_LIMITS ismini bekler.
PLAN_LIMITS = PLAN_DEFAULTS

# -----------------------------------------------------------------------------
# Back-compat: eski testler için beklenen anahtarlar
# -----------------------------------------------------------------------------
PLAN_LIMITS_COMPAT: Dict[str, Dict[str, int]] = {
    "basic": {"predict_daily": 10, "api_request_daily": 100},
    "premium": {"predict_daily": 100, "api_request_daily": 1000},
}


def _normalize_plan_name(user) -> str:
    """
    Kullanıcı nesnesinden güvenilir bir plan adı üret.
    String/Enum/Plan objesi -> "BASIC" vb.
    """
    raw = None
    try:
        raw = getattr(user, "subscription_level", None)
        if raw is None:
            raw = getattr(getattr(user, "plan", None), "name", None)
    except Exception:
        raw = None

    if isinstance(raw, str):
        key = raw
    else:
        key = getattr(raw, "name", None) or getattr(raw, "value", None) or (
            str(raw) if raw is not None else ""
        )
    if isinstance(key, str):
        key = key.split(".")[-1]
        return (key or "BASIC").upper()
    return "BASIC"


def _user_for(user_id: Optional[str]):
    # Önce g.user varsa onu döndür
    try:
        if hasattr(g, "user") and getattr(getattr(g, "user", None), "id", None):
            return g.user  # type: ignore[return-value]
    except Exception:
        pass
    if not user_id:
        return None
    try:
        from backend.db.models import User  # local import
        return User.query.get(user_id)
    except Exception:
        return None


def _get_effective_feature_limits(user_id: Optional[str], feature_key: str) -> Dict[str, Any]:
    """Tek bir feature için efektif limitleri döndür."""
    user = _user_for(user_id)
    plan_name = _normalize_plan_name(user)
    daily_quota, burst_per_minute = PLAN_DEFAULTS.get(plan_name, {}).get(feature_key, (0, 0))

    # Opsiyonel DB sorguları
    try:
        from backend.db.models import PlanLimit, UserLimitOverride  # type: ignore

        pl = (
            PlanLimit.query.filter_by(plan_name=plan_name, feature_key=feature_key)
            .order_by(PlanLimit.updated_at.desc())
            .first()
        )
        if pl:
            daily_quota = int(pl.daily_quota or daily_quota)
            burst_per_minute = int(pl.burst_per_minute or burst_per_minute)

        if user:
            ov = (
                UserLimitOverride.query.filter_by(user_id=user.id, feature_key=feature_key)
                .order_by(UserLimitOverride.updated_at.desc())
                .first()
            )
            if ov and (not getattr(ov, "expires_at", None) or ov.expires_at > datetime.utcnow()):
                if getattr(ov, "daily_quota", None) is not None:
                    daily_quota = int(ov.daily_quota)
                if getattr(ov, "burst_per_minute", None) is not None:
                    burst_per_minute = int(ov.burst_per_minute)
    except Exception:
        pass

    return {
        "plan_name": plan_name,
        "daily_quota": int(daily_quota),
        "burst_per_minute": int(burst_per_minute),
    }


def get_user_effective_limits(arg1: Any = None,
                              feature_key: Optional[str] = None,
                              **kwargs) -> Dict:
    """Back-compat çok biçimli fonksiyon."""
    if feature_key is not None:
        user_id = kwargs.get("user_id")
        if user_id is None:
            user_id = str(arg1) if arg1 is not None else None
        return _get_effective_feature_limits(user_id=user_id, feature_key=feature_key)

    user = arg1
    limits: Dict[str, Any] = {}
    try:
        plan_features = getattr(getattr(user, "plan", None), "features", {}) or {}
        if isinstance(plan_features, str):
            plan_features = json.loads(plan_features or "{}")
        limits.update(plan_features or {})
    except Exception:
        pass

    try:
        if getattr(user, "boost_expire_at", None) and getattr(user, "boost_expire_at") > datetime.utcnow():
            boost = getattr(user, "boost_features", {}) or {}
            if isinstance(boost, str):
                boost = json.loads(boost or "{}")
            limits.update(boost or {})
    except Exception:
        pass

    try:
        custom = getattr(user, "custom_features", {}) or {}
        if isinstance(custom, str):
            custom = json.loads(custom or "{}")
        limits.update({k: v for k, v in (custom or {}).items() if isinstance(v, (int, bool))})
    except Exception:
        pass

    if limits:
        return limits

    plan_key = _normalize_plan_name(user).lower()
    return PLAN_LIMITS_COMPAT.get(plan_key, PLAN_LIMITS_COMPAT["basic"]).copy()


def give_user_boost(user, features: Dict[str, Any], expires_at: datetime) -> None:
    """Kullanıcıya geçici feature boost'u ver."""
    try:
        from backend.db.models import db  # local import
        user.boost_features = json.dumps(features)
        user.boost_expire_at = expires_at
        db.session.add(user)
        db.session.commit()
    except Exception:
        try:
            from backend.db.models import db  # local import
            db.session.rollback()
        except Exception:
            pass


def check_custom_feature(user, feature: str) -> bool:
    """Kullanıcının custom bir feature'a sahip olup olmadığını kontrol et."""
    try:
        data = getattr(user, "custom_features", {}) or {}
        if isinstance(data, str):
            data = json.loads(data or "{}")
        return bool(data.get(feature))
    except Exception:
        return False


def check_and_increment_usage(user, limit_key: str) -> bool:
    """
    Belirtilen limit için kullanım kotasını kontrol eder ve bir artırır.
    DB yoksa engelleme yapmaz.
    """
    try:
        limits = get_user_effective_limits(user)
        max_val = limits.get(limit_key)
        if max_val is None:
            return True

        from backend.db.models import UsageLog, db  # local import
        start = datetime.utcnow() - timedelta(days=1)
        usage = (
            UsageLog.query.filter_by(user_id=user.id, action=limit_key)
            .filter(UsageLog.timestamp > start)
            .count()
        )
        if usage >= int(max_val):
            return False
        db.session.add(UsageLog(user_id=user.id, action=limit_key, timestamp=datetime.utcnow()))
        db.session.commit()
        return True
    except Exception:
        return True


def get_all_feature_keys() -> List[str]:
    """UI için bilinen feature anahtarları."""
    keys = set()
    for d in PLAN_DEFAULTS.values():
        keys.update(d.keys())
    try:
        from backend.db.models import PlanLimit  # type: ignore
        for (fk,) in PlanLimit.query.with_entities(PlanLimit.feature_key).distinct().all():
            keys.add(fk)
    except Exception:
        pass
    return sorted(keys)


# -----------------------------------------------------------------------------
# Back-compat: enforce_plan_limits dekoratörü
# -----------------------------------------------------------------------------

def enforce_plan_limits(limit_key: str):
    def decorator(fn):
        def inner(*args, **kwargs):
            from backend.db.models import User, UsageLog, db  # local import
            user = getattr(g, "user", None)
            if user is None:
                api_key = request.headers.get("X-API-KEY")
                if api_key:
                    u = User.query.filter_by(api_key=api_key).first()
                    if u:
                        g.user = u
                        user = u
            if user is None:
                return jsonify({"error": "Auth required"}), 401

            plan_key = _normalize_plan_name(user).lower()
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


__all__ = [
    "PLAN_DEFAULTS",
    "PLAN_LIMITS",
    "PLAN_LIMITS_COMPAT",
    "get_user_effective_limits",
    "get_all_feature_keys",
    "give_user_boost",
    "check_custom_feature",
    "check_and_increment_usage",
    "enforce_plan_limits",
]
