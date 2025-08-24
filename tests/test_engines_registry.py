from backend.decision_engines import ENGINE_REGISTRY
from backend.decision_engines.base import DecisionRequest
import pandas as pd


def _mk_df(n=120):
    import numpy as np
    ts = pd.date_range("2024-01-01", periods=n, freq="H")
    close = pd.Series(100 + np.cumsum(np.random.normal(0, 0.3, size=n)))
    high = close + abs(np.random.normal(0, 0.2, size=n))
    low = close - abs(np.random.normal(0, 0.2, size=n))
    open_ = close.shift(1).fillna(close.iloc[0])
    volu = abs(np.random.normal(100, 10, size=n))
    return pd.DataFrame({"ts": ts, "open": open_, "high": high, "low": low, "close": close, "volume": volu})


def test_registry_and_basic_run():
    for eid in ("KM1", "KM2", "KM3", "KM4"):
        assert eid in ENGINE_REGISTRY
    eng = ENGINE_REGISTRY["KM1"]()
    df = _mk_df()
    req = DecisionRequest(engine_id="KM1", symbol="BTCUSDT", timeframe="1h", ohlcv=df, params={})
    res = eng.run(req)
    assert res.engine_id == "KM1"
    assert res.action in {"buy", "sell", "hold"}
    assert 0.0 <= res.confidence <= 1.0
