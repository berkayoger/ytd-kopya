#!/usr/bin/env python3
import os
from app.core.security import SecretManager

def main():
    provider = os.getenv("SECRET_PROVIDER", "aws")
    sm = SecretManager(provider=provider)
    new_secret = sm.rotate_jwt_secret()
    print("Rotated JWT secret on provider:", provider)
    print("IMPORTANT: Bump JWT_KEY_VERSION in environment to complete rotation.")

if __name__ == "__main__":
    main()

