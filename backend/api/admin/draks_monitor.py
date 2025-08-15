from __future__ import annotations
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from backend.auth.middlewares import admin_required
from backend.db.models import DraksDecision, DraksSignalRun
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log

admin_draks_bp = Blueprint("admin_draks", __name__, url_prefix="/api/admin/draks")


def _paginated_query(q, default_limit=25):
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", default_limit))
    except Exception:
        page, limit = 1, default_limit
    page = max(1, page)
    limit = max(1, min(100, limit))
    total = q.count()
    rows = q.offset((page - 1) * limit).limit(limit).all()
    return rows, {"page": page, "limit": limit, "total": total}


@admin_draks_bp.get("/decisions")
@jwt_required()
@admin_required()
def list_decisions():
    if not feature_flag_enabled("draks"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403
    symbol = request.args.get("symbol")
    q = DraksDecision.query.order_by(DraksDecision.created_at.desc())
    if symbol:
        q = q.filter(DraksDecision.symbol == symbol)
    rows, meta = _paginated_query(q)
    out = [
        {
            "id": r.id,
            "symbol": r.symbol,
            "decision": r.decision,
            "position_pct": r.position_pct,
            "stop": r.stop,
            "take_profit": r.take_profit,
            "created_at": r.created_at.isoformat() + "Z",
        }
        for r in rows
    ]
    user = g.get("user")
    if user:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="admin_draks_decisions",
            target=request.path,
            description="Draks kararları listelendi.",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    return jsonify({"items": out, "meta": meta})


@admin_draks_bp.get("/signals")
@jwt_required()
@admin_required()
def list_signals():
    if not feature_flag_enabled("draks"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403
    symbol = request.args.get("symbol")
    q = DraksSignalRun.query.order_by(DraksSignalRun.created_at.desc())
    if symbol:
        q = q.filter(DraksSignalRun.symbol == symbol)
    rows, meta = _paginated_query(q)
    out = [
        {
            "id": r.id,
            "symbol": r.symbol,
            "timeframe": r.timeframe,
            "score": r.score,
            "decision": r.decision,
            "created_at": r.created_at.isoformat() + "Z",
        }
        for r in rows
    ]
    user = g.get("user")
    if user:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="admin_draks_signals",
            target=request.path,
            description="Draks sinyalleri listelendi.",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    return jsonify({"items": out, "meta": meta})

