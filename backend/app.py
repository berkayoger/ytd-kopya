import sys

from backend import create_app
from backend.app_rate_limit import setup_rate_limit
from backend.app_security import harden_app

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ gerekiyor; mevcut: %s" % (sys.version.split()[0],))

# optional: correlation id hook
try:  # pragma: no cover
    from backend.utils.logging import before_request_hook
except Exception:  # pragma: no cover
    before_request_hook = None

app = create_app()

if before_request_hook:
    app.before_request(before_request_hook)
harden_app(app)
limiter = setup_rate_limit(app)


# Basit sağlık ucu (CI ve canlı izleme için iyi bir çıpa)
@app.get("/api/health")
def _health():
    return {"status": "ok"}
