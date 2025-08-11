import importlib
import os
from typing import Callable, Any

def _try_load(cand: str):
    mod, _, attr = cand.partition(":")
    try:
        m = importlib.import_module(mod)
        obj = getattr(m, attr)
        return obj() if callable(obj) else obj
    except Exception:
        return None

def load_app() -> Any:
    candidates = os.getenv(
        "APP_IMPORT_CANDIDATES",
        "backend.app:create_app,backend.app:app,app:create_app,app:app"
    ).split(",")
    for c in [x.strip() for x in candidates if x.strip()]:
        app = _try_load(c)
        if app is not None:
            return app
    # Fallback: minimal app ki health endpoint'leri çalışsın
    from flask import Flask, jsonify
    app = Flask("fallback")

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/readiness")
    def readiness():
        # Gerçek app bulunamadıysa readiness'ı 503 döndürelim
        return jsonify(status="degraded", detail="app import failed"), 503

    return app

app = load_app()
