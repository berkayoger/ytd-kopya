"""Geçici Feature Flag kontrol sistemi.

İleride Redis veya DB destekli yapıya taşınabilir.
"""


def feature_flag_enabled(flag_name: str) -> bool:
    """Return ``True`` if the feature flag is enabled.

    Flags are currently stored in a static dictionary. This helper can be
    replaced with a database- or Redis-backed implementation in the future.
    """

    enabled_flags = {
        "recommendation_enabled": True,
        # "advanced_forecast": False,
        # "next_generation_model": False,
    }
    return enabled_flags.get(flag_name, False)


def all_feature_flags() -> dict:
    """Return a mapping of all feature flags and their states."""

    return {
        "recommendation_enabled": feature_flag_enabled("recommendation_enabled"),
    }

