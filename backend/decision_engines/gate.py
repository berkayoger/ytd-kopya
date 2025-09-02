from __future__ import annotations

import numpy as np
import pandas as pd


class RegimeResult(pd.Series):
    """Rejim tespiti çıktısı."""

    @property
    def _constructor(self):  # pragma: no cover - pandas için
        return RegimeResult


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def detect_regime(ohlcv: pd.DataFrame, atr_window: int = 14) -> RegimeResult:
    """Trend ve volatiliteye göre basit rejim tespiti."""

    df = ohlcv.copy().sort_values("ts")
    close = df["close"]
    ema50 = _ema(close, 50)
    ema200 = _ema(close, 200)
    trend = (ema50 - ema200) / (close + 1e-12)

    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = np.maximum.reduce([hl.values, hc.values, lc.values])
    atr = pd.Series(tr, index=df.index).rolling(atr_window).mean()
    vol_pct = (atr / (close + 1e-12)).fillna(0)

    t = float(trend.iloc[-1]) if len(trend) else 0.0
    v = float(vol_pct.iloc[-1]) if len(vol_pct) else 0.0

    up = t > 0.002
    down = t < -0.002
    low_vol = v < 0.02
    high_vol = v > 0.04

    if np.isnan(t) or np.isnan(v):
        label = "mixed"
    elif up and low_vol:
        label = "risk_on"
    elif down and high_vol:
        label = "risk_off"
    else:
        label = "mixed"

    return RegimeResult({"label": label, "trend_strength": t, "vol_pct": v})
