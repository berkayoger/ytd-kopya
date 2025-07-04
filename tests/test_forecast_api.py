import sys
import os
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend import create_app, db
from backend.db.models import User, Role, SubscriptionPlan


def setup_user(app):
    with app.app_context():
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
            db.session.commit()
        user = User(username="forecast", api_key="fkey", role_id=role.id, subscription_level=SubscriptionPlan.PREMIUM)
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()
    return user


def test_forecast_success(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    client = app.test_client()
    user = setup_user(app)

    def fake_collect(_coin):
        return {"prices": [1]*30, "times": ["2025-01-01"]*30}

    def fake_forecast(prices, times, days=1, coin_name=None):
        preds = [10.0] * days
        bounds = {"upper": [11.0]*days, "lower": [9.0]*days}
        dates = [f"2025-01-{i+1:02d}" for i in range(days)]
        return preds, "prophet", bounds, dates, 0.8, "test"

    monkeypatch.setattr(app.ytd_system_instance, "collector", SimpleNamespace(collect_price_data=fake_collect))
    monkeypatch.setattr(app.ytd_system_instance, "ai", SimpleNamespace(forecast=fake_forecast))

    resp = client.get("/api/forecast/bitcoin?days=3", headers={"X-API-KEY": user.api_key})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["days"] == 3
    assert len(data["forecast"]) == 3
    assert data["explanation"] == "test"


def test_forecast_invalid_days(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    client = app.test_client()
    user = setup_user(app)
    resp = client.get("/api/forecast/bitcoin?days=abc", headers={"X-API-KEY": user.api_key})
    assert resp.status_code == 400


def test_forecast_unavailable(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    client = app.test_client()
    user = setup_user(app)

    def fake_collect(_coin):
        return {"prices": [1]*30, "times": ["2025-01-01"]*30}

    def fake_forecast(prices, times, days=1, coin_name=None):
        return None, "error", {"upper": None, "lower": None}, [], 0.0, ""

    monkeypatch.setattr(app.ytd_system_instance, "collector", SimpleNamespace(collect_price_data=fake_collect))
    monkeypatch.setattr(app.ytd_system_instance, "ai", SimpleNamespace(forecast=fake_forecast))

    resp = client.get("/api/forecast/bitcoin?days=3", headers={"X-API-KEY": user.api_key})
    assert resp.status_code == 503
