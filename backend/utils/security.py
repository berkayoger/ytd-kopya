"""
Güvenlik middleware'leri - Input validation, XSS koruması, SQL injection önleme
"""

import html
import logging
import re
from functools import wraps
from typing import Any, Dict, List, Optional

from flask import jsonify, request

logger = logging.getLogger(__name__)

# Güvenli karakter pattern'leri
SAFE_PATTERNS = {
    "alphanumeric": re.compile(r"^[a-zA-Z0-9_-]+$"),
    "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "numeric": re.compile(r"^\d+$"),
    "decimal": re.compile(r"^\d+(\.\d+)?$"),
    "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "safe_string": re.compile(r"^[a-zA-Z0-9\s\-_.,!?()]+$"),
}

# Tehlikeli pattern'ler (SQL injection, XSS)
DANGEROUS_PATTERNS = [
    re.compile(
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        re.IGNORECASE,
    ),
    re.compile(r"(<script|javascript:|onload=|onerror=|onclick=)", re.IGNORECASE),
    re.compile(r"(\-\-|\#|\/\*|\*\/)", re.IGNORECASE),
    re.compile(r"(\'|\"|;|\||&)", re.IGNORECASE),
]


def sanitize_input(value: str) -> str:
    """Kullanıcı girdisini HTML escape ve whitespace temizleme ile güvenli hale getirir."""
    if not isinstance(value, str):
        return str(value)

    # HTML escape
    clean_value = html.escape(value.strip())

    # Fazla whitespace'leri temizle
    clean_value = " ".join(clean_value.split())

    return clean_value


def validate_input(
    value: str, pattern_name: str = "safe_string", max_length: int = 255
) -> bool:
    """Input'u belirlenen pattern'e göre doğrular."""
    if not value:
        return True  # Boş değerler kabul edilir

    # Uzunluk kontrolü
    if len(value) > max_length:
        return False

    # Tehlikeli pattern kontrolü
    for dangerous_pattern in DANGEROUS_PATTERNS:
        if dangerous_pattern.search(value):
            logger.warning(f"Dangerous pattern detected in input: {value[:50]}...")
            return False

    # Güvenli pattern kontrolü
    if pattern_name in SAFE_PATTERNS:
        return SAFE_PATTERNS[pattern_name].match(value) is not None

    return True


def validate_request_args(validation_rules: Dict[str, Dict[str, Any]]):
    """Request arguments'larını doğrular."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            validated_args = {}

            for param_name, rules in validation_rules.items():
                value = request.args.get(param_name)

                # Required kontrolü
                if rules.get("required", False) and not value:
                    return (
                        jsonify({"error": f"Required parameter missing: {param_name}"}),
                        400,
                    )

                # Default value
                if not value and "default" in rules:
                    value = rules["default"]

                if value:
                    # Sanitize
                    clean_value = sanitize_input(value)

                    # Validate
                    pattern = rules.get("pattern", "safe_string")
                    max_length = rules.get("max_length", 255)

                    if not validate_input(clean_value, pattern, max_length):
                        logger.warning(
                            f"Invalid input for {param_name}: {value[:50]}..."
                        )
                        return (
                            jsonify(
                                {"error": f"Invalid parameter format: {param_name}"}
                            ),
                            400,
                        )

                    validated_args[param_name] = clean_value
                else:
                    validated_args[param_name] = None

            # Validated args'ları request object'e ekle
            request.validated_args = validated_args
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Yaygın validation rule setleri
COMMON_VALIDATIONS = {
    "pagination": {
        "page": {
            "pattern": "numeric",
            "required": False,
            "default": "1",
            "max_length": 10,
        },
        "limit": {
            "pattern": "numeric",
            "required": False,
            "default": "10",
            "max_length": 3,
        },
        "offset": {"pattern": "numeric", "required": False, "max_length": 10},
    },
    "search_filter": {
        "search": {"pattern": "safe_string", "required": False, "max_length": 100},
        "sort_by": {"pattern": "alphanumeric", "required": False, "max_length": 50},
        "order": {"pattern": "alphanumeric", "required": False, "max_length": 4},
    },
    "date_range": {
        "start_date": {"pattern": "date", "required": False},
        "end_date": {"pattern": "date", "required": False},
    },
}


def validate_asset(asset: str) -> bool:
    """Asset ismini doğrular (coin sembolleri için)."""
    return validate_input(asset, "alphanumeric", 10)


def validate_timeframe(timeframe: str) -> bool:
    """Timeframe parametresini doğrular."""
    valid_timeframes = ["1h", "4h", "1d", "1w", "1m"]
    return timeframe in valid_timeframes


def validate_symbols_list(symbols: str) -> bool:
    """Virgülle ayrılmış sembol listesini doğrular."""
    if not symbols:
        return True
    symbol_list = symbols.split(",")
    return all(
        validate_input(symbol.strip(), "alphanumeric", 20) for symbol in symbol_list
    )


def safe_cache_key(key: str) -> str:
    """Cache key'i güvenli hale getirir - sadece alphanumeric karakterler."""
    import hashlib

    if not key:
        return "empty"
    # Sadece güvenli karakterleri tut, gerisini hash'le
    safe_chars = re.sub(r"[^a-zA-Z0-9_-]", "", key)
    if len(safe_chars) < len(key):
        # Güvenli olmayan karakterler varsa hash ekle
        hash_part = hashlib.md5(key.encode()).hexdigest()[:8]
        return f"{safe_chars[:20]}_{hash_part}"
    return safe_chars[:50]  # Max uzunluk sınırla


