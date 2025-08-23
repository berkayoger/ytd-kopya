"""
Lightweight shim for the `email_validator` package used in tests/CI.
Provides a minimal compatible API:
  - validate_email(email, allow_smtputf8=True, allow_empty_local=False)
  - EmailNotValidError (and alias EmailSyntaxError)

This is NOT a full RFC validator; it performs basic, deterministic checks
good enough for unit tests where the real dependency may not be installed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict

__all__ = ["validate_email", "EmailNotValidError", "EmailSyntaxError"]


class EmailNotValidError(ValueError):
    """Raised when an email address is deemed invalid by the shim."""


# Keep alias for compatibility with callers that import EmailSyntaxError
EmailSyntaxError = EmailNotValidError


_EMAIL_BASIC_RE = re.compile(
    r"^(?P<local>[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+)@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,})$"
)


@dataclass(frozen=True)
class _Result:
    email: str
    local: str
    domain: str
    ascii_email: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email,
            "local": self.local,
            "domain": self.domain,
            "ascii_email": self.ascii_email,
        }


def _normalize(email: str) -> _Result:
    match = _EMAIL_BASIC_RE.match(email)
    if not match:
        raise EmailNotValidError("Invalid email address format")

    local = match.group("local")
    domain = match.group("domain").lower()
    # Very small normalization akin to the real lib:
    # - trim surrounding whitespace
    # - lowercase domain
    # - keep local as-is (case-sensitive by spec, but many libs lowercase)
    normalized = f"{local}@{domain}"
    return _Result(
        email=normalized,
        local=local,
        domain=domain,
        ascii_email=normalized,
    )


def validate_email(
    email: str,
    allow_smtputf8: bool = True,
    allow_empty_local: bool = False,
    **_: Any,
) -> Dict[str, Any]:
    """
    Minimal validator: ensures it looks like local@domain.tld
    and returns a dict similar to the real library.
    """
    if not isinstance(email, str):
        raise EmailNotValidError("Email must be a string")

    s = email.strip()
    if not s:
        raise EmailNotValidError("Email must not be empty")

    if not allow_empty_local and s.startswith("@"):
        raise EmailNotValidError("Local part must not be empty")

    res = _normalize(s)
    return res.as_dict()
