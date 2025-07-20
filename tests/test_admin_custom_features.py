import json
import pytest

from backend import create_app, db
from backend.db.models import User, Role, UserRole


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr("backend.Config.SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    monkeypatch.setattr("backend.Config.SQLALCHEMY_ENGINE_OPTIONS", {}, raising=False)
    import flask_jwt_extended
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f), raising=False)
    monkeypatch.setattr(flask_jwt_extended, "fresh_jwt_required", lambda *a, **k: (lambda f: f), raising=False)
    monkeypatch.setattr("backend.auth.middlewares.admin_required", lambda: (lambda f: f))
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        role = Role.query.filter_by(name="admin").first()
        if not role:
            role = Role(name="admin")
            db.session.add(role)
            db.session.commit()
        user = User(username="admin", api_key="adminkey", role=UserRole.ADMIN, role_id=role.id)
        user.set_password("adminpass")
        db.session.add(user)
        db.session.commit()
    return app.test_client()


def test_set_custom_features_valid(client):
    user_id = 1
    valid_payload = {"custom_features": json.dumps({"can_export": True, "limit": 5})}
    resp = client.post(
        f"/api/admin/users/{user_id}/custom-features",
        json=valid_payload,
        headers={"X-API-KEY": "adminkey"},
    )
    assert resp.status_code == 200
    assert resp.get_json().get("message") == "Custom features güncellendi."


def test_set_custom_features_invalid_json(client):
    user_id = 1
    invalid_payload = {"custom_features": "{invalid: json,"}
    resp = client.post(
        f"/api/admin/users/{user_id}/custom-features",
        json=invalid_payload,
        headers={"X-API-KEY": "adminkey"},
    )
    assert resp.status_code == 400
    assert resp.get_json().get("error") == "Geçersiz JSON"


def test_set_custom_features_user_not_found(client):
    resp = client.post(
        "/api/admin/users/999/custom-features",
        json={"custom_features": "{}"},
        headers={"X-API-KEY": "adminkey"},
    )
    assert resp.status_code == 404
    assert resp.get_json().get("error") == "Kullanıcı bulunamadı."
