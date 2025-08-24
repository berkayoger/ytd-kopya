from __future__ import annotations

from typing import Any, Dict
import numpy as np
import pandas as pd

from ..registry import register_engine
from ..base import BaseDecisionEngine, DecisionRequest, DecisionResult
from ..utils import daily_volatility


def _atr(df: pd.DataFrame, w: int = 14) -> pd.Series:
    hl = (df["high"] - df["low"]).abs()
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(int(w)).mean()


@register_engine
class KM2ATRBreakout(BaseDecisionEngine):
    """
    KM2: ATR kanal kırılımı (savunmacı)
    close > MA + k*ATR => buy, close < MA - k*ATR => sell
    """
    engine_id = "KM2"

    def run(self, request: DecisionRequest) -> DecisionResult:
        df = request.ohlcv.copy().sort_values("ts")
        params: Dict[str, Any] = request.params or {}
        w = int(params.get("atr_window", 14))
        ma_w = int(params.get("ma_window", 20))
        k = float(params.get("atr_k", 1.0))
        horizon = float(params.get("horizon_days", 4.0))

        close = df["close"].astype(float)
        ma = close.rolling(ma_w).mean()
        atr = _atr(df, w)
        upper = ma + k * atr
        lower = ma - k * atr

        cu = float(close.iloc[-1]) if len(close) else np.nan
        up = float(upper.iloc[-1]) if len(upper) else np.nan
        lo = float(lower.iloc[-1]) if len(lower) else np.nan

        action = "hold"
        if np.isfinite(cu) and np.isfinite(up) and cu > up:
            action = "buy"
        elif np.isfinite(cu) and np.isfinite(lo) and cu < lo:
            action = "sell"

        dist = 0.0
        if action == "buy" and np.isfinite(up):
            dist = (cu - up) / (cu + 1e-12)
        if action == "sell" and np.isfinite(lo):
            dist = (lo - cu) / (cu + 1e-12)
        conf = float(np.clip(np.tanh(abs(dist) * 50), 0.0, 1.0))
        expected = float(np.clip(dist * 3, -0.06, 0.06))

        dvol = daily_volatility(df)
        sl = float(-1.2 * dvol)
        tp = float(+1.8 * dvol)

        return DecisionResult(
            engine_id=self.engine_id,
            action=action,
            confidence=conf,
            horizon_days=horizon,
            expected_return=expected,
            stop_loss=sl,
            take_profit=tp,
            metadata={"atr_window": w, "ma_window": ma_w, "atr_k": k},
        )
