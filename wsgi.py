import logging
import os
from loguru import logger

from backend import create_app, socketio

try:
    from backend.core.services import YTDCryptoSystem  # noqa: F401
except Exception as exc:  # pragma: no cover
    logging.getLogger(__name__).warning(
        "YTDCryptoSystem import atlandı: %s", exc
    )
    YTDCryptoSystem = None

app = create_app()

if YTDCryptoSystem:
    app.ytd_system_instance = YTDCryptoSystem()


if __name__ == '__main__':
    logger.info("Flask uygulaması başlatılıyor.")
    # CI ve container için varsayılan host'u 0.0.0.0 yap
    socketio.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
        allow_unsafe_werkzeug=True,
    )
