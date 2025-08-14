"""Tests for feature flag system."""

import os
os.environ["FLASK_ENV"] = "testing"
import pytest
from flask import Flask

from backend.api.admin.feature_flags import feature_flags_bp
from backend.utils.feature_flags import all_feature_flags, feature_flag_enabled
import backend.utils.feature_flags as feature_flags


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
    os.environ["FLASK_ENV"] = "testing"
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


class DummyRedis:
    def __init__(self):
        self.store = {}
        self.hstore = {}

    def set(self, key, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def hset(self, key, mapping):
        self.hstore[key] = mapping

    def hgetall(self, key):
        return self.hstore.get(key, {})

    def sadd(self, key, value):
        self.store.setdefault(key, set()).add(value)

    def smembers(self, key):
        return self.store.get(key, set())


def test_export_feature_flags(test_app):
    res = test_app.get("/api/admin/feature-flags/export")
    assert res.status_code == 200
    data = res.get_json()
    assert "flags" in data and "meta" in data


def test_export_feature_flags_error(test_app, monkeypatch):
    def _raise():
        raise ValueError("boom")

    monkeypatch.setattr(feature_flags, "export_all_flags", _raise)
    res = test_app.get("/api/admin/feature-flags/export")
    assert res.status_code == 500
    assert "error" in res.get_json()


def test_alias_handling(monkeypatch):
    monkeypatch.setattr(feature_flags, "USE_REDIS", False)
    monkeypatch.setattr(feature_flags, "redis_client", None)
    monkeypatch.setattr(feature_flags, "_default_flags", dict(feature_flags._default_flags))

    feature_flags.set_feature_flag("draks", True)
    assert feature_flag_enabled("draks_enabled") is True
    feature_flags.set_feature_flag("draks_enabled", False)
    assert feature_flag_enabled("draks") is False


def test_import_feature_flags(test_app, monkeypatch):
    monkeypatch.setattr(feature_flags, "_default_flags", {})
    monkeypatch.setattr(feature_flags, "_default_flag_meta", {})
    payload = {
        "flags": {"new_flag": True},
        "meta": {"new_flag": {"description": "desc", "category": "cat"}},
    }
    res = test_app.post("/api/admin/feature-flags/import", json=payload)
    assert res.status_code == 200
    res = test_app.get("/api/admin/feature-flags")
    data = res.get_json()
    assert data["new_flag"]["enabled"] is True
    assert data["new_flag"]["category"] == "cat"


def test_import_feature_flags_invalid_payload(test_app):
    res = test_app.post("/api/admin/feature-flags/import", json="invalid")
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_get_flags_by_category(test_app, monkeypatch):
    monkeypatch.setattr(feature_flags, "_default_flags", {})
    monkeypatch.setattr(feature_flags, "_default_flag_meta", {})
    payload = {
        "flags": {"a": True, "b": False},
        "meta": {
            "a": {"description": "", "category": "cat1"},
            "b": {"description": "", "category": "cat2"},
        },
    }
    test_app.post("/api/admin/feature-flags/import", json=payload)
    res = test_app.get("/api/admin/feature-flags/category/cat1")
    assert res.status_code == 200
    data = res.get_json()
    assert list(data.keys()) == ["a"]


def test_get_flags_by_category_unknown(test_app):
    res = test_app.get("/api/admin/feature-flags/category/unknown")
    assert res.status_code == 200
    assert res.get_json() == {}


def test_create_flag_in_memory(test_app, monkeypatch):
    monkeypatch.setattr(feature_flags, "USE_REDIS", False)
    monkeypatch.setattr(feature_flags, "redis_client", None)
    monkeypatch.setattr(
        feature_flags, "_default_flags", dict(feature_flags._default_flags)
    )
    monkeypatch.setattr(feature_flags, "_default_flag_meta", {})

    res = test_app.post(
        "/api/admin/feature-flags/create",
        json={
            "name": "in_memory_flag",
            "enabled": True,
            "description": "In memory",
            "category": "internal",
        },
    )
    assert res.status_code == 200

    res = test_app.get("/api/admin/feature-flags")
    data = res.get_json()
    assert data["in_memory_flag"]["enabled"] is True
    assert data["in_memory_flag"]["description"] == "In memory"
    assert data["in_memory_flag"]["category"] == "internal"


def test_create_flag_redis(test_app, monkeypatch):
    dummy = DummyRedis()
    monkeypatch.setattr(feature_flags, "redis_client", dummy)
    monkeypatch.setattr(feature_flags, "USE_REDIS", True)
    monkeypatch.setattr(
        feature_flags, "_default_flags", dict(feature_flags._default_flags)
    )
    monkeypatch.setattr(feature_flags, "_default_flag_meta", {})

    res = test_app.post(
        "/api/admin/feature-flags/create",
        json={
            "name": "redis_flag",
            "enabled": False,
            "description": "From redis",
            "category": "beta",
        },
    )
    assert res.status_code == 200

    res = test_app.get("/api/admin/feature-flags")
    data = res.get_json()
    assert data["redis_flag"]["enabled"] is False
    assert data["redis_flag"]["description"] == "From redis"
    assert data["redis_flag"]["category"] == "beta"

