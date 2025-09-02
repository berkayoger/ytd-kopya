import pytest
from flask import g

from backend import create_app, db
from backend.db.models import Role, User, UserRole


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr("backend.Config.SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    monkeypatch.setattr("backend.Config.SQLALCHEMY_ENGINE_OPTIONS", {}, raising=False)
    import flask_jwt_extended

    admin_user = None

    def fake_jwt_required(*args, **kwargs):
        def decorator(fn):
            from functools import wraps

            @wraps(fn)
            def wrapper(*a, **kw):
                g.user = admin_user
                return fn(*a, **kw)

            return wrapper

        return decorator

    monkeypatch.setattr(
        flask_jwt_extended, "jwt_required", fake_jwt_required, raising=False
    )
    monkeypatch.setattr(
        "backend.auth.middlewares.admin_required", lambda: (lambda f: f)
    )

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        admin_role = Role.query.filter_by(name="admin").first() or Role(name="admin")
        user_role = Role.query.filter_by(name="user").first() or Role(name="user")
        db.session.add_all([admin_role, user_role])
        db.session.commit()

        admin = User(
            username="admin",
            email="admin@example.com",
            api_key="adminkey",
            role=UserRole.ADMIN,
            role_id=admin_role.id,
        )
        admin.set_password("x")
        db.session.add(admin)
        db.session.commit()
        admin_user = admin

        u1 = User(
            username="alice",
            email="alice@example.com",
            api_key="alicekey",
            role=UserRole.USER,
            role_id=user_role.id,
        )
        u1.set_password("a")
        u2 = User(
            username="bob",
            email="bob@example.com",
            api_key="bobkey",
            role=UserRole.USER,
            role_id=user_role.id,
        )
        u2.set_password("b")
        db.session.add_all([u1, u2])
        db.session.commit()

    return app.test_client()


def test_admin_list_users(client):
    resp = client.get("/api/admin/users/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 3
    row = data[0]
    assert "id" in row
    assert "username" in row
    assert "email" in row
    assert "subscription_level" in row
