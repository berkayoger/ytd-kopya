#!/usr/bin/env python3
"""Basic security checks for environment configuration."""

import re
import sys
from pathlib import Path


def check_env_security() -> list[str]:
    """Validate essential secrets in the .env file."""
    issues: list[str] = []

    env_file = Path(".env")
    if not env_file.exists():
        issues.append("❌ .env file not found. Copy .env.example to .env")
        return issues

    env_content = env_file.read_text()

    jwt_secret_match = re.search(r"JWT_SECRET_KEY=(.+)", env_content)
    if not jwt_secret_match:
        issues.append("❌ JWT_SECRET_KEY not set in .env")
    else:
        jwt_secret = jwt_secret_match.group(1).strip()
        if len(jwt_secret) < 32:
            issues.append("❌ JWT_SECRET_KEY is too short (minimum 32 characters)")

    return issues


def main() -> int:
    """Run all security checks and print results."""
    print("🔐 YTD Crypto Application Security Check")
    print("=" * 50)

    issues = check_env_security()

    print("\n" + "=" * 50)
    if not issues:
        print("✅ All security checks passed!")
        return 0

    print(f"Found {len(issues)} security issues:")
    for issue in issues:
        print(f"  {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

