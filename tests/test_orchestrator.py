import pandas as pd

from backend.decision_engines.base import DecisionResult
from backend.decision_engines.orchestrator import (OrchestratorConfig,
                                                   build_consensus_result)


def _mk_df(n=240):
    import numpy as np

    ts = pd.date_range("2024-01-01", periods=n, freq="H")
    close = pd.Series(100 + np.cumsum(np.random.normal(0, 0.5, size=n)))
    high = close + abs(np.random.normal(0, 0.3, size=n))
    low = close - abs(np.random.normal(0, 0.3, size=n))
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


def test_consensus_basic():
    df = _mk_df()
    engines = {
        "E1": DecisionResult(
            engine_id="E1",
            action="buy",
            confidence=0.6,
            horizon_days=5,
            expected_return=0.03,
            stop_loss=-0.02,
            take_profit=0.06,
            metadata={},
        ),
        "E2": DecisionResult(
            engine_id="E2",
            action="hold",
            confidence=0.4,
            horizon_days=3,
            expected_return=0.0,
            stop_loss=-0.03,
            take_profit=0.04,
            metadata={},
        ),
    }
    out = build_consensus_result(
        "BTCUSDT", "1h", df, engines, OrchestratorConfig(), 100000
    )
    assert out["symbol"] == "BTCUSDT"
    assert "consensus" in out and "label" in out["consensus"]
    assert out["consensus"]["position_value"] >= 0.0
