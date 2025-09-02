import json
from datetime import datetime

import pytest

from backend import create_app, db
from backend.db.models import DraksDecision, DraksSignalRun
from backend.utils.feature_flags import set_feature_flag


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setattr("backend.Config.SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    monkeypatch.setattr("backend.Config.SQLALCHEMY_ENGINE_OPTIONS", {}, raising=False)
    import flask_jwt_extended.view_decorators as vd

    monkeypatch.setattr(vd, "verify_jwt_in_request", lambda *a, **k: None)
    monkeypatch.setattr(
        "backend.auth.roles.verify_jwt_in_request", lambda optional=False: None
    )
    monkeypatch.setattr("backend.auth.roles.current_roles", lambda: {"admin"})
    monkeypatch.setattr(
        "backend.auth.middlewares.admin_required", lambda: (lambda f: f)
    )
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
    return app.test_client()


def test_list_decisions(admin_client):
    set_feature_flag("draks", True)
    with admin_client.application.app_context():
        db.session.add(
            DraksDecision(
                symbol="BTC/USDT",
                decision="LONG",
                position_pct=0.1,
                stop=100,
                take_profit=110,
                reasons="[]",
                raw_response="{}",
                created_at=datetime.utcnow(),
            )
        )
        db.session.commit()

    resp = admin_client.get("/api/admin/draks/decisions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["meta"]["total"] == 1
    assert data["items"][0]["symbol"] == "BTC/USDT"
    # detail
    row_id = data["items"][0]["id"]
    d = admin_client.get(f"/api/admin/draks/decisions/{row_id}")
    assert d.status_code == 200
    assert d.get_json()["symbol"] == "BTC/USDT"


def test_list_signals(admin_client):
    set_feature_flag("draks", True)
    with admin_client.application.app_context():
        db.session.add(
            DraksSignalRun(
                symbol="BTC/USDT",
                timeframe="1h",
                regime_probs="{}",
                weights="{}",
                score=0.5,
                decision="LONG",
                created_at=datetime.utcnow(),
            )
        )
        db.session.commit()

    resp = admin_client.get("/api/admin/draks/signals")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["meta"]["total"] == 1
    assert data["items"][0]["symbol"] == "BTC/USDT"
    # detail
    row_id = data["items"][0]["id"]
    d = admin_client.get(f"/api/admin/draks/signals/{row_id}")
    assert d.status_code == 200
    jd = d.get_json()
    assert jd["symbol"] == "BTC/USDT"
    assert "regime_probs" in jd and "weights" in jd
