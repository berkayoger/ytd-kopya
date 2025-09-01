import logging
import uuid

from flask import g, request


class CorrelationFormatter(logging.Formatter):
    def format(self, record):
        record.correlation_id = getattr(g, "cid", "?")
        return super().format(record)


def before_request_hook():
    g.cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
