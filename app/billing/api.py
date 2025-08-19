import os
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app

from ..models.db import db, Plan, Customer, Subscription, Invoice, User
from ..core.security import decode_token, _redis_client
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
    cust = _ensure_customer(user, provider)
    site = os.getenv("SITE_URL", "").rstrip("/")
    succ = site + (os.getenv("CHECKOUT_SUCCESS_PATH") or "/billing/success")
    canc = site + (os.getenv("CHECKOUT_CANCEL_PATH") or "/billing/cancel")
    sess = provider.create_checkout_session(
        customer_id=cust.provider_customer_id,
        plan={
            "code": plan.code,
            "price_minor": plan.price_minor,
            "currency": plan.currency,
            "interval": plan.interval,
        },
        success_url=succ,
        cancel_url=canc,
    )
    return jsonify({"redirect_url": sess.url}), 200


@bp.post("/portal")
def portal():
    user = _auth_user()
    if not user:
        return jsonify({"detail": "unauthorized"}), 401
    provider = get_provider()
    cust = _ensure_customer(user, provider)
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
    current_app.logger.info("Webhook %s %s", ev_type, event_id)
    if ev_type == "checkout.session.completed":
        cust_id = data["customer"]
        sub_id = data["subscription"]
        user = Customer.query.filter_by(
            provider=provider.name, provider_customer_id=cust_id
        ).first()
        if user:
            sub = Subscription(
                user_id=user.user_id,
                plan_id=Plan.query.filter_by(code=data["metadata"].get("plan_code")).first().id,
                provider=provider.name,
                provider_sub_id=sub_id,
                status="active",
            )
            db.session.add(sub)
            db.session.commit()
    elif ev_type == "invoice.paid":
        uid = (
            Customer.query.filter_by(
                provider_customer_id=data["customer"], provider=provider.name
            ).first().user_id
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


@bp.post("/cancel")
def cancel():
    user = _auth_user()
    if not user:
        return jsonify({"detail": "unauthorized"}), 401
    sub = Subscription.query.filter_by(user_id=user.id, status="active").first()
    if not sub:
        return jsonify({"detail": "no active subscription"}), 404
    sub.cancel_at_period_end = True
    db.session.commit()
    return jsonify({"status": "scheduled"}), 200


@bp.get("/usage")
def usage():
    user = _auth_user()
    if not user:
        return jsonify({"detail": "unauthorized"}), 401
    key = f"usage:{user.id}"
    data = _redis_client.hgetall(key) or {}
    return jsonify({k.decode(): int(v) for k, v in data.items()}), 200

