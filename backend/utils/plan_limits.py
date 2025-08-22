# backend/utils/plan_limits.py
from __future__ import annotations

from typing import Dict, Optional
from flask import g
from datetime import datetime

# Mevcut modellerle uyumlu kalmak adına yalnızca User'ı zorunlu alıyoruz.
from backend.db.models import User


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
