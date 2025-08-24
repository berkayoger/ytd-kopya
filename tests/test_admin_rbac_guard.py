from backend import create_app
from backend.auth import roles as roles_mod


def _add_dummy_admin_route(app):
    # Gerçek admin uçlarına bağlı kalmamak için testte geçici bir yol ekliyoruz
    @app.route("/api/admin/__rbac_test")
    def _rbac_test():
        return "ok", 200


def test_admin_guard_forbids_without_admin(monkeypatch):
    app = create_app()
    _add_dummy_admin_route(app)

    # JWT doğrulamasını no-op yap, roller boş kalsın
    monkeypatch.setattr(roles_mod, "verify_jwt_in_request", lambda optional=False: None)
    monkeypatch.setattr(roles_mod, "current_roles", lambda: set())

    client = app.test_client()
    resp = client.get("/api/admin/__rbac_test", headers={"Authorization": "Bearer test"})
    assert resp.status_code == 403
    assert resp.json["error"] == "forbidden"


def test_admin_guard_allows_with_admin(monkeypatch):
    app = create_app()
    _add_dummy_admin_route(app)

    # JWT doğrulaması no-op, admin rolü mevcut
    monkeypatch.setattr(roles_mod, "verify_jwt_in_request", lambda optional=False: None)
    monkeypatch.setattr(roles_mod, "current_roles", lambda: {"admin"})

    client = app.test_client()
    resp = client.get("/api/admin/__rbac_test", headers={"Authorization": "Bearer test"})
    assert resp.status_code == 200
    assert resp.data.decode() == "ok"
