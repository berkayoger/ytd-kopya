from backend.app import create_app
from backend.app_rate_limit import setup_rate_limit
from backend.app_security import harden_app

try:
    from backend.utils.logging import before_request_hook
except Exception:  # pragma: no cover
    before_request_hook = None


app = create_app()

if before_request_hook:
    app.before_request(before_request_hook)
harden_app(app)
limiter = setup_rate_limit(app)
