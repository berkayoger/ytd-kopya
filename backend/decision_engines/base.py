from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class DecisionRequest:
    """Karar motoruna iletilen standart istek."""

    engine_id: str
    symbol: str
    timeframe: str
    ohlcv: pd.DataFrame
    params: Optional[Dict[str, Any]] = None


@dataclass
class DecisionResult:
    """Karar motorunun ürettiği sonuç."""

    engine_id: str
    action: str
    confidence: float
    horizon_days: float
    expected_return: float
    stop_loss: float
    take_profit: float
    metadata: Dict[str, Any]


class BaseDecisionEngine:
    """Tüm karar motorları için temel sınıf."""

    engine_id: str = "BASE"

    def run(self, request: DecisionRequest) -> DecisionResult:  # pragma: no cover - soyut
        raise NotImplementedError

