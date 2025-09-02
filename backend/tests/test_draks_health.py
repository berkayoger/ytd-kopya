import pytest

from backend import create_app, db


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_draks_health_works(app, monkeypatch):
    client = app.test_client()
    res = client.get("/api/draks/health")
    assert res.status_code == 200
    data = res.get_json()
    assert "status" in data and data["status"] in {"ok", "degraded", "error"}
    # enabled alanı her zaman dönmeli
    assert "enabled" in data
