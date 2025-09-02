from __future__ import annotations

import numpy as np
import pandas as pd


def zscore(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Basit z-skoru hesaplama, boş diziler için güvenli."""

    if x is None or len(x) == 0:
        return np.array([], dtype=float)
    m = np.nanmean(x)
    s = np.nanstd(x)
    if s < eps:
        return np.zeros_like(x, dtype=float)
    return (x - m) / (s + eps)


def winsorize01(x: np.ndarray, p: float = 0.01) -> np.ndarray:
    """0-1 aralığında Winsorize uygular."""

    if x is None or len(x) == 0:
        return np.array([], dtype=float)
    lo, hi = np.nanquantile(x, p), np.nanquantile(x, 1 - p)
    return np.clip(x, lo, hi)


def action_to_score(action: str) -> float:
    """Al/sat/ara kararlarını -1..1 skoruna çevir."""

    a = (action or "").strip().lower()
    if a in ("buy", "strong_buy", "strongbuy"):
        return 1.0
    if a in ("sell", "strong_sell", "strongsell"):
        return -1.0
    return 0.0


def daily_volatility(ohlcv: pd.DataFrame) -> float:
    """OHLCV tablosundan günlük volatilite tahmini."""

    if "ts" in ohlcv.columns:
        ohlcv = ohlcv.sort_values("ts")
    r = ohlcv["close"].pct_change().dropna()
    return float(r.std() if len(r) > 5 else 0.0)
