import pytest
from backend import create_app, db
from backend.models.log import Log
from backend.utils.logger import create_log


@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_create_log_inserts_entry(test_app):
    with test_app.app_context():
        create_log(
            user_id="123",
            username="tester",
            ip_address="127.0.0.1",
            action="login",
            target="/login",
            description="User login",
        )
        log = Log.query.filter_by(user_id="123", action="login").first()
        assert log is not None
        assert log.username == "tester"
        assert log.ip_address == "127.0.0.1"
        assert log.status == "success"
        assert log.source == "web"

