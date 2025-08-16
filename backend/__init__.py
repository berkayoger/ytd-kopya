# backend/__init__.py
from __future__ import annotations

import os
import sys
import uuid
from time import perf_counter
from datetime import timedelta, datetime
from typing import Optional

from flask import Flask, jsonify, request, g, Response
from flask.testing import FlaskClient
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import text
from celery import Celery
from flask_socketio import SocketIO, emit
from redis import Redis
from dotenv import load_dotenv
from loguru import logger
from backend.observability.metrics import prometheus_wsgi_app

# Proje içi
from backend.db import db as base_db
from backend.limiting import limiter
from backend.db.models import User, SubscriptionPlan
from backend.models.plan import Plan  # noqa: F401 (kullanıldığı modüller olabilir)
from backend.utils.usage_limits import check_usage_limit

load_dotenv()

# -----------------------------------------------------------------------------
# Ortak yardımcılar / config
# -----------------------------------------------------------------------------
def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class Config:
    # DB
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///ytd_crypto.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_SESSION_OPTIONS = {"expire_on_commit": False}
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }

    # Redis & Celery
    REDIS_URL = REDIS_URL
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_TIMEZONE = "Europe/Istanbul"

    # Auth/JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key-change-this-in-prod!")
    ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", "change_me_access")
    REFRESH_TOKEN_SECRET = os.getenv("REFRESH_TOKEN_SECRET", "change_me_refresh")
    ACCESS_TOKEN_EXP_MINUTES = int(os.getenv("ACCESS_TOKEN_EXP_MINUTES", "15"))
    REFRESH_TOKEN_EXP_DAYS = int(os.getenv("REFRESH_TOKEN_EXP_DAYS", "7"))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # Cache ve flags
    PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "300"))

    # CORS
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:80,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")

    # Ortam
    ENV = os.getenv("FLASK_ENV", "development")

    # Celery beat örnek işleri
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
            "task": "backend.tasks.celery_tasks.check_and_downgrade_subscriptions",
            "schedule": timedelta(days=1),
            "options": {"queue": "default"},
        },
        "auto-downgrade-plans-everyday": {
            "task": "backend.tasks.plan_tasks.auto_downgrade_expired_plans",
            "schedule": timedelta(days=1),
            "options": {"queue": "default"},
        },
        "auto-expire-boosts-everyday": {
            "task": "backend.tasks.plan_tasks.auto_expire_boosts",
            "schedule": timedelta(days=1),
            "options": {"queue": "default"},
        },
    }

    # Prod güvenlik doğrulamaları
    @staticmethod
    def assert_production_jwt_key() -> None:
        if Config.ENV == "production" and (
            not Config.JWT_SECRET_KEY or Config.JWT_SECRET_KEY.startswith("super-secret")
        ):
            logger.critical("🚨 Üretimde güçlü bir JWT_SECRET_KEY zorunlu!")
            sys.exit(1)

    @staticmethod
    def assert_production_cors_origins() -> None:
        if Config.ENV == "production" and ("*" in Config.CORS_ORIGINS or not Config.CORS_ORIGINS):
            logger.critical("🚨 Üretimde CORS origins '*' olamaz veya boş bırakılamaz!")
            sys.exit(1)


# Global extension instances
db: SQLAlchemy = base_db
celery_app: Celery = Celery()
socketio: SocketIO = SocketIO()


class LegacyTestClient(FlaskClient):
    """Werkzeug 2.x cookie imzası için uyumluluk."""
    def set_cookie(self, *args, **kwargs):
        if len(args) == 3 and "domain" not in kwargs:
            domain, key, value = args
            return super().set_cookie(key, value, domain=domain, **kwargs)
        return super().set_cookie(*args, **kwargs)


