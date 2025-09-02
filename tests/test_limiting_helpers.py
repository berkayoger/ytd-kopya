from flask import g

from backend import limiting
from backend.limiting import get_plan_rate_limit, rate_limit_key_func


def test_get_plan_rate_limit_defaults(app):
    with app.app_context():
        assert get_plan_rate_limit(None) == "30 per minute"


def test_get_plan_rate_limit_env_override(monkeypatch):
    monkeypatch.setitem(limiting.DEFAULT_PLAN_LIMITS, "basic", "99/minute")
    assert get_plan_rate_limit("basic") == "99 per minute"


def test_rate_limit_key_func_user(app, monkeypatch):
    monkeypatch.setattr(limiting, "verify_jwt_in_request", lambda optional=True: None)
    monkeypatch.setattr(limiting, "get_jwt", lambda: {"sub": "42"})
    with app.test_request_context("/"):
        assert rate_limit_key_func() == "user:42"


def test_rate_limit_key_func_ip(app):
    with app.test_request_context("/", environ_overrides={"REMOTE_ADDR": "7.8.9.1"}):
        assert rate_limit_key_func() == "ip:7.8.9.1"
