import pandas as pd

from backend.decision_engines.gate import detect_regime


def _mk_df(n=300, start=100.0, drift=0.0005, vol=0.01):
    import numpy as np

    ts = pd.date_range("2024-01-01", periods=n, freq="H")
    ret = np.random.normal(drift, vol, size=n)
    close = start * (1 + pd.Series(ret)).cumprod()
    high = close * (1 + abs(np.random.normal(0, 0.002, size=n)))
    low = close * (1 - abs(np.random.normal(0, 0.002, size=n)))
    open_ = close.shift(1).fillna(close.iloc[0])
    volu = abs(np.random.normal(100, 10, size=n))
    return pd.DataFrame(
        {
            "ts": ts,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volu,
        }
    )


def test_detect_regime_outputs():
    df = _mk_df()
    r = detect_regime(df)
    assert r["label"] in {"risk_on", "risk_off", "mixed"}
    assert "trend_strength" in r and "vol_pct" in r
