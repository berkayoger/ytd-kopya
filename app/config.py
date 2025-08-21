"""Uygulama yapılandırma modülü."""

import logging
import os
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional

from .secrets_manager import SecretsManager


# Uygulama genelinde kullanılacak gizli değer yöneticisi
secrets_manager = SecretsManager(os.environ.get("MASTER_ENCRYPTION_KEY"))


def _decrypt_secret(encrypted_value: Optional[str]) -> Optional[str]:
    """Şifreli ortam değişkenini çöz"""
    if not encrypted_value:
        return encrypted_value
    try:
        return secrets_manager.decrypt_value(encrypted_value)
    except Exception:
        logging.warning("Gizli değer çözülemedi")
        return None


class Config:
    """Temel yapılandırma sınıfı"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "sqlite:///" + os.path.join(os.path.dirname(__file__), "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URI else {},
    }
    # Rate limit genel anahtarı (test/staging için kapatabilmek adına)
    RATE_LIMIT_ENABLED = str(os.environ.get("RATE_LIMIT_ENABLED", "true")).lower() == "true"

    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)

    COINGECKO_API_KEY = _decrypt_secret(os.environ.get("COINGECKO_API_KEY_ENCRYPTED")) or \
        os.environ.get("COINGECKO_API_KEY")
    CRYPTOCOMPARE_API_KEY = _decrypt_secret(os.environ.get("CRYPTOCOMPARE_API_KEY_ENCRYPTED")) or \
        os.environ.get("CRYPTOCOMPARE_API_KEY")

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or secrets.token_urlsafe(64)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000))
    JWT_ALGORITHM = "HS256"

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD = _decrypt_secret(os.environ.get("REDIS_PASSWORD_ENCRYPTED")) or \
        os.environ.get("REDIS_PASSWORD")

    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    SECURITY_HEADERS = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", "app.log")
    LOG_MAX_SIZE = int(os.environ.get("LOG_MAX_SIZE", 10 * 1024 * 1024))
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))

    RATE_LIMIT_STORAGE_URL = REDIS_URL
    RATE_LIMIT_DEFAULT = os.environ.get("RATE_LIMIT_DEFAULT", "100/minute")

    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Kritik yapılandırma değerlerini doğrula"""
        issues = []
        if str(cls.SECRET_KEY).strip().lower() in {"change-me", "changeme"}:
            issues.append("SECRET_KEY varsayılan değerde")
        if not cls.COINGECKO_API_KEY:
            issues.append("COINGECKO_API_KEY ayarlanmadı")
        if len(cls.JWT_SECRET_KEY) < 32:
            issues.append("JWT_SECRET_KEY çok kısa")
        return {"valid": len(issues) == 0, "issues": issues}

    @classmethod
    def mask_sensitive_values(cls, config_dict: Dict) -> Dict:
        """Hassas yapılandırma değerlerini maskele"""
        sensitive_keys = [
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "COINGECKO_API_KEY",
            "CRYPTOCOMPARE_API_KEY",
            "REDIS_PASSWORD",
            "DATABASE_URL",
        ]
        masked = config_dict.copy()
        for key in sensitive_keys:
            if key in masked and masked[key]:
                masked[key] = f"{'*' * (len(str(masked[key])) - 4)}{str(masked[key])[-4:]}"
        return masked


class DevelopmentConfig(Config):
    """Geliştirme yapılandırması"""

    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", "False").lower() == "true"
    SECURITY_HEADERS = {
        **Config.SECURITY_HEADERS,
        "Content-Security-Policy": "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: https:;",
    }


class ProductionConfig(Config):
    """Üretim yapılandırması"""

    DEBUG = False
    TESTING = False
    FORCE_HTTPS = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 1800
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        "pool_size": 20,
        "max_overflow": 0,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }
    RATE_LIMIT_DEFAULT = "50/minute"

    @classmethod
    def validate_production_config(cls):
        """Üretim ortamı için ek doğrulamalar"""
        validation = cls.validate_config()
        # Master key zorunlu
        if not os.environ.get("MASTER_ENCRYPTION_KEY"):
            validation["issues"].append("MASTER_ENCRYPTION_KEY üretimde ayarlanmalı")
        # SECRET_KEY ve JWT_SECRET_KEY mutlaka env'den gelmeli (fallback/random olmamalı)
        if not os.environ.get("SECRET_KEY"):
            validation["issues"].append("SECRET_KEY üretimde environment üzerinden verilmelidir")
        if not os.environ.get("JWT_SECRET_KEY"):
            validation["issues"].append("JWT_SECRET_KEY üretimde environment üzerinden verilmelidir")
        # Çok kısa anahtarlar engellensin
        if len(str(cls.JWT_SECRET_KEY)) < 32:
            validation["issues"].append("JWT_SECRET_KEY çok kısa (>=32 bayt önerilir)")
        if len(str(cls.SECRET_KEY)) < 16:
            validation["issues"].append("SECRET_KEY çok kısa (>=16 bayt önerilir)")
        if cls.REDIS_URL.startswith("redis://localhost"):
            validation["issues"].append("REDIS_URL üretimde localhost olmamalı")
        if "sqlite" in cls.SQLALCHEMY_DATABASE_URI:
            validation["issues"].append("Üretimde SQLite kullanılmamalı")
        validation["valid"] = len(validation["issues"]) == 0
        return validation


class TestingConfig(Config):
    """Test yapılandırması"""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATE_LIMIT_ENABLED = False  # testlerde tüm rate-limit devre dışı
    JWT_ACCESS_TOKEN_EXPIRES = 60
    JWT_REFRESH_TOKEN_EXPIRES = 300


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}

