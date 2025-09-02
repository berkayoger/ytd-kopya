import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["FLASK_ENV"] = "testing"
from backend import create_app
from backend.db import db
from backend.db.models import User


def _noop(*_a, **_k):
    def wrap(f):
        return f

    return wrap


def setup_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr(
        "flask_jwt_extended.jwt_required", lambda *a, **k: _noop(), raising=False
    )
    monkeypatch.setattr(
        "flask_jwt_extended.view_decorators.jwt_required",
        lambda *a, **k: _noop(),
        raising=False,
    )
    # jwt/limit dekoratörleri no-op
    try:
        import backend.api.routes as routes

        setattr(routes, "limiter", SimpleNamespace(limit=lambda *_a, **_k: _noop()))
        monkeypatch.setattr(
            "backend.utils.plan_limits.get_user_effective_limits",
            lambda user_id, feature_key: {
                "plan_name": "BASIC",
                "daily_quota": 0,
                "burst_per_minute": 0,
            },
        )
        monkeypatch.setattr(
            "backend.utils.usage_limits.get_user_effective_limits",
            lambda user_id, feature_key: {
                "plan_name": "BASIC",
                "daily_quota": 0,
                "burst_per_minute": 0,
            },
        )
        monkeypatch.setattr("backend.utils.usage_limits._r", lambda: None)
        monkeypatch.setattr("backend.utils.usage_limits._inc_db", lambda uid, fk: 0)
        monkeypatch.setattr("backend.utils.usage_limits._get_db", lambda uid, fk: 0)
    except Exception:
        pass
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
    with app.app_context():
        db.create_all()
        u = User(
            id=1,
            email="t@t.t",
            username="t",
            password_hash="x",
            api_key="k",
            subscription_level="BASIC",
            is_active=True,
        )
        db.session.add(u)
        db.session.commit()

    @app.before_request
    def _inject_user():
        from flask import g

        g.user = SimpleNamespace(id=1, username="t", subscription_level="BASIC")

    monkeypatch.setattr("backend.api.routes.get_jwt_identity", lambda: 1, raising=False)
    return app


def test_limits_status_endpoint(monkeypatch):
    app = setup_app(monkeypatch)
    client = app.test_client()
    resp = client.get("/api/limits/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["plan"]
    assert "features" in data
    assert isinstance(data["features"], dict)
