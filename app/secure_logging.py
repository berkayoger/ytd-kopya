"""Güvenli loglama yardımcıları"""

import json
import logging
import re
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List


class SensitiveDataFilter(logging.Filter):
    """Log mesajlarından hassas verileri çıkaran filtre"""

    def __init__(self) -> None:
        super().__init__()
        self.sensitive_patterns = [
            # API anahtarları ve token'lar
            r'(?i)(api[_-]?key|token|secret|password|passwd)\s*[:=]\s*["\']?([a-zA-Z0-9+/=_-]{8,})["\']?',
            # E-posta adresleri
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            # Kredi kartı numaraları
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            # JWT token'ları
            r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",
            # Kullanıcı adı ve parolalı veritabanı URL'leri
            r"(?i)(postgresql|mysql|mongodb)://[^:]+:[^@]+@[^/]+",
        ]
        self.compiled_patterns = [re.compile(p) for p in self.sensitive_patterns]

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        """Log kaydındaki mesaj ve argümanları temizle"""
        if hasattr(record, "msg"):
            record.msg = self._sanitize_message(str(record.msg))
        if hasattr(record, "args") and record.args:
            record.args = tuple(
                self._sanitize_message(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True

    def _sanitize_message(self, message: str) -> str:
        """Mesaj içindeki hassas verileri maskeler"""
        sanitized = message
        for pattern in self.compiled_patterns:
            sanitized = pattern.sub(self._replacement, sanitized)
        return sanitized

    @staticmethod
    def _replacement(match: re.Match) -> str:
        """Regex eşleşmesini güvenli hale getir"""
        if match.lastindex:
            return f"{match.group(1)}=***REDACTED***"
        return "***REDACTED***"


class SecureLogger:
    """Hassas veri filtresi ile loglama kurulumunu sağlar"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Logger nesnesini güvenli şekilde yapılandır"""
        self.logger.handlers.clear()
        level = getattr(logging, self.config.get("LOG_LEVEL", "INFO").upper())
        self.logger.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SensitiveDataFilter())
        self.logger.addHandler(console_handler)

        if self.config.get("LOG_FILE"):
            file_handler = RotatingFileHandler(
                self.config["LOG_FILE"],
                maxBytes=self.config.get("LOG_MAX_SIZE", 10 * 1024 * 1024),
                backupCount=self.config.get("LOG_BACKUP_COUNT", 5),
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(SensitiveDataFilter())
            self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """Hazır logger nesnesini döndür"""
        return self.logger

    @staticmethod
    def safe_log_dict(
        data: Dict[str, Any], sensitive_keys: List[str] | None = None
    ) -> Dict[str, Any]:
        """Sözlük içindeki hassas değerleri maskele"""
        if sensitive_keys is None:
            sensitive_keys = [
                "password",
                "secret",
                "token",
                "key",
                "api_key",
                "authorization",
                "credential",
                "private",
            ]
        safe_dict: Dict[str, Any] = {}
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    safe_dict[key] = f"***{value[-4:]}"
                else:
                    safe_dict[key] = "***REDACTED***"
            else:
                safe_dict[key] = value
        return safe_dict
