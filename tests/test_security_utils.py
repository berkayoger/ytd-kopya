import io
import pytest
from flask import Flask

from backend.utils.security import (
    sanitize_input,
    validate_file_upload,
    generate_secure_token,
    hash_api_key,
    verify_api_key,
)
from backend.utils.decorators import generate_csrf_token, validate_csrf_token


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"
    return app


def test_sanitize_input_removes_script():
    raw = "<script>alert('x')</script><b>merhaba</b>"
    cleaned = sanitize_input(raw, allowed_tags=["b"])
    assert "<script>" not in cleaned
    assert "<b>merhaba</b>" in cleaned


def test_validate_file_upload(tmp_path):
    data = io.BytesIO(b"test")
    data.filename = "deneme.txt"
    valid, _ = validate_file_upload(data)
    assert valid

    bad = io.BytesIO(b"test")
    bad.filename = "deneme.exe"
    valid, msg = validate_file_upload(bad)
    assert not valid
    assert "tür" in msg


def test_api_key_hash_and_verify():
    key = generate_secure_token()
    stored = hash_api_key(key)
    assert verify_api_key(stored, key)
    # Yanlış anahtar için doğrulama başarısız olmalı
    assert not verify_api_key(stored, "yanlis")


def test_csrf_token_generation_and_validation(app, monkeypatch):
    with app.app_context():
        token = generate_csrf_token("user123")
    monkeypatch.setattr(
        "backend.utils.decorators.get_jwt_identity", lambda: "user123"
    )
    with app.app_context():
        assert validate_csrf_token(token)
