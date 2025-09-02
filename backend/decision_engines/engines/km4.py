from __future__ import annotations

from ..base import BaseDecisionEngine, DecisionRequest, DecisionResult
from ..registry import register_engine
from ..utils import daily_volatility


@register_engine
class KM4BaselineHold(BaseDecisionEngine):
    """
    KM4: Baseline/Hold – her zaman temkinli 'hold' önerir.
    Konsensüste dengeleyici rol oynar.
    """

    engine_id = "KM4"

    def run(self, request: DecisionRequest) -> DecisionResult:
        df = request.ohlcv
        dvol = daily_volatility(df)
        horizon = float((request.params or {}).get("horizon_days", 2.0))
        return DecisionResult(
            engine_id=self.engine_id,
            action="hold",
            confidence=0.25,
            horizon_days=horizon,
            expected_return=0.0,
            stop_loss=float(-1.0 * dvol),
            take_profit=float(+1.0 * dvol),
            metadata={},
        )
