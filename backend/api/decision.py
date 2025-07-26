from flask import Blueprint, request, jsonify

from backend.decision_engine import extract_features, make_decision
from backend.decision_engine.score_calculator import calculate_score
from backend.engine.strategic_decision_engine import advanced_decision_logic

# Blueprint for lightweight decision endpoints
decision_bp = Blueprint('decision', __name__, url_prefix='/api/decision')


@decision_bp.route('/evaluate', methods=['POST'])
def evaluate_decision():
    """Return decision signal and weighted score for provided indicators."""
    data = request.get_json() or {}

    # Extract normalized features and calculate weighted score
    features = extract_features(data)
    score = calculate_score(features)

    # Map data to inputs expected by advanced_decision_logic
    indicators = {
        'rsi': data.get('rsi'),
        'macd': data.get('macd'),
        'macd_signal': data.get('macd_signal'),
        'price': data.get('price'),
        'sma_10': data.get('sma_10'),
        'prev_predictions_success_rate': data.get('prev_predictions_success_rate', 0),
    }
    decision = advanced_decision_logic(indicators)

    return jsonify({'decision': decision, 'score': score, 'features': features})


@decision_bp.route('/predict', methods=['POST'])
def predict_decision():
    """Return a recommendation based on provided market indicators."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    features = extract_features(data)
    score = calculate_score(features)
    coin = data.get("coin", "UNKNOWN")
    result = make_decision(coin, score)
    return jsonify(result)
