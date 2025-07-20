import json
from backend.db.models import SubscriptionPlanLimits

def get_effective_limits(user):
    """
    Kullanıcıya özel limit varsa onu döndür, yoksa plan bazlı limitleri döndür.
    """
    if getattr(user, "custom_features", None):
        try:
            return json.loads(user.custom_features)
        except Exception:
            pass  # bozuk JSON varsa plan limitine düş
    return SubscriptionPlanLimits.get_limits(user.subscription_level)

def enforce_limit(user, key: str, usage_count: int) -> bool:
    """
    Belirli bir limit anahtarı için kullanıcının limiti aşıp aşmadığını kontrol eder.
    """
    limits = get_effective_limits(user)
    limit_value = limits.get(key)
    if limit_value is None:
        return True  # sınırsız kullanım
    return usage_count < limit_value
