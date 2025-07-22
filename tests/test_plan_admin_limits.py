import json
import flask_jwt_extended
import pytest

from backend import create_app, db
from backend.models.plan import Plan


@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f))
    monkeypatch.setattr("backend.auth.jwt_utils.require_csrf", lambda f: f)
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_update_plan_limits(test_app):
    with test_app.app_context():
        plan = Plan(name="basic", price=0.0, features=json.dumps({"predict": 1}))
        from backend.db.models import User, UserRole
        admin = User(username="admin", api_key="adminkey", role=UserRole.ADMIN)
        admin.set_password("pass")
        db.session.add_all([plan, admin])
        db.session.commit()
        pid = plan.id

    client = test_app.test_client()
    headers = {"Authorization": "adminkey"}
    response = client.post(
        f"/api/plans/{pid}/update-limits", json={"predict": 10}, headers=headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["plan"]["features"]["predict"] == 10

    with test_app.app_context():
        updated_plan = Plan.query.get(pid)
        assert json.loads(updated_plan.features)["predict"] == 10


def test_update_plan_limits_unauthorized_access(client):
    # Plan oluşturalım
    with client.application.app_context():
        plan = Plan(name="testplan", price=0.0, features=json.dumps({"predict": 5}))
        db.session.add(plan)
        db.session.commit()

    # Giriş yapılmadan endpoint'e erişmeye çalış
    resp = client.post(f"/api/plans/{plan.id}/update-limits", json={"predict": 10})

    assert resp.status_code in (401, 403)
    data = resp.get_json()
    assert "error" in data or "msg" in data
