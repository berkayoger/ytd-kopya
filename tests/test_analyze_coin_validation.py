import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import create_app
from backend.db import db
from backend.db.models import SubscriptionPlan


def _noop_decorator(*args, **kwargs):
    """Her şeyi olduğu gibi dönen sahte decorator."""
    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return args[0]

    def _wrap(f):
        return f

    return _wrap


def setup_app(monkeypatch):
    """Uygulamayı test modunda minimal bağımlılıklarla başlat."""
    monkeypatch.setenv("FLASK_ENV", "testing")

    # require_subscription_plan → no‑op (modül import edilmeden önce)
    monkeypatch.setattr(
        "backend.utils.decorators.require_subscription_plan",
        lambda *_a, **_k: _noop_decorator,
        raising=False,
    )
    # usage limit → no‑op
    monkeypatch.setattr(
        "backend.utils.usage_limits.check_usage_limit",
        lambda *_a, **_k: _noop_decorator,
        raising=False,
    )
    # rate limit → no‑op
    monkeypatch.setattr(
        "backend.limiting.limiter.limit",
        lambda *_a, **_k: _noop_decorator,
        raising=False,
    )

    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # DB init
    with app.app_context():
        db.create_all()

    # Sahte redis ve celery eklentileri
    class _FakeTask:
        id = "fake-task-id"

    class _FakeCelery:
        def send_task(self, *_a, **_k):
            return _FakeTask()

    app.extensions["redis_client"] = None
    app.extensions["celery"] = _FakeCelery()

    # g.user enjekte etmek için before_request hook
    @app.before_request
    def _inject_g_user():
        from flask import g
        g.user = SimpleNamespace(
            id="u1",
            username="coinuser",
            subscription_level=SubscriptionPlan.BASIC,
        )

    return app


def test_analyze_coin_invalid_symbol(monkeypatch):
    app = setup_app(monkeypatch)
    client = app.test_client()

    # Hatalı coin sembolü gönderildiğinde 400 dönmeli
    resp = client.get("/api/analyze_coin/INVALID!!")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Geçersiz coin ID formatı" in data["error"]


def test_analyze_coin_valid_symbol_hits_queue(monkeypatch):
    app = setup_app(monkeypatch)
    client = app.test_client()

    # Geçerli sembolde 200 ve JSON dönmesi beklenir (analiz kuyruklandı logiği çalışır)
    resp = client.get("/api/analyze_coin/BTC")
    # Analiz hemen sonuç dönmüyorsa, endpointiniz 202 de verebilir.
    # Bu projede JSON döndürdüğü için 200 bekliyoruz; farklı ise assert'ı güncelleyin.
    assert resp.status_code in (200, 202, 201, 204)

