import json
from datetime import datetime, timedelta

import pytest

from backend import create_app, db
from backend.db.models import User, SubscriptionPlan, UserRole
from backend.models.plan import Plan
from backend.utils.feature_flags import set_feature_flag


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def user(app):
    with app.app_context():
        plan = Plan(name="basic", price=0.0, features=json.dumps({"draks_decision": 1}))
        db.session.add(plan)
        db.session.commit()
        u = User(
            username="draks_user",
            subscription_level=SubscriptionPlan.BASIC,
            role=UserRole.USER,
            plan_id=plan.id,
        )
        u.set_password("pass")
        u.generate_api_key()
        db.session.add(u)
        db.session.commit()
        return u


def _candles(n=60):
    now = int(datetime.utcnow().timestamp())
    candles = []
    for i in range(n):
        ts = now - (n - i) * 60
        candles.append({"ts": ts, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1})
    return candles


def test_decision_run_feature_flag(app, user):
    client = app.test_client()
    with app.app_context():
        set_feature_flag("draks", False)
        resp = client.post(
            "/api/draks/decision/run",
            headers={"X-API-KEY": user.api_key},
            json={"symbol": "BTC/USDT", "candles": _candles()},
        )
        assert resp.status_code == 403


def test_decision_run_limit_enforced(app, user):
    client = app.test_client()
    with app.app_context():
        set_feature_flag("draks", True)
        payload = {"symbol": "BTC/USDT", "candles": _candles()}
        resp1 = client.post(
            "/api/draks/decision/run",
            headers={"X-API-KEY": user.api_key},
            json=payload,
        )
        assert resp1.status_code == 200
        resp2 = client.post(
            "/api/draks/decision/run",
            headers={"X-API-KEY": user.api_key},
            json=payload,
        )
        assert resp2.status_code == 429
