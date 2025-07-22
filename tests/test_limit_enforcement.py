import pytest
from datetime import datetime, timedelta
from backend import create_app, db
from backend.db.models import User, UsageLog, UserRole, SubscriptionPlan
from backend.models.plan import Plan
from backend.utils.usage_limits import get_usage_count


@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def user_with_limits(test_app):
    with test_app.app_context():
        import json
        plan = Plan(
            name="basic",
            price=0.0,
            features=json.dumps({
                "predict_daily": 2,
                "generate_chart": 2,
                "prediction": 2
            })
        )
        db.session.add(plan)
        db.session.commit()

        user = User(
            username="limituser",
            role=UserRole.USER,
            plan_id=plan.id,
            subscription_level=SubscriptionPlan.BASIC
        )
        user.set_password("pass")
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()
        return user


def test_limit_enforcement_logic(test_app, user_with_limits):
    with test_app.app_context():
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        db.session.add_all([
            UsageLog(user_id=user_with_limits.id, action="predict_daily", timestamp=now),
            UsageLog(user_id=user_with_limits.id, action="generate_chart", timestamp=now),
            UsageLog(user_id=user_with_limits.id, action="generate_chart", timestamp=now),
            UsageLog(user_id=user_with_limits.id, action="generate_chart", timestamp=yesterday),
        ])
        db.session.commit()

        pd_count = get_usage_count(user_with_limits, "predict_daily")
        gc_count = get_usage_count(user_with_limits, "generate_chart")

        assert pd_count == 1
        assert gc_count == 2

def test_predict_endpoint_respects_limits(test_app, user_with_limits):
    from backend.db.models import UsageLog
    from backend.utils.usage_tracking import record_usage

    with test_app.test_client() as client:
        with test_app.app_context():
            # Limiti doldur: 2 çağrı yap
            record_usage(user_with_limits, "prediction")
            record_usage(user_with_limits, "prediction")

            access_token = user_with_limits.generate_access_token()
            db.session.commit()

            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": user_with_limits.api_key,
                "X-CSRF-TOKEN": "test",  # require_csrf patch'lenmiş olmalı
                "Content-Type": "application/json"
            }

            # require_csrf ve jwt_required patch'lenmiş olmalı
            # Sınırı aşan 3. çağrı
            response = client.post("/api/predict/", json={"coin": "BTC"}, headers=headers)

            assert response.status_code == 429
            assert "limit" in response.get_json().get("error", "").lower()

