import json
import pytest
from backend import create_app, db
from backend.models.plan import Plan
from backend.auth import jwt_utils
from flask import jsonify
import flask_jwt_extended

@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f))
    monkeypatch.setattr("backend.auth.jwt_utils.require_admin", lambda f: f)
    monkeypatch.setattr("backend.auth.jwt_utils.require_csrf", lambda f: f)
    import sys
    sys.modules.pop("backend.api.plan_admin_limits", None)

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def test_full_plan_crud_flow(admin_client):
    # CREATE
    payload = {
        "name": "gold",
        "price": 29.99,
        "features": {"predict": 200, "analytics": 50},
    }
    resp_create = admin_client.post("/api/plans/create", json=payload)
    assert resp_create.status_code == 201
    created = resp_create.get_json()
    assert created["name"] == "gold"
    assert created["features"]["predict"] == 200
    pid = created["id"]

    # UPDATE
    update_payload = {"predict": 500, "analytics": 100}
    resp_update = admin_client.post(f"/api/plans/{pid}/update-limits", json=update_payload)
    assert resp_update.status_code == 200
    updated = resp_update.get_json()
    assert updated["plan"]["features"]["predict"] == 500

    # GET ALL
    resp_all = admin_client.get("/api/plans/all")
    assert resp_all.status_code == 200
    plans = resp_all.get_json()
    assert any(p["name"] == "gold" for p in plans)

    # DELETE
    resp_delete = admin_client.delete(f"/api/plans/{pid}")
    assert resp_delete.status_code == 200
    deleted = resp_delete.get_json()
    assert deleted["success"] is True

    # CONFIRM DELETE
    resp_check = admin_client.get("/api/plans/all")
    plans_after = resp_check.get_json()
    assert not any(p["id"] == pid for p in plans_after)


def test_create_plan_unauthorized(monkeypatch):
    from backend import create_app
    import flask_jwt_extended
    import sys

    monkeypatch.setenv("FLASK_ENV", "testing")
    sys.modules.pop("backend.api.plan_admin_limits", None)

    def unauthorized_decorator(func):
        def wrapper(*args, **kwargs):
            return jsonify({"error": "Missing Authorization Header"}), 401

        wrapper.__name__ = func.__name__
        return wrapper

    monkeypatch.setattr(
        flask_jwt_extended, "jwt_required", lambda *a, **kw: (lambda f: unauthorized_decorator(f))
    )

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.post("/api/plans/create", json={"name": "unauth"})
        assert res.status_code == 401


def test_create_plan_forbidden_without_admin(monkeypatch):
    from backend import create_app
    from backend.auth import jwt_utils
    import flask_jwt_extended
    import sys

    monkeypatch.setenv("FLASK_ENV", "testing")
    sys.modules.pop("backend.api.plan_admin_limits", None)

    def forbid_admin(func):
        def wrapper(*args, **kwargs):
            return jsonify({"error": "Admin değil"}), 403

        wrapper.__name__ = func.__name__
        return wrapper

    monkeypatch.setattr(jwt_utils, "require_admin", forbid_admin)
    monkeypatch.setattr(jwt_utils, "require_csrf", lambda f: f)
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", lambda *a, **kw: (lambda f: f))

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.post("/api/plans/create", json={"name": "forbidden"})
        assert res.status_code in (403, 500)
        assert "Admin değil" in res.get_json().get("error", "")


def test_update_nonexistent_plan(admin_client):
    res = admin_client.post("/api/plans/999999/update-limits", json={"predict": 100})
    assert res.status_code == 404
    assert "Plan bulunamadı" in res.get_json().get("error", "")


def test_create_plan_invalid_payload(admin_client):
    res = admin_client.post("/api/plans/create", json={"name": "x", "features": "invalid"})
    assert res.status_code == 400
    assert "Geçersiz plan verileri" in res.get_json().get("error", "")


def test_update_plan_invalid_limit_type(admin_client):
    payload = {"name": "trial", "price": 0.0, "features": {"predict": 10}}
    created = admin_client.post("/api/plans/create", json=payload).get_json()
    pid = created["id"]

    res = admin_client.post(f"/api/plans/{pid}/update-limits", json={"predict": "abc"})
    assert res.status_code == 400
    assert "geçersiz limit değeri" in res.get_json().get("error", "")


def test_unauthorized_plan_access(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    import flask_jwt_extended
    monkeypatch.setattr(flask_jwt_extended, "jwt_required", lambda *a, **k: (lambda f: f))
    monkeypatch.setattr("backend.auth.jwt_utils.require_csrf", lambda f: f)

    from backend.auth import jwt_utils

    import sys
    sys.modules.pop("backend.api.plan_admin_limits", None)

    def deny_admin(fn):
        def wrapper(*args, **kwargs):
            return jsonify({"error": "Admin yetkisi gereklidir!"}), 403

        wrapper.__name__ = fn.__name__
        return wrapper

    monkeypatch.setattr(jwt_utils, "require_admin", deny_admin)

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    resp = client.get("/api/plans/all")
    assert resp.status_code in (401, 403)

    resp = client.post("/api/plans/create", json={"name": "x", "features": {"predict": 1}})
    assert resp.status_code in (401, 403)

    resp = client.delete("/api/plans/1")
    assert resp.status_code in (401, 403)


def test_create_plan_invalid_input(admin_client):
    # Missing name
    resp = admin_client.post("/api/plans/create", json={"price": 10})
    assert resp.status_code == 400

    # Invalid features
    resp2 = admin_client.post(
        "/api/plans/create", json={"name": "invalid", "features": "not-dict"}
    )
    assert resp2.status_code == 400


def test_update_plan_invalid_features(admin_client):
    # Create a valid plan first
    create = admin_client.post(
        "/api/plans/create", json={"name": "silver", "features": {"predict": 10}}
    )
    pid = create.get_json()["id"]

    # Try invalid update (string instead of int)
    update = admin_client.post(f"/api/plans/{pid}/update-limits", json={"predict": "abc"})
    assert update.status_code == 400

    # Try negative number
    update2 = admin_client.post(f"/api/plans/{pid}/update-limits", json={"predict": -5})
    assert update2.status_code == 400

    # Valid update
    valid = admin_client.post(f"/api/plans/{pid}/update-limits", json={"predict": 999})
    assert valid.status_code == 200
