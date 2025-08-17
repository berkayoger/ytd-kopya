from __future__ import annotations
import os, json, time
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from redis import Redis
from loguru import logger

try:
    import ccxt
except Exception:
    ccxt = None
try:
    import yfinance as yf
except Exception:
    yf = None

from backend import celery_app
from backend.observability.metrics import (
    inc_batch_item,
    inc_cache_hit,
    inc_cache_miss,
    observe_batch_duration,
)
from backend.utils.security import safe_cache_key

from backend.draks.engine_min import DRAKSEngine
from flask_socketio import SocketIO

CFG = {
    "timeframe": "1h",
    "cost_bps": 6,
    "bandit": {"alpha": 0.5, "ridge": 1e-3},
    "risk": {
        "target_vol": 0.02,
        "max_risk_pct": 0.02,
        "kelly_clip": 0.4,
        "atr_stop": [1.0, 1.8],
        "atr_tp": [1.5, 2.5],
    },
    "thresholds": {"target_error_rate": 0.10, "buy": 0.02, "sell": -0.02},
    "modules": [
        {"name": "trend", "params": {}},
        {"name": "momentum", "params": {}},
        {"name": "meanrev", "params": {}},
    ],
}
ENGINE = DRAKSEngine(CFG)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OHLCV_TTL = int(os.getenv("OHLCV_CACHE_TTL", "600"))
DECISION_TTL = int(os.getenv("DECISION_CACHE_TTL", "600"))
BATCH_MAX_CANDLES = int(os.getenv("BATCH_MAX_CANDLES", "500"))
BATCH_JOB_TIMEOUT = int(os.getenv("BATCH_JOB_TIMEOUT", "300"))


def _r() -> Redis:
    return Redis.from_url(REDIS_URL, decode_responses=True)

# Socket.IO publisher (Redis MQ üzerinden)
SIO = SocketIO(message_queue=REDIS_URL)


def _df_from_ohlcv_rows(rows):
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("ts").sort_index()


