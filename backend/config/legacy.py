import os
import secrets
from datetime import timedelta

from sqlalchemy.pool import StaticPool


def env_bool(key: str, default: bool = False) -> bool:
    """Convert environment variable to boolean"""
    v = os.getenv(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


class BaseConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///ytd_crypto.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
        "pool_pre_ping": True,
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
    }
    READ_REPLICA_DATABASE_URI = os.getenv("READ_REPLICA_DATABASE_URI", "")
    # === API Versioning ===
    API_TITLE = os.getenv("API_TITLE", "YTD-Kopya Crypto Analysis API")
    API_VERSION = os.getenv("API_VERSION", "1.0.0")
    API_BASE_PREFIX = os.getenv("API_BASE_PREFIX", "/api/v1")
    API_DOCS_URL = os.getenv("API_DOCS_URL", "/docs")
    OPENAPI_JSON_URL = os.getenv("OPENAPI_JSON_URL", "/openapi.json")
    SWAGGER_UI_URL = os.getenv("SWAGGER_UI_URL", "/swagger")

    # === Logging & Monitoring ===
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    SENTRY_PROFILES_SAMPLE_RATE = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

    # === Cache Configuration ===
    CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/1"))
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))
    CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "ytd:")
    L1_CACHE_TTL = int(os.getenv("L1_CACHE_TTL", "60"))

    CELERY_TIMEZONE = "Europe/Istanbul"
    CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # === Enhanced Celery Configuration ===
    CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "300"))
    CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "240"))
    CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "4"))
    CELERY_TASK_DEFAULT_RETRY_DELAY = int(os.getenv("CELERY_TASK_DEFAULT_RETRY_DELAY", "15"))
    CELERY_TASK_MAX_RETRIES = int(os.getenv("CELERY_TASK_MAX_RETRIES", "5"))
    CELERY_ACKS_LATE = env_bool("CELERY_ACKS_LATE", True)
    CELERY_REJECT_ON_WORKER_LOST = env_bool("CELERY_REJECT_ON_WORKER_LOST", True)
    CELERY_FLOWER_PORT = int(os.getenv("CELERY_FLOWER_PORT", "5555"))
    CELERY_BEAT_SCHEDULE = {
        "auto-analyze-bitcoin-every-15-minutes": {
            "task": "backend.tasks.celery_tasks.analyze_coin_task",
            "schedule": timedelta(minutes=15),
            "args": ("bitcoin", "moderate"),
            "options": {"queue": "default"},
        },
        "auto-analyze-ethereum-every-15-minutes": {
            "task": "backend.tasks.celery_tasks.analyze_coin_task",
            "schedule": timedelta(minutes=15),
            "args": ("ethereum", "moderate"),
            "options": {"queue": "default"},
        },
        "check-and-downgrade-subscriptions-daily": {
            "task": ("backend.tasks.celery_tasks.check_and_downgrade_subscriptions"),
            "schedule": timedelta(days=1),
            "options": {"queue": "default"},
        },
    }
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://app.example.com")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", "change_me_access")
    REFRESH_TOKEN_SECRET = os.getenv("REFRESH_TOKEN_SECRET", "change_me_refresh")
    ACCESS_TOKEN_EXP_MINUTES = int(os.getenv("ACCESS_TOKEN_EXP_MINUTES", "15"))
    REFRESH_TOKEN_EXP_DAYS = int(os.getenv("REFRESH_TOKEN_EXP_DAYS", "7"))
    DRAKS_ENGINE_URL = os.getenv("DRAKS_ENGINE_URL", "http://draks-engine:8000")

    # Enhanced JWT configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(64)
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "15"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "7"))
    )
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]
    JWT_ERROR_MESSAGE_KEY = "message"
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URL", "sqlite:///ytd_crypto.db")


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///ytd_crypto.db")


class TestingConfig(BaseConfig):
    TESTING = True
    # SQLAlchemy 2.0 uyumlu: bellek içi SQLite + StaticPool
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URI", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    CELERY_TASK_ALWAYS_EAGER = True
    # Testlerde fiyat önbelleği kapalı
    PRICE_CACHE_TTL = 0
