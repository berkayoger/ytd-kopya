import os
import logging
from loguru import logger

from backend import create_app, socketio
try:
    from backend.core.services import YTDCryptoSystem  # noqa: F401
except Exception as exc:  # pragma: no cover
    logging.getLogger(__name__).warning("YTDCryptoSystem import atlandı: %s", exc)
    YTDCryptoSystem = None

app = create_app()
if YTDCryptoSystem:
    app.ytd_system_instance = YTDCryptoSystem()

if __name__ == '__main__':
    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", "5000"))
    except Exception:
        port = 5000
    logger.info("Flask uygulaması başlatılıyor. %s:%s", host, port)
    socketio.run(
        app,
        debug=app.config.get("DEBUG", False),
        host=host,
        port=port,
        allow_unsafe_werkzeug=True
    )
