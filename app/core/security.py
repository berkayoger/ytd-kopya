import os
import uuid
import secrets
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

import jwt  # PyJWT
from passlib.context import CryptContext
from argon2 import PasswordHasher
import pwnedpasswords
import boto3
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
# FastAPI yoksa bağımlılık yaratmamak için graceful fallback:
try:
    from fastapi import HTTPException, status
except Exception:  # pragma: no cover
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
    class status:
        HTTP_401_UNAUTHORIZED = 401
        HTTP_422_UNPROCESSABLE_ENTITY = 422
        HTTP_500_INTERNAL_SERVER_ERROR = 500
import redis
import pyotp
from email_validator import validate_email, EmailNotValidError

# ============================
# Argon2 Password Hashing
# ============================
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Enhanced password hasher with Argon2
ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

def get_password_hash(password: str) -> str:
    """Hash password using Argon2 (passlib wrapper for migration safety)."""
    # Use passlib context to allow algorithm agility.
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

# ============================
# Password Policy Validation
# ============================
class PasswordPolicy:
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    MAX_CONSECUTIVE_CHARS = 3
    COMMON_PATTERNS = [
        r'password', r'12345', r'qwerty', r'admin', r'letmein'
    ]
    
    @classmethod
    def validate(cls, password: str) -> Tuple[bool, str]:
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"
        
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            return False, "Password must contain at least one special character"
        
        # Check for consecutive characters
        for i in range(len(password) - cls.MAX_CONSECUTIVE_CHARS):
            if password[i:i+cls.MAX_CONSECUTIVE_CHARS+1] == password[i] * (cls.MAX_CONSECUTIVE_CHARS+1):
                return False, f"Password cannot contain more than {cls.MAX_CONSECUTIVE_CHARS} consecutive identical characters"
        
        # Check common patterns
        password_lower = password.lower()
        for pattern in cls.COMMON_PATTERNS:
            if re.search(pattern, password_lower):
                return False, "Password contains common patterns"
        
        # Check pwned passwords (do not block on outage)
        try:
            times_pwned = pwnedpasswords.check(password)
            if times_pwned > 0:
                return False, f"This password has been exposed in {times_pwned} breaches"
        except Exception:
            pass
        
        return True, "Password is valid"

# ============================
# Email Validation
# ============================
def validate_and_normalize_email(email: str) -> str:
    try:
        v = validate_email(email, check_deliverability=False)
        return v.normalized
    except EmailNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ============================
# Secret Management (AWS / Azure / Env)
# ============================
class SecretManager:
    """Manages secrets using AWS Secrets Manager or Azure Key Vault (or env fallback)."""
    
    def __init__(self, provider: str = "aws"):
        self.provider = provider
        self.jwt_secret_name = os.getenv("JWT_SECRET_NAME", "jwt-secret")
        if provider == "aws":
            self.secrets_client = boto3.client('secretsmanager')
        elif provider == "azure":
            credential = DefaultAzureCredential()
            self.secret_client = SecretClient(
                vault_url=os.getenv("AZURE_KEY_VAULT_URL", ""),
                credential=credential
            )
        else:
            # env provider
            pass
    
    def get_jwt_secret(self, version: Optional[int] = None) -> str:
        """Get JWT secret from secure storage with rotation support."""
        provider = self.provider
        if provider == "aws":
            try:
                # Prefer VersionId when specific version requested, else AWSCURRENT stage
                kwargs = {"SecretId": self.jwt_secret_name}
                if version:
                    kwargs["VersionId"] = str(version)
                else:
                    kwargs["VersionStage"] = "AWSCURRENT"
                response = self.secrets_client.get_secret_value(**kwargs)
                return response['SecretString']
            except Exception as e:
                raise HTTPException(500, f"Failed to retrieve JWT secret: {str(e)}")
        elif provider == "azure":
            try:
                if version:
                    secret = self.secret_client.get_secret(self.jwt_secret_name, version=str(version))
                else:
                    secret = self.secret_client.get_secret(self.jwt_secret_name)
                return secret.value
            except Exception as e:
                raise HTTPException(500, f"Failed to retrieve JWT secret: {str(e)}")
        else:
            secret = os.getenv("JWT_SECRET")
            if not secret:
                raise HTTPException(500, "JWT_SECRET not configured for provider=env")
            return secret
    
    def rotate_jwt_secret(self) -> str:
        """Rotate JWT secret (AWS only inline here)."""
        new_secret = secrets.token_urlsafe(64)
        if self.provider == "aws":
            self.secrets_client.update_secret(
                SecretId=self.jwt_secret_name,
                SecretString=new_secret
            )
        # Azure rotation should be handled via Key Vault set_secret
        elif self.provider == "azure":
            self.secret_client.set_secret(self.jwt_secret_name, new_secret)
        return new_secret


# ============================
# Redis (rate limit / lockout / token revocation)
# ============================
def _redis_client() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    ssl_enabled = os.getenv("REDIS_SSL_ENABLED", "false").lower() == "true"
    kwargs: Dict[str, Any] = {"decode_responses": True}
    if ssl_enabled:
        kwargs.update({"ssl": True})
    return redis.Redis.from_url(url, **kwargs)


# ============================
# Login lockout helpers
# ============================
def record_failed_login(identifier: str) -> int:
    r = _redis_client()
    max_attempts = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    lockout_min = int(os.getenv("LOGIN_LOCKOUT_DURATION_MINUTES", "15"))
    fail_key = f"auth:fail:{identifier}"
    cnt = r.incr(fail_key)
    # ensure expiry on every increment (sliding window-ish)
    r.expire(fail_key, lockout_min * 60)
    if cnt >= max_attempts:
        r.setex(f"auth:lock:{identifier}", lockout_min * 60, "1")
    return cnt

