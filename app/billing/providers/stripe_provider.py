import os

import stripe

from .base import BillingPortal, BillingProvider, CheckoutSession


class StripeProvider(BillingProvider):
    name = "stripe"

    def __init__(self):
        sk = os.getenv("STRIPE_SECRET_KEY")
        if not sk:
            raise RuntimeError("STRIPE_SECRET_KEY not set")
        stripe.api_key = sk

    def create_checkout_session(
        self, *, customer_id, plan, success_url, cancel_url, metadata=None
    ) -> CheckoutSession:
        interval = plan["interval"]
        unit_amount = plan["price_minor"]
        currency = plan["currency"].lower()
        params = {
            "mode": "subscription",
            "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": cancel_url,
            "line_items": [
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": plan["code"]},
                        "unit_amount": unit_amount,
                        "recurring": {"interval": interval},
                    },
                    "quantity": 1,
                }
            ],
            "allow_promotion_codes": True,
        }
        if metadata:
            params["metadata"] = dict(metadata)
        if customer_id:
            params["customer"] = customer_id
        sess = stripe.checkout.Session.create(**params)
        return CheckoutSession(url=sess.url)

    def create_billing_portal(
        self, *, customer_id: str, return_url: str
    ) -> BillingPortal:
        sess = stripe.billing_portal.Session.create(
            customer=customer_id, return_url=return_url
        )
        return BillingPortal(url=sess.url)

    def verify_and_parse_webhook(self, *, payload: bytes, sig_header: str):
        secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=secret
        )
        return event["type"], event["data"]["object"], event["id"]
