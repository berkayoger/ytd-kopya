from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass
class CheckoutSession:
    url: str


@dataclass
class BillingPortal:
    url: str


class BillingProvider:
    name: str = "base"

    def create_checkout_session(
        self,
        *,
        customer_id: Optional[str],
        plan: Dict[str, Any],
        success_url: str,
        cancel_url: str,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> CheckoutSession:
        raise NotImplementedError

    def create_billing_portal(
        self, *, customer_id: str, return_url: str
    ) -> BillingPortal:
        raise NotImplementedError

    def verify_and_parse_webhook(self, *, payload: bytes, sig_header: str):
        """Return (event_type:str, data:dict, event_id:str)."""
        raise NotImplementedError
