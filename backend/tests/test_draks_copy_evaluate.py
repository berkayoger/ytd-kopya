import json
from datetime import datetime
import pytest

from backend import create_app, db
from backend.db.models import User, SubscriptionPlan, UserRole
from backend.models.plan import Plan
from backend.utils.feature_flags import create_feature_flag


def _candles(n=80):
    now = int(datetime.utcnow().timestamp())
    out = []
    px = 100.0
    for i in range(n):
        ts = now - (n - i) * 60
        px *= 1.001  # küçük drift
        out.append({"ts": ts, "open": px-2, "high": px+2, "low": px-3, "close": px, "volume": 1000+i})
    return out


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    # JWT doğrulamayı bypass et
    monkeypatch.setattr(
        "flask_jwt_extended.view_decorators.verify_jwt_in_request",
        lambda *a, **k: None,
    )
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
        plan = Plan(
            name="basic",
            price=0.0,
            features=json.dumps({"draks_copy": 2, "predict_daily": 10}),
        )
        db.session.add(plan)
        db.session.commit()
        u = User(
            username="copy_user",
            subscription_level=SubscriptionPlan.BASIC,
            role=UserRole.USER,
            plan_id=plan.id,
        )
        u.set_password("pass")
        u.generate_api_key()
        db.session.add(u)
        db.session.commit()
        return u


@pytest.fixture
def auth_headers(app, user):
    with app.app_context():
        token = user.generate_access_token()
    return {"Authorization": f"Bearer {token}", "X-API-KEY": user.api_key}


def test_copy_eval_flag_off(app, user, auth_headers):
    client = app.test_client()
    with app.app_context():
        create_feature_flag("draks", False)
        resp = client.post("/api/draks/copy/evaluate",
                           headers=auth_headers,
                           json={"symbol": "BTC/USDT", "side": "BUY", "candles": _candles()})
        assert resp.status_code == 403


def test_copy_eval_ok_and_limit(app, user, auth_headers, monkeypatch):
    client = app.test_client()
    with app.app_context():
        create_feature_flag("draks", True)
        payload = {"symbol": "BTC/USDT", "side": "BUY", "size": 1000, "candles": _candles()}
        r1 = client.post("/api/draks/copy/evaluate", headers=auth_headers, json=payload)
        assert r1.status_code == 200
        body = r1.get_json()
        assert "greenlight" in body and "scale_factor" in body and "draks" in body
        # 2. istek: plan 'draks_copy': 2 → bu da geçmeli
        r2 = client.post("/api/draks/copy/evaluate", headers=auth_headers, json=payload)
        assert r2.status_code == 200
        # 3. istek: limit aşımı
        r3 = client.post("/api/draks/copy/evaluate", headers=auth_headers, json=payload)
        assert r3.status_code == 429


@pytest.mark.parametrize("side", ["", "BUYSELL", "hold", None])
def test_copy_eval_bad_side(app, user, auth_headers, side):
    client = app.test_client()
    with app.app_context():
        create_feature_flag("draks", True)
        payload = {"symbol": "BTC/USDT", "side": side, "candles": _candles()}
        r = client.post("/api/draks/copy/evaluate", headers=auth_headers, json=payload)
        assert r.status_code == 400
        assert "side" in r.get_json().get("error", "").lower()


def test_copy_eval_bad_size(app, user, auth_headers):
    client = app.test_client()
    with app.app_context():
        create_feature_flag("draks", True)
        # str size
        r1 = client.post("/api/draks/copy/evaluate", headers=auth_headers,
                         json={"symbol": "BTC/USDT", "side": "BUY", "size": "x", "candles": _candles()})
        assert r1.status_code == 400
        # negatif size
        r2 = client.post("/api/draks/copy/evaluate", headers=auth_headers,
                         json={"symbol": "BTC/USDT", "side": "BUY", "size": -10, "candles": _candles()})
        assert r2.status_code == 400


def test_copy_eval_no_candles_and_no_ccxt(app, user, auth_headers, monkeypatch):
    client = app.test_client()
    with app.app_context():
        create_feature_flag("draks", True)
        # ccxt kullanılamasın diye modül referansını None yap
        monkeypatch.setattr("backend.draks.routes.ccxt", None, raising=False)
        resp = client.post("/api/draks/copy/evaluate",
                           headers=auth_headers,
                           json={"symbol": "BTC/USDT", "side": "BUY"})
        assert resp.status_code == 400
        assert "candles" in resp.get_json().get("error","")


def test_copy_eval_insufficient_data(app, user, auth_headers):
    client = app.test_client()
    with app.app_context():
        create_feature_flag("draks", True)
        few = _candles(10)  # yetersiz
        resp = client.post("/api/draks/copy/evaluate",
                           headers=auth_headers,
                           json={"symbol": "BTC/USDT", "side": "BUY", "candles": few})
        assert resp.status_code == 400
        assert resp.get_json().get("error") == "yetersiz veri"
