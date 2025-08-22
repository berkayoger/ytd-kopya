"""Gizli yapılandırma değerlerini güvenle yönetmek için yardımcı sınıf"""

import base64
import logging
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecretsManager:
    """Hassas değerlerin şifrelenmesini ve çözülmesini yönetir"""

    def __init__(self, master_key: Optional[str] = None):
        """Şifreleme için anahtar hazırla"""
        self.master_key = master_key or os.environ.get("ENCRYPTION_KEY")
        self._fernet: Optional[Fernet] = None
        if self.master_key:
            self._setup_encryption()

    def _setup_encryption(self):
        """Fernet tabanlı şifrelemeyi yapılandır"""
        try:
            salt = b"ytd-kopya-salt-2024"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
            self._fernet = Fernet(key)
        except Exception as exc:  # pragma: no cover - kritik hata loglanır
            logging.error(f"Şifreleme kurulamadı: {exc}")
            self._fernet = None

    def encrypt_value(self, value: str) -> str:
        """Düz metni şifrele"""
        if not self._fernet:
            raise ValueError("Şifreleme kullanılamıyor")
        encrypted = self._fernet.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_value(self, encrypted_value: str) -> str:
        """Şifrelenmiş metni çöz"""
        if not self._fernet:
            raise ValueError("Şifre çözme kullanılamıyor")
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
        return self._fernet.decrypt(encrypted_bytes).decode()

    def encrypt_env_file(self, env_file_path: str, output_path: str):
        """Bir .env dosyasındaki hassas alanları şifrele"""
        if not os.path.exists(env_file_path):
            raise FileNotFoundError(f"Ortam dosyası bulunamadı: {env_file_path}")
        if not self._fernet:
            raise ValueError("Şifreleme kullanılamıyor")

        encrypted_vars: Dict[str, str] = {}
        with open(env_file_path, "r") as src:
            for line in src:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if self._is_sensitive_key(key):
                        encrypted_vars[f"{key}_ENCRYPTED"] = self.encrypt_value(value)
                    else:
                        encrypted_vars[key] = value

        with open(output_path, "w") as dest:
            for key, value in encrypted_vars.items():
                dest.write(f"{key}={value}\n")

    def _is_sensitive_key(self, key: str) -> bool:
        """Anahtarın hassas olup olmadığını kontrol et"""
        patterns = [
            "PASSWORD",
            "SECRET",
            "KEY",
            "TOKEN",
            "API_KEY",
            "PRIVATE",
            "CREDENTIAL",
            "AUTH",
            "CERT",
        ]
        return any(pat in key.upper() for pat in patterns)

    @staticmethod
    def generate_master_key() -> str:
        """Yeni bir ana şifreleme anahtarı oluştur"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def validate_secrets(self, secrets_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Gizli değerleri güvenlik kriterlerine göre doğrula"""
        issues = []
        for key, value in secrets_dict.items():
            if not value:
                continue
            value_str = str(value)
            if "PASSWORD" in key.upper() and len(value_str) < 12:
                issues.append(f"{key}: Şifre çok kısa (min 12 karakter)")
            if "SECRET" in key.upper() and len(value_str) < 32:
                issues.append(f"{key}: Gizli anahtar çok kısa (min 32 karakter)")
            if "API_KEY" in key.upper() and len(value_str) < 16:
                issues.append(f"{key}: API anahtarı çok kısa")
            weak_patterns = ["password", "123456", "admin", "test", "default"]
            if any(pat in value_str.lower() for pat in weak_patterns):
                issues.append(f"{key}: Zayıf/tekerrür eden ifadeler içeriyor")
        return {"valid": len(issues) == 0, "issues": issues}