def ip_allowed(ip_address: str) -> bool:
    """IP adresinin güvenli olup olmadığını kontrol eder."""
    import ipaddress

    try:
        ip = ipaddress.ip_address(ip_address)
        # Localhost ve private IP'lere izin ver
        return ip.is_private or ip.is_loopback or str(ip) == "127.0.0.1"
    except:
        return False


def check_iyzico_signature(data: str, signature: str, secret_key: str) -> bool:
    """Iyzico webhook signature'ını doğrular."""
    import base64
    import hashlib
    import hmac

    try:
        expected = base64.b64encode(
            hmac.new(secret_key.encode(), data.encode(), hashlib.sha1).digest()
        ).decode()
        return hmac.compare_digest(expected, signature)
    except:
        return False


def verify_iyzico_signature(
    request_data: dict, signature: str, secret_key: str
) -> bool:
    """Iyzico imzasını doğrular."""
    import json

    data_string = json.dumps(request_data, separators=(",", ":"), sort_keys=True)
    return check_iyzico_signature(data_string, signature, secret_key)


def is_2fa_required(user) -> bool:
    """Kullanıcı için 2FA gerekli mi kontrol eder."""
    if not user:
        return False
    # Admin kullanıcılar için 2FA zorunlu
    return hasattr(user, "role") and user.role == "admin"


def is_user_2fa_ok(user) -> bool:
    """Kullanıcının 2FA durumunu kontrol eder."""
    if not user:
        return False
    # 2FA gerekli değilse OK
    if not is_2fa_required(user):
        return True
    # 2FA gerekli ise kullanıcının 2FA aktif olması gerekir
    return hasattr(user, "two_factor_enabled") and user.two_factor_enabled


def need_admin_approval(operation: str) -> bool:
    """Belirtilen operasyon için admin onayı gerekli mi kontrol eder."""
    high_risk_operations = ["batch_predict", "mass_delete", "data_export"]
    return operation in high_risk_operations


def has_admin_approval(user, operation: str) -> bool:
    """Kullanıcının belirtilen operasyon için admin onayı var mı kontrol eder."""
    if not user:
        return False
    # Admin kullanıcılar otomatik onaylı
    if hasattr(user, "role") and user.role == "admin":
        return True
    # Normal kullanıcılar için onay kontrol et
    return hasattr(user, "approved_operations") and operation in getattr(
        user, "approved_operations", []
    )
