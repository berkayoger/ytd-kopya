import os
import json
import importlib
import sys
from flask import Flask
from flask_jwt_extended import JWTManager

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["FLASK_ENV"] = "testing"

import backend.app as app_module


def test_health_ok():
    app = app_module.create_app()
    client = app.test_client()
    rv = client.get("/health")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data.get("status") == "ok"


def test_ready_ok():
    app = app_module.create_app()
    client = app.test_client()
    rv = client.get("/ready")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data.get("status") == "ready"


def test_health_requires_auth_when_enabled(monkeypatch):
    """Auth zorunlu olduğunda yetkisiz erişim reddedilmeli."""
    monkeypatch.setenv("REQUIRE_AUTH_FOR_HEALTH", "true")
    monkeypatch.setenv("FLASK_ENV", "development")
    import backend.app.health as health_mod
    importlib.reload(health_mod)
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test"
    JWTManager(app)
    app.register_blueprint(health_mod.bp)
    client = app.test_client()
    rv = client.get("/health")
    assert rv.status_code == 401
    # Ortamı ve modülleri eski haline getir
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.delenv("REQUIRE_AUTH_FOR_HEALTH", raising=False)
    importlib.reload(health_mod)


def test_ready_requires_auth_when_enabled(monkeypatch):
    """Auth zorunlu olduğunda /ready yetkisiz erişimi reddetmeli."""
    monkeypatch.setenv("REQUIRE_AUTH_FOR_HEALTH", "true")
    monkeypatch.setenv("FLASK_ENV", "development")
    import backend.app.health as health_mod
    importlib.reload(health_mod)
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test"
    JWTManager(app)
    app.register_blueprint(health_mod.bp)
    client = app.test_client()
    rv = client.get("/ready")
    assert rv.status_code == 401
    # ortamı geri al
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.delenv("REQUIRE_AUTH_FOR_HEALTH", raising=False)
    importlib.reload(health_mod)
