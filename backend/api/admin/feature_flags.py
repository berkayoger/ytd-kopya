from flask import Blueprint, jsonify, request

from backend.utils.feature_flags import (
    all_feature_flags,
    feature_flag_enabled,
    set_feature_flag,
)


feature_flags_bp = Blueprint("feature_flags", __name__)


@feature_flags_bp.route("/feature-flags", methods=["GET"])
def get_feature_flags():
    """Return a mapping of feature flags and their states."""
    flags = all_feature_flags()
    return jsonify(flags)


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
