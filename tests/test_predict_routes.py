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


