# Pytest için global ayarlar: offline ve determinizm
import os
import pytest
from typing import Iterator
from types import SimpleNamespace
from flask import Flask, request

# CoinGecko şimini çevrimdışı modda çalıştır, bekleme yok
os.environ.setdefault("COINGECKO_SHIM_OFFLINE", "1")
os.environ.setdefault("COINGECKO_MIN_INTERVAL_SEC", "0")

# Uygulama testleri için standart ortam değişkenleri
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("PYTHONHASHSEED", "0")


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
    # verify_jwt_in_request'i no-op'a çevir
    try:
        import flask_jwt_extended.view_decorators as vd  # type: ignore
        monkeypatch.setattr(vd, "verify_jwt_in_request", lambda *a, **k: None)
    except Exception:
        pass
    # get_jwt_identity() çağrıları test-user döndürsün
    try:
        import flask_jwt_extended as jwt  # type: ignore
        monkeypatch.setattr(jwt, "get_jwt_identity", lambda: "test-user")
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

    def _inject_hook(app: Flask):
        if getattr(app, "_testing_user_injected", False):
            return
        @app.before_request
        def _inject_testing_user():
            # REQUIRE_AUTH_FOR_HEALTH=true iken /health için bypass ETME
            require_auth_health = (os.getenv("REQUIRE_AUTH_FOR_HEALTH", "").lower() in ("1", "true", "yes"))
            if require_auth_health and request.path.startswith("/health"):
                return  # enjekte etme -> 401 beklenen davranış
            from flask import g, current_app
            if current_app and current_app.config.get("TESTING") and not getattr(g, "user", None):
                g.user = SimpleNamespace(
                    id="test-user",
                    subscription_level="BASIC",
                    # plan.features bazı middleware'lerde okunuyor → boş dict ekle
                    plan=SimpleNamespace(name="basic", features={}),
                    role="admin",
                    username="test-admin",
                    is_admin=True,
                    api_key="test-api-key",
                    # Tüm feature erişimleri
                    custom_features='{"draks": true}',
                )
        app._testing_user_injected = True

    def _wrapped_create_app(*args, **kwargs):
        app = orig_create_app(*args, **kwargs)
        _inject_hook(app)
        return app

    monkeypatch.setattr(backend, "create_app", _wrapped_create_app, raising=True)

# 3) create_app kullanılmadan doğrudan Flask() ile oluşturulan app'ler için de
#    test client üretilmeden önce aynı hook'u ekleyelim.
@pytest.fixture(autouse=True)
def _patch_flask_test_client(monkeypatch):
    orig_test_client = Flask.test_client

    def _inject(app: Flask):
        if getattr(app, "_testing_user_injected", False):
            return
        @app.before_request
        def _inject_testing_user():
            require_auth_health = (os.getenv("REQUIRE_AUTH_FOR_HEALTH", "").lower() in ("1", "true", "yes"))
            if require_auth_health and request.path.startswith("/health"):
                return
            from flask import g, current_app
            if current_app and current_app.config.get("TESTING") and not getattr(g, "user", None):
                g.user = SimpleNamespace(
                    id="test-user",
                    subscription_level="BASIC",
                    plan=SimpleNamespace(name="basic", features={}),
                    role="admin",
                    username="test-admin",
                    is_admin=True,
                    api_key="test-api-key",
                    # Tüm feature erişimleri
                    custom_features='{"draks": true}',
                )
        app._testing_user_injected = True

    def patched(self: Flask, *args, **kwargs):
        # Test ortamında her app'e hook'u ekle
        try:
            if self.config.get("TESTING", True):
                _inject(self)
        finally:
            return orig_test_client(self, *args, **kwargs)

    monkeypatch.setattr(Flask, "test_client", patched, raising=True)


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


@pytest.fixture
def auth_headers():
    """Test için auth header'ları."""
    return {
        "Authorization": "Bearer test-token",
        "X-API-KEY": "test-api-key",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }


@pytest.fixture
def test_user():
    """Test kullanıcı objesi."""
    return SimpleNamespace(id="test-user", username="test-admin", is_admin=True, custom_features='{"draks": true}')
