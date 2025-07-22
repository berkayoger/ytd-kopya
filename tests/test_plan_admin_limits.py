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
    monkeypatch.setattr("backend.auth.middlewares.admin_required", lambda: (lambda f: f))
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
        db.session.add(plan)
        db.session.commit()
        pid = plan.id

    client = test_app.test_client()
    resp = client.post(f"/api/plans/{pid}/update-limits", json={"predict": 5})
    assert resp.status_code == 200
    with test_app.app_context():
        updated = Plan.query.get(pid)
        assert json.loads(updated.features)["predict"] == 5
