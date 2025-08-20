import os
import pathlib
import importlib.util
import pytest

# Güvenlik modülünü uygulama paketi yüklenmeden dinamik olarak yükle
SECURITY_PATH = pathlib.Path(__file__).resolve().parents[1] / "app" / "core" / "security.py"
spec = importlib.util.spec_from_file_location("security", SECURITY_PATH)
security = importlib.util.module_from_spec(spec)
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

    token = security.create_email_token(subject="42")
    payload = security.decode_token(token, require_type="email")
    assert payload["sub"] == "42"

    with pytest.raises(security.HTTPException):
        security.decode_token(token, require_type="access")
