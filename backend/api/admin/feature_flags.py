from flask import Blueprint, jsonify, request, g
import json

from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.utils.logger import create_log

from backend.utils.feature_flags import (
    all_feature_flags,
    feature_flag_enabled,
    set_feature_flag,
    create_feature_flag,
    get_feature_flag_metadata,
)


feature_flags_bp = Blueprint("feature_flags", __name__)


def _log_flag_action(action: str, description: str = "") -> None:
    """Flag işlemlerini logla."""
    user = g.get("user")
    if not user:
        return
    try:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action=action,
            target=request.path,
            description=description,
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    except Exception:
        pass


@feature_flags_bp.route("/feature-flags", methods=["GET"])
@jwt_required_if_not_testing()
def get_feature_flags():
    """Tüm feature flag'leri ve durumlarını döndür."""
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
@jwt_required_if_not_testing()
def update_feature_flag(flag_name):
    """Bir feature flag'i aç veya kapat."""
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
<<<<<<< HEAD
@jwt_required_if_not_testing()
=======
>>>>>>> 7ff5221 (Add tests for feature flag creation metadata)
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
<<<<<<< HEAD
    _log_flag_action("feature_flag_create", f"Yeni flag: {data['name']}")
    return jsonify({"status": "created", "flag": data["name"]})


@feature_flags_bp.route("/feature-flags/export", methods=["GET"])
@jwt_required_if_not_testing()
def export_flags():
    """Tüm flag'leri JSON olarak dışa aktar."""
    from backend.utils.feature_flags import export_all_flags

    try:
        data = json.loads(export_all_flags())
        _log_flag_action("feature_flags_export", "Flagler dışa aktarıldı")
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@feature_flags_bp.route("/feature-flags/import", methods=["POST"])
@jwt_required_if_not_testing()
def import_flags():
    """JSON verisinden flag'leri içe aktar."""
    from backend.utils.feature_flags import import_flags_from_json

    data = request.get_json()
    try:
        import_flags_from_json(json.dumps(data))
        _log_flag_action("feature_flags_import", "Flagler içe aktarıldı")
        return jsonify({"status": "imported"})
    except Exception as e:
        _log_flag_action("feature_flags_import_error", str(e))
        return jsonify({"error": str(e)}), 400


@feature_flags_bp.route("/feature-flags/category/<category>", methods=["GET"])
@jwt_required_if_not_testing()
def get_flags_by_category(category):
    """Belirli kategoriye ait flag'leri döndür."""
    from backend.utils.feature_flags import get_flags_by_category, get_feature_flag_metadata

    flags = get_flags_by_category(category)
    enriched = {}
    for key, val in flags.items():
        meta = get_feature_flag_metadata(key)
        enriched[key] = {
            "enabled": val,
            "description": meta.get("description", ""),
            "category": meta.get("category", "general"),
        }
    _log_flag_action("feature_flags_list_category", f"Kategori: {category}")
    return jsonify(enriched)
=======
    return jsonify({"status": "created", "flag": data["name"]})
>>>>>>> 7ff5221 (Add tests for feature flag creation metadata)
