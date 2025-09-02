from __future__ import annotations

import requests
from flask import Blueprint, current_app, g, jsonify, request
from flask_jwt_extended import jwt_required

from backend.middleware.plan_limits import enforce_plan_limit
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log

# DRAKS entegrasyonu
draks_bp = Blueprint("draks", __name__, url_prefix="/api/draks")


@draks_bp.route("/decision/run", methods=["POST"])
@jwt_required()
@enforce_plan_limit("predict_daily")
def draks_decision_run():
    """DRAKS karar motorunu çalıştırır."""
    if not feature_flag_enabled("draks_enabled"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403

    user = g.get("user")
    ip_address = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")
    status = "error"
    try:
        payload = request.get_json() or {}
        url = f"{current_app.config.get('DRAKS_ENGINE_URL')}/api/decision/run"
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        status = "success" if resp.ok else "error"
        return jsonify(data), (200 if resp.ok else 502)
    except Exception as exc:  # pragma: no cover
        current_app.logger.exception("draks_decision_run hata: %s", exc)
        return jsonify({"error": "draks-error"}), 500
    finally:
        if user:
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="draks_decision",
                target="/api/draks/decision/run",
                description="DRAKS karar çalıştırıldı.",
                status=status,
                user_agent=user_agent,
            )


@draks_bp.route("/copy/evaluate", methods=["POST"])
@jwt_required()
@enforce_plan_limit("predict_daily")
def draks_copy_evaluate():
    """Lider sinyalini DRAKS ile değerlendirir."""
    if not feature_flag_enabled("draks_enabled"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403

    user = g.get("user")
    ip_address = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")
    status = "error"
    try:
        payload = request.get_json() or {}
        url = f"{current_app.config.get('DRAKS_ENGINE_URL')}/api/decision/run"
        req_body = {"symbol": payload.get("symbol"), "candles": payload.get("candles")}
        resp = requests.post(url, json=req_body, timeout=10)
        data = resp.json()
        if not resp.ok:
            return jsonify(data), 502
        score = float(data.get("score", 0))
        decision = str(data.get("decision", "HOLD")).upper()
        side = str(payload.get("side", "")).upper()
        greenlight = (decision == "LONG" and side == "BUY") or (
            decision == "SHORT" and side == "SELL"
        )
        scaled_size = None
        if greenlight and payload.get("size") is not None:
            scaled_size = payload["size"] * max(0, min(1, abs(score) * 1.5))
        status = "success"
        return jsonify(
            {"greenlight": greenlight, "scaled_size": scaled_size, "draks": data}
        )
    except Exception as exc:  # pragma: no cover
        current_app.logger.exception("draks_copy_evaluate hata: %s", exc)
        return jsonify({"error": "draks-eval-error"}), 500
    finally:
        if user:
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="draks_copy_evaluate",
                target="/api/draks/copy/evaluate",
                description="DRAKS sinyali değerlendirildi.",
                status=status,
                user_agent=user_agent,
            )
