import importlib.util
import os
import pathlib
import sys
import types

import pytest

from app import create_app
from app.models.db import User, _attach_db, db

# Güvenlik modülünü uygulama paketi yüklenmeden dinamik olarak yükle
SECURITY_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "app" / "core" / "security.py"
)
spec = importlib.util.spec_from_file_location("security", SECURITY_PATH)
security = importlib.util.module_from_spec(spec)
# Azure bağımlılıkları için sahte modüller ekleyelim
sys.modules.setdefault("azure", types.ModuleType("azure"))
sys.modules.setdefault("azure.identity", types.ModuleType("azure.identity"))
sys.modules.setdefault("azure.keyvault", types.ModuleType("azure.keyvault"))
sys.modules.setdefault(
    "azure.keyvault.secrets", types.ModuleType("azure.keyvault.secrets")
)
sys.modules["azure.identity"].DefaultAzureCredential = object


class _DummySecretClient:
    def __init__(self, *a, **k):
        pass


sys.modules["azure.keyvault.secrets"].SecretClient = _DummySecretClient

spec.loader.exec_module(security)


def test_create_email_token_and_decode(monkeypatch):
    # Ortamı test moduna ayarlıyoruz
    monkeypatch.setenv("SECRET_PROVIDER", "env")
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    # Redis istemcisini sahte nesne ile değiştiriyoruz
    class _DummyRedis:
        def exists(self, key):
            return 0

    security._redis_client = lambda: _DummyRedis()
    import app.core.security as core_sec

    core_sec._redis_client = lambda: _DummyRedis()

    token = security.create_email_token(subject="42")
    payload = security.decode_token(token, require_type="email")
    assert payload["sub"] == "42"

    with pytest.raises(security.HTTPException):
        security.decode_token(token, require_type="access")


def test_verify_endpoint_requires_email_token(monkeypatch):
    # Gerekli ortam değişkenlerini ayarlayalım
    monkeypatch.setenv("SECRET_PROVIDER", "env")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    # Redis istemcisini sahte nesne ile değiştiriyoruz
    class _DummyRedis:
        def exists(self, key):
            return 0

        def setex(self, *args, **kwargs):
            return 1

    security._redis_client = lambda: _DummyRedis()
    import app.core.security as core_sec

    core_sec._redis_client = lambda: _DummyRedis()

    # Uygulamayı oluştur ve gerekli bileşenleri bağla
    app = create_app()
    _attach_db(app)
    from app.authx.api import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    client = app.test_client()

    # Sadece kullanıcı tablosunu oluştur
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[User.__table__])
        user = User(email="u@example.com", password_hash="x")
        db.session.add(user)
        db.session.commit()
        uid = user.id

    # E-posta olmayan token ile doğrulama reddedilmeli
    non_email = security.create_access_token(subject=uid)
    resp_invalid = client.get(f"/api/auth/verify?token={non_email}")
    assert resp_invalid.status_code == 401

    # Doğru tipte token ile doğrulama başarılı olmalı
    email_tok = security.create_email_token(subject=uid)
    resp_ok = client.get(f"/api/auth/verify?token={email_tok}")
    assert resp_ok.status_code == 200
    data = resp_ok.get_json()
    assert "access" in data and "refresh" in data

    # Kullanıcının e-postası işaretlenmeli
    with app.app_context():
        refreshed = User.query.get(uid)
        assert refreshed.email_verified is True
