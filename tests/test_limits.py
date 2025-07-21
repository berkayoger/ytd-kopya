import json
import pytest

from backend import create_app, db
from backend.db.models import User, UserRole
from backend.models.plan import Plan
from backend.utils.limits import enforce_limit
from backend.middleware.plan_limits import enforce_plan_limit
from flask import jsonify

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


@pytest.fixture
def test_user(test_app):
    with test_app.app_context():
        plan = Plan(name="basic", price=0.0, features=json.dumps({"predict_daily": 5}))
        db.session.add(plan)
        db.session.commit()

        user = User(username="limit_user", subscription_level="BASIC", role=UserRole.USER, plan_id=plan.id)
        user.custom_features = json.dumps({"predict_daily": 3})
        user.set_password("pass")
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()
        return user

def test_enforce_limit_allows_usage(test_user):
    assert enforce_limit(test_user, "predict_daily", 2) is True

def test_enforce_limit_denies_usage(test_user):
    assert enforce_limit(test_user, "predict_daily", 3) is False

def test_enforce_limit_with_missing_key_allows(test_user):
    assert enforce_limit(test_user, "unknown_limit", 999) is True


def test_enforce_plan_limit_decorator_behavior(test_app, test_user):
    app = test_app

    @app.route("/test-decorated", methods=["POST"])
    @enforce_plan_limit("predict_daily")
    def decorated_route():
        return jsonify({"message": "OK"}), 200

    with app.test_client() as client:
        with app.app_context():
            from flask import g
            g.user = test_user
            response = client.post("/test-decorated")
            assert response.status_code == 200


def test_enforce_plan_limit_blocked_usage(test_app, test_user):
    app = test_app

    # Kullanıcının limiti 3, 3 kullanım ile dolduğunu varsayalım
    test_user.custom_features = json.dumps({"predict_daily": 3})
    db.session.commit()

    @app.route("/test-decorated-block", methods=["POST"])
    @enforce_plan_limit("predict_daily")
    def blocked_route():
        return jsonify({"message": "BLOCKED SHOULD NOT RETURN"}), 200

    with app.test_client() as client:
        with app.app_context():
            from flask import g
            g.user = test_user
            # simulate limit hit by mocking check_usage_count result
            from unittest.mock import patch
            with patch("backend.middleware.plan_limits.get_usage_count", return_value=3):
                response = client.post("/test-decorated-block")
                assert response.status_code == 429
                assert b"limit asildi" in response.data


def test_get_effective_limits_custom_json(test_user):
    test_user.custom_features = json.dumps({"predict_daily": 99})
    limits = enforce_limit.__globals__["get_effective_limits"](test_user)
    assert limits.get("predict_daily") == 99


def test_get_effective_limits_fallback(test_user):
    test_user.custom_features = "{INVALID_JSON}"
    limits = enforce_limit.__globals__["get_effective_limits"](test_user)
    # should fallback to default plan limits
    assert isinstance(limits, dict)
