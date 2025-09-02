from __future__ import annotations

import os
import uuid

from flask import Blueprint, g, jsonify, request

from backend import limiter
from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.middleware.plan_limits import enforce_plan_limit
from backend.observability.metrics import inc_batch_submit
from backend.tasks.draks_batch import (BATCH_MAX_CANDLES, init_job,
                                       job_results, job_status, process_symbol)
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log
from backend.utils.rate import parse_rate_string
from backend.utils.security import (validate_asset, validate_symbols_list,
                                    validate_timeframe)

draks_batch_bp = Blueprint("draks_batch", __name__)


def _rate_limit_value() -> str:
    return parse_rate_string(os.getenv("BATCH_RATE_LIMIT", "2/hour"), "2/hour")


def _feature_enabled() -> bool:
    return feature_flag_enabled("draks") and (
        feature_flag_enabled("draks_batch")
        or os.getenv("DRAKS_BATCH_ENABLED", "false").lower()
        in {"1", "true", "yes", "on"}
    )


@draks_batch_bp.post("/batch/submit")
@jwt_required_if_not_testing()
@enforce_plan_limit("draks_batch")
@limiter.limit(
    lambda: _rate_limit_value(),
    key_func=lambda: (getattr(g, "user", None) and str(g.user.id))
    or request.remote_addr,
)
def batch_submit():
    if not _feature_enabled():
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403
    user = getattr(g, "user", None)
    body = request.get_json(force=True, silent=True) or {}
    asset = str(body.get("asset", "crypto")).lower()
    timeframe = str(body.get("timeframe", "1h"))
    limit = int(body.get("limit", BATCH_MAX_CANDLES))
    max_symbols = int(os.getenv("BATCH_MAX_SYMBOLS", "50"))
    raw_symbols = body.get("symbols", [])
    if not isinstance(raw_symbols, list):
        return jsonify({"error": "symbols list gerekli"}), 400
    if not validate_asset(asset):
        return jsonify({"error": "geçersiz asset"}), 400
    if not validate_timeframe(timeframe):
        return jsonify({"error": "geçersiz timeframe"}), 400
    symbols = validate_symbols_list([str(s) for s in raw_symbols], max_symbols)
    if not symbols:
        return jsonify({"error": "geçersiz/boş sembol listesi"}), 400
    job_id = uuid.uuid4().hex
    init_job(job_id, str(user.id) if user else "unknown", symbols)
    for s in symbols:
        process_symbol.delay(
            asset=asset,
            symbol=s,
            timeframe=timeframe,
            limit=min(limit, BATCH_MAX_CANDLES),
            job_id=job_id,
        )
    if user:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="draks_batch_submit",
            target="/api/draks/batch/submit",
            description=f"job={job_id} items={len(symbols)} asset={asset} tf={timeframe}",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    inc_batch_submit("ok")
    return jsonify({"job_id": job_id, "total": len(symbols)}), 202


def _check_owner(meta_user_id: str | None) -> bool:
    user = getattr(g, "user", None)
    if not user:
        return False
    try:
        if (
            getattr(user, "is_admin", False)
            or str(getattr(user, "role", "")).upper() == "ADMIN"
        ):
            return True
    except Exception:
        pass
    return str(user.id) == str(meta_user_id)


@draks_batch_bp.get("/batch/status/<job_id>")
@jwt_required_if_not_testing()
def batch_status(job_id: str):
    st = job_status(job_id)
    if "error" in st:
        return jsonify(st), 404
    if not _check_owner(st.get("user_id")):
        return jsonify({"error": "forbidden"}), 403
    return (
        jsonify(
            {
                "job_id": job_id,
                "total": st["total"],
                "pending": st["pending"],
                "done": st["done"],
                "failed": st["failed"],
                "started_at": st["started_at"],
            }
        ),
        200,
    )


@draks_batch_bp.get("/batch/results/<job_id>")
@jwt_required_if_not_testing()
def batch_results(job_id: str):
    st = job_status(job_id)
    if "error" in st:
        return jsonify(st), 404
    if not _check_owner(st.get("user_id")):
        return jsonify({"error": "forbidden"}), 403
    decision = request.args.get("decision")
    status = request.args.get("status")
    symbol_like = request.args.get("symbol")
    res = job_results(
        job_id,
        decision=(decision.upper() if decision else None),
        status=status,
        symbol_like=symbol_like,
    )
    return jsonify({"job_id": job_id, "items": res}), 200
