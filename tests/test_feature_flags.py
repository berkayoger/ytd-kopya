"""Tests for feature flag system."""

import pytest
from flask import Flask

from backend.api.admin.feature_flags import feature_flags_bp
from backend.utils.feature_flags import feature_flag_enabled, all_feature_flags


def test_feature_flag_enabled_true():
    assert feature_flag_enabled("recommendation_enabled") is True


def test_feature_flag_enabled_false():
    assert feature_flag_enabled("non_existent_feature") is False


def test_all_feature_flags():
    flags = all_feature_flags()
    assert isinstance(flags, dict)
    assert "recommendation_enabled" in flags


@pytest.fixture
def test_app():
    app = Flask(__name__)
    app.register_blueprint(feature_flags_bp, url_prefix="/api/admin")
    app.config["TESTING"] = True
    return app.test_client()


def test_get_feature_flags(test_app):
    res = test_app.get("/api/admin/feature-flags")
    assert res.status_code == 200
    data = res.get_json()
    assert "recommendation_enabled" in data


def test_update_feature_flag(test_app):
    res = test_app.put("/api/admin/feature-flags", json={
        "recommendation_enabled": False,
        "next_generation_model": True
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["updated"]["recommendation_enabled"] is False
    assert data["updated"]["next_generation_model"] is True


def test_invalid_update_payload(test_app):
    res = test_app.put("/api/admin/feature-flags", json=["not", "a", "dict"])
    assert res.status_code == 400
    assert "error" in res.get_json()

