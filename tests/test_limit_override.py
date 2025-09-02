import json

import pytest

from backend import create_app, db
from backend.db.models import SubscriptionPlan, User
from backend.utils.limits import enforce_limit


@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_enforce_limit_with_custom_override(test_app):
    with test_app.app_context():
        user = User(
            username="premium_user", subscription_level=SubscriptionPlan.PREMIUM
        )
        user.custom_features = json.dumps({"predict_daily": 2})
        user.set_password("test123")  # Set password
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()

        # Test with usage under limit
        allowed, used, limit = enforce_limit(user, "predict_daily")
        assert allowed  # Should be allowed since no usage recorded yet
        assert used == 0  # No usage recorded


def test_enforce_limit_fallback_to_plan(test_app, monkeypatch):
    with test_app.app_context():
        # Mock the plan limits reading
        def mock_get_plan_limit(user, action, default=None):
            if action == "predict_daily":
                return 5
            return default

        monkeypatch.setattr("backend.utils.limits.get_plan_limit", mock_get_plan_limit)

        user = User(username="basic_user", subscription_level=SubscriptionPlan.BASIC)
        user.custom_features = None
        user.set_password("test123")  # Set password
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()

        allowed, used, limit = enforce_limit(user, "predict_daily")
        assert allowed  # Should be allowed
        assert used == 0  # No usage recorded
        assert limit == 5  # Should use mocked plan limit


def test_enforce_limit_malformed_json(test_app):
    with test_app.app_context():
        user = User(username="corrupted", subscription_level=SubscriptionPlan.BASIC)
        user.custom_features = "{invalid_json: true"
        user.set_password("test123")  # Set password
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()

        allowed, used, limit = enforce_limit(user, "predict_daily")
        assert allowed  # Should be allowed (no limit found)
        assert used == 0  # No usage recorded


def test_enforce_limit_with_no_limits(test_app):
    with test_app.app_context():
        user = User(
            username="unlimited_user", subscription_level=SubscriptionPlan.PREMIUM
        )
        user.custom_features = None
        user.set_password("test123")  # Set password
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()

        allowed, used, limit = enforce_limit(user, "predict_daily")
        assert allowed  # Should be allowed when no limits defined
        assert used == 0  # No usage recorded
        assert limit is None  # No limit should be found
