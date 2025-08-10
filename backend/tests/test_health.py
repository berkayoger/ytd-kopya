import os
import json

os.environ["FLASK_ENV"] = "testing"

from backend.app import create_app


def test_health_ok():
    app = create_app()
    client = app.test_client()
    rv = client.get("/health")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data.get("status") == "ok"


def test_ready_ok():
    app = create_app()
    client = app.test_client()
    rv = client.get("/ready")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data.get("status") == "ready"
