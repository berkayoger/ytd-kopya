# backend/utils/security.py

import hmac
import hashlib
import base64
from typing import Optional, Tuple
from flask import request, jsonify, Response
from loguru import logger

def verify_iyzico_signature(secret: str, data: bytes, signature: str) -> bool:
    """
    Iyzico callback imzasını HMAC-SHA256 kullanarak doğrular.
    
    Args:
        secret (str): Iyzico gizli anahtarınız (secret key).
        data (bytes): Callback'ten gelen ham istek gövdesi (raw request body).
        signature (str): 'X-Iyzico-Signature' başlığından gelen imza.

    Returns:
        bool: İmza geçerliyse True, değilse False döner.
    """
    if not secret or not signature:
        return False
    
    # Beklenen imzayı hesapla
    computed_hash = hmac.new(secret.encode('utf-8'), data, hashlib.sha256).digest()
    expected_signature = base64.b64encode(computed_hash).decode('utf-8')

    # Güvenli karşılaştırma yaparak zamanlama saldırılarını önle
    return hmac.compare_digest(expected_signature, signature)

def check_iyzico_signature(secret: str) -> Optional[Tuple[Response, int]]:
    """
    Wrapper helper: request üzerindeki raw body ve
    X-Iyzico-Signature header’ını alıp imzayı doğrular.
    Hata durumunda bir Flask Response nesnesi, başarılıysa None döner.
    """
    # Ham gövdeyi al (cache=False → diğer middleware’ler değiştirmediğinden emin oluruz)
    raw_body = request.get_data(cache=False)
    
    # Header’ı farklı formatlarla kontrol et
    signature = (
        request.headers.get('X-Iyzico-Signature')
        or request.headers.get('x-iyzico-signature')
    )
    
    if not verify_iyzico_signature(secret, raw_body, signature):
        # Başarısız imza denemelerini logla
        logger.warning(f"Iyzico imza doğrulama başarısız. IP={request.remote_addr}")
        # Saldırgana sistem içi detay vermek yerine genel cevap
        return jsonify({"error": "Geçersiz istek"}), 400
        
    # Geçerliyse None döndür, devam edilsin
    return None

def generate_csrf_token() -> str:
    """
    Güvenli bir CSRF token'ı oluşturur.
    """
    import secrets
    return secrets.token_hex(16)

# --- DRAKS Batch yardımcıları ---

import re

_SYMBOL_RE = re.compile(r"^[A-Z0-9./:-]{1,20}$")
_TIMEFRAME_WHITELIST = {
    "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"
}
_ASSET_WHITELIST = {"crypto", "equity"}


def validate_symbol(symbol: str) -> bool:
    """Sembolü büyük harfe çevirip regex ile doğrular."""
    try:
        return bool(_SYMBOL_RE.match(str(symbol).upper()))
    except Exception:
        return False


def validate_symbols_list(symbols: list[str], max_count: int) -> list[str]:
    """Geçerli sembolleri liste olarak döndürür."""
    out: list[str] = []
    for s in symbols[:max_count]:
        su = str(s).upper().strip()
        if validate_symbol(su):
            out.append(su)
    return out


def validate_timeframe(tf: str) -> bool:
    """Desteklenen timeframe'leri kontrol eder."""
    try:
        return str(tf) in _TIMEFRAME_WHITELIST
    except Exception:
        return False


def validate_asset(asset: str) -> bool:
    """Varlık tipini whitelist ile doğrular."""
    return str(asset).lower() in _ASSET_WHITELIST


def safe_cache_key(prefix: str, *parts: str) -> str:
    """Cache anahtarını temizleyip birleştirir."""
    clean = []
    for p in parts:
        x = re.sub(r"[^A-Z0-9./:\-]", "", str(p).upper())
        clean.append(x[:32])
    return f"{prefix}:" + ":".join(clean)
