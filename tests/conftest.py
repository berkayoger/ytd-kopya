import os
import sys

import pytest
from backend import create_app, db as _db, Config

# Proje kökünü sys.path'e ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def app(monkeypatch):
    """Tam uygulama (in-memory DB ile)"""
    def _noop_decorator(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]
        def _wrap(f):
            return f
        return _wrap

    monkeypatch.setattr("backend.utils.decorators.require_subscription_plan", lambda *_a, **_k: _noop_decorator, raising=False)
    monkeypatch.setattr("backend.utils.usage_limits.check_usage_limit", lambda *_a, **_k: _noop_decorator, raising=False)
    monkeypatch.setattr("backend.limiting.limiter.limit", lambda *_a, **_k: _noop_decorator, raising=False)

    Config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    Config.SQLALCHEMY_ENGINE_OPTIONS = {}
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """SQLAlchemy veritabanı örneği"""
    return _db


@pytest.fixture(autouse=True)
def _jwt_noop(monkeypatch):
    """JWT kontrollerini testlerde devre dışı bırak."""
    import flask_jwt_extended
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f), raising=False)
    monkeypatch.setattr(flask_jwt_extended, "jwt_required_if_not_testing", lambda *a, **k: (lambda f: f), raising=False)

