import os

from .base import BillingProvider, CheckoutSession, BillingPortal


class CraftgateProvider(BillingProvider):
    """İskelet – gerçek Craftgate entegrasyonu için SDK çağrılarını ekleyin."""

    name = "craftgate"

    def __init__(self):
        if not os.getenv("CRAFTGATE_API_KEY"):
            raise RuntimeError("CRAFTGATE_API_KEY not set")

    def create_checkout_session(self, *, customer_id, plan, success_url, cancel_url, metadata=None):
        url = success_url + "?mock=cg"
        return CheckoutSession(url=url)

    def create_billing_portal(self, *, customer_id: str, return_url: str) -> BillingPortal:
        return BillingPortal(url=return_url)

    def verify_and_parse_webhook(self, *, payload: bytes, sig_header: str):
        return "subscription.updated", {}, "mock-event-id"

