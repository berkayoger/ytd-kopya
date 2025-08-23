"""Utils paketinin ana başlatıcısı."""

from .plan_limits import (
    PLAN_DEFAULTS,
    PLAN_LIMITS,
    PLAN_LIMITS_COMPAT,
    get_user_effective_limits,
    get_all_feature_keys,
    give_user_boost,
    check_custom_feature,
    check_and_increment_usage,
    enforce_plan_limits,
    # Ekstra yardımcılar (iki yama uyumu)
    get_plan_rate_limit,
    rate_limit_key_func,
)

from .usage_limits import (
    check_usage_limit,
    get_usage_status,
    get_usage_count,
)

__all__ = [
    "PLAN_DEFAULTS",
    "PLAN_LIMITS",
    "PLAN_LIMITS_COMPAT",
    "get_user_effective_limits",
    "get_all_feature_keys",
    "give_user_boost",
    "check_custom_feature",
    "check_and_increment_usage",
    "enforce_plan_limits",
    "check_usage_limit",
    "get_usage_status",
    "get_usage_count",
    # Ekstra yardımcılar (iki yama uyumu)
    "get_plan_rate_limit",
    "rate_limit_key_func",
]

