"""Secret management for different deployment environments."""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    """Abstract base class for secret providers."""

    @abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key."""

    @abstractmethod
    async def get_secrets(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Retrieve multiple secrets."""


class EnvironmentSecretProvider(SecretProvider):
    """Secret provider that reads from environment variables."""

    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    async def get_secret(self, key: str) -> Optional[str]:
        """Get secret from environment variable."""
        return os.getenv(f"{self.prefix}{key}")

    async def get_secrets(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets from environment variables."""
        return {key: os.getenv(f"{self.prefix}{key}") for key in keys}


class FileSecretProvider(SecretProvider):
    """Secret provider that reads secrets from a JSON file."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._secrets: Dict[str, Any] = {}
        if file_path.exists():
            try:
                self._secrets = json.loads(file_path.read_text())
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                logger.error("Failed to parse secrets file %s: %s", file_path, exc)

    async def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from the JSON file."""
        value = self._secrets.get(key)
        return str(value) if value is not None else None

    async def get_secrets(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Retrieve multiple secrets from the JSON file."""
        return {key: await self.get_secret(key) for key in keys}


class SecretManager:
    """High-level helper for loading secrets using a provider."""

    def __init__(self, provider: SecretProvider):
        self.provider = provider

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret with a default fallback."""
        value = await self.provider.get_secret(key)
        return value if value is not None else default

    async def load_into_env(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Load selected secrets into environment variables."""
        secrets = await self.provider.get_secrets(keys)
        for name, value in secrets.items():
            if value is not None:
                os.environ[name] = value
        return secrets
