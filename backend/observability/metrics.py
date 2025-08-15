from __future__ import annotations
import os, time
from contextlib import contextmanager
from typing import Iterable, Optional
from prometheus_client import Counter, Histogram, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest

# Custom registry so we can export only our app metrics if needed
REGISTRY = CollectorRegistry()

def _latency_buckets_from_env() -> Optional[Iterable[float]]:
    raw = os.getenv("METRICS_LATENCY_BUCKETS", "").strip()
    if not raw:
        return None
    try:
        return [float(x) for x in raw.split(",") if x.strip()]
    except Exception:
        return None

_latency_buckets = _latency_buckets_from_env()

REQUEST_LATENCY = Histogram(
    "draks_request_latency_seconds",
    "Request latency in seconds.",
    ["route"],
    registry=REGISTRY,
    buckets=_latency_buckets or (
        0.01, 0.025, 0.05, 0.075, 0.1,
        0.2, 0.3, 0.5, 0.75, 1.0,
        2.0, 3.0, 5.0, 8.0, 13.0
    ),
)

DECISION_REQ_TOTAL = Counter(
    "draks_decision_requests_total",
    "Total number of decision/run requests.",
    ["status"],
    registry=REGISTRY,
)

COPY_REQ_TOTAL = Counter(
    "draks_copy_requests_total",
    "Total number of copy/evaluate requests.",
    ["status"],
    registry=REGISTRY,
)

ERRORS_TOTAL = Counter(
    "draks_errors_total",
    "Total number of DRAKS errors.",
    ["type"],
    registry=REGISTRY,
)


def inc_decision(status: str) -> None:
    DECISION_REQ_TOTAL.labels(status=str(status)).inc()


def inc_copy(status: str) -> None:
    COPY_REQ_TOTAL.labels(status=str(status)).inc()


def inc_error(err_type: str) -> None:
    ERRORS_TOTAL.labels(type=str(err_type)).inc()


@contextmanager
def observe(route: str):
    """Context manager to time a section and observe into REQUEST_LATENCY."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        REQUEST_LATENCY.labels(route=route).observe(dt)


def prometheus_wsgi_app(environ, start_response):
    """Minimal WSGI app returning metrics content. Use with Flask via a wrapper route."""
    data = generate_latest(REGISTRY)
    status = "200 OK"
    headers = [("Content-Type", CONTENT_TYPE_LATEST), ("Content-Length", str(len(data)))]
    start_response(status, headers)
    return [data]
