from flask import Blueprint, jsonify, request

from backend.utils.feature_flags import all_feature_flags, set_feature_flag


feature_flags_bp = Blueprint("feature_flags", __name__)


@feature_flags_bp.route("/feature-flags", methods=["GET"])
def get_feature_flags():
    """Return a mapping of feature flags and their states."""
    flags = all_feature_flags()
    return jsonify(flags)


@feature_flags_bp.route("/feature-flags", methods=["PUT"])
def update_feature_flags():
    """Update one or more feature flags."""
    updates = request.json
    if not isinstance(updates, dict):
        return jsonify({"error": "Invalid payload"}), 400

    applied = {}
    for flag, value in updates.items():
        if isinstance(value, bool):
            set_feature_flag(flag, value)
            applied[flag] = value

    return jsonify({
        "updated": applied,
        "all_flags": all_feature_flags()
    })

