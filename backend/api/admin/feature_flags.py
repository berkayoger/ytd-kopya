from flask import Blueprint, jsonify

from backend.utils.feature_flags import all_feature_flags


feature_flags_bp = Blueprint("feature_flags", __name__)


@feature_flags_bp.route("/feature-flags", methods=["GET"])
def get_feature_flags():
    """Return a mapping of feature flags and their states."""
    flags = all_feature_flags()
    return jsonify(flags)

