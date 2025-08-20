"""
Güvenlik sarmalayıcı WSGI:
- APP_IMPORT_CANDIDATES env değişkeninden (module:attr) ilk çalışanı import eder.
- Eğer attr çağrılabilir create_app ise çağırır, değilse Flask app nesnesi olarak kabul eder.
- app.security_bootstrap.bootstrap_security ile güvenlik katmanlarını uygular.

gunicorn örneği:
  gunicorn -w 4 -t 120 -b 0.0.0.0:8000 app.secure_app:app
"""
import importlib
import os
from typing import Optional

from app.security_bootstrap import bootstrap_security
from app.auto_register import register_all
from werkzeug.middleware.proxy_fix import ProxyFix

def _resolve_candidate(spec: str):
    mod, _, attr = spec.partition(":")
    if not mod or not attr:
        return None
    module = importlib.import_module(mod)
    obj = getattr(module, attr, None)
    if obj is None:
        return None
    if callable(obj):
        try:
            return obj()
        except TypeError:
            # Parametre istiyorsa desteklemiyoruz
            return None
    return obj

def _load_app_from_candidates() -> Optional[object]:
    candidates = os.getenv(
        "APP_IMPORT_CANDIDATES",
        "backend.app:create_app,backend.app:app,app:create_app,app:app",
    )
    for cand in [c.strip() for c in candidates.split(",") if c.strip()]:
        app = _resolve_candidate(cand)
        if app is not None:
            return app
    raise RuntimeError("Uygulama bulunamadı. APP_IMPORT_CANDIDATES değerini kontrol edin.")

# Gerçek uygulamayı çözüp güvenlik katmanlarını uygula
_real_app = _load_app_from_candidates()

# Reverse proxy arkasında güvenli şema/host bilgisini doğru okuyabilmek için (HSTS, secure cookie, is_secure)
def _maybe_apply_proxy_fix(app):
    if os.getenv("PROXY_FIX_ENABLED", "true").lower() == "true":
        x_for   = int(os.getenv("PROXY_FIX_X_FOR", "1"))
        x_proto = int(os.getenv("PROXY_FIX_X_PROTO", "1"))
        x_host  = int(os.getenv("PROXY_FIX_X_HOST", "1"))
        x_port  = int(os.getenv("PROXY_FIX_X_PORT", "1"))
        x_pref  = int(os.getenv("PROXY_FIX_X_PREFIX", "0"))
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto, x_host=x_host, x_port=x_port, x_prefix=x_pref)
    return app

_real_app = _maybe_apply_proxy_fix(_real_app)
app = bootstrap_security(_real_app)

# Otomatik blueprint ve veritabanı kayıtları
register_all(app)

