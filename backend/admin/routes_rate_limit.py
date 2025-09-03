from __future__ import annotations

import ipaddress

from flask import Blueprint, g, jsonify, request

from backend.extensions import redis_client
from backend.models import db
from backend.models.api_key import APIKey

admin_bp = Blueprint("admin_rl", __name__, url_prefix="/admin")


def admin_required(fn):
    """Placeholder admin check; replace with real RBAC."""

    def wrapper(*args, **kwargs):
        if not getattr(g, "user_id", None):
            return jsonify({"error": "auth required"}), 401
        return fn(*args, **kwargs)

    wrapper.__name__ = fn.__name__
    return wrapper


@admin_bp.get("/rate-limits/stats")
@admin_required
def stats():
    if not redis_client:
        return jsonify({"redis": "down"}), 500
    total_banned = len(list(redis_client.scan_iter(match="banned_ip:*")))
    return jsonify({"banned_ips": total_banned})


@admin_bp.get("/api-keys")
@admin_required
def list_keys():
    keys = APIKey.query.filter_by(user_id=g.user_id).all()
    return jsonify({"api_keys": [k.to_dict() for k in keys]})


@admin_bp.post("/api-keys")
@admin_required
def create_key():
    from backend.auth.api_keys import APIKeyManager

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    rl = data.get("rate_limit_override")
    api_key, kid = APIKeyManager.create_api_key(g.user_id, name, rl)
    return jsonify({"api_key": api_key, "key_id": kid, "warning": "Store it now"}), 201


@admin_bp.delete("/api-keys/<int:key_id>")
@admin_required
def delete_key(key_id: int):
    rec = APIKey.query.filter_by(id=key_id, user_id=g.user_id).first()
    if not rec:
        return jsonify({"error": "not found"}), 404
    rec.is_active = False
    db.session.commit()
    return jsonify({"ok": True})


@admin_bp.post("/rate-limits/unban-ip")
@admin_required
def unban_ip():
    ip = (request.get_json() or {}).get("ip")
    try:
        ipaddress.ip_address(ip)
    except Exception:
        return jsonify({"error": "invalid ip"}), 400
    deleted = 0
    if redis_client:
        deleted = redis_client.delete(f"banned_ip:{ip}")
    return jsonify({"deleted": int(deleted)})
