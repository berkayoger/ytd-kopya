# Pytest için global ayarlar: offline ve determinizm
import os
import pytest
from typing import Iterator
from types import SimpleNamespace

# CoinGecko şimini çevrimdışı modda çalıştır, bekleme yok
os.environ.setdefault("COINGECKO_SHIM_OFFLINE", "1")
os.environ.setdefault("COINGECKO_MIN_INTERVAL_SEC", "0")

# Uygulama testleri için standart ortam değişkenleri
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("PYTHONHASHSEED", "0")

try:
    import backend.utils.usage_limits as _ul
    def _noop(feature_key: str):
        def deco(fn):
            return fn
        return deco
    _ul.check_usage_limit = _noop
    _ul._inc_db = lambda *a, **k: 0
except Exception:
    pass



@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Testlerde dış ağ bağlantılarını engelle."""
    import socket

    def guard(*args, **kwargs):
        raise RuntimeError("Test sırasında ağ erişimi engellendi")

    # Gerçek ağ gerekliyse bu iki satırı yorum satırına al.
    monkeypatch.setattr(socket, "create_connection", guard, raising=True)
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Test sırasında ağ engellendi")),
    )
    yield

# ---- Global auth bypass (TESTING) -------------------------------------------
# 1) jwt_required kontrolünü no-op yap
@pytest.fixture(autouse=True)
def _bypass_jwt(monkeypatch):
    def _noop_decorator(*args, **kwargs):
        def _wrap(f):
            return f
        return _wrap
    try:
        import flask_jwt_extended as jwt  # type: ignore
        monkeypatch.setattr(jwt, 'jwt_required', _noop_decorator, raising=False)
        monkeypatch.setattr(jwt, 'fresh_jwt_required', _noop_decorator, raising=False)
        monkeypatch.setattr(jwt, 'get_jwt_identity', lambda: 'test-user', raising=False)
    except Exception:
        pass
    try:
        import flask_jwt_extended.view_decorators as vd  # type: ignore
        monkeypatch.setattr(vd, 'verify_jwt_in_request', lambda *a, **k: None)
    except Exception:
        pass
# 3) kullanım limiti DB güncellemelerini no-op yap
@pytest.fixture(autouse=True)
def _mute_usage_db(monkeypatch):
    try:
        import backend.utils.usage_limits as ul
        def _noop(feature_key: str):
            def deco(fn):
                return fn
            return deco
        monkeypatch.setattr(ul, 'check_usage_limit', _noop)
        monkeypatch.setattr(ul, '_inc_db', lambda *a, **k: 0)
    except Exception:
        pass

# 2) create_app ile üretilen her app'e before_request ile test kullanıcısı enjekte et
@pytest.fixture(autouse=True)
def _wrap_create_app(monkeypatch):
    try:
        import backend  # type: ignore
        orig_create_app = backend.create_app
    except Exception:
        return

    def _wrapped_create_app(*args, **kwargs):
        try:
            import backend.utils.usage_limits as ul
            def _noop(feature_key: str):
                def deco(fn):
                    return fn
                return deco
            monkeypatch.setattr(ul, "check_usage_limit", _noop)
            monkeypatch.setattr(ul, "_inc_db", lambda *a, **k: 0)
        except Exception:
            pass
        app = orig_create_app(*args, **kwargs)
        # Aynı handler'ın iki kez eklenmesini önlemek için bayrak
        if not getattr(app, "_testing_user_injected", False):
            @app.before_request
            def _inject_testing_user():
                # Uygulama TESTING modunda ve g.user henüz yoksa doldur
                from flask import g, current_app
                if current_app and current_app.config.get("TESTING") and not getattr(g, "user", None):
                    g.user = SimpleNamespace(
                        id="test-user",
                        subscription_level="BASIC",
                        plan=SimpleNamespace(name="basic"),
                        role="admin",
                        is_admin=True,
                    )
            app._testing_user_injected = True
        return app

    monkeypatch.setattr(backend, "create_app", _wrapped_create_app, raising=True)




# ---- Flask test client fallback ---------------------------------------------
# Bazı ortamlarda pytest-flask kurulu olmayabilir. tests/ tarafında zaten bir
# `app` fixture'ı görünür durumda; yalnızca `client` eksik. Burada hafif bir
# client fixture'ı sağlayarak bağımlılık olmadan çalıştırıyoruz.
@pytest.fixture
def client(app) -> Iterator:
    """Flask test client (pytest-flask olmadan sade fallback)."""
    with app.test_client() as c:
        # İsteyen testler context'e ihtiyaç duyarsa app fixture'ı zaten sağlıyor.
        yield c