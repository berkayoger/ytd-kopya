# -*- coding: utf-8 -*-
from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app
from typing import Any, Dict, List
from sqlalchemy import Table, select, func, and_

admin_logs_bp = Blueprint("admin_logs_bp", __name__, url_prefix="/api/admin")


def _get_db():
    """
    Flask-SQLAlchemy instance'ını güvenli şekilde yakala.
    (create_app içinde extensions'e ekli ise oradan alır.)
    """
    try:
        ext = getattr(current_app, "extensions", {})
        db = ext.get("sqlalchemy")
        if db is None:
            from flask_sqlalchemy import SQLAlchemy  # type: ignore
            # Bazı kurulumlarda current_app.extensions["sqlalchemy"] yoksa:
            db = SQLAlchemy()
            db.init_app(current_app)
        return db
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"SQLAlchemy not available: {e}")


def _load_logs_table(db) -> Table:
    """ORM modeline ihtiyaç duymadan 'logs' tablosunu reflekte et."""
    return Table("logs", db.metadata, autoload_with=db.engine)  # type: ignore[arg-type]


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(row)
    ts = d.get("timestamp")
    if hasattr(ts, "isoformat"):
        d["timestamp"] = ts.isoformat()
    return d


@admin_logs_bp.get("/logs")
def list_logs():
    """
    GET /api/admin/logs
      - Query params:
          username: alt string araması (case-insensitive)
          action:   eşitlik (case-insensitive)
          limit:    default 50
          offset:   default 0
      - Response:
          { "results": [...], "total": <int> }
    """
    db = _get_db()
    logs = _load_logs_table(db)

    # --- Query params ---
    username = request.args.get("username", "").strip()
    action = request.args.get("action", "").strip()
    try:
        limit = int(request.args.get("limit", 50))
    except Exception:
        limit = 50
    try:
        offset = int(request.args.get("offset", 0))
    except Exception:
        offset = 0

    # Güvenli sınırlar (testler için küçük, prod'da daha yüksek tutulabilir)
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    if offset < 0:
        offset = 0

    # --- Filtreleri kur ---
    conds = []
    if username:
        conds.append(func.lower(logs.c.username).like(f"%{username.lower()}%"))
    if action:
        conds.append(func.lower(logs.c.action) == action.lower())

    where_clause = and_(*conds) if conds else None

    # --- Toplam sayıyı çek ---
    count_stmt = select(func.count()).select_from(logs)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = db.session.execute(count_stmt).scalar() or 0

    # --- Sayfalı sorgu (timestamp DESC sıralı) ---
    stmt = select(logs)
    if where_clause is not None:
        stmt = stmt.where(where_clause)
    # timestamp kolonu yoksa sıralama kısmı sessizce atlanır
    try:
        stmt = stmt.order_by(logs.c.timestamp.desc())
    except Exception:
        pass
    stmt = stmt.offset(offset).limit(limit)

    rows = db.session.execute(stmt).mappings().all()  # RowMapping listesi
    results: List[Dict[str, Any]] = [_serialize_row(r) for r in rows]

    return jsonify({"results": results, "total": int(total)})
