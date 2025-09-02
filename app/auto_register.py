from flask import Blueprint

from .models.db import ensure_db_and_tables, seed_plans


def _has_prefix(app, prefix: str) -> bool:
    """Uygulamada verilen prefix ile kayıtlı blueprint var mı?"""
    for rule in app.url_map.iter_rules():
        if str(rule.rule).startswith(prefix.rstrip("/")):
            return True
    return False


def _register_if_missing(app, bp: Blueprint, prefix: str) -> None:
    """Prefix mevcut değilse blueprint'i kaydet."""
    if not _has_prefix(app, prefix):
        app.register_blueprint(bp, url_prefix=prefix)


def register_all(app) -> None:
    """Blueprint'leri ve tabloları otomatik bağla (idempotent)."""
    ensure_db_and_tables(app)
    seed_plans(app)
    from .authx.api import bp as auth_bp
    from .billing.api import bp as billing_bp
    from .core.csrf_api import bp as csrf_bp

    _register_if_missing(app, auth_bp, "/api/auth")
    _register_if_missing(app, billing_bp, "/api/billing")
    _register_if_missing(app, csrf_bp, "/api/csrf")
