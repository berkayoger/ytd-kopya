from flask import Blueprint, jsonify
from backend.db.models import TechnicalIndicator

bp = Blueprint('ta', __name__)


@bp.route('/api/technical/latest')
def latest_ta():
    latest = TechnicalIndicator.query.order_by(TechnicalIndicator.created_at.desc()).first()
    return jsonify(latest.to_dict() if latest else {}), 200
