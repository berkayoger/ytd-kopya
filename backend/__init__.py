# backend/__init__.py
import os
import sys
from datetime import timedelta, datetime
from flask import Flask, jsonify, request, g
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from celery import Celery
from flask_socketio import SocketIO, emit
from flask.testing import FlaskClient
from sqlalchemy import text
from redis import Redis
from dotenv import load_dotenv
from loguru import logger

from backend.db import db as base_db
from backend.limiting import limiter
from backend.db.models import User, SubscriptionPlan
from backend.models.plan import Plan
from backend.utils.usage_limits import check_usage_limit

load_dotenv()

# Redis default URL
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///ytd_crypto.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_SESSION_OPTIONS = {"expire_on_commit": False}
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }

    REDIS_URL = REDIS_URL
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_TIMEZONE = "Europe/Istanbul"

    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "super-secret-jwt-key-change-this-in-prod!"
    )
    ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", "change_me_access")
    REFRESH_TOKEN_SECRET = os.getenv("REFRESH_TOKEN_SECRET", "change_me_refresh")
    ACCESS_TOKEN_EXP_MINUTES = int(os.getenv("ACCESS_TOKEN_EXP_MINUTES", "15"))
    REFRESH_TOKEN_EXP_DAYS = int(os.getenv("REFRESH_TOKEN_EXP_DAYS", "7"))

    PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "300"))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

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

    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:80,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")

    ENV = os.getenv("FLASK_ENV", "development")

    @staticmethod
    def assert_production_jwt_key():
        if Config.ENV == "production" and (
            not Config.JWT_SECRET_KEY
            or Config.JWT_SECRET_KEY.startswith("super-secret")
        ):
            logger.critical(
                "🚨 KRİTİK HATA: Üretim ortamında geçersiz JWT_SECRET_KEY kullanılamaz!"
            )
            sys.exit(1)

    @staticmethod
    def assert_production_cors_origins():
        if Config.ENV == "production" and (
            "*" in Config.CORS_ORIGINS or len(Config.CORS_ORIGINS) == 0
        ):
            logger.critical(
                "🚨 KRİTİK HATA: Üretim ortamında CORS origins '*' içeremez!"
            )
            sys.exit(1)


# Global extension instances
db = base_db
celery_app = Celery()
socketio = SocketIO()


class LegacyTestClient(FlaskClient):
    def set_cookie(self, *args, **kwargs):
        if len(args) == 3 and "domain" not in kwargs:
            domain, key, value = args
            return super().set_cookie(key, value, domain=domain, **kwargs)
        return super().set_cookie(*args, **kwargs)


def create_app():
    app = Flask(__name__)
    app.test_client_class = LegacyTestClient
    app.config.from_object(Config)

    # Test env adjustments
    if os.getenv("FLASK_ENV") == "testing":
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False}
        }
        app.config["PRICE_CACHE_TTL"] = 0

    # Prod safety checks
    Config.assert_production_jwt_key()
    Config.assert_production_cors_origins()

    # Init extensions
    CORS(app, supports_credentials=True, origins=Config.CORS_ORIGINS)
    db.init_app(app)
    limiter.init_app(app)
    celery_app.conf.update(app.config)
    socketio.init_app(
        app,
        message_queue=Config.CELERY_BROKER_URL,
        cors_allowed_origins=Config.CORS_ORIGINS,
    )

    # DB setup for non-prod
    with app.app_context():
        if app.config["ENV"].lower() != "production":
            db.create_all()
            from backend.db.models import Role, Permission
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
            logger.info("Üretim ortamı: Otomatik tablo oluşturma atlandı.")

    # Attach extensions
    app.extensions["db"] = db
    app.extensions["limiter"] = limiter
    app.extensions["celery"] = celery_app
    app.extensions["socketio"] = socketio
    app.extensions["redis_client"] = Redis.from_url(app.config.get("REDIS_URL"))

    # YTD system init
    if os.getenv("FLASK_ENV") == "testing":
        from types import SimpleNamespace
        app.ytd_system_instance = SimpleNamespace(collector=None, ai=None, engine=None)
    else:
        try:
            from backend.core.services import YTDCryptoSystem
            app.ytd_system_instance = YTDCryptoSystem()
        except ImportError as e:
            logger.warning(f"YTDCryptoSystem yüklenemedi: {e}")
            app.ytd_system_instance = None

    # Blueprint registration
    from backend.auth.routes import auth_bp
    from backend.api.routes import api_bp
    from backend.admin_panel.routes import admin_bp
    from backend.api.plan_routes import plan_bp
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
    from backend.limits.routes import limits_bp
    from backend.api.ta_routes import bp as ta_bp
    from backend.api.public.technical import technical_bp
    from backend.api.public.subscriptions import subscriptions_bp
    from backend.api.decision import decision_bp
    from backend.routes.predict_routes import predict_bp

    blueprints = [
        (auth_bp, "/api/auth"),
        (api_bp, "/api"),
        (predict_bp, "/api"),
        (plan_admin_limits_bp, None),
        (plan_bp, "/api"),
        (plan_admin_bp, "/api"),
        (admin_bp, "/api/admin"),
        (admin_usage_bp, None),
        (admin_promo_bp, None),
        (admin_promotion_bp, None),
        (stats_bp, None),
        (predictions_bp, None),
        (user_admin_bp, None),
        (audit_bp, "/api"),
        (backup_bp, None),
        (events_bp, None),
        (analytics_bp, None),
        (admin_logs_bp, "/api/admin"),
        (ta_bp, None),
        (technical_bp, None),
        (feature_flags_bp, "/api/admin"),
        (decision_bp, None),
        (subscriptions_bp, None),
        (limits_bp, None),
    ]
    for bp, prefix in blueprints:
        app.register_blueprint(bp, url_prefix=prefix)

    # Health check
    @app.route("/health", methods=["GET"])
    def health_check():
        db_status, redis_status = "ok", "ok"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {e}"
            logger.error(f"DB health check failed: {e}")
        try:
            app.extensions["redis_client"].ping()
        except Exception as e:
            redis_status = f"error: {e}"
            logger.error(f"Redis health check failed: {e}")
        overall_status = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
        return jsonify({
            "status": overall_status,
            "database": db_status,
            "redis": redis_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }), 200

    # Error handlers
    @app.errorhandler(500)
    def internal_error(error):
        logger.exception(f"Internal Server Error: {error}")
        return jsonify({"error": "Sunucu hatası"}), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Kaynak bulunamadı."}), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({"error": "Erişim engellendi."}), 403

    # WebSocket events
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

    @socketio.on("disconnect", namespace="/")
    def handle_disconnect():
        logger.info("WS disconnected")

    @socketio.on("disconnect", namespace="/alerts")
    def handle_alerts_disconnect():
        logger.info("WS alerts disconnected")

    return app
