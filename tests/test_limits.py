import json
import pytest

from backend import create_app, db
from backend.db.models import User, UserRole
from backend.utils.limits import enforce_limit

@pytest.fixture
def test_user(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        user = User(username="limit_user", subscription_level="BASIC", role=UserRole.USER)
        user.set_password("pass")
        user.generate_api_key()
        user.custom_features = json.dumps({"predict_daily": 3})
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.remove()
        db.drop_all()

def test_enforce_limit_allows_usage(test_user):
    assert enforce_limit(test_user, "predict_daily", 2) is True

def test_enforce_limit_denies_usage(test_user):
    assert enforce_limit(test_user, "predict_daily", 3) is False

def test_enforce_limit_with_missing_key_allows(test_user):
    assert enforce_limit(test_user, "unknown_limit", 999) is True
