"""Minimal boto3 stub for tests.
Supports only secretsmanager client used in app.core.security."""
from __future__ import annotations
from typing import Any, Dict

class _SecretsClient:
    """Simplified Secrets Manager client."""
    def get_secret_value(self, *_, **kwargs) -> Dict[str, str]:
        secret_id = kwargs.get("SecretId", "test-secret")
        return {"SecretString": f"stub-{secret_id}"}

    def update_secret(self, **kwargs):
        return {"ARN": "stub", "Name": kwargs.get("SecretId", ""), "VersionId": "1"}

def client(service_name: str, *_, **__):
    if service_name == "secretsmanager":
        return _SecretsClient()
    raise NotImplementedError(f"boto3 stub only supports 'secretsmanager', got {service_name!r}")

__all__ = ["client"]
