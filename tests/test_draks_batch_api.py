import json
import pytest
from datetime import datetime

from backend import create_app, db
from backend.db.models import User, SubscriptionPlan, UserRole
from backend.models.plan import Plan
from backend.utils.feature_flags import set_feature_flag


class DummyRedis:
    def __init__(self):
        self.store = {}
        self.sets = {}
        self.hashes = {}

    # key-value
    def setex(self, k, ttl, v):
        self.store[k] = v

    def get(self, k):
        return self.store.get(k)

    def delete(self, k):
        self.store.pop(k, None)
        self.sets.pop(k, None)

    # sets
    def sadd(self, key, *members):
        self.sets.setdefault(key, set()).update(members)

    def srem(self, key, member):
        self.sets.get(key, set()).discard(member)

    def scard(self, key):
        return len(self.sets.get(key, set()))

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    # hashes
    def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value

    def ping(self):
        return True


def _symbols(n=5):
    base = [
        "BTC/USDT",
        "ETH/USDT",
        "BNB/USDT",
        "ADA/USDT",
        "XRP/USDT",
        "SOL/USDT",
        "DOGE/USDT",
    ]
    return base[:n]


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    import flask_jwt_extended.view_decorators as vd
    monkeypatch.setattr(vd, "verify_jwt_in_request", lambda *a, **k: None)
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
        plan = Plan(name="pro", price=0.0, features=json.dumps({"draks_batch": 10}))
        db.session.add(plan)
        db.session.commit()
        u = User(
            username="batch_user",
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


def _patch_batch(monkeypatch):
    import backend.tasks.draks_batch as mod
    dummy = DummyRedis()
    monkeypatch.setattr(mod, "_r", lambda: dummy)
    import pandas as pd
    import numpy as np

    def fake_get(asset, symbol, timeframe, limit):
        now = pd.Timestamp.utcnow().floor("s")
        idx = pd.date_range(end=now, periods=80, freq="1min", tz="UTC")
        df = pd.DataFrame(
            {
                "open": np.linspace(100, 110, len(idx)),
                "high": np.linspace(101, 111, len(idx)),
                "low": np.linspace(99, 109, len(idx)),
                "close": np.linspace(100, 110, len(idx)),
                "volume": np.ones(len(idx)) * 1000,
            },
            index=idx,
        )
        return df

    monkeypatch.setattr(mod, "_get_ohlcv_cached", fake_get)
    def _fake_delay(**kw):
        r = dummy
        try:
            df = mod._get_ohlcv_cached(kw["asset"], kw["symbol"], kw["timeframe"], kw["limit"])
            if len(df) < 60:
                raise RuntimeError("insufficient_data")
            out = mod.ENGINE.run(df, kw["symbol"].replace(" ", ""))
            out["as_of"] = datetime.utcnow().isoformat() + "Z"
            r.setex(mod._result_key(kw["job_id"], kw["symbol"]), mod.DECISION_TTL, json.dumps({"status": "ok", "draks": out}))
            r.sadd(mod._set_key(kw["job_id"], "done"), kw["symbol"])
            mod.inc_batch_item(kw["asset"], "ok")
        except Exception:
            r.setex(mod._result_key(kw["job_id"], kw["symbol"]), mod.DECISION_TTL, json.dumps({"status": "error", "error": "internal_error"}))
            r.sadd(mod._set_key(kw["job_id"], "failed"), kw["symbol"])
            mod.inc_batch_item(kw["asset"], "error")
        finally:
            r.srem(mod._set_key(kw["job_id"], "pending"), kw["symbol"])
            mod._try_finalize(kw["job_id"])

    class _Task:
        def delay(self, **kw):
            return _fake_delay(**kw)

    dummy_task = _Task()
    monkeypatch.setattr(mod, "process_symbol", dummy_task)
    import backend.api.draks.batch as api_batch
    monkeypatch.setattr(api_batch, "process_symbol", dummy_task)
    return dummy


def test_submit_flag_off(app, auth_headers, monkeypatch):
    client = app.test_client()
    with app.app_context():
        set_feature_flag("draks", False)
        set_feature_flag("draks_batch", False)
    r = client.post(
        "/api/draks/batch/submit",
        headers=auth_headers,
        json={"asset": "crypto", "timeframe": "1h", "symbols": _symbols(2)},
    )
    assert r.status_code == 403


def test_submit_ok_and_status_results(app, auth_headers, monkeypatch):
    client = app.test_client()
    with app.app_context():
        set_feature_flag("draks", True)
        set_feature_flag("draks_batch", True)
    _patch_batch(monkeypatch)
    sub = client.post(
        "/api/draks/batch/submit",
        headers=auth_headers,
        json={"asset": "crypto", "timeframe": "1h", "symbols": _symbols(3)},
    )
    assert sub.status_code in (200, 202)
    job_id = sub.get_json()["job_id"]
    st = client.get(f"/api/draks/batch/status/{job_id}", headers=auth_headers)
    assert st.status_code == 200
    body = st.get_json()
    assert body["total"] == 3
    res = client.get(f"/api/draks/batch/results/{job_id}", headers=auth_headers)
    assert res.status_code == 200
    items = res.get_json()["items"]
    assert all(i["status"] == "ok" for i in items)


def test_submit_invalid_input(app, auth_headers, monkeypatch):
    client = app.test_client()
    with app.app_context():
        set_feature_flag("draks", True)
        set_feature_flag("draks_batch", True)
    monkeypatch.setenv("BATCH_RATE_LIMIT", "100/hour")
    _patch_batch(monkeypatch)
    r1 = client.post(
        "/api/draks/batch/submit",
        headers=auth_headers,
        json={"asset": "fx", "timeframe": "1h", "symbols": _symbols(2)},
    )
    assert r1.status_code == 400
    r2 = client.post(
        "/api/draks/batch/submit",
        headers=auth_headers,
        json={"asset": "crypto", "timeframe": "13h", "symbols": _symbols(2)},
    )
    assert r2.status_code == 400
    r3 = client.post(
        "/api/draks/batch/submit",
        headers=auth_headers,
        json={"asset": "crypto", "timeframe": "1h", "symbols": "BTC"},
    )
    assert r3.status_code == 400


def test_rate_limit(app, auth_headers, monkeypatch):
    client = app.test_client()
    with app.app_context():
        set_feature_flag("draks", True)
        set_feature_flag("draks_batch", True)
    monkeypatch.setenv("BATCH_RATE_LIMIT", "1/hour")
    _patch_batch(monkeypatch)
    p1 = client.post(
        "/api/draks/batch/submit",
        headers=auth_headers,
        json={"asset": "crypto", "timeframe": "1h", "symbols": _symbols(1)},
    )
    assert p1.status_code in (200, 202)
    p2 = client.post(
        "/api/draks/batch/submit",
        headers=auth_headers,
        json={"asset": "crypto", "timeframe": "1h", "symbols": _symbols(1)},
    )
    assert p2.status_code == 429


def test_results_filters(app, auth_headers, monkeypatch):
    client = app.test_client()
    with app.app_context():
        set_feature_flag("draks", True)
        set_feature_flag("draks_batch", True)
    _patch_batch(monkeypatch)
    sub = client.post(
        "/api/draks/batch/submit",
        headers=auth_headers,
        json={"asset": "crypto", "timeframe": "1h", "symbols": _symbols(3)},
    )
    job_id = sub.get_json()["job_id"]
    ok = client.get(
        f"/api/draks/batch/results/{job_id}?status=ok",
        headers=auth_headers,
    )
    assert ok.status_code == 200
    items_ok = ok.get_json()["items"]
    assert all(i["status"] == "ok" for i in items_ok)
    btc = client.get(
        f"/api/draks/batch/results/{job_id}?symbol=BTC",
        headers=auth_headers,
    )
    assert btc.status_code == 200
    assert all("BTC" in i["symbol"] for i in btc.get_json()["items"])
