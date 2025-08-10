from __future__ import annotations

import logging
from pythonjsonlogger import jsonlogger


def configure_json_logging(level: str = "INFO") -> None:
    """JSON formatında logging yapılandır."""
    root = logging.getLogger()
    root.handlers = []
    root.setLevel(level)

    handler = logging.StreamHandler()
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d %(funcName)s"
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)
    # örnek kullanım: logging.getLogger("app").info("service_started", extra={"component": "api"})
