from __future__ import annotations
from flask import request, jsonify, current_app, g
from datetime import datetime, timezone
import pandas as pd
import numpy as np

try:
    import ccxt  # opsiyonel: candles yoksa otomatik çeker
except Exception:  # pragma: no cover
    ccxt = None

from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.middleware.plan_limits import enforce_plan_limit
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log
from backend.db.models import UsageLog
from backend import db

from . import draks_bp
from .engine_min import DRAKSEngine

# Basit konfig (gerekirse .yaml'dan okunabilir)
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


def _df_from_candles(candles: list[dict]) -> pd.DataFrame:
    """Gelen candle verisini DataFrame'e dönüştür."""
    idx = []
    rows = []
    for c in candles:
        ts = c.get("ts")
        if isinstance(ts, (int, float)):
            ts = datetime.fromtimestamp(
                float(ts) / (1000 if float(ts) > 1e12 else 1), tz=timezone.utc
            )
        else:
            ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        idx.append(ts)
        rows.append(
            {
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": float(c.get("volume", 0.0)),
            }
        )
    df = pd.DataFrame(rows, index=pd.to_datetime(idx, utc=True))
    return df.sort_index()


def _fetch_ohlcv_ccxt(
    symbol: str, timeframe: str = "1h", limit: int = 500
) -> pd.DataFrame:
    """CCXT ile borsadan OHLCV verisi çek."""
    if ccxt is None:
        raise RuntimeError("ccxt kurulu değil ve candles verilmedi")
    ex = ccxt.binance({"enableRateLimit": True})
    o = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(o, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("ts").sort_index()
    return df


@draks_bp.post("/decision/run")
@jwt_required_if_not_testing()
@enforce_plan_limit("draks_decision")
def decision_run():
    """Karar motorunu çalıştır."""
    if not feature_flag_enabled("draks"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403

    user = getattr(g, "user", None)
    ip_address = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")

    try:
        p = request.get_json(force=True, silent=True) or {}
        symbol = str(p.get("symbol", "BTC/USDT"))
        timeframe = str(p.get("timeframe", CFG["timeframe"]))
        limit = int(p.get("limit", 500))
        candles = p.get("candles")

        if candles:
            df = _df_from_candles(candles)
        else:
            df = _fetch_ohlcv_ccxt(symbol, timeframe=timeframe, limit=limit)

        if len(df) < 60:
            return jsonify({"error": "yetersiz veri"}), 400

        out = ENGINE.run(df, symbol.replace(" ", ""))
        out["as_of"] = datetime.utcnow().isoformat() + "Z"

        if user:
            db.session.add(UsageLog(user_id=user.id, action="draks_decision"))
            db.session.commit()
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="draks_decision",
                target="/api/draks/decision/run",
                description="DRAKS karar çalıştırıldı.",
                status="success",
                user_agent=user_agent,
            )

        return jsonify(out)
    except Exception as e:  # pragma: no cover
        current_app.logger.exception("draks decision error")
        if user:
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="draks_decision",
                target="/api/draks/decision/run",
                description=str(e),
                status="error",
                user_agent=user_agent,
            )
        return jsonify({"error": str(e)}), 500


@draks_bp.post("/copy/evaluate")
@jwt_required_if_not_testing()
@enforce_plan_limit("draks_copy")
def copy_evaluate():
    """Lider sinyalini değerlendir."""
    if not feature_flag_enabled("draks"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403

    user = getattr(g, "user", None)
    ip_address = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")

    try:
        p = request.get_json(force=True, silent=True) or {}
        side = str(p.get("side", "")).upper()
        symbol = str(p.get("symbol", "BTC/USDT"))
        timeframe = str(p.get("timeframe", CFG["timeframe"]))
        limit = int(p.get("limit", 500))
        candles = p.get("candles")

        df = _df_from_candles(candles) if candles else _fetch_ohlcv_ccxt(
            symbol, timeframe=timeframe, limit=limit
        )
        out = ENGINE.run(df, symbol.replace(" ", ""))

        score = float(out.get("score", 0.0))
        decision = str(out.get("decision", "HOLD")).upper()
        greenlight = (decision == "LONG" and side == "BUY") or (
            decision == "SHORT" and side == "SELL"
        )
        scale = max(0.0, min(1.0, abs(score) * 1.5)) if greenlight else 0.0
        size = p.get("size")
        scaled_size = (float(size) * scale) if (size is not None) else None

        if user:
            db.session.add(UsageLog(user_id=user.id, action="draks_copy"))
            db.session.commit()
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="draks_copy",
                target="/api/draks/copy/evaluate",
                description="DRAKS kopya sinyali değerlendirildi.",
                status="success",
                user_agent=user_agent,
            )

        return jsonify({"greenlight": greenlight, "scaled_size": scaled_size, "draks": out})
    except Exception as e:  # pragma: no cover
        current_app.logger.exception("draks eval error")
        if user:
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="draks_copy",
                target="/api/draks/copy/evaluate",
                description=str(e),
                status="error",
                user_agent=user_agent,
            )
        return jsonify({"error": str(e)}), 500
