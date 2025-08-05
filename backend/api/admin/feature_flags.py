from flask import Blueprint, jsonify, request

from backend.utils.feature_flags import (
    all_feature_flags,
    feature_flag_enabled,
    set_feature_flag,
    create_feature_flag,
    get_feature_flag_metadata,
)


feature_flags_bp = Blueprint("feature_flags", __name__)


@feature_flags_bp.route("/feature-flags", methods=["GET"])
def get_feature_flags():
    """Return a mapping of feature flags and their states."""
    flags = all_feature_flags()
    enriched = {}
    for key, val in flags.items():
        meta = get_feature_flag_metadata(key)
        enriched[key] = {
            "enabled": val,
            "description": meta.get("description", ""),
            "category": meta.get("category", "general"),
        }
    return jsonify(enriched)


@feature_flags_bp.route("/feature-flags/<flag_name>", methods=["POST"])
def update_feature_flag(flag_name):
    """Enable or disable a feature flag."""
    data = request.get_json()
    if not data or "enabled" not in data:
        return jsonify({"error": "Missing 'enabled' field"}), 400
    try:
        enabled = bool(data["enabled"])
        set_feature_flag(flag_name, enabled)
        return jsonify({flag_name: feature_flag_enabled(flag_name)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@feature_flags_bp.route("/feature-flags/create", methods=["POST"])
def create_flag():
    data = request.get_json()
    required_fields = ["name", "enabled"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    create_feature_flag(
        flag_name=data["name"],
        enabled=bool(data["enabled"]),
        description=data.get("description", ""),
        category=data.get("category", "general"),
    )
    return jsonify({"status": "created", "flag": data["name"]})
