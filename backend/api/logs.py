from flask import Blueprint, request, jsonify

from backend.models.log import Log


logs_bp = Blueprint("logs", __name__, url_prefix="/api/admin/logs")


@logs_bp.route("", methods=["GET"])
def get_logs():
    """Return paginated log entries optionally filtered by search string."""

    query = Log.query

    search = request.args.get("search")
    if search:
        query = query.filter(Log.description.ilike(f"%{search}%"))

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    pagination = (
        query.order_by(Log.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    )

    return jsonify(
        {
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "logs": [log.to_dict() for log in pagination.items],
        }
    )

