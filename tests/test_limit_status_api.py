import json
import flask_jwt_extended
import pytest

from backend import create_app, db
from flask import g
from backend.db.models import User, Role, UserRole, UsageLog
from backend.models.plan import Plan
from backend.models.log import Log


@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f))
    monkeypatch.setattr("backend.auth.jwt_utils.require_csrf", lambda f: f)
    monkeypatch.setattr(
        "backend.utils.feature_flags.feature_flag_enabled", lambda name: True
    )
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(test_app):
    with test_app.app_context():
        role = Role.query.filter_by(name="user").first()
        plan = Plan(
            name="basic",
            price=0.0,
            features=json.dumps({"predict_daily": 5, "api_request_daily": 100}),
        )
        db.session.add(plan)
        db.session.commit()
        user = User(username="limitstatus", role=UserRole.USER, plan_id=plan.id)
        user.set_password("pass")
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()

        from datetime import datetime, timedelta

        now = datetime.utcnow()
        db.session.add(UsageLog(user_id=user.id, action="api_request", timestamp=now))
        db.session.add(
            UsageLog(
                user_id=user.id,
                action="api_request",
                timestamp=now - timedelta(days=1),
            )
        )
        db.session.add(
            UsageLog(
                user_id=user.id,
                action="api_request",
                timestamp=now.replace(day=1),
            )
        )
        db.session.commit()

        return user


def test_limit_status_endpoint(test_app, test_user):
    with test_app.app_context():
        token = test_user.generate_access_token()
    client = test_app.test_client()
    with test_app.app_context():
        g.user = db.session.merge(test_user)
        resp = client.get(
            "/api/limits/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["plan"] == "basic"
    assert data["limits"]["daily_requests"]["used"] >= 1
    assert data["limits"]["daily_requests"]["max"] == 100
    log = Log.query.filter_by(action="limit_status").first()
    assert log is not None
    assert log.user_id == str(test_user.id)


def test_limit_status_flag_disabled(test_app, test_user, monkeypatch):
    monkeypatch.setattr(
        "backend.api.limits.feature_flag_enabled", lambda name: False
    )
    client = test_app.test_client()
    with test_app.app_context():
        g.user = db.session.merge(test_user)
        resp = client.get("/api/limits/status")
    assert resp.status_code == 403
