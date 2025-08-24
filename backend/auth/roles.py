from __future__ import annotations
from functools import wraps
from typing import Iterable, Set, Union
from flask import jsonify, request

# Güvenli import: JWT yoksa testlerde monkeypatch ile doldurulacak
try:  # pragma: no cover
    from flask_jwt_extended import verify_jwt_in_request, get_jwt  # type: ignore
except Exception:  # pragma: no cover
    def verify_jwt_in_request(optional: bool = False) -> None:  # type: ignore
        if not optional:
            raise RuntimeError("JWT extension not available")
    def get_jwt() -> dict:  # type: ignore
        return {}


def _normalize_roles(raw: Union[str, Iterable[str], None]) -> Set[str]:
    if raw is None:
        return set()
    if isinstance(raw, str):
        # "admin,user" | "admin" | "['admin','user']" gibi varyantlar
        cleaned = raw.replace("[", "").replace("]", "")
        parts = [p.strip().strip("'\"") for p in cleaned.split(",")]
        return {p for p in parts if p}
    try:
        return {str(x).strip() for x in raw if isinstance(x, str)}
    except Exception:
        return set()


def current_roles() -> Set[str]:
    '''
    JWT claim'lerinden rollerin kümesini üretir.
    Destek: roles (list/str), role (str), is_admin (bool).
    '''
    claims = get_jwt() or {}
    roles: Set[str] = set()
    roles |= _normalize_roles(claims.get("roles"))
    roles |= _normalize_roles(claims.get("role"))
    if claims.get("is_admin") is True:
        roles.add("admin")
    return roles


def has_any_role(*required: str) -> bool:
    r = {x.lower() for x in required if x}
    return bool(current_roles() & r)


def require_roles(*required: str):
    """
    Route decorator: JWT zorunlu, verilen rollerden en az biri gerekli.
    """
    required_l = tuple(x.lower() for x in required)
    def _wrap(fn):
        @wraps(fn)
        def _inner(*args, **kwargs):
            verify_jwt_in_request(optional=False)
            if not has_any_role(*required_l):
                return jsonify({"error": "forbidden", "required_roles": required_l}), 403
            return fn(*args, **kwargs)
        return _inner
    return _wrap


def ensure_admin_for_admin_paths():
    """
    Global guard: /api/admin/* isteklerinde admin rolü zorunlu.
    Flask before_request içinde çağrılmak üzere tasarlanmıştır.
    """
    path = (request.path or "").lower()
    if path.startswith("/api/admin"):
        verify_jwt_in_request(optional=False)
        if not has_any_role("admin"):
            return jsonify({"error": "forbidden", "required_roles": ["admin"]}), 403
    return None
