import os
import sys

import pytest
from flask import Flask

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.api.decision import decision_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(decision_bp)
    app.testing = True
    return app.test_client()


def test_predict_decision_success(client):
    response = client.post(
        "/api/decision/predict",
        json={
            "coin": "BTC",
            "rsi": 45,
            "macd": 1.2,
            "macd_signal": 0.9,
            "sma_7": 105,
            "sma_30": 100,
            "prev_success_rate": 0.7,
            "sentiment_score": 0.2,
            "news_count": 10,
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "recommendation" in data
    assert "score" in data
    assert data["coin"] == "BTC"


def test_predict_decision_invalid_json(client):
    response = client.post(
        "/api/decision/predict", data="invalid json", content_type="application/json"
    )
    assert response.status_code == 400
    assert "error" in response.get_json()
