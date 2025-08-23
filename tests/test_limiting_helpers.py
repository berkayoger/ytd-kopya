from flask import g
from backend import limiting
from backend.limiting import get_plan_rate_limit, rate_limit_key_func


def test_get_plan_rate_limit_defaults(app):
    with app.app_context():
        assert get_plan_rate_limit(None) == "30/minute"


def test_get_plan_rate_limit_env_override(monkeypatch):
    monkeypatch.setitem(limiting.DEFAULT_PLAN_LIMITS, "basic", "99/minute")
    assert get_plan_rate_limit("basic") == "99/minute"


def test_rate_limit_key_func_user(app):
    with app.test_request_context("/"):
        g.user_id = 42
        assert rate_limit_key_func() == "user:42"


def test_rate_limit_key_func_ip(app):
    with app.test_request_context("/", environ_overrides={"REMOTE_ADDR": "7.8.9.1"}):
        if hasattr(g, "user_id"):
            del g.user_id
        assert rate_limit_key_func() == "ip:7.8.9.1"