def is_locked(identifier: str) -> bool:
    r = _redis_client()
    return r.exists(f"auth:lock:{identifier}") == 1

def reset_login_failures(identifier: str) -> None:
    r = _redis_client()
    r.delete(f"auth:fail:{identifier}")
    r.delete(f"auth:lock:{identifier}")


# ============================
# CSRF token helpers (stateful HMAC)
# ============================
def generate_csrf_token(session_id: str) -> str:
    secret = os.getenv("CSRF_SECRET")
    if not secret:
        raise HTTPException(500, "CSRF_SECRET not configured")
    ts = int(datetime.now(timezone.utc).timestamp())
    nonce = secrets.token_hex(8)
    data = f"{session_id}.{nonce}.{ts}"
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{data}.{sig}"

def validate_csrf_token(token: str, session_id: str, max_age_seconds: int = 7200) -> bool:
    try:
        secret = os.getenv("CSRF_SECRET")
        parts = token.split(".")
        if len(parts) != 4:
            return False
        sid, nonce, ts_s, sig = parts
        if sid != session_id:
            return False
        data = f"{sid}.{nonce}.{ts_s}"
        expected = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return False
        ts = int(ts_s)
        now = int(datetime.now(timezone.utc).timestamp())
        return (now - ts) <= max_age_seconds
    except Exception:
        return False


# ============================
# TOTP (2FA)
# ============================
def generate_totp_secret() -> str:
    return pyotp.random_base32()

def get_totp_uri(email: str, secret: str) -> str:
    issuer = os.getenv("TOTP_ISSUER_NAME", "YTD-Crypto")
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

def verify_totp(code: str, secret: str, valid_window: int = 1) -> bool:
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=valid_window)
    except Exception:
        return False


# ============================
# JWT utilities (HS512 + rotation)
# ============================
ALGORITHM = "HS512"

def _secret_manager() -> SecretManager:
    provider = os.getenv("SECRET_PROVIDER", "aws")
    return SecretManager(provider=provider)

def _jwt_exp(minutes: int = 15) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)

def _jwt_days(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)

def _encode_jwt(claims: Dict[str, Any], version: int) -> str:
    secret = _secret_manager().get_jwt_secret(version=version)
    return jwt.encode(claims, secret, algorithm=ALGORITHM)

def _try_decode_with_versions(token: str, versions: Tuple[int, ...]) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    for v in versions:
        try:
            secret = _secret_manager().get_jwt_secret(version=v)
            payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
            # Ensure the embedded version matches the key tried
            if int(payload.get("ver", v)) == v:
                return payload
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

def _jti_blacklist_key(jti: str) -> str:
    return f"jwt:revoked:{jti}"

def revoke_token(jti: str, exp: int) -> None:
    """Blacklist a token JTI until its expiry (epoch seconds)."""
    ttl = max(0, exp - int(datetime.now(timezone.utc).timestamp()))
    _redis_client().setex(_jti_blacklist_key(jti), ttl, "1")

def is_token_revoked(jti: str) -> bool:
    return _redis_client().exists(_jti_blacklist_key(jti)) == 1

def create_access_token(subject: str, extra: Optional[Dict[str, Any]] = None, expires_minutes: Optional[int] = None) -> str:
    """Create a short-lived access token."""
    ver = int(os.getenv("JWT_KEY_VERSION", "1"))
    exp_m = int(expires_minutes or os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "15"))
    now = datetime.now(timezone.utc)
    claims: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(_jwt_exp(exp_m).timestamp()),
        "jti": uuid.uuid4().hex,
        "t": "access",
        "ver": ver,
    }
    if extra:
        claims.update(extra)
    return _encode_jwt(claims, version=ver)

def create_refresh_token(subject: str, extra: Optional[Dict[str, Any]] = None, expires_days: Optional[int] = None) -> str:
    ver = int(os.getenv("JWT_KEY_VERSION", "1"))
    exp_d = int(expires_days or os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    now = datetime.now(timezone.utc)
    claims: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(_jwt_days(exp_d).timestamp()),
        "jti": uuid.uuid4().hex,
        "t": "refresh",
        "ver": ver,
    }
    if extra:
        claims.update(extra)
    return _encode_jwt(claims, version=ver)

def generate_tokens(user_id: str) -> Tuple[str, str]:
    """Belirtilen kullanıcı için access ve refresh token üret."""
    access = create_access_token(subject=str(user_id))
    refresh = create_refresh_token(subject=str(user_id))
    return access, refresh

def decode_token(token: str, require_type: Optional[str] = None) -> Dict[str, Any]:
    """Decode token trying current and previous key versions (graceful rotation)."""
    cur = int(os.getenv("JWT_KEY_VERSION", "1"))
    prev = max(1, cur - 1)
    payload = _try_decode_with_versions(token, (cur, prev)) if cur > 1 else _try_decode_with_versions(token, (cur,))
    if require_type and payload.get("t") != require_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    if is_token_revoked(payload.get("jti", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    return payload

def rotate_refresh_token(refresh_token: str) -> str:
    payload = decode_token(refresh_token, require_type="refresh")
    # Revoke old token
    revoke_token(payload["jti"], payload["exp"])
    # Issue new token for the same subject
    return create_refresh_token(subject=payload["sub"])

# End of module
