import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import create_app, db
from backend.db.models import PromoCode, SubscriptionPlan, Role, User


def setup_admin(app):
    with app.app_context():
        role = Role.query.filter_by(name="user").first()
        admin = User(username="adminuser", api_key="adminkey", role_id=role.id)
        admin.set_password("pass")
        # flag expected by admin_required
        admin.is_admin = True
        db.session.add(admin)
        db.session.commit()
    return admin


def create_promo(app):
    with app.app_context():
        promo = PromoCode(
            code="TEST",
            plan=SubscriptionPlan.BASIC,
            duration_days=10,
            max_uses=1,
            expires_at=datetime.utcnow() + timedelta(days=5),
        )
        db.session.add(promo)
        db.session.commit()
    return promo


def test_update_expiration_success(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr("flask_jwt_extended.jwt_required", lambda *a, **k: (lambda f: f))
    monkeypatch.setattr("backend.auth.middlewares.admin_required", lambda: (lambda f: f))
    app = create_app()
    client = app.test_client()
    setup_admin(app)
    promo = create_promo(app)

    new_date = datetime.utcnow() + timedelta(days=30)
    resp = client.patch(
        f"/api/admin/promo-codes/{promo.id}/expiration",
        json={"expires_at": new_date.isoformat()},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["expires_at"].startswith(new_date.date().isoformat())


def test_update_expiration_past_date(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr("flask_jwt_extended.jwt_required", lambda *a, **k: (lambda f: f))
    monkeypatch.setattr("backend.auth.middlewares.admin_required", lambda: (lambda f: f))
    app = create_app()
    client = app.test_client()
    setup_admin(app)
    promo = create_promo(app)

    past_date = datetime.utcnow() - timedelta(days=1)
    resp = client.patch(
        f"/api/admin/promo-codes/{promo.id}/expiration",
        json={"expires_at": past_date.isoformat()},
    )
    assert resp.status_code == 400
