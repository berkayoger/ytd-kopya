from unittest.mock import patch

import backend


def test_load_dotenv_called_when_not_production(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    with patch("backend.load_dotenv") as mock_load:
        backend.create_app()
        mock_load.assert_called_once()


def test_load_dotenv_skipped_in_production(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    with patch("backend.load_dotenv") as mock_load:
        backend.create_app()
        mock_load.assert_not_called()
