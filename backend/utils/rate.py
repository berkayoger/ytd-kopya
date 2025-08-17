"""Basit rate limit string doğrulama yardımcıları."""

from __future__ import annotations


def parse_rate_string(s: str, default: str = "2/hour") -> str:
    """<int>/<second|minute|hour|day> formatını doğrular."""
    if not isinstance(s, str):
        return default

    s = s.strip().lower()
    try:
        n, per = s.split("/")
        n_int = int(n)
        if n_int <= 0:
            return default
        if per not in {"second", "minute", "hour", "day"}:
            return default
        return f"{n_int}/{per}"
    except Exception:
        return default

