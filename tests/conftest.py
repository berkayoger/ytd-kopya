import os
import sys

import pytest
from flask import Flask

# Proje kökünü sys.path'e ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def app():
    """Minimal Flask app for tests."""
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    with app.app_context():
        yield app

