import os, sys
from datetime import datetime, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend import create_app, db
from backend.db.models import User, Role, UserRole
from backend.models.plan import Plan
from backend.utils.plan_limits import get_user_effective_limits, give_user_boost


def setup_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    return create_app()


def test_effective_limits_with_boost(monkeypatch):
    app = setup_app(monkeypatch)
    with app.app_context():
        role = Role.query.filter_by(name="user").first()
        p = Plan(name="LimitPlan", price=0.0, features="{\"max_prediction_per_day\": 5}")
        db.session.add(p)
        db.session.commit()
        user = User(username="limituser", api_key="limitkey", role_id=role.id, role=UserRole.USER, plan_id=p.id)
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()
        give_user_boost(user, {"max_prediction_per_day": 10}, datetime.utcnow() + timedelta(days=1))
        limits = get_user_effective_limits(user)
        assert limits["max_prediction_per_day"] == 10