# -----------------------------------------------------------------------------
# App Factory
# -----------------------------------------------------------------------------
def create_app() -> Flask:
    app = Flask(__name__)
    app.test_client_class = LegacyTestClient
    app.config.from_object(Config)
    app.logger.info("App booting with observability metrics enabled.")

    # Test ortamı ayarları
    if os.getenv("FLASK_ENV") == "testing":
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}
        app.config["PRICE_CACHE_TTL"] = 0

    # Prod güvenlik kontrolleri
    Config.assert_production_jwt_key()
    Config.assert_production_cors_origins()

    # Uzantıları başlat
    CORS(app, supports_credentials=True, origins=Config.CORS_ORIGINS)
    db.init_app(app)
    limiter.init_app(app)
    celery_app.conf.update(app.config)
    socketio.init_app(
        app,
        message_queue=Config.CELERY_BROKER_URL,
        cors_allowed_origins=Config.CORS_ORIGINS,
    )

    # Dev/Test için otomatik tablo oluşturma (Prod’da migration kullanın)
    with app.app_context():
        if app.config["ENV"].lower() != "production":
            db.create_all()
            from backend.db.models import Role, Permission  # lazy import
            if not Role.query.filter_by(name="user").first():
                db.session.add_all([Role(name="user"), Role(name="admin")])
                db.session.commit()
            if not Permission.query.filter_by(name="admin_access").first():
                perm = Permission(name="admin_access")
                db.session.add(perm)
                db.session.commit()
                admin_role = Role.query.filter_by(name="admin").first()
                admin_role.permissions.append(perm)
                db.session.commit()
        else:
            logger.info("Prod: db.create_all() atlandı; migration kullanın.")

    # Extensions kayıt
    app.extensions["db"] = db
    app.extensions["limiter"] = limiter
    app.extensions["celery"] = celery_app
    app.extensions["socketio"] = socketio
    app.extensions["redis_client"] = Redis.from_url(app.config.get("REDIS_URL", REDIS_URL))

    # Ağır servis (model/analiz) import & instance – CI/Smoke’ta opsiyonel
    def _is_skip_heavy() -> bool:
        return _bool_env("SKIP_HEAVY_IMPORTS", False)

    if os.getenv("FLASK_ENV") == "testing":
        from types import SimpleNamespace
        app.ytd_system_instance = SimpleNamespace(collector=None, ai=None, engine=None)
    else:
        YTDCryptoSystem: Optional[type] = None
        if not _is_skip_heavy():
            try:
                from backend.core.services import YTDCryptoSystem as _YT
                YTDCryptoSystem = _YT
            except Exception as exc:
                logger.warning(f"YTDCryptoSystem import atlandı: {exc}")
        try:
            app.ytd_system_instance = (YTDCryptoSystem() if YTDCryptoSystem else None)  # type: ignore[call-arg]
        except Exception as exc:
            logger.warning(f"YTDCryptoSystem instance oluşturulamadı: {exc}")
            app.ytd_system_instance = None

    # -------- Observability: request id + latency logging --------
    @app.before_request
    def _inject_request_id_and_timer():
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_id = rid
        g._t0 = perf_counter()

    @app.after_request
    def _after(resp):
        try:
            dt = perf_counter() - getattr(g, "_t0", perf_counter())
            app.logger.info(
                {
                    "event": "http_access",
                    "method": request.method,
                    "path": request.path,
                    "status": resp.status_code,
                    "request_id": getattr(g, "request_id", None),
                    "user_id": getattr(getattr(g, "user", None), "id", None),
                    "remote_addr": request.remote_addr,
                    "latency_sec": round(dt, 4),
                }
            )
            resp.headers["X-Request-ID"] = getattr(g, "request_id", "")
        except Exception:
            pass
        return resp

    # -------- /metrics endpoint (optional auth / IP allow) --------
    def _metrics_allowed() -> bool:
        allow_ips = [x.strip() for x in os.getenv("METRICS_ALLOW_IPS", "").split(",") if x.strip()]
        return (not allow_ips) or (request.remote_addr in allow_ips)

    @app.route("/metrics")
    def metrics():
        if not _metrics_allowed():
            return jsonify({"error": "forbidden"}), 403
        u, p = os.getenv("METRICS_BASIC_AUTH_USER"), os.getenv("METRICS_BASIC_AUTH_PASS")
        if u and p:
            auth = request.authorization
            if not auth or auth.username != u or auth.password != p:
                return Response("Auth required", 401, {"WWW-Authenticate": 'Basic realm="metrics"'})
        return Response(b"".join(prometheus_wsgi_app({}, lambda *a, **k: None)), mimetype="text/plain")

    # Blueprint’ler
    from backend.auth.routes import auth_bp
    from backend.api.routes import api_bp
    from backend.admin_panel.routes import admin_bp
    # plan_bp importunu proxy üzerinden yap (backend/api/plan.py)
    from backend.api.plan import plan_bp
    from backend.api.admin.plans import plan_admin_bp
    from backend.api.plan_admin_limits import plan_admin_limits_bp
    from backend.api.admin.usage_limits import admin_usage_bp
    from backend.api.admin.promo_codes import admin_promo_bp
    from backend.api.admin.promotion_codes import admin_promotion_bp
    from backend.api.admin.promo_stats import stats_bp
    from backend.api.admin.predictions import predictions_bp
    from backend.api.admin.users import user_admin_bp
    from backend.api.admin.audit import audit_bp
    from backend.api.admin.backup import backup_bp
    from backend.api.admin.system_events import events_bp
    from backend.api.admin.analytics import analytics_bp
    from backend.api.admin.logs import admin_logs_bp
    from backend.api.admin.feature_flags import feature_flags_bp
    from backend.api.admin.draks_monitor import admin_draks_bp
    from backend.api.admin.tests import admin_tests_bp
    from backend.api.limits import bp as limits_bp
    from backend.api.ta_routes import bp as ta_bp
    from backend.api.public.technical import technical_bp
    from backend.api.public.subscriptions import subscriptions_bp
    from backend.api.decision import decision_bp

    # Ağır bağımlılıkları gerektiren blueprint'i CI/Smoke ortamında yükleme
    def _maybe_import_predict_bp():
        val = os.getenv("SKIP_HEAVY_IMPORTS", "false").strip().lower()
        if val in {"1", "true", "yes", "on"}:
            logger.info("SKIP_HEAVY_IMPORTS aktif, predict_routes yüklenmiyor.")
            return None
        try:
            from backend.routes.predict_routes import predict_bp
            return predict_bp
        except Exception as exc:  # pragma: no cover
            logger.warning(f"predict_routes yüklenemedi: {exc}")
            return None

    predict_bp = _maybe_import_predict_bp()

    # Kayıt
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    if predict_bp:
        app.register_blueprint(predict_bp, url_prefix="/api")
    app.register_blueprint(plan_admin_limits_bp)
    app.register_blueprint(plan_bp, url_prefix="/api")
    app.register_blueprint(plan_admin_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_usage_bp)
    app.register_blueprint(admin_promo_bp)
    app.register_blueprint(admin_promotion_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(user_admin_bp)
    app.register_blueprint(audit_bp, url_prefix="/api")
    app.register_blueprint(backup_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(admin_logs_bp, url_prefix="/api/admin")
    app.register_blueprint(ta_bp)
    app.register_blueprint(technical_bp)
    app.register_blueprint(feature_flags_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_draks_bp)
    app.register_blueprint(admin_tests_bp)
    app.register_blueprint(decision_bp)
    app.register_blueprint(subscriptions_bp)
    app.register_blueprint(limits_bp)

    # --- DRAKS Karar Motoru blueprint ---
    try:
        from backend.draks import draks_bp
        app.register_blueprint(draks_bp)
    except Exception as e:  # pragma: no cover
        logger.warning(f"DRAKS blueprint yüklenemedi: {e}")

    # Health
    @app.route("/health", methods=["GET"])
    def health_check():
        db_status, redis_status = "ok", "ok"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {e}"
            logger.error(f"Health DB: {e}")
        try:
            app.extensions["redis_client"].ping()
        except Exception as e:
            redis_status = f"error: {e}"
            logger.error(f"Health Redis: {e}")
        overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
        return jsonify(
            {
                "status": overall,
                "database": db_status,
                "redis": redis_status,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        ), 200

    # Error handlers
    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal Server Error: %s", error)
        return jsonify({"error": "Sunucu hatası"}), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Kaynak bulunamadı."}), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({"error": "Erişim engellendi."}), 403

    # Socket.IO events
    @socketio.on("connect", namespace="/")
    def handle_connect():
        logger.info("WS connected")
        emit("my response", {"data": "Connected"})

    @socketio.on("connect", namespace="/alerts")
    @check_usage_limit("realtime_alert")
    def handle_alerts_connect(auth):
        api_key = auth.get("api_key") if auth else None
        user = User.query.filter_by(api_key=api_key).first()
        if not user or user.subscription_level.value < SubscriptionPlan.PREMIUM.value:
            logger.warning("Unauthorized WS alerts connection")
            return False
        g.user = user
        logger.info(f"Alerts WS connected: {user.username}")

    @socketio.on("disconnect", namespace="/")
    def handle_disconnect():
        logger.info("WS disconnected")

    @socketio.on("disconnect", namespace="/alerts")
    def handle_alerts_disconnect():
        logger.info("Alerts WS disconnected")

    # Opsiyonel: scheduler tetikleyicisi (ENV ile aç/kapat)
    if os.getenv("ENABLE_SCHEDULER", "0") == "1":
        try:
            from backend.api.admin import prediction_scheduler  # noqa: F401
        except Exception as exc:
            logger.warning(f"Scheduler yüklenemedi: {exc}")

    return app
