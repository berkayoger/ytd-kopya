import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
JWT_ALG = "HS256"
ACCESS_TTL = int(os.getenv("ACCESS_TTL_SEC", "900"))  # 15 dk
REFRESH_TTL = int(os.getenv("REFRESH_TTL_SEC", "2592000"))  # 30 gün


def _fp_hash(fp: str) -> str:
    return hashlib.sha256(fp.encode("utf-8")).hexdigest()


def issue_tokens(user_id: int, fingerprint: str):
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ACCESS_TTL)).timestamp()),
    }
    jti = str(uuid.uuid4())
    refresh_payload = {
        "sub": user_id,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=REFRESH_TTL)).timestamp()),
    }
    access = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALG)
    refresh = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALG)
    return access, refresh, jti, _fp_hash(fingerprint)
