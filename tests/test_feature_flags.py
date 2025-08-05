"""Tests for feature flag system."""

import pytest
from flask import Flask

from backend.api.admin.feature_flags import feature_flags_bp
from backend.utils.feature_flags import all_feature_flags, feature_flag_enabled


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
    res = test_app.post(
        "/api/admin/feature-flags/recommendation_enabled",
        json={"enabled": False},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["recommendation_enabled"] is False

    # Restore to True for consistency
    res = test_app.post(
        "/api/admin/feature-flags/recommendation_enabled",
        json={"enabled": True},
    )
    assert res.status_code == 200
    assert res.get_json()["recommendation_enabled"] is True


def test_invalid_update_request(test_app):
    res = test_app.post(
        "/api/admin/feature-flags/recommendation_enabled",
        json={},
    )
    assert res.status_code == 400
    assert "error" in res.get_json()

