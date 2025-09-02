from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from backend.models.log import Log


def create_log_entry(db, username="admin", action="login"):
    log = Log(
        id=str(uuid4()),
        username=username,
        action=action,
        target="/api/auth/login",
        description="Test login",
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
        status="success",
        timestamp=datetime.utcnow() - timedelta(minutes=5),
    )
    db.session.add(log)
    db.session.commit()
    return log


def test_get_logs(client, db):
    create_log_entry(db)

    response = client.get("/api/admin/logs")
    assert response.status_code == 200

    data = response.get_json()
    assert "total" in data
    assert "results" in data
    assert data["total"] >= 1
    assert any(entry["action"] == "login" for entry in data["results"])


def test_logs_filter_by_username(client, db):
    create_log_entry(db, username="admin")
    create_log_entry(db, username="otheruser")

    response = client.get("/api/admin/logs?username=admin")
    assert response.status_code == 200

    data = response.get_json()
    for log in data["results"]:
        assert "admin" in log["username"]


def test_logs_filter_by_action(client, db):
    create_log_entry(db, action="predict")
    create_log_entry(db, action="llm_analyze")

    response = client.get("/api/admin/logs?action=predict")
    assert response.status_code == 200

    data = response.get_json()
    assert all(log["action"] == "predict" for log in data["results"])


def test_logs_date_range(client, db):
    log = create_log_entry(db)
    start = (log.timestamp - timedelta(minutes=1)).isoformat()
    end = (log.timestamp + timedelta(minutes=1)).isoformat()

    response = client.get(f"/api/admin/logs?start_date={start}&end_date={end}")
    assert response.status_code == 200
    data = response.get_json()
    assert any(entry["id"] for entry in data["results"])


def test_logs_pagination(client, db):
    for i in range(20):
        create_log_entry(db, username=f"user{i}")

    response = client.get("/api/admin/logs?limit=5&offset=0")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["results"]) <= 5

    response2 = client.get("/api/admin/logs?limit=5&offset=5")
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert len(data2["results"]) <= 5
    assert data["results"] != data2["results"]
