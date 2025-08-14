from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np, pandas as pd


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().astype(float)
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema50"] = out["close"].ewm(span=50, adjust=False).mean()
    ema12 = out["close"].ewm(span=12, adjust=False).mean()
    ema26 = out["close"].ewm(span=26, adjust=False).mean()
    out["macd"] = ema12 - ema26
    out["macd_sig"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_sig"]
    delta = out["close"].diff()
    gain = (delta.clip(lower=0)).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / (loss + 1e-12)
    out["rsi14"] = 100 - (100 / (1 + rs))
    bb_p = 20
    bb_k = 2.0
    ma = out["close"].rolling(bb_p).mean()
    sd = out["close"].rolling(bb_p).std(ddof=0)
    out["bb_mid"], out["bb_up"], out["bb_dn"] = ma, ma + bb_k * sd, ma - bb_k * sd
    out["bb_width"] = (out["bb_up"] - out["bb_dn"]) / out["close"]
    prev_c = out["close"].shift(1)
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - prev_c).abs(),
            (out["low"] - prev_c).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr"] = tr.rolling(14).mean()
    return out.dropna()


class RegimeHMM:
    states = ("bull", "bear", "volatile", "range")

    def probs(self, last: pd.Series) -> Dict[str, float]:
        ema_spread = float((last["ema20"] - last["ema50"]) / (last["close"] + 1e-12))
        vola = float(last["atr"] / (last["close"] + 1e-12))
        bbw = float(last["bb_width"])
        s_bull = max(0.0, ema_spread)
        s_bear = max(0.0, -ema_spread)
        s_vol = max(0.0, vola - 0.02) + max(0.0, bbw - 0.04)
        s_rng = max(0.0, 0.04 - bbw)
        z = np.array([s_bull, s_bear, s_vol, s_rng]) + 1e-6
        z = z / z.sum()
        return dict(zip(self.states, z.tolist()))


@dataclass
class ModuleOutput:
    module: str
    direction: int
    edge: float
    prob: float
    horizon_days: int
    reasons: List[str]
    meta: Dict


def trend_module(
    df: pd.DataFrame, rp: Dict[str, float], params: Dict, cost_bps: int = 6
) -> Optional[ModuleOutput]:
    row = df.iloc[-1]
    spread = row["ema20"] - row["ema50"]
    direction = 1 if spread > 0 else (-1 if spread < 0 else 0)
    slope = (df["ema20"].iloc[-1] - df["ema20"].iloc[-5]) / 5
    prob = float(
        min(
            0.9,
            0.55
            + 0.20 * abs(spread / row["close"])
            + 0.10 * np.sign(direction) * np.sign(slope),
        )
    )
    gross_edge = abs(spread) / row["close"] * 0.8
    net_edge = float(gross_edge - cost_bps * 1e-4)
    return ModuleOutput(
        "trend", direction, max(0.0, net_edge), prob, 15, ["EMA20-EMA50", "slope"], {"rp": rp}
    )


def momentum_module(
    df: pd.DataFrame, rp: Dict[str, float], params: Dict, cost_bps: int = 6
) -> Optional[ModuleOutput]:
    row = df.iloc[-1]
    rsi = row["rsi14"]
    hist = row["macd_hist"]
    direction = 1 if (rsi > 50 and hist > 0) else (-1 if (rsi < 50 and hist < 0) else 0)
    prob = float(min(0.9, 0.50 + 0.25 * abs(hist) + 0.25 * abs(rsi - 50) / 50))
    gross_edge = (abs(hist) / (df["close"].rolling(26).std().iloc[-1] + 1e-8)) * 0.5
    net_edge = float(gross_edge - cost_bps * 1e-4)
    return ModuleOutput(
        "momentum", direction, max(0.0, net_edge), prob, 10, ["RSI", "MACD_hist"], {}
    )


def meanrev_module(
    df: pd.DataFrame, rp: Dict[str, float], params: Dict, cost_bps: int = 6
) -> Optional[ModuleOutput]:
    row = df.iloc[-1]
    z = (row["close"] - row["bb_mid"]) / ((row["bb_up"] - row["bb_mid"]) + 1e-8)
    direction = -1 if z > 1 else (1 if z < -1 else 0)
    prob = float(min(0.9, 0.5 + 0.3 * abs(z)))
    gross_edge = float(min(0.03, 0.5 * abs(z)))
    net_edge = float(max(0.0, gross_edge - cost_bps * 1e-4))
    return ModuleOutput("meanrev", direction, net_edge, prob, 7, ["BB_zscore"], {"z": float(z)})


class LinUCB:
    def __init__(self, d: int, alpha: float = 0.5, ridge: float = 1e-3):
        self.alpha = alpha
        import numpy as _np

        self.A = _np.eye(d) * ridge
        self.b = _np.zeros((d, 1))

    def weight(self, x: np.ndarray) -> Tuple[float, np.ndarray]:
        x = x.reshape(-1, 1)
        A_inv = np.linalg.pinv(self.A)
        theta = A_inv @ self.b
        mu = float((x.T @ theta).ravel())
        ucb = self.alpha * float(np.sqrt((x.T @ A_inv @ x).ravel()))
        return mu + ucb, theta.ravel()

    def update(self, x: np.ndarray, reward: float):
        x = x.reshape(-1, 1)
        self.A += x @ x.T
        self.b += reward * x


