from __future__ import annotations

import json
import os
from typing import List, Optional, Tuple

from flask import Blueprint, current_app, g, jsonify, request
from flask_socketio import SocketIO

from backend import celery_app, limiter, socketio
from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.middleware.plan_limits import enforce_plan_limit
from backend.observability.anomaly import record_submit
from backend.observability.metrics import inc_error
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log
from backend.utils.rate import parse_rate_string
from backend.utils.security import (has_admin_approval, ip_allowed,
                                    is_2fa_required, is_user_2fa_ok,
                                    need_admin_approval, safe_cache_key,
                                    validate_asset, validate_symbols_list,
                                    validate_timeframe)

batch_bp = Blueprint("batch", __name__, url_prefix="/api/batch")


def _conf_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


@batch_bp.post("/submit")
@jwt_required_if_not_testing()
@enforce_plan_limit("draks_batch")
@limiter.limit(lambda: parse_rate_string(os.getenv("BATCH_RATE_LIMIT", "2/hour")))
def submit_batch():
    """Toplu analiz başlatır."""
    if not feature_flag_enabled("draks") or not os.getenv(
        "DRAKS_BATCH_ENABLED", "false"
    ).lower() in {"1", "true", "yes", "on"}:
        return jsonify({"error": "Özellik devre dışı."}), 403
    body = request.get_json(silent=True) or {}
    raw_symbols = body.get("symbols") or []
    if not isinstance(raw_symbols, list) or not raw_symbols:
        return jsonify({"error": "symbols listesi gerekli"}), 400

    max_symbols = _conf_int("BATCH_MAX_SYMBOLS", 50)
    symbols = validate_symbols_list(raw_symbols, max_symbols)
    if not symbols:
        return jsonify({"error": "Geçerli sembol bulunamadı"}), 400

    timeframe = body.get("timeframe", "1h")
    if not validate_timeframe(timeframe):
        return jsonify({"error": "Geçersiz timeframe"}), 400
    asset = (body.get("asset") or "crypto").lower()
    if not validate_asset(asset):
        return jsonify({"error": "Geçersiz asset"}), 400

    # IP allowlist kontrolü
    if not ip_allowed(request.remote_addr):
        inc_error("batch_ip_block")
        return jsonify({"error": "IP yetkili değil"}), 403

    # 2FA zorunlu mu?
    if is_2fa_required() and not is_user_2fa_ok():
        return jsonify({"error": "2FA doğrulaması gerekli"}), 403

    # Büyük batch için admin onayı
    user = g.get("user")
    if need_admin_approval(len(symbols)):
        r = current_app.extensions["redis_client"]
        if not has_admin_approval(r, str(getattr(user, "id", "")) or None):
            return jsonify({"error": "Admin onayı gerekli"}), 403

    # Anomali kaydı
    try:
        r = current_app.extensions["redis_client"]
        is_anom = record_submit(
            r,
            str(getattr(user, "id", "")) if user else None,
            request.remote_addr or "unknown",
        )
        if is_anom:
            inc_error("batch_anomaly_submit")
    except Exception:
        pass

    job = _dispatch(symbols, timeframe, asset)
    if user:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="batch_submit",
            target="/api/batch/submit",
            description=f"symbols={len(symbols)} tf={timeframe} asset={asset}",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    return jsonify({"job_id": job.id, "count": len(symbols)})


def _dispatch(symbols: List[str], timeframe: str, asset: str):
    timeout = _conf_int("BATCH_JOB_TIMEOUT", 300)
    return run_batch.apply_async(
        kwargs={"symbols": symbols, "timeframe": timeframe, "asset": asset},
        time_limit=timeout,
        soft_time_limit=timeout - 5,
    )


@batch_bp.get("/status/<job_id>")
@jwt_required_if_not_testing()
def status(job_id: str):
    res = celery_app.AsyncResult(job_id)
    return jsonify({"id": job_id, "state": res.state, "ready": res.ready()})


@batch_bp.get("/results/<job_id>")
@jwt_required_if_not_testing()
def results(job_id: str):
    res = celery_app.AsyncResult(job_id)
    if not res.ready():
        return jsonify({"error": "hazır değil", "state": res.state}), 202
    try:
        return jsonify(res.get(timeout=1))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------- Celery Task --------
@celery_app.task(bind=True)
def run_batch(self, *, symbols: List[str], timeframe: str, asset: str):
    """
    Not: Çıktı demo amaçlı; gerçek karar motoru ile entegre edilirken backend.draks ENGINE kullanılabilir.
    Bellek koruması için per-parça kontrolü yapılır.
    """
    import os
    import time

    import psutil

    mem_limit_mb = _conf_int("CELERY_WORKER_MEMORY_LIMIT_MB", 512)
    # Socket.IO publisher (Redis MQ üzerinden; backend.socketio zaten MQ ile bağlı)
    sio = SocketIO(message_queue=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    results = []
    total = len(symbols)
    done = 0
    for s in symbols:
        # Basit RAM kontrolü
        try:
            rss_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            if rss_mb > mem_limit_mb:
                raise MemoryError(
                    f"Worker memory over limit: {rss_mb:.1f}MB > {mem_limit_mb}MB"
                )
        except Exception:
            pass
        # Simüle analiz (gerçek hayatta cache + ENGINE.run + karar)
        time.sleep(0.01)
        results.append(
            {
                "symbol": s,
                "timeframe": timeframe,
                "asset": asset,
                "score": 0.0,
                "decision": "HOLD",
            }
        )
        done += 1
        try:
            sio.emit(
                "progress",
                {"job_id": self.request.id, "done": done, "failed": 0, "total": total},
                namespace="/batch",
                to=f"job:{self.request.id}",
            )
        except Exception:
            pass
    try:
        sio.emit(
            "progress",
            {
                "job_id": self.request.id,
                "done": done,
                "failed": 0,
                "total": total,
                "finished": True,
            },
            namespace="/batch",
            to=f"job:{self.request.id}",
        )
    except Exception:
        pass
    return {"items": results, "count": len(results)}
