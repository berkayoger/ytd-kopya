import json
from datetime import datetime


def get_limit_status(user, limit_name, usage_value):
    """Return limit status for a user feature usage."""
    limits = user.plan.features_dict() if user.plan else {}
    if getattr(user, "boost_expire_at", None) and user.boost_expire_at > datetime.utcnow():
        try:
            limits.update(json.loads(user.boost_features or "{}"))
        except Exception:
            pass
    if getattr(user, "custom_features", None):
        try:
            limits.update(json.loads(user.custom_features or "{}"))
        except Exception:
            pass
    max_value = limits.get(limit_name)
    if not max_value:
        return "unlimited"
    try:
        ratio = float(usage_value) / float(max_value)
    except ZeroDivisionError:
        return "limit_exceeded"
    if ratio >= 1:
        return "limit_exceeded"
    elif ratio >= 0.8:
        return "limit_warning"
    return "ok"


def get_user_effective_limits(user):
    """Return merged feature limits for a user including plan, custom and boost."""
    limits = user.plan.features_dict() if user.plan else {}
    if getattr(user, "custom_features", None):
        try:
            limits.update(json.loads(user.custom_features or "{}"))
        except Exception:
            pass
    if getattr(user, "boost_expire_at", None) and user.boost_expire_at > datetime.utcnow():
        try:
            limits.update(json.loads(user.boost_features or "{}"))
        except Exception:
            pass
    return limits


def give_user_boost(user, features, expire_at):
    user.boost_features = json.dumps(features)
    user.boost_expire_at = expire_at
    from backend import db
    db.session.commit()
