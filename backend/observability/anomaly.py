from __future__ import annotations

import os
import time
from typing import Optional

from redis import Redis

ANOMALY_WINDOW_SEC = int(os.getenv("ANOMALY_WINDOW_SEC", "900"))
ANOMALY_MAX_SUBMITS_PER_WINDOW = int(os.getenv("ANOMALY_MAX_SUBMITS_PER_WINDOW", "5"))


def _key(user_id: Optional[str], ip: str) -> str:
    uid = user_id or "anon"
    return f"anomaly:submits:{uid}:{ip}"


def record_submit(r: Redis, user_id: Optional[str], ip: str) -> bool:
    """
    Kaydırmalı pencere ZSET ile kayıt tutar.
    Dönüş: is_anomalous (eşik aşımı)
    """
    now = time.time()
    k = _key(user_id, ip)
    pipe = r.pipeline()
    pipe.zadd(k, {str(now): now})
    pipe.zremrangebyscore(k, 0, now - ANOMALY_WINDOW_SEC)
    pipe.zcard(k)
    pipe.expire(k, ANOMALY_WINDOW_SEC + 60)
    _, _, cnt, _ = pipe.execute()
    return int(cnt) > ANOMALY_MAX_SUBMITS_PER_WINDOW
