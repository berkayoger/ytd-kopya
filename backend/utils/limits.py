# backend/utils/limits.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple, Any, Dict

# -----------------------------------------------------------------------------
# DB ve Model yardımcıları
# -----------------------------------------------------------------------------
def _get_db_and_model():
    """UsageLog ve db objesine ulaş."""
    try:
        from backend.db.models import db as _db, UsageLog as _UsageLog  # type: ignore
        return _db, _UsageLog
    except Exception:
        pass
    try:
        from backend.extensions import db as _db, UsageLog as _UsageLog  # type: ignore
        return _db, _UsageLog
    except Exception:
        pass
    return None, None


# -----------------------------------------------------------------------------
# Zaman pencereleri
# -----------------------------------------------------------------------------
_ACTION_WINDOWS: Dict[str, str] = {
    # Aksiyon -> pencere türü
    "predict_daily": "daily",
    "generate_chart": "daily",
}

def _resolve_window(action: str) -> str:
    return _ACTION_WINDOWS.get(action, "daily")

def _window_for_action(action: str, now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    now = now or datetime.utcnow()
    window = _resolve_window(action)

    if window == "hourly":
        start = now.replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        return start, end

    if window == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    # daily (varsayılan)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


# -----------------------------------------------------------------------------
# Sayım / Artırım
# -----------------------------------------------------------------------------
def get_usage_count(user: Any, action: str, now: Optional[datetime] = None) -> int:
    """
    İlgili pencere için UsageLog sayısı.

    Notlar:
    - Daima UsageLog.query (scoped session) kullanılır; testlerde db.session ile aynıdır.
    - 'timestamp' yoksa 'created_at' kolonuna düşer. Her ikisi de yoksa zaman filtresi uygulanmaz.
    """
    db_obj, UsageLog = _get_db_and_model()
    if UsageLog is None:
        return 0

    user_id = getattr(user, "id", user)
    q = UsageLog.query.filter(UsageLog.user_id == user_id, UsageLog.action == action)

    # Kolon tespiti ve pencere filtresi
    time_col = getattr(UsageLog, "timestamp", None) or getattr(UsageLog, "created_at", None)
    if time_col is not None:
        start, end = _window_for_action(action, now)
        q = q.filter(time_col >= start, time_col < end)

    try:
        return q.count()
    except Exception:
        return 0


def increment_usage(user: Any, action: str, ts: Optional[datetime] = None, **extra) -> None:
    """
    Yeni UsageLog ekle. UsageLog.query.session / db.session üzerinden commit edilir.
    """
    db_obj, UsageLog = _get_db_and_model()
    if UsageLog is None:
        return

    ts = ts or datetime.utcnow()
    user_id = getattr(user, "id", user)

    # Yalnızca modelde olan alanları ekstra olarak geçir
    payload = {k: v for k, v in (extra or {}).items() if hasattr(UsageLog, k)}
    log = UsageLog(user_id=user_id, action=action, timestamp=ts, **payload)

    # Öncelik: db.session; yoksa Model.query.session
    sess = None
    if db_obj is not None:
        sess = getattr(db_obj, "session", None)
    if sess is None:
        q = getattr(UsageLog, "query", None)
        sess = getattr(q, "session", None) if q is not None else None
    if sess is None:
        return  # Güvenli çıkış

    sess.add(log)
    try:
        sess.commit()
    except Exception:
        try:
            sess.rollback()
        except Exception:
            pass
        raise


# -----------------------------------------------------------------------------
# Limit okuma ve uygulama
# -----------------------------------------------------------------------------
def _as_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    try:
        return dict(obj.__dict__)
    except Exception:
        return {}

def _extract_plan_limits(user: Any) -> Dict[str, Any]:
    plan = getattr(user, "plan", None)
    if plan is not None:
        for attr in ("features", "limits"):
            val = getattr(plan, attr, None)
            if isinstance(val, dict):
                return val
            d = _as_dict(val)
            if d:
                return d
    feats = getattr(user, "features", None)
    if isinstance(feats, dict):
        return feats
    d = _as_dict(feats)
    if d:
        return d
    return {}

def get_plan_limit(user: Any, action: str, default: Optional[int] = None) -> Optional[int]:
    limits = _extract_plan_limits(user)
    if not limits:
        return default
    keys = [
        action,
        action.lower(),
        action.upper(),
        action.replace("-", "_"),
        action.replace("-", "_").lower(),
    ]
    for k in keys:
        if k in limits and isinstance(limits[k], (int, float)):
            return int(limits[k])
    return default

def remaining_quota(
    user: Any,
    action: str,
    limit: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Optional[int]:
    limit_val = limit if limit is not None else get_plan_limit(user, action, None)
    if limit_val is None:
        return None
    used = get_usage_count(user, action, now=now)
    return max(limit_val - used, 0)

def enforce_limit(
    user: Any,
    action: str,
    limit: Optional[int] = None,
    *,
    increment: bool = False,
    now: Optional[datetime] = None,
):
    """
    Dönüş: (allowed, used_count, limit)
    - limit None ise plan’dan okunur; yine yoksa sınırsız kabul edilir.
    - increment=True ise izin verildiğinde log kaydı eklenir.
    """
    eff_limit = limit if limit is not None else get_plan_limit(user, action, None)
    used = get_usage_count(user, action, now=now)

    if eff_limit is None:
        if increment:
            increment_usage(user, action, ts=now or datetime.utcnow())
        return True, used, eff_limit

    allowed = used < eff_limit
    if allowed and increment:
        increment_usage(user, action, ts=now or datetime.utcnow())
    return allowed, used, eff_limit


__all__ = [
    "get_usage_count",
    "increment_usage",
    "get_plan_limit",
    "remaining_quota",
    "enforce_limit",
]
