from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd

from .registry import ENGINE_REGISTRY
from .base import DecisionRequest, DecisionResult
from .utils import action_to_score, zscore, winsorize01, daily_volatility
from .gate import detect_regime


@dataclass
class OrchestratorConfig:
    """Orkestrasyon için konfigürasyon."""

    weights_risk_on: Dict[str, float] = field(
        default_factory=lambda: {"KM1": 0.35, "KM2": 0.15, "KM3": 0.35, "KM4": 0.15}
    )
    weights_mixed: Dict[str, float] = field(
        default_factory=lambda: {"KM1": 0.30, "KM2": 0.30, "KM3": 0.30, "KM4": 0.10}
    )
    weights_risk_off: Dict[str, float] = field(
        default_factory=lambda: {"KM1": 0.15, "KM2": 0.45, "KM3": 0.30, "KM4": 0.10}
    )
    vol_target_annual: float = 0.15
    max_position_fraction: float = 0.02


def _pick_weights(cfg: OrchestratorConfig, regime_label: str) -> Dict[str, float]:
    if regime_label == "risk_on":
        return cfg.weights_risk_on
    if regime_label == "risk_off":
        return cfg.weights_risk_off
    return cfg.weights_mixed


def _normalized_weights(engine_ids: Sequence[str], raw_map: Dict[str, float]) -> np.ndarray:
    w = np.array([float(raw_map.get(e, 0.0)) for e in engine_ids], dtype=float)
    s = w.sum()
    if not np.isfinite(s) or s <= 1e-12:
        w = np.ones(len(engine_ids), dtype=float)
        s = float(len(engine_ids))
    return w / s


def _weighted_avg(values: Sequence[float], weights: np.ndarray) -> float:
    v = np.array([float(x) for x in values], dtype=float)
    ws = float(weights.sum())
    if not np.isfinite(ws) or ws <= 1e-12:
        return float(np.nanmean(v)) if len(v) else 0.0
    return float(np.average(v, weights=weights))


def build_consensus_result(
    symbol: str,
    timeframe: str,
    ohlcv: pd.DataFrame,
    engine_results: Dict[str, DecisionResult],
    cfg: OrchestratorConfig,
    account_value: float | None = None,
) -> Dict[str, Any]:
    """Motor çıktılarından rejim-ağırlıklı konsensüs kararı üret."""

    regime = detect_regime(ohlcv)
    ids: List[str] = list(engine_results.keys())
    weights = _normalized_weights(ids, _pick_weights(cfg, regime["label"]))

    raw_scores, confs, exp_rets = [], [], []
    for eid in ids:
        res = engine_results[eid]
        raw_scores.append(action_to_score(res.action) * float(res.confidence))
        confs.append(float(res.confidence))
        exp_rets.append(float(res.expected_return))
    raw_scores = winsorize01(np.array(raw_scores, dtype=float), 0.01)
    norm_scores = zscore(raw_scores)

    s_consensus = float((norm_scores * weights).sum()) if len(norm_scores) else 0.0
    exp_consensus = float((np.array(exp_rets) * weights).sum()) if len(exp_rets) else 0.0
    conf_consensus = float((np.array(confs) * weights).sum()) if len(confs) else 0.0

    label = "hold"
    if s_consensus > 0.15:
        label = "buy"
    elif s_consensus < -0.15:
        label = "sell"

    spread = float(np.nanstd(norm_scores)) if len(norm_scores) else 0.0
    conf_low = exp_consensus - spread * 0.5
    conf_high = exp_consensus + spread * 0.5

    dvol = daily_volatility(ohlcv)
    ann_vol = float(dvol * np.sqrt(252)) if dvol > 0 else 0.0
    frac = cfg.max_position_fraction
    if ann_vol > 0:
        frac = min(cfg.max_position_fraction, cfg.vol_target_annual / (ann_vol + 1e-8))
    if regime["label"] == "risk_off":
        frac *= 0.5
    if exp_consensus <= 0 and label == "buy":
        frac *= 0.5
    position_value = float(frac * (account_value or 0.0))

    rationale = [
        f"{eid}:{engine_results[eid].action}({engine_results[eid].confidence:.2f})"
        for eid in ids
    ]
    top_drivers = sorted(
        [
            (
                eid,
                abs(action_to_score(engine_results[eid].action))
                * engine_results[eid].confidence,
            )
            for eid in ids
        ],
        key=lambda x: x[1],
        reverse=True,
    )[:3]

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "regime": {
            "label": regime["label"],
            "trend_strength": regime["trend_strength"],
            "vol_pct": regime["vol_pct"],
        },
        "consensus": {
            "label": label,
            "score_raw": s_consensus,
            "expected_return": exp_consensus,
            "confidence": conf_consensus,
            "conf_int": [conf_low, conf_high],
            "horizon_days": _weighted_avg(
                [engine_results[e].horizon_days for e in ids], weights
            ),
            "position_fraction": frac,
            "position_value": position_value,
            "stop_loss": _weighted_avg(
                [engine_results[e].stop_loss for e in ids], weights
            ),
            "take_profit": _weighted_avg(
                [engine_results[e].take_profit for e in ids], weights
            ),
            "rationale": rationale,
            "top_drivers": [k for k, _ in top_drivers],
        },
        "engines": {eid: engine_results[eid].__dict__ for eid in ids},
    }

