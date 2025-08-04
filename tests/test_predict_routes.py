"""Tests for prediction routes."""

import pytest
from flask import Flask

from backend.routes.predict_routes import predict_bp


@pytest.fixture
def test_app():
    """Create a Flask test client with the prediction blueprint."""

    app = Flask(__name__)
    app.register_blueprint(predict_bp, url_prefix="/api")
    app.config["TESTING"] = True
    return app.test_client()


def test_recommend_endpoint_enabled(test_app):
    """``/api/recommend`` should respond with data or an error."""

    response = test_app.post("/api/recommend")
    assert response.status_code in [200, 403]
    data = response.get_json()
    if response.status_code == 200:
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) <= 5
    else:
        assert "error" in data


def test_recommend_endpoint_method_not_allowed(test_app):
    """Only POST method should be allowed on ``/api/recommend``."""

    response = test_app.get("/api/recommend")
    assert response.status_code == 405

