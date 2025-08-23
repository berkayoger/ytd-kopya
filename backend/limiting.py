"""
Plan bazlı rate limit yardımcıları.
Test/CI ortamında güvenli varsayılanlarla çalışır.
"""
from __future__ import annotations
import os
from flask import request, g
from flask_limiter import Limiter

# Plan -> rate ifade haritası (Flask-Limiter formatı)
# ENV ile override edilebilir (ör: PLAN_LIMIT_PREMIUM="120/minute")
DEFAULT_PLAN_LIMITS = {
    "free": os.getenv("PLAN_LIMIT_FREE", "30/minute"),
    "basic": os.getenv("PLAN_LIMIT_BASIC", "60/minute"),
    "premium": os.getenv("PLAN_LIMIT_PREMIUM", "120/minute"),
    "enterprise": os.getenv("PLAN_LIMIT_ENTERPRISE", "240/minute"),
}



def get_plan_rate_limit(plan_name: str | None = None) -> str:
    """
    Verilen plan adı için rate-limit dizesi döndürür.
    Tanınmayan/boş planlarda güvenli bir varsayılan kullanır.
    """
    if plan_name is None:
        plan = getattr(g, "user", None)
        plan_name = getattr(getattr(plan, "plan", None), "name", None) if plan else None
    if not plan_name:
        return DEFAULT_PLAN_LIMITS["free"]
    key = str(plan_name).strip().lower()
    return DEFAULT_PLAN_LIMITS.get(key, DEFAULT_PLAN_LIMITS["free"])


def rate_limit_key_func() -> str:
    """
    Limiter için anahtar (IP ya da kullanıcı kimliği).
    - Auth'lu isteklerde user_id tercih edilir (adil ve doğru kota takibi).
    - Aksi durumda client IP kullanılır.
    Bu fonksiyon test/CI'da da güvenle çalışır.
    """
    user_id = getattr(g, "user_id", None) or getattr(getattr(g, "user", None), "id", None)
    if user_id:
        return f"user:{user_id}"
    ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
        or "unknown"
    )
    return f"ip:{ip}"


# Flask-Limiter instance (uygulama init'de init_app ile bağlanır)
limiter = Limiter(key_func=rate_limit_key_func)

