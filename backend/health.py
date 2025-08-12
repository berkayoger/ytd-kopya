import time
from flask import Blueprint, jsonify
import os

bp = Blueprint("health", __name__)
_start = time.time()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/ytdcrypto")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def _db_ok():
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=2)
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def _redis_ok():
    try:
        import redis
        r = redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        return (r.ping(), None)
    except Exception as e:
        return False, str(e)

def _alembic_status():
    """
    Alembic durumu opsiyonel olarak raporlanır.
    - alembic.ini/Script Location yoksa veya erişilemiyorsa hata sayılmaz (bilgi amaçlı döner).
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        cfg_path = os.getenv("ALEMBIC_INI", "alembic.ini")
        script_location = os.getenv("ALEMBIC_SCRIPT_LOCATION")  # yoksa ini'den okunur
        cfg = Config(cfg_path)
        if script_location:
            cfg.set_main_option("script_location", script_location)
        script = ScriptDirectory.from_config(cfg)
        head_rev = script.get_current_head()
        # DB'deki mevcut sürüm
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=2)
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version_num FROM alembic_version LIMIT 1;")
                row = cur.fetchone()
        conn.close()
        db_rev = row[0] if row else None
        return {
            "head": head_rev,
            "db_rev": db_rev,
            "up_to_date": (db_rev == head_rev) if (db_rev and head_rev) else None
        }
    except Exception as e:
        return {"error": str(e)}

@bp.get("/healthz")
def healthz():
    return jsonify(status="ok", uptime_seconds=round(time.time() - _start, 3)), 200

@bp.get("/readiness")
def readiness():
    db_ok, db_err = _db_ok()
    redis_ok, redis_err = _redis_ok()
    alembic = _alembic_status()
    ready = db_ok and redis_ok
    payload = {
        "db_ok": db_ok,
        "redis_ok": redis_ok,
        "alembic": alembic,
    }
    if not db_ok:
        payload["db_error"] = db_err
    if not redis_ok:
        payload["redis_error"] = redis_err
    return jsonify(payload), (200 if ready else 503)
