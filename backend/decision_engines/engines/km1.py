from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from ..base import BaseDecisionEngine, DecisionRequest, DecisionResult
from ..registry import register_engine
from ..utils import daily_volatility


def _ema(x: pd.Series, span: int) -> pd.Series:
    return x.ewm(span=span, adjust=False).mean()


@register_engine
class KM1MomentumEMACrossover(BaseDecisionEngine):
    """
    KM1: Momentum / EMA crossover (varsayılan: 12/48)
    Trend gücü = (ema_fast - ema_slow)/close
    """

    engine_id = "KM1"

    def run(self, request: DecisionRequest) -> DecisionResult:
        df = request.ohlcv.copy().sort_values("ts")
        params: Dict[str, Any] = request.params or {}
        fast = int(params.get("ema_fast", 12))
        slow = int(params.get("ema_slow", 48))
        horizon = float(params.get("horizon_days", 5.0))
        atr_mult = float(params.get("atr_mult", 1.5))

        close = df["close"].astype(float)
        ema_fast = _ema(close, fast)
        ema_slow = _ema(close, slow)
        trend = (ema_fast - ema_slow) / (close + 1e-12)
        t = float(trend.iloc[-1]) if len(trend) else 0.0

        cross_up = (
            bool(
                (ema_fast.iloc[-2] <= ema_slow.iloc[-2])
                and (ema_fast.iloc[-1] > ema_slow.iloc[-1])
            )
            if len(df) > 2
            else False
        )
        cross_dn = (
            bool(
                (ema_fast.iloc[-2] >= ema_slow.iloc[-2])
                and (ema_fast.iloc[-1] < ema_slow.iloc[-1])
            )
            if len(df) > 2
            else False
        )

        action = "hold"
        if t > 0:
            action = "buy"
        if t < 0:
            action = "sell"
        if cross_up:
            action = "buy"
        if cross_dn:
            action = "sell"

        conf = float(np.tanh(abs(t) * 100))
        expected = float(np.clip(t * 5, -0.08, 0.08))
        dvol = daily_volatility(df)
        sl = float(-atr_mult * dvol)
        tp = float(+2.0 * atr_mult * dvol)

        return DecisionResult(
            engine_id=self.engine_id,
            action=action,
            confidence=conf,
            horizon_days=horizon,
            expected_return=expected,
            stop_loss=sl,
            take_profit=tp,
            metadata={
                "trend": t,
                "cross_up": cross_up,
                "cross_dn": cross_dn,
                "ema_fast": fast,
                "ema_slow": slow,
            },
        )
