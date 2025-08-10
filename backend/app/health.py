from __future__ import annotations

from flask import Blueprint, jsonify, g, request
import time
import logging

from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log

bp = Blueprint("health", __name__)
_started_at = time.time()


def _log_health(action: str) -> None:
    """Sağlık kontrolleri için basit log oluştur."""
    user = g.get("user")
    if not user:
        return
    try:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action=action,
            target=request.path,
            description="health endpoint",  # kısa açıklama
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    except Exception as exc:  # pragma: no cover - log hata yakalama
        logging.getLogger(__name__).warning("health log başarısız: %s", exc)


@bp.get("/health")
def health() -> tuple:
    """Servis ayakta mı?"""
    if not feature_flag_enabled("health_check"):
        return jsonify({"error": "Özellik kapalı"}), 403
    uptime = round(time.time() - _started_at, 2)
    _log_health("health_check")
    return jsonify(status="ok", uptime_sec=uptime), 200


@bp.get("/ready")
def ready() -> tuple:
    """Kritik bağımlılıklar hazır mı?"""
    if not feature_flag_enabled("health_check"):
        return jsonify({"error": "Özellik kapalı"}), 403
    deps = {"database": "unknown", "cache": "unknown"}
    _log_health("ready_check")
    return jsonify(status="ready", deps=deps), 200
