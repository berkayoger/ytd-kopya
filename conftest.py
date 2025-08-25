# -*- coding: utf-8 -*-
# Pytest için global ayarlar: offline, determinizm, güvenli test ortamı

import os
import pytest
from typing import Iterator
from types import SimpleNamespace
from flask import Flask, request

# --- Ortam değişkenleri (deterministik & offline) ---------------------------
os.environ.setdefault("COINGECKO_SHIM_OFFLINE", "1")
os.environ.setdefault("COINGECKO_MIN_INTERVAL_SEC", "0")
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("PYTHONHASHSEED", "0")


# --- Ağ erişimini kapat -----------------------------------------------------
@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Testlerde dış ağ bağlantılarını engelle."""
    import socket

    def guard(*args, **kwargs):
        raise RuntimeError("Test sırasında ağ erişimi engellendi")

    monkeypatch.setattr(socket, "create_connection", guard, raising=True)
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Test sırasında ağ engellendi")),
    )
    yield


# --- JWT doğrulamasını bypass et (test kolaylığı) ---------------------------
@pytest.fixture(autouse=True)
def _bypass_jwt(monkeypatch):
    # verify_jwt_in_request'i no-op yap
    try:
        import flask_jwt_extended.view_decorators as vd  # type: ignore
        monkeypatch.setattr(vd, "verify_jwt_in_request", lambda *a, **k: None)
    except Exception:
        pass

    # get_jwt_identity() çağrıları "test-user" döndürsün
    try:
        import flask_jwt_extended as jwt  # type: ignore
        monkeypatch.setattr(jwt, "get_jwt_identity", lambda: "test-user")
    except Exception:
        pass


# --- backend.create_app varsa, her app'e test kullanıcısı enjekte et --------
@pytest.fixture(autouse=True)
def _wrap_create_app(monkeypatch):
    try:
        import backend  # type: ignore
        orig_create_app = backend.create_app  # type: ignore[attr-defined]
    except Exception:
        return

    def _inject_hook(app: Flask):
        if getattr(app, "_testing_user_injected", False):
            return

        @app.before_request
        def _inject_testing_user():
            # REQUIRE_AUTH_FOR_HEALTH=true ise /health'e dokunma (bazı testler 401 bekliyor)
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
                    custom_features='{"draks": true}',
                )

        app._testing_user_injected = True

    def _wrapped_create_app(*args, **kwargs):
        app = orig_create_app(*args, **kwargs)
        _inject_hook(app)
        return app

    monkeypatch.setattr(backend, "create_app", _wrapped_create_app, raising=True)


# --- Doğrudan Flask() ile üretilen app'lere de aynı enjeksiynu uygula -------
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
                    custom_features='{"draks": true}',
                )

        app._testing_user_injected = True

    def patched(self: Flask, *args, **kwargs):
        try:
            if self.config.get("TESTING", True):
                _inject(self)
        finally:
            return orig_test_client(self, *args, **kwargs)

    monkeypatch.setattr(Flask, "test_client", patched, raising=True)


# --- Test APP fixture --------------------------------------------------------
@pytest.fixture(scope="session")
def app():
    """
    Proje create_app() verirse onu kullanır; vermezse minimal bir Flask app kurar.
    Fallback app'te /api/admin/logs blueprint'i mutlaka register edilir.
    """
    # Güvenli test ortamı değişkenleri
    os.environ.setdefault("TESTING", "1")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

    # create_app import
    try:
        from backend.app import create_app as _create_app  # type: ignore
    except Exception:
        _create_app = None

    if _create_app is None:
        # ---- Fallback minimal app ----
        _app = Flask("conftest")
        _app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///:memory:"),
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )

        # SQLAlchemy extension ekle
        from flask_sqlalchemy import SQLAlchemy
        _db = SQLAlchemy()
        _db.init_app(_app)
        if not hasattr(_app, "extensions"):
            _app.extensions = {}
        _app.extensions["sqlalchemy"] = _db

        # Logs blueprint'ini mutlaka eklemeyi dene
        try:
            from backend.api.admin.logs import admin_logs_bp  # type: ignore
            _app.register_blueprint(admin_logs_bp)
        except Exception as e:  # pragma: no cover
            _app.logger.warning(f"admin_logs_bp fallback register failed: {e}")
    else:
        # ---- Projenin gerçek create_app'i ----
        try:
            _app = _create_app(testing=True)  # type: ignore
        except TypeError:
            _app = _create_app()  # type: ignore
            _app.config.update(TESTING=True)

        # Her ihtimale karşı, /api/admin/logs kuralı yoksa blueprint'i ekle
        try:
            rules = {r.rule for r in _app.url_map.iter_rules()}
            if "/api/admin/logs" not in rules:
                from backend.api.admin.logs import admin_logs_bp  # type: ignore
                _app.register_blueprint(admin_logs_bp)
        except Exception:
            pass

    # App context’i açık tut
    ctx = _app.app_context()
    ctx.push()
    try:
        yield _app
    finally:
        ctx.pop()


# --- DB fixture (Flask-SQLAlchemy) ------------------------------------------
@pytest.fixture
def db(app):
    """
    SQLAlchemy 'db' fixture:
      - app.extensions['sqlalchemy'] varsa onu kullanır,
      - yoksa backend.extensions.db / backend.models.db arar,
      - yine yoksa yeni bir SQLAlchemy() oluşturur.
      - backend.models içindeki tüm alt-modülleri import eder (tablolar kaydolur),
      - 'logs' tablosu yoksa minimal bir Log modeli oluşturup create_all yapar.
    """
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import inspect, func
    import importlib
    import pkgutil

    # DB ayarları (in-memory)
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", os.getenv("DATABASE_URL", "sqlite:///:memory:"))
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    sqlalchemy_db = None

    # 1) App extensions üzerinden
    try:
        ext = getattr(app, "extensions", {})
        if isinstance(ext, dict) and "sqlalchemy" in ext and isinstance(ext["sqlalchemy"], SQLAlchemy):
            sqlalchemy_db = ext["sqlalchemy"]
    except Exception:
        pass

    # 2) Proje modüllerinden 'db' yakalamayı dene
    if sqlalchemy_db is None:
        for modpath in ("backend.extensions", "backend.models"):
            try:
                mod = importlib.import_module(modpath)
                candidate = getattr(mod, "db", None)
                if isinstance(candidate, SQLAlchemy):
                    sqlalchemy_db = candidate
                    try:
                        candidate.engine  # init edilmiş mi
                    except Exception:
                        candidate.init_app(app)
                    break
            except Exception:
                continue

    # 3) Hiçbiri yoksa yeni instance
    if sqlalchemy_db is None:
        sqlalchemy_db = SQLAlchemy()
        sqlalchemy_db.init_app(app)

    # --- MODELLERİ YÜKLE: backend.models ve alt-modüller
    def _load_models():
        try:
            pkg = importlib.import_module("backend.models")
        except Exception:
            pkg = None

        if pkg and hasattr(pkg, "__path__"):
            for m in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
                try:
                    importlib.import_module(m.name)
                except Exception:
                    pass

        # Muhtemel tekil modül isimleri
        for name in (
            "backend.models.log",
            "backend.models.logs",
            "backend.models.logging",
            "backend.log",
            "backend.logs",
        ):
            try:
                importlib.import_module(name)
            except Exception:
                pass

    with app.app_context():
        _load_models()

        # Şemayı tazele
        try:
            sqlalchemy_db.drop_all()
        except Exception:
            pass
        sqlalchemy_db.create_all()

        # 'logs' tablosu var mı?
        insp = inspect(sqlalchemy_db.engine)
        if "logs" not in insp.get_table_names():
            # Minimal Log modeli (testlerin kullandığı alanlar)
            class Log(sqlalchemy_db.Model):  # type: ignore
                __tablename__ = "logs"
                id = sqlalchemy_db.Column(sqlalchemy_db.String(36), primary_key=True)
                timestamp = sqlalchemy_db.Column(sqlalchemy_db.DateTime, server_default=func.now())
                user_id = sqlalchemy_db.Column(sqlalchemy_db.String(64), nullable=True)
                username = sqlalchemy_db.Column(sqlalchemy_db.String(128))
                ip_address = sqlalchemy_db.Column(sqlalchemy_db.String(64))
                action = sqlalchemy_db.Column(sqlalchemy_db.String(64))
                target = sqlalchemy_db.Column(sqlalchemy_db.String(256))
                description = sqlalchemy_db.Column(sqlalchemy_db.Text)
                status = sqlalchemy_db.Column(sqlalchemy_db.String(32))
                source = sqlalchemy_db.Column(sqlalchemy_db.String(64), nullable=True)
                user_agent = sqlalchemy_db.Column(sqlalchemy_db.String(256), nullable=True)

            sqlalchemy_db.create_all()

        yield sqlalchemy_db

        # Temizlik
        sqlalchemy_db.session.remove()
        try:
            sqlalchemy_db.drop_all()
        except Exception:
            pass


# --- Basit client & yardımcı fixture'lar ------------------------------------
@pytest.fixture
def client(app) -> Iterator:
    """pytest-flask olmadan sade test client."""
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_headers():
    return {
        "Authorization": "Bearer test-token",
        "X-API-KEY": "test-api-key",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }


@pytest.fixture
def test_user():
    return SimpleNamespace(
        id="test-user",
        username="test-admin",
        is_admin=True,
        custom_features='{"draks": true}',
    )
