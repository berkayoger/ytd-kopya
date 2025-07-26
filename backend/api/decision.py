from flask import Blueprint, request, jsonify
from backend.decision_engine.feature_extraction import extract_features
from backend.decision_engine.score_calculator import calculate_score
from backend.engine.decision_maker import build_prediction

# Blueprint with url_prefix '/api/decision'
decision_bp = Blueprint("decision", __name__, url_prefix="/api/decision")

@decision_bp.route("/predict", methods=["POST"])
def predict_decision():
    """Calculate decision engine output based on posted indicators."""
    try:
        data = request.get_json() or {}
        coin = data.get("coin", "UNKNOWN")
        features = extract_features(data)
        score = calculate_score(features)
        # convert to decision using existing build_prediction or simple mapping
        decision = {
            "coin": coin,
            "score": score,
        }
        # Use build_prediction if needed for additional info
        try:
            decision.update(build_prediction(
                # expect df-like placeholder; pass features for minimal stub
                features,
                {"signal": "buy" if score > 50 else "avoid", "confidence": score/100}
            ))
        except Exception:
            pass
        return jsonify(decision), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
