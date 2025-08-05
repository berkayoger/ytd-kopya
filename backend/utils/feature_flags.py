"""Geçici Feature Flag kontrol sistemi.

İleride Redis veya DB destekli yapıya taşınabilir.
"""


def feature_flag_enabled(flag_name: str) -> bool:
    """Return ``True`` if the feature flag is enabled."""

    return _flags.get(flag_name, False)


def set_feature_flag(flag_name: str, value: bool) -> None:
    """Update a specific feature flag."""
    if flag_name in _flags:
        _flags[flag_name] = value


# Internal flag storage (can be replaced by Redis or DB in the future)
_flags = {
    "recommendation_enabled": True,
    "next_generation_model": False,
    "advanced_forecast": False,
}


def all_feature_flags() -> dict:
    """Return a mapping of all feature flags and their states."""

    return {flag: feature_flag_enabled(flag) for flag in _flags}