class Calibrator:
    def predict(self, y_raw: float) -> float:
        return float(max(0.0, min(1.0, y_raw)))


from collections import deque


class ConformalGate:
    def __init__(self, target_err: float = 0.10, window: int = 500):
        self.delta = target_err
        self.residuals = deque(maxlen=window)

    def thresholds(self) -> Tuple[float, float]:
        if len(self.residuals) < 50:
            return 0.02, -0.02
        q = float(np.quantile(np.array(self.residuals), 1 - self.delta))
        return q, -q

    def update(self, residual: float):
        self.residuals.append(float(residual))


def position_size(
    S: float,
    atr: float,
    price: float,
    target_vol: float = 0.02,
    maxRisk: float = 0.02,
    kelly_clip: float = 0.4,
    p: Optional[float] = None,
    b: Optional[float] = None,
) -> float:
    realized_vol = max(1e-8, atr / (price + 1e-8))
    conf_adj = 0.8 + 0.4 * min(abs(S), 1.0)
    vola_part = min(maxRisk, target_vol / realized_vol) * conf_adj
    kelly = 0.0
    if p is not None and b is not None and b > 0:
        kelly = max(0.0, min(kelly_clip, (p * b - (1 - p)) / b))
    return float(min(maxRisk, vola_part + kelly * maxRisk))


class DRAKSEngine:
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.regime = RegimeHMM()
        self.conformal = ConformalGate(
            cfg.get("thresholds", {}).get("target_error_rate", 0.10)
        )
        self.calibrators: Dict[str, Calibrator] = {}
        self.bandits: Dict[str, LinUCB] = {}

    def context_vec(self, df: pd.DataFrame, rp: Dict[str, float]) -> np.ndarray:
        row = df.iloc[-1]
        vola = float(row["atr"] / (row["close"] + 1e-8))
        bbw = float(row["bb_width"])
        return np.array(
            [
                rp.get("bull", 0),
                rp.get("bear", 0),
                rp.get("volatile", 0),
                rp.get("range", 0),
                vola,
                bbw,
            ],
            dtype=float,
        )

    def _bandit_score(self, module: str, x: np.ndarray) -> float:
        b = self.bandits.setdefault(
            module,
            LinUCB(
                d=len(x),
                alpha=self.cfg.get("bandit", {}).get("alpha", 0.5),
                ridge=self.cfg.get("bandit", {}).get("ridge", 1e-3),
            ),
        )
        score, _ = b.weight(x)
        return float(score)

    def run(self, raw_df: pd.DataFrame, symbol: str) -> Dict:
        df = compute_features(raw_df)
        row = df.iloc[-1]
        rp = self.regime.probs(row)
        outputs: List[Tuple[str, ModuleOutput, float]] = []
        for name, fn in [
            ("trend", trend_module),
            ("momentum", momentum_module),
            ("meanrev", meanrev_module),
        ]:
            out = fn(df, rp, params={}, cost_bps=self.cfg.get("cost_bps", 6))
            if not out:
                continue
            cal = self.calibrators.setdefault(name, Calibrator())
            prob_cal = cal.predict(out.prob)
            outputs.append((name, out, prob_cal))
        x = self.context_vec(df, rp)
        logits = {name: self._bandit_score(name, x) for name, _, _ in outputs}
        if not logits:
            return {"symbol": symbol, "decision": "HOLD", "score": 0.0}
        z = np.array(list(logits.values()))
        w = np.exp(z - z.max())
        w = w / w.sum() if w.sum() > 0 else np.ones_like(z) / len(z)
        weights = {list(logits.keys())[i]: float(w[i]) for i in range(len(w))}
        S = 0.0
        reasons = []
        for name, out, pcal in outputs:
            contrib = weights[name] * out.direction * out.edge * (0.5 + 0.5 * pcal)
            S += contrib
            reasons += out.reasons
        tau_buy, tau_sell = self.conformal.thresholds()
        decision_dir = 0
        if S > tau_buy:
            decision_dir = +1
        elif S < tau_sell:
            decision_dir = -1
        atr = float(row["atr"])
        price = float(row["close"])
        pos_pct = position_size(
            S,
            atr,
            price,
            target_vol=self.cfg.get("risk", {}).get("target_vol", 0.02),
            maxRisk=self.cfg.get("risk", {}).get("max_risk_pct", 0.02),
            kelly_clip=self.cfg.get("risk", {}).get("kelly_clip", 0.4),
            p=max(0.01, min(0.99, 0.5 + 0.5 * abs(S))),
            b=1.5,
        )
        kst = self.cfg.get("risk", {}).get("atr_stop", [1.0, 1.8])
        ktp = self.cfg.get("risk", {}).get("atr_tp", [1.5, 2.5])
        mult = 1 if decision_dir == +1 else -1
        stop = price - mult * kst[0] * atr
        tp = price + mult * ktp[0] * atr
        return {
            "symbol": symbol,
            "timeframe": self.cfg.get("timeframe", "1h"),
            "decision": ["SHORT", "HOLD", "LONG"][decision_dir + 1],
            "direction": decision_dir,
            "score": float(S),
            "position_pct": float(pos_pct),
            "stop": float(stop),
            "take_profit": float(tp),
            "horizon_days": 15,
            "regime_probs": rp,
            "weights": weights,
            "reasons": reasons[:8],
        }