def _fetch_ccxt(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    if ccxt is None:
        raise RuntimeError("ccxt not installed")
    ex = ccxt.binance({"enableRateLimit": True})
    data = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    return _df_from_ohlcv_rows(data)


def _fetch_yf(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance not installed")
    tf_map = {
        "1m": "1m",
        "2m": "2m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "60m": "60m",
        "1h": "60m",
        "90m": "90m",
        "1d": "1d",
        "1wk": "1wk",
        "1mo": "1mo",
        "1w": "1wk",
    }
    interval = tf_map.get(timeframe, "1h")
    period = "60d" if any(x in interval for x in ["d", "wk", "mo"]) else "7d"
    hist = yf.Ticker(symbol).history(interval=interval, period=period)
    if hist is None or hist.empty:
        raise RuntimeError("yfinance empty")
    hist = hist[-limit:]
    df = pd.DataFrame(
        {
            "open": hist["Open"].astype(float),
            "high": hist["High"].astype(float),
            "low": hist["Low"].astype(float),
            "close": hist["Close"].astype(float),
            "volume": hist["Volume"].astype(float),
        }
    )
    df.index = pd.to_datetime(hist.index, utc=True)
    return df.sort_index()


def _get_ohlcv_cached(asset: str, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    r = _r()
    safe = safe_cache_key("draks:ohlcv", asset, symbol, timeframe, str(limit))
    val = r.get(safe)
    if val:
        inc_cache_hit(asset)
        try:
            arr = json.loads(val)
            return _df_from_ohlcv_rows(arr)
        except Exception:
            r.delete(safe)
    inc_cache_miss(asset)
    if asset == "crypto":
        df = _fetch_ccxt(symbol, timeframe, min(limit, BATCH_MAX_CANDLES))
    else:
        df = _fetch_yf(symbol, timeframe, min(limit, BATCH_MAX_CANDLES))
    rows = [
        [int(ts.value / 10**6), float(o), float(h), float(l), float(c), float(v)]
        for ts, (o, h, l, c, v) in zip(
            df.index,
            df[["open", "high", "low", "close", "volume"]].itertuples(index=False, name=None),
        )
    ]
    r.setex(safe, OHLCV_TTL, json.dumps(rows))
    return df


def _result_key(job_id: str, symbol: str) -> str:
    return safe_cache_key(f"draks:batch:{job_id}:result", symbol)


def _meta_key(job_id: str) -> str:
    return f"draks:batch:{job_id}:meta"


def _set_key(job_id: str, name: str) -> str:
    return f"draks:batch:{job_id}:{name}"


def _try_finalize(job_id: str):
    r = _r()
    try:
        meta_raw = r.get(_meta_key(job_id))
        if not meta_raw:
            return
        meta = json.loads(meta_raw)
        total = int(meta.get("total", 0))
        done = r.scard(_set_key(job_id, "done"))
        failed = r.scard(_set_key(job_id, "failed"))
        if done + failed >= total and total > 0:
            started_at = float(meta.get("started_at", time.time()))
            observe_batch_duration(max(0.0, time.time() - started_at))
            r.hset("draks:batch:index", job_id, int(time.time()))
            # tamamlandı bildirimi
            try:
                SIO.emit("progress", {"job_id": job_id, "done": int(done), "failed": int(failed), "total": int(total), "finished": True},
                         namespace="/batch", to=f"job:{job_id}")
            except Exception:
                pass
    except Exception:
        logger.exception("finalize failed")


@celery_app.task(bind=True, name="draks.process_symbol", time_limit=BATCH_JOB_TIMEOUT)
def process_symbol(self, *, asset: str, symbol: str, timeframe: str, limit: int, job_id: str):
    r = _r()
    try:
        df = _get_ohlcv_cached(asset, symbol, timeframe, limit)
        if len(df) < 60:
            raise RuntimeError("insufficient_data")
        out = ENGINE.run(df, symbol.replace(" ", ""))
        out["as_of"] = datetime.utcnow().isoformat() + "Z"
        r.setex(_result_key(job_id, symbol), DECISION_TTL, json.dumps({"status": "ok", "draks": out}))
        r.sadd(_set_key(job_id, "done"), symbol)
        inc_batch_item(asset, "ok")
    except Exception:
        r.setex(
            _result_key(job_id, symbol),
            DECISION_TTL,
            json.dumps({"status": "error", "error": "internal_error"}),
        )
        r.sadd(_set_key(job_id, "failed"), symbol)
        inc_batch_item(asset, "error")
        logger.exception(f"batch item failed: {asset} {symbol} {timeframe} {limit}")
    finally:
        r.srem(_set_key(job_id, "pending"), symbol)
        # anlık ilerleme bildir
        try:
            total = int(json.loads(r.get(_meta_key(job_id)) or "{}").get("total", 0))
            done = r.scard(_set_key(job_id, "done"))
            failed = r.scard(_set_key(job_id, "failed"))
            SIO.emit("progress", {"job_id": job_id, "done": int(done), "failed": int(failed), "total": int(total)},
                     namespace="/batch", to=f"job:{job_id}")
        except Exception:
            pass
        _try_finalize(job_id)


def init_job(job_id: str, user_id: str, symbols: list[str]):
    r = _r()
    meta = {"user_id": user_id, "total": len(symbols), "started_at": time.time()}
    r.setex(_meta_key(job_id), BATCH_JOB_TIMEOUT * 10, json.dumps(meta))
    if symbols:
        r.sadd(_set_key(job_id, "pending"), *symbols)
    r.delete(_set_key(job_id, "done"))
    r.delete(_set_key(job_id, "failed"))


def job_status(job_id: str) -> dict:
    r = _r()
    meta_raw = r.get(_meta_key(job_id))
    if not meta_raw:
        return {"error": "not_found"}
    meta = json.loads(meta_raw)
    pending = r.smembers(_set_key(job_id, "pending"))
    done = r.smembers(_set_key(job_id, "done"))
    failed = r.smembers(_set_key(job_id, "failed"))
    return {
        "total": int(meta.get("total", 0)),
        "pending": sorted(list(pending)),
        "done": sorted(list(done)),
        "failed": sorted(list(failed)),
        "started_at": meta.get("started_at"),
        "user_id": meta.get("user_id"),
    }


def job_results(
    job_id: str,
    *,
    decision: Optional[str] = None,
    status: Optional[str] = None,
    symbol_like: Optional[str] = None,
) -> list[dict]:
    r = _r()
    s_done = r.smembers(_set_key(job_id, "done"))
    s_failed = r.smembers(_set_key(job_id, "failed"))
    out: list[dict] = []
    for sym in s_failed:
        body = {"symbol": sym, "status": "error"}
        if status and status != "error":
            continue
        if symbol_like and symbol_like.upper() not in sym:
            continue
        out.append(body)
    for sym in s_done:
        raw = r.get(_result_key(job_id, sym))
        if not raw:
            continue
        try:
            body = json.loads(raw)
            if body.get("status") != "ok":
                continue
            d = body.get("draks", {})
            dec = str(d.get("decision", "HOLD")).upper()
            if decision and decision != dec:
                continue
            if status and status != "ok":
                continue
            if symbol_like and symbol_like.upper() not in sym:
                continue
            out.append(
                {
                    "symbol": sym,
                    "status": "ok",
                    "decision": dec,
                    "score": float(d.get("score", 0.0)),
                    "draks": d,
                }
            )
        except Exception:
            continue
    return out
