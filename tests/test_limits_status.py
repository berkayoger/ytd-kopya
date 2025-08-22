import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"



def _noop(*_a, **_k):
    def wrap(f):
        return f
    return wrap


def setup_app(monkeypatch):
    # jwt/limit dekoratörleri no-op
    monkeypatch.setattr("backend.api.routes.jwt_required", lambda *a, **k: _noop(), raising=False)
    try:
        import backend.api.routes as routes
        setattr(routes, "limiter", SimpleNamespace(limit=lambda *_a, **_k: _noop()))
    except Exception:
        pass

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    from backend import create_app
    from backend.db import db
    from backend.db.models import User
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
    with app.app_context():
        db.create_all()
        u = User(id="u1", email="t@t.t", username="t", password_hash="x", subscription_level="BASIC", is_active=True)
        db.session.add(u)
        db.session.commit()

    @app.before_request
    def _inject_user():
        from flask import g
        g.user = SimpleNamespace(id="u1", username="t", subscription_level="BASIC")

    monkeypatch.setattr("backend.api.routes.get_jwt_identity", lambda: "u1", raising=False)
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
