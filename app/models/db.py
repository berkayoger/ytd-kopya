import os
from datetime import datetime
from uuid import uuid4

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import OperationalError


db: SQLAlchemy = SQLAlchemy(session_options={"autoflush": False})


class User(db.Model):
    __tablename__ = "auth_users"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    totp_secret = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Plan(db.Model):
    __tablename__ = "plans"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    price_minor = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(8), nullable=False, default="TRY")
    interval = db.Column(db.String(16), nullable=False, default="month")
    active = db.Column(db.Boolean, default=True, nullable=False)
    limits_json = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("auth_users.id"), nullable=False, index=True)
    provider = db.Column(db.String(32), nullable=False)
    provider_customer_id = db.Column(db.String(128), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("auth_users.id"), nullable=False, index=True)
    plan_id = db.Column(db.String(36), db.ForeignKey("plans.id"), nullable=False)
    provider = db.Column(db.String(32), nullable=False)
    provider_sub_id = db.Column(db.String(128), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False)
    current_period_end = db.Column(db.DateTime, nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("auth_users.id"), nullable=False, index=True)
    provider_invoice_id = db.Column(db.String(128), nullable=False, index=True)
    amount_minor = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(8), nullable=False)
    status = db.Column(db.String(32), nullable=False)
    hosted_url = db.Column(db.String(512), nullable=True)
    pdf_url = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def _attach_db(app):
    """Flask uygulamasına SQLAlchemy örneğini bağla."""
    if "sqlalchemy" in app.extensions:
        return app.extensions["sqlalchemy"].db
    uri = app.config.get("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", uri)
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    db.init_app(app)
    return db


def ensure_db_and_tables(app) -> None:
    """Veritabanını ve tabloları oluştur."""
    _attach_db(app)
    try:
        with app.app_context():
            db.create_all()
    except OperationalError:
        # DB yoksa uygulama yine kalksın
        pass


def seed_plans(app) -> None:
    """SEED_PLANS ortam değişkeninden plan verilerini ekle."""
    seeds = (os.getenv("SEED_PLANS") or "").strip()
    if not seeds:
        return
    with app.app_context():
        for item in seeds.split(","):
            try:
                code, price, curr, interval = item.split(":")
            except ValueError:
                continue
            exists = Plan.query.filter_by(code=code).first()
            if not exists:
                db.session.add(
                    Plan(
                        code=code,
                        price_minor=int(price),
                        currency=curr,
                        interval=interval,
                    )
                )
        db.session.commit()

