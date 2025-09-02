from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from flask import current_app, g, jsonify, request

try:
    import ccxt  # opsiyonel: candles yoksa otomatik çeker
except Exception:  # pragma: no cover
    ccxt = None

from backend import limiter
from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.db import db
from backend.db.models import DraksDecision, DraksSignalRun, UsageLog
from backend.middleware.plan_limits import enforce_plan_limit
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log

from . import draks_bp
from .engine_min import DRAKSEngine

# Gelişmiş mantık (opsiyonel)
try:  # pragma: no cover - unit testler bu modüle ihtiyaç duymaz
    from .advanced import advanced_decision_logic
except Exception:  # pragma: no cover
    advanced_decision_logic = None  # type: ignore

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


@draks_bp.get("/health")
def draks_health():
    """
    DRAKS health endpoint.
    - Özelliğin açık/kapalı bilgisini ve motorun hazır olduğunu döndürür.
    - Kimlik doğrulaması gerektirmez; sistem izleme için hafif bir sağlık kontrolü.
    """
    try:
        enabled = feature_flag_enabled("draks")
        use_advanced = feature_flag_enabled("draks_advanced") or os.getenv(
            "DRAKS_ADVANCED", "0"
        ).lower() in {"1", "true", "yes"}
        live_mode = os.getenv("DRAKS_LIVE_MODE", "0").lower() in {"1", "true", "yes"}
        # Minimal kontrol: engine objesi çalışıyor mu?
        ok = ENGINE is not None
        return (
            jsonify(
                {
                    "status": "ok" if ok else "degraded",
                    "enabled": enabled,
                    "advanced": bool(use_advanced),
                    "live_mode": bool(live_mode),
                    "timeframe": CFG.get("timeframe", "1h"),
                }
            ),
            200,
        )
    except Exception as e:  # pragma: no cover
        current_app.logger.exception("draks health error")
        return jsonify({"status": "error", "error": str(e)}), 500


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
@limiter.limit("60/minute")
def decision_run():
    """Karar motorunu çalıştır."""
    # Hem eski hem yeni isimlendirmeyi destekle: draks / draks_enabled
    if not (feature_flag_enabled("draks") and feature_flag_enabled("draks_enabled")):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403

    user = getattr(g, "user", None)
    ip_address = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")
    # çalışma anı toggles (env veya flag)
    use_advanced = feature_flag_enabled("draks_advanced") or os.getenv(
        "DRAKS_ADVANCED", "0"
    ).lower() in {"1", "true", "yes"}
    live_mode = os.getenv("DRAKS_LIVE_MODE", "0").lower() in {"1", "true", "yes"}
    # not: live_mode sadece risk kapaklarını sıkılaştırır, plan/flag kontrollerini etkilemez

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

        # Opsiyonel kalıcı kaydetme
        try:
            db.session.add(
                DraksSignalRun(
                    symbol=out["symbol"],
                    timeframe=out.get("timeframe", "1h"),
                    regime_probs=json.dumps(out.get("regime_probs", {})),
                    weights=json.dumps(out.get("weights", {})),
                    score=float(out.get("score", 0.0)),
                    decision=str(out.get("decision", "HOLD")),
                )
            )
            db.session.add(
                DraksDecision(
                    symbol=out["symbol"],
                    decision=str(out.get("decision", "HOLD")),
                    position_pct=float(out.get("position_pct", 0.0)),
                    stop=float(out.get("stop", 0.0)),
                    take_profit=float(out.get("take_profit", 0.0)),
                    reasons=json.dumps(out.get("reasons", [])),
                    raw_response=json.dumps(out),
                )
            )
            db.session.commit()
        except Exception:  # pragma: no cover
            current_app.logger.exception("draks persistence error")
            db.session.rollback()

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
@limiter.limit("60/minute")
def copy_evaluate():
    """Lider sinyalini değerlendir."""
    if not feature_flag_enabled("draks"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403

    user = getattr(g, "user", None)
    ip_address = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")

    # çalışma anı toggles (env veya bayrak)
    use_advanced = feature_flag_enabled("draks_advanced") or os.getenv(
        "DRAKS_ADVANCED", "0"
    ).lower() in {"1", "true", "yes"}
    live_mode = os.getenv("DRAKS_LIVE_MODE", "0").lower() in {"1", "true", "yes"}
    # not: live_mode sadece risk kapaklarını kısar, plan/flag kontrollerini etkilemez

    try:
        p = request.get_json(force=True, silent=True) or {}
        # --- zorunlular / doğrulama ---
        symbol = str(p.get("symbol", "BTC/USDT"))
        side = str(p.get("side", "")).upper()
        if side not in {"BUY", "SELL"}:
            return jsonify({"error": "Geçersiz side. BUY veya SELL olmalı."}), 400
        # opsiyoneller
        timeframe = str(p.get("timeframe", CFG["timeframe"]))
        try:
            limit = int(p.get("limit", 500))
        except Exception:
            return jsonify({"error": "limit sayısal olmalı"}), 400
        candles = p.get("candles")
        size = p.get("size")
        if size is not None:
            try:
                size = float(size)
                if size < 0:
                    return jsonify({"error": "size negatif olamaz"}), 400
            except Exception:
                return jsonify({"error": "size sayısal olmalı"}), 400

        # veri kaynağı: candles → ccxt fallback
        if candles:
            df = _df_from_candles(candles)
        else:
            # ccxt kurulu değilse net bir mesaj döndür
            if ccxt is None:
                return jsonify({"error": "candles sağlanmalı veya ccxt kurulmalı"}), 400
            df = _fetch_ohlcv_ccxt(symbol, timeframe=timeframe, limit=limit)

        if len(df) < 60:
            return jsonify({"error": "yetersiz veri"}), 400
        out = ENGINE.run(df, symbol.replace(" ", ""))

        score = float(out.get("score", 0.0))
        decision = str(out.get("decision", "HOLD")).upper()
        greenlight = (decision == "LONG" and side == "BUY") or (
            decision == "SHORT" and side == "SELL"
        )
        # temel ölçek faktörü
        base_scale = max(0.0, min(1.0, abs(score) * 1.5)) if greenlight else 0.0

        # Gelişmiş mantık (rejim & canlı kapakları) flag/env ile devreye girer
        final_green = greenlight
        final_scale = base_scale
        if use_advanced and advanced_decision_logic:
            try:
                final_green, final_scale = advanced_decision_logic(
                    draks_out=out,
                    side=side,
                    base_scale=base_scale,
                    live_mode=live_mode,
                )
            except Exception:  # pragma: no cover
                final_green, final_scale = greenlight, base_scale
        scaled_size = (size * final_scale) if (size is not None) else None

        if user:
            db.session.add(UsageLog(user_id=user.id, action="draks_copy"))
            db.session.commit()
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="draks_copy",
                target="/api/draks/copy/evaluate",
                description=f"DRAKS kopya sinyali değerlendirildi (adv={use_advanced}, live={live_mode}).",
                status="success",
                user_agent=user_agent,
            )

        return jsonify(
            {
                "greenlight": final_green,
                "scale_factor": final_scale,
                "scaled_size": scaled_size,
                "draks": out,
            }
        )
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
