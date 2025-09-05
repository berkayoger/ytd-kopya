import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    try:
        log_level = getattr(logging, str(level).upper(), logging.INFO)
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                stream=sys.stdout,
            )
        else:
            logging.getLogger().setLevel(log_level)
    except Exception:
        # Fallback to basic INFO if anything goes wrong
        logging.basicConfig(level=logging.INFO)

