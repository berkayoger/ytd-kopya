import os, sys
from datetime import datetime, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend import create_app, db
from backend.db.models import User, Role, UserRole
from backend.models.plan import Plan
from flask import g
import flask_jwt_extended
from backend.utils.plan_limits import get_user_effective_limits, give_user_boost
from backend.db.models import UsageLog


def create_test_client(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f))
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
    return app.test_client()


def create_user(app, plan="basic"):
    with app.app_context():
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
            db.session.commit()
        user = User(username="planuser", api_key="apikey", role_id=role.id, role=UserRole.USER)
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()
    return user


def log_usage(app, user_id, action):
    with app.app_context():
        log = UsageLog(user_id=user_id, action=action, timestamp=datetime.utcnow())
        db.session.add(log)
        db.session.commit()


def setup_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    return create_app()


def test_effective_limits_with_boost(monkeypatch):
    app = setup_app(monkeypatch)
    with app.app_context():
        role = Role.query.filter_by(name="user").first()
        p = Plan(name="LimitPlan", price=0.0, features="{\"max_prediction_per_day\": 5}")
        db.session.add(p)
        db.session.commit()
        user = User(username="limituser", api_key="limitkey", role_id=role.id, role=UserRole.USER, plan_id=p.id)
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()
        give_user_boost(user, {"max_prediction_per_day": 10}, datetime.utcnow() + timedelta(days=1))
        limits = get_user_effective_limits(user)
        assert limits["max_prediction_per_day"] == 10


def test_plan_limit_exceeded(monkeypatch):
    client = create_test_client(monkeypatch)
    app = client.application
    user = create_user(app)

    for _ in range(10):
        log_usage(app, user.id, "predict_daily")

    resp = client.post("/api/predict/", headers={"X-API-KEY": user.api_key})
    assert resp.status_code == 429
