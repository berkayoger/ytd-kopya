# backend/utils/validators.py
import re
from typing import Final

_SYMBOL_RE: Final = re.compile(r"^[A-Z0-9\-_.]{1,15}$")


def validate_crypto_symbol(symbol: str) -> bool:
    """Kripto sembolünü basit kurallarla doğrular."""
    if not symbol:
        return False
    return bool(_SYMBOL_RE.fullmatch(symbol))
