import json
import flask_jwt_extended
import pytest
from flask import jsonify

from backend import create_app, db
from backend.models.plan import Plan


@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr(
        flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f)
    )
    monkeypatch.setattr("backend.auth.jwt_utils.require_csrf", lambda f: f)
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr(
        flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f)
    )
    monkeypatch.setattr("backend.auth.jwt_utils.require_csrf", lambda f: f)
    from backend.auth import jwt_utils

    monkeypatch.setattr(jwt_utils, "require_admin", lambda f: f)
    import sys

    sys.modules.pop("backend.api.plan_admin_limits", None)
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def unauthorized_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr(
        flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f)
    )
    monkeypatch.setattr("backend.auth.jwt_utils.require_csrf", lambda f: f)

    import sys
    from backend.auth import jwt_utils

    def deny_decorator(func):
        def wrapper(*args, **kwargs):
            return jsonify({"error": "Admin yetkisi gereklidir!"}), 403

        wrapper.__name__ = func.__name__
        return wrapper

    monkeypatch.setattr(jwt_utils, "require_admin", deny_decorator)
    sys.modules.pop("backend.api.plan_admin_limits", None)

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_update_plan_limits(test_app, monkeypatch):
    from backend.auth import jwt_utils

    # Skip admin check
    monkeypatch.setattr(jwt_utils, "require_admin", lambda f: f)
    with test_app.app_context():
        plan = Plan(name="basic", price=0.0, features=json.dumps({"predict": 1}))
        from backend.db.models import User, UserRole

        admin = User(username="admin", api_key="adminkey", role=UserRole.ADMIN)
        admin.set_password("pass")
        db.session.add_all([plan, admin])
        db.session.commit()
        pid = plan.id

    client = test_app.test_client()
    response = client.post(f"/api/plans/{pid}/update-limits", json={"predict": 10})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["plan"]["features"]["predict"] == 10
    assert data["plan"]["old_features"] == {"predict": 1}

    with test_app.app_context():
        updated_plan = Plan.query.get(pid)
        assert json.loads(updated_plan.features)["predict"] == 10


def test_update_plan_limits_unauthorized_access(unauthorized_app):
    with unauthorized_app.app_context():
        plan = Plan(name="unauth", price=0.0, features=json.dumps({"predict": 2}))
        db.session.add(plan)
        db.session.commit()
        pid = plan.id

    client = unauthorized_app.test_client()
    resp = client.post(f"/api/plans/{pid}/update-limits", json={"predict": 10})

    assert resp.status_code in (401, 403)
    data = resp.get_json()
    assert "error" in data or "msg" in data


def test_get_all_plans(admin_app):
    with admin_app.app_context():
        Plan.query.delete()
        db.session.add_all(
            [
                Plan(name="basic", price=0.0, features=json.dumps({"predict": 1})),
                Plan(name="pro", price=1.0, features=json.dumps({"predict": 2})),
            ]
        )
        db.session.commit()

    client = admin_app.test_client()
    resp = client.get("/api/plans/all")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
