from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from ..base import BaseDecisionEngine, DecisionRequest, DecisionResult
from ..registry import register_engine
from ..utils import daily_volatility


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


@register_engine
class KM3RSIMeanReversion(BaseDecisionEngine):
    """
    KM3: RSI Mean-Reversion
    RSI<30 => buy, RSI>70 => sell, aksi hold
    """

    engine_id = "KM3"

    def run(self, request: DecisionRequest) -> DecisionResult:
        df = request.ohlcv.copy().sort_values("ts")
        params: Dict[str, Any] = request.params or {}
        period = int(params.get("rsi_period", 14))
        low_th = float(params.get("rsi_low", 30.0))
        high_th = float(params.get("rsi_high", 70.0))
        horizon = float(params.get("horizon_days", 3.0))

        close = df["close"].astype(float)
        rsi = _rsi(close, period)
        val = float(rsi.iloc[-1]) if len(rsi) else 50.0

        action = "hold"
        if val < low_th:
            action = "buy"
        elif val > high_th:
            action = "sell"

        dist = 0.0
        if action == "buy":
            dist = (low_th - val) / 100.0
        elif action == "sell":
            dist = (val - high_th) / 100.0
        conf = float(np.clip(np.tanh(abs(dist) * 6), 0.0, 1.0))
        expected = float(np.clip(dist * 4, -0.05, 0.05))

        dvol = daily_volatility(df)
        sl = float(-1.4 * dvol)
        tp = float(+1.6 * dvol)

        return DecisionResult(
            engine_id=self.engine_id,
            action=action,
            confidence=conf,
            horizon_days=horizon,
            expected_return=expected,
            stop_loss=sl,
            take_profit=tp,
            metadata={"rsi": val, "rsi_period": period},
        )
