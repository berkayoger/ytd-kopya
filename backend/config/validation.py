"""Configuration validation and health checks."""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

import aioredis
import asyncpg
from pydantic.v1 import ValidationError

from .settings import Settings

logger = logging.getLogger(__name__)


class ConfigurationValidator:
    """Validates configuration settings and external dependencies."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.validation_results: Dict[str, Dict[str, Any]] = {}

    async def validate_all(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate all configuration sections and dependencies."""
        logger.info("Starting comprehensive configuration validation")

        validation_tasks = [
            ("configuration", self._validate_configuration()),
            ("database", self._validate_database_connection()),
            ("redis", self._validate_redis_connection()),
            ("external_apis", self._validate_external_apis()),
            ("security", self._validate_security_settings()),
        ]

        results: Dict[str, Dict[str, Any]] = {}
        overall_success = True

        for name, task in validation_tasks:
            try:
                success, details = await task
                results[name] = {"success": success, "details": details}
                if not success:
                    overall_success = False
            except Exception as exc:  # pragma: no cover - logging
                logger.error("Validation failed for %s: %s", name, exc)
                results[name] = {"success": False, "error": str(exc)}
                overall_success = False

        self.validation_results = results
        return overall_success, results

    async def _validate_configuration(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate configuration structure and required fields."""
        try:
            config_dict = self.settings.dict()
            required_checks = []

            if self.settings.is_production():
                if self.settings.security.secret_key.get_secret_value() == "dev-key":
                    required_checks.append("SECRET_KEY must be changed in production")

                if not self.settings.security.cors_origins:
                    required_checks.append(
                        "CORS origins must be configured in production"
                    )

                if self.settings.debug:
                    required_checks.append(
                        "Debug mode should be disabled in production"
                    )

            return len(required_checks) == 0, {
                "config_size": len(config_dict),
                "environment": self.settings.environment.value,
                "issues": required_checks,
            }

        except ValidationError as exc:  # pragma: no cover - defensive
            return False, {"validation_errors": exc.errors()}

    async def _validate_database_connection(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate database connectivity and configuration."""
        try:
            db_url = str(self.settings.database.url)
            parsed = urlparse(db_url)

            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip("/"),
                command_timeout=10,
            )

            version = await conn.fetchval("SELECT version()")
            await conn.close()

            return True, {
                "host": parsed.hostname,
                "port": parsed.port,
                "database": parsed.path.lstrip("/"),
                "version": (version[:50] + "...") if len(version) > 50 else version,
            }

        except Exception as exc:  # pragma: no cover - network/DB issues
            return False, {"error": str(exc)}

    async def _validate_redis_connection(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate Redis connectivity and configuration."""
        try:
            redis_url = str(self.settings.redis.url)

            redis = aioredis.from_url(
                redis_url,
                socket_timeout=self.settings.redis.socket_timeout,
                socket_connect_timeout=self.settings.redis.socket_connect_timeout,
            )

            await redis.ping()
            info = await redis.info()
            await redis.close()

            return True, {
                "version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }

        except Exception as exc:  # pragma: no cover - network
            return False, {"error": str(exc)}

    async def _validate_external_apis(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate external API configurations and connectivity."""
        results: Dict[str, Any] = {}
        overall_success = True

        if self.settings.apis.coingecko_api_key:
            try:
                import aiohttp

                headers = {
                    "x-cg-demo-api-key": self.settings.apis.coingecko_api_key.get_secret_value()
                }

                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(
                        total=self.settings.apis.coingecko_timeout
                    )
                ) as session:
                    async with session.get(
                        f"{self.settings.apis.coingecko_base_url}/ping",
                        headers=headers,
                    ) as response:
                        if response.status == 200:
                            results["coingecko"] = {
                                "success": True,
                                "status": response.status,
                            }
                        else:
                            results["coingecko"] = {
                                "success": False,
                                "status": response.status,
                            }
                            overall_success = False
            except Exception as exc:  # pragma: no cover - network
                results["coingecko"] = {"success": False, "error": str(exc)}
                overall_success = False
        else:
            results["coingecko"] = {
                "success": True,
                "note": "API key not configured, using free tier",
            }

        return overall_success, results

    async def _validate_security_settings(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate security configuration."""
        issues = []

        secret_key = self.settings.security.secret_key.get_secret_value()
        if len(secret_key) < 32:
            issues.append("Secret key is too short")

        if self.settings.security.jwt_access_token_expires > 86400:
            issues.append("JWT access token expiry is too long")

        if self.settings.security.password_hash_rounds < 10:
            issues.append("Password hash rounds too low")

        return len(issues) == 0, {
            "issues": issues,
            "jwt_access_expires": self.settings.security.jwt_access_token_expires,
            "password_rounds": self.settings.security.password_hash_rounds,
        }
