from __future__ import annotations
from flask import Blueprint, request, jsonify, g, current_app
from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.auth.middlewares import admin_required
from backend.utils.logger import create_log

batch_controls_bp = Blueprint("batch_controls", __name__, url_prefix="/api/admin/batch")

@batch_controls_bp.post("/approval/grant")
@jwt_required_if_not_testing()
@admin_required()
def grant_batch_approval():
    """
    Büyük batch'ler için kullanıcıya geçici onay.
    Query/body: user_id (zorunlu), ttl_s (opsiyonel; default 3600)
    """
    from redis import Redis
    user_id = request.json.get("user_id") if request.is_json else request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id gerekli"}), 400
    try:
        ttl_s = int((request.json or {}).get("ttl_s", request.args.get("ttl_s", 3600)))
    except Exception:
        ttl_s = 3600
    r: Redis = g.get("redis_client") or current_app.extensions["redis_client"]  # type: ignore
    k = f"batch_admin_approval:{user_id}"
    r.setex(k, ttl_s, "1")
    user = g.get("user")
    if user:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="batch_admin_approval_grant",
            target=request.path,
            description=f"grant user_id={user_id} ttl={ttl_s}",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    return jsonify({"ok": True, "user_id": user_id, "ttl_s": ttl_s})

@batch_controls_bp.post("/approval/revoke")
@jwt_required_if_not_testing()
@admin_required()
def revoke_batch_approval():
    from redis import Redis
    user_id = request.json.get("user_id") if request.is_json else request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id gerekli"}), 400
    r: Redis = current_app.extensions["redis_client"]  # type: ignore
    k = f"batch_admin_approval:{user_id}"
    r.delete(k)
    user = g.get("user")
    if user:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="batch_admin_approval_revoke",
            target=request.path,
            description=f"revoke user_id={user_id}",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    return jsonify({"ok": True, "user_id": user_id})
