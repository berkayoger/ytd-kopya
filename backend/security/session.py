from datetime import datetime, timedelta, timezone

SESSION_TTL_MIN = 30


def is_session_active(last_seen: datetime) -> bool:
    return datetime.now(timezone.utc) - last_seen <= timedelta(minutes=SESSION_TTL_MIN)
