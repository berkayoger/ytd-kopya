import json
import pytest
from flask import g

from backend import create_app, db
from backend.db.models import User, Role, UserRole


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
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", fake_jwt_required, raising=False)
    monkeypatch.setattr(flask_jwt_extended, "fresh_jwt_required", lambda *a, **k: (lambda f: f), raising=False)
    monkeypatch.setattr("backend.auth.middlewares.admin_required", lambda: (lambda f: f))
    app = create_app()
    # Global admin guard'ı aşmak için JWT doğrulamasını bypass et
    monkeypatch.setattr("backend.auth.roles.verify_jwt_in_request", lambda optional=False: None)
    monkeypatch.setattr("backend.auth.roles.current_roles", lambda: {"admin"})
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        role = Role.query.filter_by(name="admin").first()
        if not role:
            role = Role(name="admin")
            db.session.add(role)
            db.session.commit()
        admin = User(username="admin", api_key="adminkey", role=UserRole.ADMIN, role_id=role.id)
        admin.set_password("adminpass")
        db.session.add(admin)
        db.session.commit()
        admin_user = admin
    return app.test_client()


@pytest.fixture
def admin_headers():
    return {"X-API-KEY": "adminkey"}


@pytest.fixture
def test_user(client):
    with client.application.app_context():
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
            db.session.commit()
        user = User(username="tester", api_key="testkey", role=UserRole.USER, role_id=role.id)
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()
    return user


def test_admin_can_update_custom_features(client, admin_headers, test_user):
    payload = {
        "can_export_csv": True,
        "predict_daily": 99,
    }

    res = client.put(
        f"/api/admin/users/{test_user.id}/custom_features",
        headers=admin_headers,
        json=payload,
    )

    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    from backend.db.models import User
    with client.application.app_context():
        updated = User.query.get(test_user.id)
        features = json.loads(updated.custom_features)
    assert features["can_export_csv"] is True
    assert features["predict_daily"] == 99

    res_get = client.get(
        f"/api/admin/users/{test_user.id}/custom_features",
        headers=admin_headers,
    )
    assert res_get.status_code == 200
    data_get = res_get.get_json()
    assert data_get["custom_features"]["predict_daily"] == 99


def test_update_custom_features_invalid_json(client, admin_headers, test_user):
    invalid_payload = ["invalid"]
    resp = client.put(
        f"/api/admin/users/{test_user.id}/custom_features",
        json=invalid_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.get_json().get("error") == "Geçersiz veri"


def test_update_custom_features_user_not_found(client, admin_headers):
    resp = client.put(
        "/api/admin/users/999/custom_features",
        json={},
        headers=admin_headers,
    )
    assert resp.status_code == 404
    assert resp.get_json().get("error") == "Kullanıcı bulunamadı"


def test_update_custom_features_invalid_user_id(client, admin_headers):
    resp = client.get(
        "/api/admin/users/notint/custom_features",
        headers=admin_headers,
    )
    assert resp.status_code == 404
    assert resp.get_json().get("error") == "Kullanıcı bulunamadı"

