"""
Plan bazlı rate limit yardımcıları.
Test/CI ortamında güvenli varsayılanlarla çalışır.
"""
from __future__ import annotations
import os
from typing import Optional
from flask import request, g
from flask_limiter import Limiter

# Güvenli import: jwt fonksiyonu yoksa None olsun
try:  # pragma: no cover
    from flask_jwt_extended import get_jwt_identity  # type: ignore
except Exception:  # pragma: no cover
    get_jwt_identity = None  # type: ignore

from backend.utils.plan_limits import get_user_effective_limits

# Plan -> rate ifade haritası (ENV ile override edilebilir)
DEFAULT_PLAN_LIMITS = {
    "free": os.getenv("PLAN_LIMIT_FREE", "30/minute"),
    "basic": os.getenv("PLAN_LIMIT_BASIC", "60/minute"),
    "premium": os.getenv("PLAN_LIMIT_PREMIUM", "120/minute"),
    "enterprise": os.getenv("PLAN_LIMIT_ENTERPRISE", "240/minute"),
}


def _normalize_rate_string(val: str) -> str:
    """'60/minute' -> '60 per minute' normalize et."""
    v = (val or "").strip()
    if "/" in v and " per " not in v:
        num, unit = v.split("/", 1)
        return f"{num.strip()} per {unit.strip()}"
    return v


def _resolve_user_id() -> Optional[str]:
    """g.user.id, JWT vb. üzerinden kullanıcı kimliğini çöz."""
    try:
        if hasattr(g, "user") and getattr(g.user, "id", None):
            return str(g.user.id)
    except Exception:
        pass
    if get_jwt_identity is not None:
        try:
            uid = get_jwt_identity()
            if uid:
                return str(uid)
        except Exception:
            pass
    return None


def get_plan_rate_limit(plan_name: str | None = None) -> str:
    """
    Flask-Limiter için limit string'i döndür (örn. "60 per minute").
    Öncelik: kullanıcıya özel efektif limitler → plan bazlı defaultlar.
    """
    # 1) Kullanıcıya özel efektif limit (global_api burst_per_minute)
    user_id = _resolve_user_id()
    try:
        if user_id:
            eff = get_user_effective_limits(user_id, "global_api")
            burst = int(eff.get("burst_per_minute") or 0)
            if burst > 0:
                return f"{max(1, burst)} per minute"
    except Exception:
        # Sessizce plan bazlı fallback'e düş
        pass

    # 2) Plan bazlı default
    if plan_name is None:
        plan = getattr(g, "user", None)
        plan_name = getattr(getattr(plan, "plan", None), "name", None) if plan else None
    key = (str(plan_name).strip().lower() if plan_name else "free")
    return _normalize_rate_string(DEFAULT_PLAN_LIMITS.get(key, DEFAULT_PLAN_LIMITS["free"]))


def rate_limit_key_func() -> str:
    """Limiter key: varsa API key; yoksa uzak IP."""
    api_key = request.headers.get("X-API-KEY") or request.args.get("api_key")
    if api_key:
        return f"api:{api_key}"
    return request.remote_addr or "unknown"


# Flask-Limiter instance (uygulama init'de init_app ile bağlanır)
limiter = Limiter(key_func=rate_limit_key_func)
