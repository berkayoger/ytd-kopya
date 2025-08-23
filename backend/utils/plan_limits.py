"""
Plan ve kullanıcı bazlı limit yardımcıları.
Kullanıcının planındaki özelliklerle geçici boost ve özel tanımları
birleştirerek efektif limitleri hesaplar.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

import json

from flask import g, request, jsonify

from backend.db import db
from backend.db.models import User, UsageLog


# Örnek plan limiti tanımları (gerekirse genişletilebilir)
PLAN_LIMITS: Dict[str, Dict[str, int]] = {
    "basic": {"predict_daily": 10, "api_request_daily": 100},
    "premium": {"predict_daily": 100, "api_request_daily": 1000},
}


def get_user_effective_limits(user: User) -> Dict[str, Any]:
    """Kullanıcının plan, boost ve özel tanımlarını birleştirir."""

    limits: Dict[str, Any] = {}

    if getattr(user, "plan", None):
        features = user.plan.features
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except Exception:
                features = {}
        limits.update(features or {})

    if getattr(user, "boost_features", None) and getattr(user, "boost_expire_at", None):
        if user.boost_expire_at > datetime.utcnow():
            try:
                boosts = json.loads(user.boost_features) if isinstance(user.boost_features, str) else user.boost_features
                limits.update(boosts or {})
            except Exception:
                pass

    if getattr(user, "custom_features", None):
        try:
            custom = json.loads(user.custom_features) if isinstance(user.custom_features, str) else user.custom_features
            limits.update(custom or {})
        except Exception:
            pass

    return limits


def get_all_feature_keys() -> list[str]:
    """Bilinen tüm limit anahtarlarını döndür."""
    keys = set()
    for features in PLAN_LIMITS.values():
        keys.update(features.keys())
    return sorted(keys)


def give_user_boost(user: User, features: Dict[str, Any], expire_at: datetime) -> None:
    """Kullanıcıya geçici limit artışı tanımlar."""
    user.boost_features = json.dumps(features)
    user.boost_expire_at = expire_at
    db.session.commit()


def check_custom_feature(user: User, key: str) -> bool:
    """Kullanıcıya özel bir özelliğin tanımlı olup olmadığını kontrol eder."""
    try:
        features = json.loads(user.custom_features) if isinstance(user.custom_features, str) else (user.custom_features or {})
        if key in features:
            return bool(features[key])
    except Exception:
        pass
    limits = get_user_effective_limits(user)
    return bool(limits.get(key))


def check_and_increment_usage(user: User, limit_key: str) -> bool:
    """Belirtilen limit için kullanım kotasını kontrol eder ve bir artırır."""
    limits = get_user_effective_limits(user)
    max_value = limits.get(limit_key)
    if max_value is None:
        return True

    start_time = datetime.utcnow() - timedelta(days=1)
    usage_count = (
        UsageLog.query.filter_by(user_id=user.id, action=limit_key)
        .filter(UsageLog.timestamp > start_time)
        .count()
    )
    if usage_count >= int(max_value):
        return False

    db.session.add(UsageLog(user_id=user.id, action=limit_key, timestamp=datetime.utcnow()))
    db.session.commit()
    return True


def get_plan_rate_limit(plan_name: str | None = None) -> str:
    """Plan adına göre istek hız limiti dizesi döndür."""
    from backend.limiting import get_plan_rate_limit as _gprl

    return _gprl(plan_name)


def rate_limit_key_func() -> str:
    """Limiter anahtarını döndür (kullanıcı kimliği/IP)."""
    from backend.limiting import rate_limit_key_func as _rlkf

    return _rlkf()


def enforce_plan_limits(limit_key):
    """Legacy decorator – mevcut middleware kullanılmaktadır."""

    def wrapper(fn):
        def inner(*args, **kwargs):
            user = g.user if hasattr(g, "user") else None
            if not user:
                api_key = request.headers.get("X-API-KEY")
                if api_key:
                    user = User.query.filter_by(api_key=api_key).first()
                    if user:
                        g.user = user
            if not user:
                return jsonify({"error": "Auth required"}), 401

            plan_name = user.plan.name.lower() if getattr(user, "plan", None) else "basic"
            limits = PLAN_LIMITS.get(plan_name, {})
            limit = limits.get(limit_key)

            if limit is None:
                return fn(*args, **kwargs)

            start_time = datetime.utcnow() - timedelta(days=1)
            usage_count = (
                UsageLog.query.filter_by(user_id=user.id, action=limit_key)
                .filter(UsageLog.timestamp > start_time)
                .count()
            )

            if usage_count >= limit:
                return jsonify({"error": "PlanLimitExceeded"}), 429

            db.session.add(UsageLog(user_id=user.id, action=limit_key, timestamp=datetime.utcnow()))
            db.session.commit()
            return fn(*args, **kwargs)

        return inner

    return wrapper

