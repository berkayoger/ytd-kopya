"""
Dayanıklı WSGI loader:
- Önce APP_IMPORT_CANDIDATES içindeki (modul:attr) yollarını dener.
- Bulamazsa minimal Flask app döndürür ve /healthz = 200, /readiness = 503 verir.
- Import hataları asla prosesi düşürmez (worker crash yok).
"""
from __future__ import annotations
import importlib
import os
from typing import Any

DEFAULT_CANDIDATES = (
    "backend.app:create_app,"
    "backend.app:app,"
    "app:create_app,"
    "app:app"
)

def _try_load(cand: str) -> Any | None:
    mod, _, attr = cand.partition(":")
    try:
        m = importlib.import_module(mod)
        obj = getattr(m, attr)
        return obj() if callable(obj) else obj
    except Exception as exc:  # sakin kal, sıradakine geç
        # Debug için istersen burada print bırakabilirsin:
        # print(f"[wsgi] import failed for {cand}: {exc}")
        return None

def load_app() -> Any:
    raw = os.getenv("APP_IMPORT_CANDIDATES", DEFAULT_CANDIDATES)
    candidates = [c.strip() for c in raw.split(",") if c.strip()]
    for c in candidates:
        app = _try_load(c)
        if app is not None:
            return app
    # Fallback: minimal app ki health endpoint'leri çalışsın
    from flask import Flask, jsonify
    app = Flask("fallback")

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok"), 200

    @app.get("/readiness")
    def readiness():
        return jsonify(status="degraded", detail="app import failed"), 503

    return app

app = load_app()

# Varsa gerçek health blueprint'i ekle (opsiyonel). Hata olursa sus.
try:
    from backend.health import bp as health_bp  # type: ignore
    paths = {str(r.rule) for r in app.url_map.iter_rules()}
    if "/healthz" not in paths or "/readiness" not in paths:
        app.register_blueprint(health_bp)
except Exception:
    pass
