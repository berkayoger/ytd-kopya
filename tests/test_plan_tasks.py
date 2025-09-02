import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend import create_app, db
from backend.db.models import Role, User, UserRole
from backend.models.plan import Plan


def setup_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    return create_app()


def test_auto_downgrade_expired_plan(monkeypatch):
    import pytest

    pytest.skip("Test requires Celery setup, skipping for now")


def test_auto_expire_boost(monkeypatch):
    import pytest

    pytest.skip("Test requires Celery setup, skipping for now")


def test_activate_pending_plan(monkeypatch):
    import pytest

    pytest.skip("Test requires Celery setup, skipping for now")
