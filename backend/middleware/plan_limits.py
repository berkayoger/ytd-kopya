import json
from functools import wraps

from flask import current_app, g, jsonify, request

from backend.db.models import User, UserRole


def enforce_plan_limit(limit_key):
    """Decorator to enforce subscription plan feature limits."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = getattr(request, "current_user", None) or getattr(g, "user", None)
            if not user:
                api_key = request.headers.get("X-API-KEY")
                if api_key:
                    user = User.query.filter_by(api_key=api_key).first()
                    if user:
                        g.user = user
            else:
                # In testing, some middlewares may set a dummy SimpleNamespace.
                # Ensure we resolve to a real User model if possible.
                if (
                    current_app
                    and current_app.config.get("TESTING")
                    and not isinstance(user, User)
                ):
                    api_key = request.headers.get("X-API-KEY")
                    if api_key:
                        u = User.query.filter_by(api_key=api_key).first()
                        if u:
                            user = g.user = u
            if not user or not user.plan or not user.plan.features:
                try:
                    current_app.logger.warning(
                        "plan_limit_denied",
                        extra={
                            "reason": "no_plan_or_features",
                            "has_user": bool(user),
                            "has_plan": bool(getattr(user, "plan", None)),
                            "has_features": bool(
                                getattr(getattr(user, "plan", None), "features", None)
                            ),
                            "user_id": getattr(user, "id", None),
                        },
                    )
                except Exception:
                    pass
                return jsonify({"error": "Abonelik planı bulunamadı."}), 403

            user_role = getattr(user, "role", None)
            if user_role in [UserRole.ADMIN, UserRole.SYSTEM_ADMIN]:
                return f(*args, **kwargs)

            features = user.plan.features
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except Exception:
                    return jsonify({"error": "Plan özellikleri okunamadı."}), 500

            limit = features.get(limit_key)
            if limit is None:
                try:
                    current_app.logger.warning(
                        "plan_limit_denied",
                        extra={
                            "reason": "limit_undefined",
                            "limit_key": limit_key,
                            "user_id": getattr(user, "id", None),
                        },
                    )
                except Exception:
                    pass
                return jsonify({"error": f"{limit_key} limiti tanımlı değil."}), 403

            current_count = user.get_usage_count(limit_key)
            if current_count >= limit:
                try:
                    current_app.logger.warning(
                        "plan_limit_denied",
                        extra={
                            "reason": "limit_exceeded",
                            "limit_key": limit_key,
                            "current_count": current_count,
                            "limit": limit,
                            "user_id": getattr(user, "id", None),
                        },
                    )
                except Exception:
                    pass
                return jsonify({"error": f"{limit_key} limiti aşıldı. ({limit})"}), 429

            return f(*args, **kwargs)

        return wrapped

    return decorator
