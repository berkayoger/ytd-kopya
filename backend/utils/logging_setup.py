import logging
import sys
import uuid
from contextvars import ContextVar
from flask import request, g

# Try to import pythonjsonlogger, fallback to regular logging if not available
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Filter to add request ID to log records"""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get() or "-"
        return True


def setup_logging(level: str = "INFO") -> None:
    """Setup logging with optional JSON formatting and request ID correlation"""
    try:
        log_level = getattr(logging, str(level).upper(), logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        
        handler = logging.StreamHandler(sys.stdout)
        
        if HAS_JSON_LOGGER:
            # Use structured JSON logging if available
            fmt = jsonlogger.JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s"
            )
        else:
            # Fallback to regular formatting
            fmt = logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [%(request_id)s]: %(message)s"
            )
        
        handler.setFormatter(fmt)
        handler.addFilter(RequestIdFilter())
        
        root.setLevel(log_level)
        root.addHandler(handler)
        
    except Exception:
        # Fallback to basic INFO if anything goes wrong
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            stream=sys.stdout
        )


def setup_json_logging(level: str = "INFO") -> None:
    """Setup JSON structured logging with request ID correlation"""
    if not HAS_JSON_LOGGER:
        # Fallback to regular logging
        setup_logging(level)
        return
    
    handler = logging.StreamHandler(sys.stdout)
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s"
    )
    handler.setFormatter(fmt)
    handler.addFilter(RequestIdFilter())
    
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)
    else:
        root.handlers = [handler]


def with_request_id():
    """Middleware to generate/maintain X-Request-ID for request correlation"""
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    g.request_id = rid
    _request_id_ctx.set(rid)

