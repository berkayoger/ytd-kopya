import io
import logging

from app.secure_logging import SecureLogger, SensitiveDataFilter


def test_filter_redacts_api_key():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SensitiveDataFilter())
    logger = logging.getLogger("secure-test")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)

    logger.info("api_key=1234567890abcdef")
    contents = stream.getvalue()

    assert "***REDACTED***" in contents
    assert "1234567890abcdef" not in contents


def test_safe_log_dict_masks_values():
    data = {"password": "secret123", "token": "abcd1234", "note": "ok"}
    masked = SecureLogger.safe_log_dict(data)

    assert masked["password"].startswith("***") and masked["password"].endswith("t123")
    assert masked["token"] == "***1234"
    assert masked["note"] == "ok"
