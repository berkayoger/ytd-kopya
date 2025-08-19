import os

from .stripe_provider import StripeProvider
from .stub_craftgate import CraftgateProvider


def get_provider():
    name = (os.getenv("BILLING_PROVIDER") or "stripe").lower()
    if name == "stripe":
        return StripeProvider()
    if name == "craftgate":
        return CraftgateProvider()
