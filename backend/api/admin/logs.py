from flask import Blueprint, request, jsonify
from backend.models.log import Log
from datetime import datetime

admin_logs_bp = Blueprint("admin_logs", __name__)

@admin_logs_bp.route("/logs", methods=["GET"])
def get_logs():
    """Logları filtreleyip JSON döner."""
    username = request.args.get("username")
    action = request.args.get("action")
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    query = Log.query
    if username:
        query = query.filter(Log.username.ilike(f"%{username}%"))
    if action:
        query = query.filter(Log.action == action)
    if start:
        start_dt = datetime.fromisoformat(start)
        query = query.filter(Log.timestamp >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        query = query.filter(Log.timestamp <= end_dt)

    total = query.count()
    logs = (
        query.order_by(Log.timestamp.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    results = [
        {
            "id": log.id,
            "username": log.username,
            "action": log.action,
            "target": log.target,
            "description": log.description,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "timestamp": log.timestamp.isoformat(),
            "status": log.status,
        }
        for log in logs
    ]
    return jsonify({"total": total, "results": results})
