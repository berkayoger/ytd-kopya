"""SecretsManager yardımcı sınıfı için testler"""

from app.secrets_manager import SecretsManager


def test_encrypt_decrypt_roundtrip():
    """Şifrelenen değerin geri çözülebilmesi gerekir"""
    manager = SecretsManager(SecretsManager.generate_master_key())
    original = "s3cr3t-deger"
    encrypted = manager.encrypt_value(original)
    assert manager.decrypt_value(encrypted) == original


def test_validate_secrets_rules():
    """Güçsüz gizli değerler tespit edilmelidir"""
    manager = SecretsManager()
    secrets = {
        "TEST_PASSWORD": "123",
        "API_KEY": "short",
        "GOOD_SECRET": "x" * 40,
    }
    result = manager.validate_secrets(secrets)
    assert not result["valid"]
    assert any("TEST_PASSWORD" in issue for issue in result["issues"])
