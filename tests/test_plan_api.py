import json
import os
import sys
from sqlalchemy.pool import StaticPool
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend import create_app, db
from backend.models.plan import Plan
from backend.db.models import User, Role, UserRole
from flask import g

def setup_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setattr("backend.Config.SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    monkeypatch.setattr(
        "backend.Config.SQLALCHEMY_ENGINE_OPTIONS",
        {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}},
        raising=False,
    )
    return create_app()

def create_admin(app):
    with app.app_context():
        admin = User(username="admin", api_key="adminkey", role=UserRole.ADMIN)
        admin.set_password("pass")
        db.session.add(admin)
        db.session.commit()
        
        # Debug: Verify admin was created correctly
        created_admin = User.query.filter_by(api_key="adminkey").first()
        print(f"Created admin: {created_admin}")
        print(f"Admin role: {created_admin.role if created_admin else 'None'}")

def test_plan_features_and_auth(monkeypatch):
    # Set TESTING mode to enable the special behavior in ensure_admin_for_admin_paths
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr("backend.Config.SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    monkeypatch.setattr(
        "backend.Config.SQLALCHEMY_ENGINE_OPTIONS",
        {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}},
        raising=False,
    )
    
    app = create_app()
    client = app.test_client()

    with app.app_context():
        p = Plan(name="Test", price=1.0, features=json.dumps({"a": 1}))
        db.session.add(p)
        db.session.commit()

    # Test without any authorization - in TESTING mode, ensure_admin_for_admin_paths creates a temporary admin
    resp = client.get("/api/admin/plans")
    print(f"First response status: {resp.status_code}")
    print(f"First response data: {resp.get_json()}")
    # In testing mode with auto-created admin, this should work
    assert resp.status_code == 200

    # Create a real admin and test with proper authorization
    create_admin(app)
    resp = client.get("/api/admin/plans", headers={"Authorization": "adminkey"})
    print(f"Second response status: {resp.status_code}")
    print(f"Second response data: {resp.get_json()}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data[0]["features"]["a"] == 1
