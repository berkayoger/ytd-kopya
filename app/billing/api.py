import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from ..core.security import _redis_client, decode_token
from ..models.db import Customer, Invoice, Plan, Subscription, User, db
from .providers import get_provider

bp = Blueprint("billing", __name__)


def _json():
    try:
        return request.get_json(force=True) or {}
    except Exception:
        return {}


def _auth_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        p = decode_token(auth.split(" ", 1)[1], require_type="access")
        return User.query.get(p["sub"])
    except Exception:
        return None


@bp.get("/usage")
def usage():
    user = _auth_user()
    if not user:
        return jsonify({"detail": "unauthorized"}), 401
    key = f"usage:{user.id}"
    # _redis_client decode_responses=True ile döner; .decode() gereksiz ve hata üretir.
    data = _redis_client().hgetall(key) or {}
    # string->int çevirmeye çalış, sayı değilse olduğu gibi bırak
    norm = {}
    for k, v in data.items():
        try:
            norm[k] = int(v)
        except Exception:
            norm[k] = v
    return jsonify(norm), 200


@bp.get("/plans")
def plans():
    rows = Plan.query.filter_by(active=True).all()
    return (
        jsonify(
            [
                {
                    "code": r.code,
                    "price_minor": r.price_minor,
                    "currency": r.currency,
                    "interval": r.interval,
                }
                for r in rows
            ]
        ),
        200,
    )


def _ensure_customer(user, provider):
    cust = Customer.query.filter_by(user_id=user.id, provider=provider.name).first()
    if cust:
        return cust
    provider_customer_id = f"{provider.name}:{user.id}"
    cust = Customer(
        user_id=user.id,
        provider=provider.name,
        provider_customer_id=provider_customer_id,
    )
    db.session.add(cust)
    db.session.commit()
    return cust


@bp.post("/checkout")
def checkout():
    user = _auth_user()
    if not user:
        return jsonify({"detail": "unauthorized"}), 401
    data = _json()
    plan = Plan.query.filter_by(code=data.get("plan_code"), active=True).first()
    if not plan:
        return jsonify({"detail": "plan not found"}), 404
    provider = get_provider()
    # Stripe: ilk alışverişte customer yaratmasın diye boş bırakıyoruz,
    # webhook’ta gelen customer id ile mapping oluşturacağız.
    cust = Customer.query.filter_by(user_id=user.id, provider=provider.name).first()
    customer_id = cust.provider_customer_id if cust else None
    site = os.getenv("SITE_URL", "").rstrip("/")
    succ = site + (os.getenv("CHECKOUT_SUCCESS_PATH") or "/billing/success")
    canc = site + (os.getenv("CHECKOUT_CANCEL_PATH") or "/billing/cancel")
    sess = provider.create_checkout_session(
        customer_id=customer_id,
        plan={
            "code": plan.code,
            "price_minor": plan.price_minor,
            "currency": plan.currency,
            "interval": plan.interval,
        },
        success_url=succ,
        cancel_url=canc,
        metadata={
            "user_id": str(user.id),
            "plan_code": plan.code,
        },
    )
    return jsonify({"redirect_url": sess.url}), 200


@bp.post("/portal")
def portal():
    user = _auth_user()
    if not user:
        return jsonify({"detail": "unauthorized"}), 401
    provider = get_provider()
    cust = Customer.query.filter_by(user_id=user.id, provider=provider.name).first()
    if not cust:
        return jsonify({"detail": "no customer"}), 404
    site = os.getenv("SITE_URL", "").rstrip("/")
    ret = site + (os.getenv("PORTAL_RETURN_PATH") or "/billing")
    sess = provider.create_billing_portal(
        customer_id=cust.provider_customer_id, return_url=ret
    )
    return jsonify({"redirect_url": sess.url}), 200


@bp.post("/webhook")
def webhook():
    provider = get_provider()
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature") or ""
    try:
        ev_type, data, event_id = provider.verify_and_parse_webhook(
            payload=payload, sig_header=sig
        )
    except Exception as e:
        current_app.logger.warning("Webhook verify failed: %s", e)
        return jsonify({"detail": "invalid"}), 400
    # idempotency
    key = f"billing:webhook:{event_id}"
    r = _redis_client()
    if not r.setnx(key, "1"):
        return jsonify({"status": "duplicate"}), 200
    r.expire(key, 60 * 60 * 24 * 3)

    current_app.logger.info("Webhook %s %s", ev_type, event_id)
    if ev_type == "checkout.session.completed":
        cust_id = data.get("customer")
        sub_id = data.get("subscription")
        meta = data.get("metadata") or {}
        plan_code = meta.get("plan_code")
        user_id = meta.get("user_id")
        if not (cust_id and sub_id and plan_code and user_id):
            current_app.logger.warning("checkout.completed missing fields")
            return jsonify({"status": "ignored"}), 200
        # Customer mapping yoksa oluştur
        cust = Customer.query.filter_by(
            provider=provider.name, provider_customer_id=cust_id
        ).first()
        if not cust:
            cust = Customer(
                user_id=user_id, provider=provider.name, provider_customer_id=cust_id
            )
            db.session.add(cust)
            db.session.commit()
        plan = Plan.query.filter_by(code=plan_code).first()
        if plan:
            sub = Subscription.query.filter_by(
                provider=provider.name, provider_sub_id=sub_id
            ).first()
            if not sub:
                db.session.add(
                    Subscription(
                        user_id=cust.user_id,
                        plan_id=plan.id,
                        provider=provider.name,
                        provider_sub_id=sub_id,
                        status="active",
                    )
                )
                db.session.commit()
    elif ev_type == "invoice.paid":
        uid = (
            Customer.query.filter_by(
                provider_customer_id=data["customer"], provider=provider.name
            )
            .first()
            .user_id
        )
        inv = Invoice(
            user_id=uid,
            provider_invoice_id=data["id"],
            amount_minor=data["amount_paid"],
            currency=data["currency"],
            status="paid",
            hosted_url=data.get("hosted_invoice_url"),
            pdf_url=data.get("invoice_pdf"),
        )
        db.session.add(inv)
        db.session.commit()
    return jsonify({"status": "ok"}), 200
