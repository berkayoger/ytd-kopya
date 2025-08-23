# backend/limiting.py
"""Plan-bazlı dinamik rate-limit yardımcıları.

Flask-Limiter için kullanıcının planından türetilen burst-per-minute değeri
üretir. Kullanıcı bulunamazsa güvenli bir IP fallback değeri döner.
"""
from __future__ import annotations

from typing import Optional
from flask import g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

try:  # Projenizde olabilir / olmayabilir
    from flask_jwt_extended import get_jwt_identity  # type: ignore
except Exception:  # pragma: no cover
    get_jwt_identity = None  # type: ignore

from backend.utils.plan_limits import get_user_effective_limits


limiter = Limiter(key_func=get_remote_address)


def _resolve_user_id() -> Optional[str]:
    """g.user ya da JWT'den kullanıcı kimliği çöz."""
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


def get_plan_rate_limit() -> str:
    """Flask‑Limiter için limit string'i döndür (örn. "60 per minute")."""
    user_id = _resolve_user_id()
    feature_key = "global_api"

    # Güvenli varsayılan: 30/dk (kullanıcı yoksa IP bazlı uygulanacak)
    default_burst = 30

    try:
        if user_id:
            eff = get_user_effective_limits(user_id, feature_key)
            burst = int(eff.get("burst_per_minute") or default_burst)
            return f"{max(1, burst)} per minute"
    except Exception:
        pass

    return f"{default_burst} per minute"


def rate_limit_key_func() -> str:
    """Limiter key: varsa API key; yoksa uzak IP."""
    api_key = request.headers.get("X-API-KEY") or request.args.get("api_key")
    if api_key:
        return f"api:{api_key}"
    return request.remote_addr or "unknown"
