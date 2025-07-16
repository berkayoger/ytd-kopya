from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from backend.auth.middlewares import admin_required
from backend.db.models import AuditLog

audit_bp = Blueprint("audit_bp", __name__)


@audit_bp.route("/admin/audit-logs", methods=["GET"])
@jwt_required()
@admin_required()
def get_logs():
    limit = int(request.args.get("limit", 100))
    logs = (
        AuditLog.query.order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([
        {
            "id": l.id,
            "user_id": l.user_id,
            "username": l.username,
            "action": l.action,
            "ip_address": l.ip_address,
            "details": l.details,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ])
