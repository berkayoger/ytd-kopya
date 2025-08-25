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
        user.generate_api_key()  # API key gerekli
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


def test_usage_count_basic_functionality(test_app):
    """Temel kullanım sayma fonksiyonalitesini test et."""
    with test_app.app_context():
        import json
        plan = Plan(
            name="test_plan",
            price=0.0,
            features=json.dumps({"test_feature": 5})
        )
        db.session.add(plan)
        db.session.commit()

        user = User(
            username="testuser",
            role=UserRole.USER,
            plan_id=plan.id,
            subscription_level=SubscriptionPlan.BASIC
        )
        user.set_password("pass")
        user.generate_api_key()  # API key eklendi
        db.session.add(user)
        db.session.commit()

        # Bugün 3 kullanım ekle
        now = datetime.utcnow()
        for i in range(3):
            db.session.add(UsageLog(
                user_id=user.id, 
                action="test_feature", 
                timestamp=now
            ))
        
        # Dün 2 kullanım ekle (bunlar sayılmamalı)
        yesterday = now - timedelta(days=1)
        for i in range(2):
            db.session.add(UsageLog(
                user_id=user.id, 
                action="test_feature", 
                timestamp=yesterday
            ))
        
        db.session.commit()

        # Sadece bugünküler sayılmalı
        count = get_usage_count(user, "test_feature")
        assert count == 3

        # Olmayan özellik için 0 dönmeli
        count_nonexistent = get_usage_count(user, "nonexistent_feature")
        assert count_nonexistent == 0


def test_usage_tracking_basic(test_app):
    """Usage tracking fonksiyonunun temel çalışmasını test et."""
    with test_app.app_context():
        from backend.utils.usage_tracking import record_usage
        import json
        
        plan = Plan(
            name="tracking_plan",
            price=0.0,
            features=json.dumps({"track_feature": 3})
        )
        db.session.add(plan)
        db.session.commit()

        user = User(
            username="trackuser",
            role=UserRole.USER,
            plan_id=plan.id,
            subscription_level=SubscriptionPlan.BASIC
        )
        user.set_password("pass")
        user.generate_api_key()  # API key eklendi
        db.session.add(user)
        db.session.commit()

        # Kullanımı kaydet
        record_usage(user, "track_feature")
        record_usage(user, "track_feature")

        # Sayım kontrolü
        count = get_usage_count(user, "track_feature")
        assert count == 2
