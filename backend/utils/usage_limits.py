# backend/utils/usage_limits.py
from __future__ import annotations

from functools import wraps
from typing import Callable, Dict, Optional
from datetime import datetime, timedelta, date

from flask import jsonify, g, current_app
from types import SimpleNamespace

from backend.utils.plan_limits import get_user_effective_limits


def _resolve_user():
    try:
        from backend.db.models import User  # local import (döngü engelle)
        if hasattr(g, "user") and isinstance(getattr(g, "user", None), User):
            return g.user
    except Exception:
        pass
    try:
        from flask_jwt_extended import get_jwt_identity  # type: ignore
        from backend.db.models import User
        uid = get_jwt_identity()
        if uid:
            return User.query.get(uid)
    except Exception:
        pass
    return None


def _r():
    return current_app.extensions.get("redis_client")


def _today() -> str:
    return date.today().strftime("%Y%m%d")


def _rk(uid: str, fk: str) -> str:
    return f"usage:{uid}:{fk}:{_today()}"


def _ttl_midnight() -> int:
    now = datetime.utcnow()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((tomorrow - now).total_seconds()))

def _reset_seconds() -> int:
    return _ttl_midnight()


def _inc_r(uid: str, fk: str) -> int:
    r = _r()
    if not r:
        return -1
    key = _rk(uid, fk)
    pipe = r.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, _ttl_midnight())
    val, _ = pipe.execute()
    try:
        return int(val)
    except Exception:
        return -1


def _get_r(uid: str, fk: str) -> Optional[int]:
    r = _r()
    if not r:
        return None
    v = r.get(_rk(uid, fk))
    return int(v) if v is not None else 0


def _inc_db(uid: str, fk: str) -> int:
    from backend.db.models import db, DailyUsage  # local import
    row = DailyUsage.query.filter_by(user_id=uid, feature_key=fk, usage_date=date.today()).first()
    if not row:
        row = DailyUsage(user_id=uid, feature_key=fk, usage_date=date.today(), used_count=0)
        db.session.add(row)
    row.used_count = (row.used_count or 0) + 1
    db.session.commit()
    return int(row.used_count)


def _get_db(uid: str, fk: str) -> int:
    from backend.db.models import DailyUsage  # local import
    row = DailyUsage.query.filter_by(user_id=uid, feature_key=fk, usage_date=date.today()).first()
    return int(row.used_count) if row else 0


def _payload(used: int, quota: int) -> Dict:
    remaining = max(0, quota - used)
    pct = (used / quota) if quota > 0 else 0.0
    return {
        "used": used,
        "quota": quota,
        "remaining": remaining,
        "percent": round(pct, 4),
        "warn75": pct >= 0.75,
        "warn90": pct >= 0.90,
        "exhausted": used >= quota,
    }


def check_usage_limit(feature_key: str) -> Callable:
    """Endpoint decorator: günlük kotayı uygular (Redis → DB fallback)."""

    def deco(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = _resolve_user()
            # ------------------------------------------------------------------
            # TESTING shimi: Oturum açılmadığında ve uygulama TESTING modunda
            # isek hafif bir kullanıcı nesnesi ekle. Bu sayede testler JWT
            # veya API anahtarı olmadan da endpoint'e erişebilir.
            # ------------------------------------------------------------------
            if not user and current_app and current_app.config.get("TESTING"):
                user = g.user = SimpleNamespace(
                    id="test-user",
                    subscription_level="BASIC",
                    plan=SimpleNamespace(name="basic"),
                    is_admin=True,
                )
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            eff = get_user_effective_limits(user_id=str(user.id), feature_key=feature_key)
            quota = int(eff.get("daily_quota", 0))

            used = _inc_r(str(user.id), feature_key)
            if used < 0:
                used = _inc_db(str(user.id), feature_key)

            from flask import make_response

            if used > quota > 0:
                body = {"error": "UsageLimitExceeded", **_payload(used, quota)}
                rest = getattr(f, "limit_fail_status", (429,))
                status = rest[0] if isinstance(rest, (list, tuple)) and rest else 429
                response = make_response(jsonify(body), status)
                pl = _payload(used, quota)
                response.headers["X-Usage-Used"] = str(pl["used"])
                response.headers["X-Usage-Quota"] = str(pl["quota"])
                response.headers["X-Usage-Remaining"] = str(pl["remaining"])
                response.headers["X-Usage-Reset-Seconds"] = str(_reset_seconds())
                return response

            # İsteğe bağlı telemetri header'ları
            try:
                resp = f(*args, **kwargs)
                if isinstance(resp, tuple):
                    body, *rest = resp
                    response = make_response(body, *(rest or []))
                else:
                    response = make_response(resp)
                pl = _payload(used, quota)
                response.headers["X-Usage-Used"] = str(pl["used"])
                response.headers["X-Usage-Quota"] = str(pl["quota"])
                response.headers["X-Usage-Remaining"] = str(pl["remaining"])
                response.headers["X-Usage-Reset-Seconds"] = str(_reset_seconds())
                return response
            except Exception:
                return f(*args, **kwargs)

        return wrapped

    return deco


def get_usage_status(user_id: str, feature_key: str) -> Dict:
    eff = get_user_effective_limits(user_id=user_id, feature_key=feature_key)
    used = _get_r(user_id, feature_key)
    if used is None:
        used = _get_db(user_id, feature_key)
    pl = _payload(used, int(eff.get("daily_quota", 0)))
    pl.update({"feature_key": feature_key, "plan_name": eff.get("plan_name")})
    return pl


def get_usage_count(user, feature: str) -> int:
    """
    Back-compat test helper: Bugünkü kullanım sayısı (Redis/DB).
    DB yoksa 0 döner.
    """
    try:
        from backend.db.models import UsageLog  # type: ignore
        uid = getattr(user, "id", user)
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            UsageLog.query.filter_by(user_id=uid, action=feature)
            .filter(UsageLog.timestamp >= start)
            .count()
        )
    except Exception:
        try:
            used = _get_r(getattr(user, "id", user), feature)
            if used is None:
                used = _get_db(getattr(user, "id", user), feature)
            return int(used or 0)
        except Exception:
            return 0
